"""POST /api/admin/reindex: rebuild TRACE links by running the engine's index_nc.

Use right after reset-demo (the seed currently loads no links).
scope=golden -> the 6 golden NCs only (fast); scope=all -> every NC.
"""
from __future__ import annotations

import time
from typing import Literal

import os
import secrets

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import models as m
from app.db import get_db
from app.trace_hooks import get_engine

router = APIRouter(prefix="/api/admin", tags=["admin"])
def require_admin_token(x_admin_token: str | None = Header(default=None)) -> None:
    expected = os.environ.get("DEMO_ADMIN_TOKEN")
    if not expected:
        raise HTTPException(503, "DEMO_ADMIN_TOKEN is not configured")
    if not x_admin_token or not secrets.compare_digest(x_admin_token, expected):
        raise HTTPException(401, "invalid admin token")

GOLDEN = (361, 377, 390, 401, 408, 412)


@router.post("/reindex", dependencies=[Depends(require_admin_token)])
def reindex(scope: Literal["golden", "all"] = "golden", db: Session = Depends(get_db)) -> dict:
    t0 = time.perf_counter()
    if scope == "golden":
        ids = [f"NC-{n:04d}" for n in GOLDEN]
    else:
        ids = list(db.scalars(select(m.NC.id).order_by(m.NC.id)).all())

    engine = get_engine(db)
    done, failed = 0, []
    for nc_id in ids:
        if db.get(m.NC, nc_id) is None:
            failed.append({"nc_id": nc_id, "error": "not found"})
            continue
        try:
            engine.index_nc(nc_id)
            done += 1
        except NotImplementedError:
            raise HTTPException(503, "engine index_nc is not available in this build")
        except Exception as exc:  # noqa: BLE001
            db.rollback()
            failed.append({"nc_id": nc_id, "error": str(exc)[:200]})

    links = db.scalar(select(func.count()).select_from(m.Link)) or 0
    return {"status": "ok", "scope": scope, "indexed": done, "failed": failed,
            "links_total": links, "seconds": round(time.perf_counter() - t0, 2)}
