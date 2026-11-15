"""Load Hanu's seed bundle (seed.generate.generate()) into Postgres.

reset_and_load() wipes every app table, then inserts:
departments (taxonomy) -> users (demo personas + placeholder ids found in the bundle)
-> process_owners -> ncs -> action_plans (+ scope) -> evidence -> verifications -> links (if present).
"""
from __future__ import annotations

from enum import Enum
from typing import Any

from sqlalchemy import insert, text
from sqlalchemy.orm import Session

from app import models as m
from app.db import Base
from app.engine import taxonomy as tax

ADMIN_ID, HEAD_ID = 1, 2  # fixed demo personas; seed placeholder ids start at 101


def _plain(obj) -> dict[str, Any]:
    """Contract object -> dict with enums turned into plain strings."""
    d = obj.model_dump()
    return {k: (v.value if isinstance(v, Enum) else v) for k, v in d.items()}


def _wipe(db: Session) -> None:
    names = ", ".join(f'"{t.name}"' for t in Base.metadata.sorted_tables)
    db.execute(text(f"TRUNCATE TABLE {names} RESTART IDENTITY CASCADE"))


def _fix_sequences(db: Session) -> None:
    """Explicit ids were inserted, so move each id sequence past the max id."""
    for t in Base.metadata.sorted_tables:
        if "id" in t.c and t.c.id.type.python_type is int:
            db.execute(text(
                f"SELECT setval(pg_get_serial_sequence('\"{t.name}\"', 'id'), "
                f"COALESCE((SELECT MAX(id) FROM \"{t.name}\"), 0) + 1, false)"
            ))


def reset_and_load(db: Session, data: dict[str, Any]) -> dict[str, int]:
    ncs = list(data["ncs"])
    plans = list(data.get("action_plans", []))
    evidence = list(data.get("evidence", []))
    verifs = list(data.get("verifications", []))
    scope: dict[str, list[str]] = data.get("action_scope") or {}

    _wipe(db)

    # ---- departments
    db.execute(insert(m.Department), [{"id": i, "name": n} for i, n in tax.DEPARTMENTS.items()])

    # ---- users: personas + every placeholder id referenced by the bundle
    users: dict[int, dict] = {
        ADMIN_ID: dict(id=ADMIN_ID, name="Demo Admin", email="admin@trace.demo", role="admin", department_id=None),
        HEAD_ID: dict(id=HEAD_ID, name="Demo Auditing Head", email="head@trace.demo", role="auditing_head", department_id=6),
    }
    auditor_ids = {n.auditor_id for n in ncs if n.auditor_id} | {v.auditor_id for v in verifs}
    auditee_dept: dict[int, int] = {}
    for n in ncs:
        if n.auditee_id:
            auditee_dept.setdefault(n.auditee_id, n.department_id)
    referenced = (
        auditor_ids | set(auditee_dept)
        | {p.owner_id for p in plans} | {e.uploaded_by for e in evidence}
    )
    for uid in sorted(referenced):
        if uid in users:
            continue
        is_auditor = uid in auditor_ids
        users[uid] = dict(
            id=uid,
            name=f"{'Auditor' if is_auditor else 'Auditee'} {uid}",
            email=f"user{uid}@trace.demo",
            role="auditor" if is_auditor else "auditee",
            department_id=None if is_auditor else auditee_dept.get(uid),
        )
    db.execute(insert(m.User), list(users.values()))

    # ---- process -> default auditee (auto-assignment)
    owners = []
    for process, dept_id in tax.PROCESS_DEPARTMENT.items():
        candidates = sorted(u["id"] for u in users.values() if u["role"] == "auditee" and u["department_id"] == dept_id)
        if candidates:
            owners.append(dict(process=process, auditee_id=candidates[0], department_id=dept_id))
    if owners:
        db.execute(insert(m.ProcessOwner), owners)

    # ---- NCs (report_id points at audit reports we do not seed -> None)
    nc_rows = []
    for n in ncs:
        d = _plain(n)
        d["report_id"] = None
        nc_rows.append(d)
    db.execute(insert(m.NC), nc_rows)

    # ---- action plans, with the engine's scope lines
    plan_rows = []
    for p in plans:
        d = _plain(p)
        lines = scope.get(p.nc_id)
        d["applies_to_lines"] = list(lines) if lines is not None else None
        plan_rows.append(d)
    if plan_rows:
        db.execute(insert(m.ActionPlan), plan_rows)
    if evidence:
        db.execute(insert(m.Evidence), [_plain(e) for e in evidence])
    if verifs:
        db.execute(insert(m.Verification), [_plain(v) for v in verifs])

    # ---- precomputed links, if the bundle has them (a < b enforced by the DB)
    links = list(data.get("links") or [])
    if links:
        db.execute(insert(m.Link), [
            dict(a=l.a, b=l.b, score=l.score,
                 signals=[s.model_dump(mode="json") for s in l.signals], confirmed=l.confirmed)
            for l in links
        ])

    _fix_sequences(db)
    db.commit()
    return {
        "departments": len(tax.DEPARTMENTS), "users": len(users), "ncs": len(nc_rows),
        "action_plans": len(plan_rows), "evidence": len(evidence),
        "verifications": len(verifs), "links": len(links),
    }
