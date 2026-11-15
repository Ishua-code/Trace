"""Hash-chained event log: hash = sha256(prev_hash + canonical(event_type, actor, payload, created_at))."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app import models as m

GENESIS = "0" * 64
_LOCK_KEY = 70415  # arbitrary constant for the advisory lock


def _ts(dt: datetime) -> str:
    """Fixed-format UTC timestamp so write and verify hash the same string."""
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt.strftime("%Y-%m-%dT%H:%M:%S.%f")


def _hash(prev: str, event_type: str, actor_id: int | None, payload: dict[str, Any], created_at: datetime) -> str:
    body = json.dumps(
        {"event_type": event_type, "actor": actor_id, "payload": payload, "created_at": _ts(created_at)},
        sort_keys=True, separators=(",", ":"), default=str,
    )
    return hashlib.sha256((prev + body).encode("utf-8")).hexdigest()


def log_event(db: Session, event_type: str, actor_id: int | None, payload: dict[str, Any]) -> m.EventLog:
    """Append an event. Call before db.commit() so it shares the transaction with the change."""
    db.execute(text("SELECT pg_advisory_xact_lock(:k)"), {"k": _LOCK_KEY})  # one writer at a time
    last = db.execute(select(m.EventLog).order_by(m.EventLog.index.desc()).limit(1)).scalar_one_or_none()
    prev = last.hash if last else GENESIS
    now = datetime.now(timezone.utc)
    row = m.EventLog(
        event_type=event_type, actor_id=actor_id, payload=payload,
        prev_hash=prev, hash=_hash(prev, event_type, actor_id, payload, now), created_at=now,
    )
    db.add(row)
    db.flush()
    return row


def verify_chain(db: Session) -> dict[str, Any]:
    prev = GENESIS
    count = 0
    for row in db.execute(select(m.EventLog).order_by(m.EventLog.index)).scalars():
        expected = _hash(prev, row.event_type, row.actor_id, row.payload, row.created_at)
        if row.prev_hash != prev or row.hash != expected:
            return {"valid": False, "checked": count, "broken_at_index": row.index}
        prev = row.hash
        count += 1
    return {"valid": True, "checked": count, "broken_at_index": None}