"""NC state machine: which status can move to which, and who may do it."""
from __future__ import annotations

from fastapi import HTTPException

A, H, U, E = "admin", "auditing_head", "auditor", "auditee"

# (from, to) -> roles allowed. Admin may do any legal move.
TRANSITIONS: dict[tuple[str, str], tuple[str, ...]] = {
    ("OPEN", "ASSIGNED"): (H, A),
    ("ASSIGNED", "ACTION_PLANNED"): (E, A),
    ("ACTION_PLANNED", "IN_PROGRESS"): (E, A),
    ("IN_PROGRESS", "EVIDENCE_SUBMITTED"): (E, A),
    ("EVIDENCE_SUBMITTED", "AUDITOR_VERIFIED"): (U, A),
    ("EVIDENCE_SUBMITTED", "REJECTED"): (U, A),
    ("REJECTED", "IN_PROGRESS"): (E, A),
    ("AUDITOR_VERIFIED", "TRACE_REVIEW"): (U, H, A),
    ("TRACE_REVIEW", "PENDING_HEAD_APPROVAL"): (U, H, A),
    ("PENDING_HEAD_APPROVAL", "CLOSED"): (H, A),   # M2: only via Closure Gate
    ("PENDING_HEAD_APPROVAL", "REJECTED"): (H, A),
    ("CLOSED", "REOPENED"): (H, U, A),
    ("REOPENED", "ASSIGNED"): (H, A),
}


def check_transition(current: str, new: str, role: str) -> None:
    allowed = TRANSITIONS.get((current, new))
    if allowed is None:
        raise HTTPException(409, f"illegal transition {current} -> {new}")
    if role not in allowed:
        raise HTTPException(403, f"role {role} cannot move {current} -> {new}")


def next_states(current: str) -> list[str]:
    return [b for (a, b) in TRANSITIONS if a == current]