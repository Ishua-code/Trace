"""GET /api/kpis/overview: every number is computed from the database, never stored."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import models as m
from app.auth import get_current_user
from app.contracts import AgeingBuckets, KPIOverview, PersonStatus
from app.db import get_db

router = APIRouter(prefix="/api/kpis", tags=["kpis"])


def _pct(a: int, b: int) -> float:
    return round(100.0 * a / b, 1) if b else 0.0


@router.get("/overview", response_model=KPIOverview)
def overview(db: Session = Depends(get_db), user: m.User = Depends(get_current_user)) -> KPIOverview:
    now = datetime.now(timezone.utc)
    today = now.date()
    rows = db.execute(select(
        m.NC.status, m.NC.raised_at, m.NC.target_date, m.NC.closed_at, m.NC.auditee_id, m.NC.auditor_id
    )).all()

    open_rows = [r for r in rows if r.status != "CLOSED"]
    closed = [r for r in rows if r.status == "CLOSED" and r.closed_at is not None]
    overdue = [r for r in open_rows if r.target_date and r.target_date < today]

    with_target = [r for r in closed if r.target_date]
    on_time = [r for r in with_target if r.closed_at.date() <= r.target_date]
    lead = [(r.closed_at - r.raised_at).total_seconds() / 86400 for r in closed]

    buckets = {"d0_7": 0, "d8_14": 0, "d15_30": 0, "d30_plus": 0}
    for r in open_rows:
        age = (now - r.raised_at).days
        key = "d0_7" if age <= 7 else "d8_14" if age <= 14 else "d15_30" if age <= 30 else "d30_plus"
        buckets[key] += 1

    slots_total = db.scalar(select(func.count()).select_from(m.AuditSlot)) or 0
    slots_done = db.scalar(select(func.count()).select_from(m.AuditSlot).where(m.AuditSlot.completed.is_(True))) or 0

    def people(role: str, field: str) -> list[PersonStatus]:
        out = []
        for u in db.scalars(select(m.User).where(m.User.role == role).order_by(m.User.id)).all():
            mine = [r for r in rows if getattr(r, field) == u.id]
            mine_open = [r for r in mine if r.status != "CLOSED"]
            out.append(PersonStatus(
                user_id=u.id, name=u.name, open=len(mine_open),
                overdue=len([r for r in mine_open if r.target_date and r.target_date < today]),
                closed=len(mine) - len(mine_open),
            ))
        return out

    return KPIOverview(
        plan_vs_completed_pct=_pct(slots_done, slots_total),
        open_count=len(open_rows), overdue_count=len(overdue), closed_count=len(rows) - len(open_rows),
        on_time_closure_pct=_pct(len(on_time), len(with_target)),
        avg_closure_lead_days=round(sum(lead) / len(lead), 1) if lead else 0.0,
        ageing=AgeingBuckets(**buckets),
        pending_approvals=len([r for r in rows if r.status == "PENDING_HEAD_APPROVAL"]),
        auditors=people("auditor", "auditor_id"), auditees=people("auditee", "auditee_id"),
    )
