"""Reminders and escalation, plus the in-app Outbox.

Rules for every open NC with a target date (days_left = target_date - today):
  days_left == 3   -> [T-3]  reminder to the auditee
  days_left == 0   -> [DUE]  reminder to the auditee
  overdue >= 1     -> [L1]   escalation to the NC's auditor
  overdue >= N     -> [L2]   escalation to the Auditing Head   (N = l2_after_days, default 7)
Each (NC, recipient, level) is sent once, so running it again never duplicates.

POST /api/jobs/escalate       manual "Run now" (Auditing Head / admin), supports dry_run
GET  /api/jobs/escalate/cron  for Vercel Cron (Authorization: Bearer $CRON_SECRET)
GET  /api/outbox              notification list (auditees see only their own)
"""
from __future__ import annotations

import os
import secrets
from datetime import date, datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import models as m
from app.auth import get_current_user
from app.db import get_db
from app.services.events import log_event

router = APIRouter(prefix="/api", tags=["jobs"])


def _key(nc_id: Optional[str], to_user_id: int, subject: str) -> tuple:
    return (nc_id, to_user_id, subject.split("]")[0])  # "[L1" etc.


def run_escalation(db: Session, today: date, l2_after_days: int = 7, dry_run: bool = False) -> dict:
    ncs = db.execute(
        select(m.NC.id, m.NC.title, m.NC.target_date, m.NC.auditee_id, m.NC.auditor_id)
        .where(m.NC.status != "CLOSED", m.NC.target_date.is_not(None))
    ).all()
    head = db.scalars(select(m.User).where(m.User.role == "auditing_head").order_by(m.User.id)).first()
    existing = {_key(r.nc_id, r.to_user_id, r.subject)
                for r in db.execute(select(m.Notification.nc_id, m.Notification.to_user_id, m.Notification.subject)).all()}

    created = {"T-3": 0, "DUE": 0, "L1": 0, "L2": 0}
    skipped = 0
    new_rows: list[m.Notification] = []

    def add(tag: str, kind: str, to_user: Optional[int], nc, subject_tail: str, body: str) -> None:
        nonlocal skipped
        if to_user is None:
            return
        subject = f"[{tag}] {nc.id}: {subject_tail}"
        if _key(nc.id, to_user, subject) in existing:
            skipped += 1
            return
        existing.add(_key(nc.id, to_user, subject))
        created[tag] += 1
        new_rows.append(m.Notification(to_user_id=to_user, kind=kind, subject=subject, body=body, nc_id=nc.id))

    for nc in ncs:
        days_left = (nc.target_date - today).days
        overdue = -days_left
        if days_left == 3:
            add("T-3", "reminder", nc.auditee_id, nc, "due in 3 days",
                f"'{nc.title}' is due on {nc.target_date}. Please complete the action plan and evidence.")
        elif days_left == 0:
            add("DUE", "reminder", nc.auditee_id, nc, "due today",
                f"'{nc.title}' is due today ({nc.target_date}).")
        if overdue >= 1:
            add("L1", "escalation_l1", nc.auditor_id, nc, f"overdue by {overdue} day(s)",
                f"'{nc.title}' passed its target date ({nc.target_date}). Please follow up with the auditee.")
        if overdue >= l2_after_days:
            add("L2", "escalation_l2", head.id if head else None, nc, f"overdue by {overdue} days",
                f"'{nc.title}' is {overdue} days overdue (target {nc.target_date}). Escalated to the Auditing Head.")

    if not dry_run and new_rows:
        db.add_all(new_rows)
        db.commit()
    return {"dry_run": dry_run, "today": today.isoformat(), "l2_after_days": l2_after_days,
            "created": created, "total_created": sum(created.values()), "skipped_existing": skipped}


@router.post("/jobs/escalate")
def escalate_now(
    dry_run: bool = False, l2_after_days: int = Query(7, ge=1, le=60),
    db: Session = Depends(get_db), user: m.User = Depends(get_current_user),
) -> dict:
    if user.role not in ("auditing_head", "admin"):
        raise HTTPException(403, "only the Auditing Head or admin can run escalation")
    result = run_escalation(db, datetime.now(timezone.utc).date(), l2_after_days, dry_run)
    if not dry_run:
        log_event(db, "escalation.run", user.id, {"created": result["created"]})
        db.commit()
    return result


@router.get("/jobs/escalate/cron")
def escalate_cron(authorization: str | None = Header(default=None), db: Session = Depends(get_db)) -> dict:
    secret = os.environ.get("CRON_SECRET")
    if not secret:
        raise HTTPException(503, "CRON_SECRET is not configured")
    if not authorization or not secrets.compare_digest(authorization, f"Bearer {secret}"):
        raise HTTPException(401, "invalid cron secret")
    result = run_escalation(db, datetime.now(timezone.utc).date())
    log_event(db, "escalation.cron", None, {"created": result["created"]})
    db.commit()
    return result


@router.get("/outbox")
def outbox(
    kind: Optional[str] = None, nc_id: Optional[str] = None,
    limit: int = Query(50, le=200), offset: int = 0,
    db: Session = Depends(get_db), user: m.User = Depends(get_current_user),
) -> dict:
    stmt = select(m.Notification, m.User.name).join(m.User, m.User.id == m.Notification.to_user_id)
    if user.role == "auditee":
        stmt = stmt.where(m.Notification.to_user_id == user.id)
    if kind:
        stmt = stmt.where(m.Notification.kind == kind)
    if nc_id:
        stmt = stmt.where(m.Notification.nc_id == nc_id)
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = db.execute(stmt.order_by(m.Notification.id.desc()).limit(limit).offset(offset)).all()
    return {"total": total, "items": [
        {"id": n.id, "to_user_id": n.to_user_id, "to_name": name, "kind": n.kind, "subject": n.subject,
         "body": n.body, "nc_id": n.nc_id, "sent_at": n.sent_at.isoformat() if n.sent_at else None}
        for n, name in rows
    ]}
