"""Closure Gate: TRACE simulates the closure, the Head decides.

Head may approve only if verdict is CLEAR, or every verification task is done,
or a typed justification (override) is given. Every decision goes to the hash-chained event log.
"""
from __future__ import annotations

from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models as m
from app.auth import get_current_user
from app.db import get_db
from app.services.events import log_event
from app.trace_hooks import get_engine

router = APIRouter(prefix="/api", tags=["closure"])

GATE_STATES = ("AUDITOR_VERIFIED", "TRACE_REVIEW", "PENDING_HEAD_APPROVAL")


def _nc(db: Session, nc_id: str) -> m.NC:
    nc = db.get(m.NC, nc_id)
    if nc is None:
        raise HTTPException(404, "NC not found")
    return nc


def _latest_report(db: Session, nc_id: str) -> Optional[m.ClosureReport]:
    return db.scalars(
        select(m.ClosureReport).where(m.ClosureReport.nc_id == nc_id).order_by(m.ClosureReport.id.desc())
    ).first()


def _tasks(db: Session, report_id: int) -> list[m.VerificationTask]:
    return list(db.scalars(
        select(m.VerificationTask).where(m.VerificationTask.closure_report_id == report_id)
        .order_by(m.VerificationTask.priority, m.VerificationTask.id)
    ).all())


def _report_json(rep: m.ClosureReport, tasks: list[m.VerificationTask]) -> dict:
    return {
        "id": rep.id, "nc_id": rep.nc_id, "verdict": rep.verdict, "findings": rep.findings,
        "generated_at": rep.generated_at.isoformat() if rep.generated_at else None,
        "tasks": [{"id": t.id, "title": t.title, "priority": t.priority,
                   "suggested_owner_role": t.suggested_owner_role, "done": t.done} for t in tasks],
    }


@router.post("/ncs/{nc_id}/closure/simulate")
def simulate(nc_id: str, db: Session = Depends(get_db), user: m.User = Depends(get_current_user)) -> dict:
    if user.role not in ("admin", "auditing_head", "auditor"):
        raise HTTPException(403, "only audit staff can run the closure simulation")
    nc = _nc(db, nc_id)
    if nc.status not in GATE_STATES:
        raise HTTPException(409, f"NC must be auditor-verified first, it is {nc.status}")
    try:
        result = get_engine(db).simulate_closure(nc_id)
    except NotImplementedError:
        raise HTTPException(503, "TRACE closure simulation is not available in this build yet")

    findings = [f.model_dump(mode="json") for f in result.findings]
    rep = _latest_report(db, nc_id)
    if rep is None:  # tasks are generated once per closure report; later runs only update the verdict
        rep = m.ClosureReport(nc_id=nc_id, verdict=result.verdict.value, findings=findings)
        db.add(rep)
        db.flush()
        for t in result.tasks:
            db.add(m.VerificationTask(
                closure_report_id=rep.id, nc_id=nc_id, title=t.title, priority=t.priority,
                suggested_owner_role=t.suggested_owner_role.value, done=False,
            ))
    else:
        rep.verdict = result.verdict.value
        rep.findings = findings
    nc.status = "PENDING_HEAD_APPROVAL"
    log_event(db, "closure.simulated", user.id, {"nc_id": nc_id, "verdict": rep.verdict, "findings": len(findings)})
    db.commit()
    db.refresh(rep)
    return _report_json(rep, _tasks(db, rep.id))


@router.get("/ncs/{nc_id}/closure")
def get_closure(nc_id: str, db: Session = Depends(get_db), user: m.User = Depends(get_current_user)) -> dict:
    _nc(db, nc_id)
    rep = _latest_report(db, nc_id)
    if rep is None:
        raise HTTPException(404, "no closure report yet")
    return _report_json(rep, _tasks(db, rep.id))


class TaskPatch(BaseModel):
    done: bool


@router.patch("/tasks/{task_id}")
def patch_task(task_id: int, body: TaskPatch, db: Session = Depends(get_db),
               user: m.User = Depends(get_current_user)) -> dict:
    task = db.get(m.VerificationTask, task_id)
    if task is None:
        raise HTTPException(404, "task not found")
    task.done = body.done
    log_event(db, "task.done" if body.done else "task.reopened", user.id, {"task_id": task_id, "nc_id": task.nc_id})
    db.commit()
    return {"id": task.id, "done": task.done}


class DecisionIn(BaseModel):
    decision: Literal["approve", "send_back", "override"]
    justification: Optional[str] = None


@router.post("/ncs/{nc_id}/closure/decision")
def decide(nc_id: str, body: DecisionIn, db: Session = Depends(get_db),
           user: m.User = Depends(get_current_user)) -> dict:
    if user.role not in ("auditing_head", "admin"):
        raise HTTPException(403, "only the Auditing Head can decide")
    nc = _nc(db, nc_id)
    if nc.status != "PENDING_HEAD_APPROVAL":
        raise HTTPException(409, f"NC is {nc.status}, not waiting for approval")
    rep = _latest_report(db, nc_id)
    if rep is None:
        raise HTTPException(409, "run the closure simulation first")
    tasks = _tasks(db, rep.id)
    open_tasks = [t for t in tasks if not t.done]
    text = (body.justification or "").strip()

    if body.decision == "send_back":
        if not text:
            raise HTTPException(422, "sending back needs a reason")
        nc.status, decision = "REOPENED", "send_back"
    else:
        gate_clear = rep.verdict == "CLEAR" or not open_tasks
        if body.decision == "approve" and not gate_clear:
            raise HTTPException(409, f"gate is {rep.verdict} with {len(open_tasks)} open verification task(s); "
                                     "complete them or use decision 'override' with a justification")
        if body.decision == "override" and len(text) < 15:
            raise HTTPException(422, "an override needs a typed justification (at least 15 characters)")
        decision = "approve" if gate_clear and body.decision == "approve" else "override"
        nc.status = "CLOSED"
        from datetime import datetime, timezone
        nc.closed_at = datetime.now(timezone.utc)

    approval = m.Approval(nc_id=nc_id, head_id=user.id, decision=decision,
                          justification=text or None, closure_report_id=rep.id)
    db.add(approval)
    log_event(db, f"closure.{decision}", user.id, {
        "nc_id": nc_id, "verdict": rep.verdict, "open_tasks": len(open_tasks), "justification": text or None,
    })
    db.commit()
    return {"id": nc_id, "status": nc.status, "decision": decision, "verdict": rep.verdict,
            "open_tasks": len(open_tasks)}
