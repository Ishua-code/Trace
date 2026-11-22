"""GET /api/audit-log: list of hash-chained events (read-only), newest first."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import models as m
from app.auth import get_current_user
from app.db import get_db

router = APIRouter(prefix="/api", tags=["audit-log"])


@router.get("/audit-log")
def audit_log(
    event_type: Optional[str] = None,
    nc_id: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user: m.User = Depends(get_current_user),
) -> dict:
    stmt = select(m.EventLog, m.User.name).join(m.User, m.User.id == m.EventLog.actor_id, isouter=True)
    if event_type:
        stmt = stmt.where(m.EventLog.event_type == event_type)
    if nc_id:
        stmt = stmt.where(m.EventLog.payload["nc_id"].astext == nc_id)
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = db.execute(stmt.order_by(m.EventLog.index.desc()).limit(limit).offset(offset)).all()
    return {
        "total": total,
        "items": [
            {
                "index": e.index, "event_type": e.event_type, "actor_id": e.actor_id,
                "actor_name": name, "payload": e.payload,
                "prev_hash": e.prev_hash, "hash": e.hash,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e, name in rows
        ],
    }
