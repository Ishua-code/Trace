"""POST /api/admin/reset-demo: wipe and reseed the demo data.

Protected by the X-Admin-Token header (env DEMO_ADMIN_TOKEN) until real JWT roles exist (M1).
Swap the dependency for the admin-role check then.
"""
from __future__ import annotations

import os
import secrets
import sys
import time
from pathlib import Path

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.seed_loader import reset_and_load

router = APIRouter(prefix="/api/admin", tags=["admin"])


def require_admin_token(x_admin_token: str | None = Header(default=None)) -> None:
    expected = os.environ.get("DEMO_ADMIN_TOKEN")
    if not expected:
        raise HTTPException(503, "DEMO_ADMIN_TOKEN is not configured")
    if not x_admin_token or not secrets.compare_digest(x_admin_token, expected):
        raise HTTPException(401, "invalid admin token")


def _bundle(seed: int | None):
    try:
        from seed.generate import SEED_DEFAULT, generate
    except ImportError as exc:  # seed package missing in this deployment
        raise HTTPException(500, f"seed package not available in this deployment: {exc}") from exc
    return generate(SEED_DEFAULT if seed is None else seed)

@router.post("/reset-demo", dependencies=[Depends(require_admin_token)])
def reset_demo(seed: int | None = None, db: Session = Depends(get_db)) -> dict:
    t0 = time.perf_counter()
    counts = reset_and_load(db, _bundle(seed))
    return {"status": "ok", "seconds": round(time.perf_counter() - t0, 2), "loaded": counts}
