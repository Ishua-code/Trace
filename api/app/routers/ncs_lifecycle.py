"""NC lifecycle: create (auto-assign), list, detail, action plan, evidence, auditor verify/reject."""
from __future__ import annotations

import re
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app import models as m
from app.auth import get_current_user
from app.contracts import NC, ClosureReport
from app.db import get_db
from app.engine import taxonomy as tax
from app.pg_store import PostgresStore, _to
from app.services.events import log_event
from app.trace_hooks import reindex_nc

router = APIRouter(prefix="/api/ncs", tags=["ncs-lifecycle"])

TARGET_DAYS = {"critical": 3, "major": 7, "minor": 14}
STAFF = ("admin", "auditing_head", "auditor")


def _need(user: m.User, *roles: str) -> None:
    if user.role not in roles:
        raise HTTPException(403, f"role '{user.role}' cannot do this")


def _get_nc(db: Session, nc_id: str) -> m.NC:
    nc = db.get(m.NC, nc_id)
    if nc is None:
        raise HTTPException(404, "NC not found")
    return nc


def _own_or_staff(user: m.User, nc: m.NC) -> None:
    if user.role == "auditee" and nc.auditee_id != user.id:
        raise HTTPException(403, "not your NC")


def _next_id(db: Session) -> str:
    nums = [int(re.sub(r"\D", "", i) or 0) for i in db.scalars(select(m.NC.id)).all()]
    return f"NC-{(max(nums) if nums else 0) + 1:04d}"


# ---------------------------------------------------------------- create
class NCCreate(BaseModel):
    title: str = Field(min_length=3)
    description: str = Field(min_length=3)
    severity: str = Field(pattern="^(minor|major|critical)$")
    product: str
    process: str
    line: Optional[str] = None
    audit_type: str = Field(default="product", pattern="^(product|revalidation)$")
    machine: Optional[str] = None
    lot: Optional[str] = None
    defect_code: Optional[str] = None


@router.post("", status_code=201)
def create_nc(body: NCCreate, db: Session = Depends(get_db), user: m.User = Depends(get_current_user)) -> dict:
    _need(user, *STAFF)
    errors = tax.validate_fields(product=body.product, line=body.line, process=body.process,
                                 defect_code=body.defect_code)
    if errors:
        raise HTTPException(422, errors)
    now = datetime.now(timezone.utc)
    owner = db.get(m.ProcessOwner, body.process)
    nc = m.NC(
        id=_next_id(db), audit_type=body.audit_type, title=body.title, description=body.description,
        severity=body.severity, product=body.product, process=body.process, line=body.line,
        department_id=tax.PROCESS_DEPARTMENT[body.process], machine=body.machine, lot=body.lot,
        defect_code=body.defect_code, status="ASSIGNED" if owner else "OPEN",
        auditee_id=owner.auditee_id if owner else None,
        auditor_id=user.id if user.role == "auditor" else None,
        raised_at=now, target_date=(now + timedelta(days=TARGET_DAYS[body.severity])).date(),
    )
    db.add(nc)
    log_event(db, "nc.created", user.id, {"nc_id": nc.id, "auditee_id": nc.auditee_id})
    db.commit()
    reindex_nc(db, nc.id)  # links to related NCs; never breaks the workflow
    return _to(NC, nc).model_dump(mode="json")


# ---------------------------------------------------------------- list + detail
@router.get("")
def list_ncs(
    status: Optional[str] = None, process: Optional[str] = None, severity: Optional[str] = None,
    q: Optional[str] = None, limit: int = Query(50, le=200), offset: int = 0,
    db: Session = Depends(get_db), user: m.User = Depends(get_current_user),
) -> dict:
    stmt = select(m.NC)
    if user.role == "auditee":
        stmt = stmt.where(m.NC.auditee_id == user.id)
    if status:
        stmt = stmt.where(m.NC.status == status)
    if process:
        stmt = stmt.where(m.NC.process == process)
    if severity:
        stmt = stmt.where(m.NC.severity == severity)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(m.NC.title.ilike(like), m.NC.description.ilike(like), m.NC.id.ilike(like)))
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = db.scalars(stmt.order_by(m.NC.raised_at.desc()).limit(limit).offset(offset)).all()
    return {"total": total, "items": [_to(NC, r).model_dump(mode="json") for r in rows]}


@router.get("/{nc_id}")
def nc_detail(nc_id: str, db: Session = Depends(get_db), user: m.User = Depends(get_current_user)) -> dict:
    nc = _get_nc(db, nc_id)
    _own_or_staff(user, nc)
    store = PostgresStore(db)
    closure = db.scalars(
        select(m.ClosureReport).where(m.ClosureReport.nc_id == nc_id).order_by(m.ClosureReport.id.desc())
    ).first()
    tasks = []
    if closure:
        tasks = db.scalars(
            select(m.VerificationTask).where(m.VerificationTask.closure_report_id == closure.id)
            .order_by(m.VerificationTask.priority, m.VerificationTask.id)
        ).all()
    return {
        "nc": _to(NC, nc).model_dump(mode="json"),
        "actions": [a.model_dump(mode="json") for a in store.get_actions(nc_id)],
        "evidence": [e.model_dump(mode="json") for e in store.get_evidence(nc_id)],
        "verifications": [v.model_dump(mode="json") for v in store.get_verifications(nc_id)],
        "links": [l.model_dump(mode="json") for l in store.get_links(nc_id)],
        "closure": None if closure is None else {
            "id": closure.id, "verdict": closure.verdict, "findings": closure.findings,
            "generated_at": closure.generated_at.isoformat(),
            "tasks": [{"id": t.id, "title": t.title, "priority": t.priority,
                       "suggested_owner_role": t.suggested_owner_role, "done": t.done} for t in tasks],
        },
    }


# ---------------------------------------------------------------- action plan
class ActionPlanIn(BaseModel):
    root_cause_category: str
    corrective_action: str = Field(min_length=3)
    preventive_action: Optional[str] = None
    target_date: date
    applies_to_lines: Optional[list[str]] = None


@router.post("/{nc_id}/action-plan", status_code=201)
def add_action_plan(nc_id: str, body: ActionPlanIn, db: Session = Depends(get_db),
                    user: m.User = Depends(get_current_user)) -> dict:
    nc = _get_nc(db, nc_id)
    _own_or_staff(user, nc)
    if user.role == "auditor":
        raise HTTPException(403, "auditors do not write action plans")
    if body.root_cause_category not in tax.ROOT_CAUSE_CATEGORIES:
        raise HTTPException(422, f"unknown root cause: {body.root_cause_category}")
    if nc.status not in ("ASSIGNED", "ACTION_PLANNED", "REJECTED", "REOPENED"):
        raise HTTPException(409, f"cannot add an action plan while NC is {nc.status}")
    plan = m.ActionPlan(
        nc_id=nc_id, root_cause_category=body.root_cause_category,
        corrective_action=body.corrective_action, preventive_action=body.preventive_action,
        owner_id=user.id, target_date=body.target_date, applies_to_lines=body.applies_to_lines,
    )
    db.add(plan)
    nc.root_cause_category = body.root_cause_category
    old, nc.status = nc.status, "ACTION_PLANNED"
    log_event(db, "nc.action_plan_added", user.id, {"nc_id": nc_id, "from": old})
    db.commit()
    reindex_nc(db, nc_id)
    return {"id": plan.id, "nc_id": nc_id, "status": nc.status}


# ---------------------------------------------------------------- evidence
class EvidenceIn(BaseModel):
    file_name: str = Field(min_length=1)
    file_url: str = Field(min_length=1)
    has_before_after: bool = False


@router.post("/{nc_id}/evidence", status_code=201)
def add_evidence(nc_id: str, body: EvidenceIn, db: Session = Depends(get_db),
                 user: m.User = Depends(get_current_user)) -> dict:
    nc = _get_nc(db, nc_id)
    _own_or_staff(user, nc)
    if user.role == "auditor":
        raise HTTPException(403, "auditors do not upload evidence")
    if nc.status not in ("ACTION_PLANNED", "IN_PROGRESS", "REJECTED", "REOPENED"):
        raise HTTPException(409, f"cannot add evidence while NC is {nc.status}")
    has_plan = db.scalar(select(func.count()).select_from(m.ActionPlan).where(m.ActionPlan.nc_id == nc_id))
    if not has_plan:
        raise HTTPException(409, "add an action plan first")
    ev = m.Evidence(nc_id=nc_id, file_url=body.file_url, file_name=body.file_name,
                    uploaded_by=user.id, has_before_after=body.has_before_after)
    db.add(ev)
    old, nc.status = nc.status, "EVIDENCE_SUBMITTED"
    log_event(db, "nc.evidence_submitted", user.id, {"nc_id": nc_id, "from": old, "file": body.file_name})
    db.commit()
    return {"id": ev.id, "nc_id": nc_id, "status": nc.status}


# ---------------------------------------------------------------- auditor verify / reject
class VerifyIn(BaseModel):
    accepted: bool
    comment: Optional[str] = None


@router.post("/{nc_id}/verify")
def verify(nc_id: str, body: VerifyIn, db: Session = Depends(get_db),
           user: m.User = Depends(get_current_user)) -> dict:
    _need(user, *STAFF)
    nc = _get_nc(db, nc_id)
    if nc.status != "EVIDENCE_SUBMITTED":
        raise HTTPException(409, f"NC must be EVIDENCE_SUBMITTED, it is {nc.status}")
    if not body.accepted and not (body.comment and body.comment.strip()):
        raise HTTPException(422, "a rejection needs a comment")
    db.add(m.Verification(nc_id=nc_id, auditor_id=user.id, accepted=body.accepted, comment=body.comment))
    nc.status = "AUDITOR_VERIFIED" if body.accepted else "REJECTED"
    log_event(db, "nc.verified" if body.accepted else "nc.rejected", user.id,
              {"nc_id": nc_id, "accepted": body.accepted})
    db.commit()
    return {"id": nc_id, "status": nc.status}
