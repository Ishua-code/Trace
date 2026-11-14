"""POST /api/admin/reset-demo: wipe and reseed the demo data.

Allowed for an admin JWT, or the X-Admin-Token header (env DEMO_ADMIN_TOKEN)
as a bootstrap fallback when the database is empty.
"""
from __future__ import annotations

import os
import secrets
import time

import jwt
from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.auth import ALGORITHM, _secret, bearer
from app.db import get_db
from app.seed_loader import reset_and_load

router = APIRouter(prefix="/api/admin", tags=["admin"])


def require_admin(
    creds=Depends(bearer),
    x_admin_token: str | None = Header(default=None),
) -> None:
    expected = os.environ.get("DEMO_ADMIN_TOKEN")
    if expected and x_admin_token and secrets.compare_digest(x_admin_token, expected):
        return
    if creds is not None:
        try:
            payload = jwt.decode(creds.credentials, _secret(), algorithms=[ALGORITHM])
        except jwt.PyJWTError:
            raise HTTPException(401, "invalid or expired token")
        if payload.get("role") == "admin":
            return
        raise HTTPException(403, "requires role: admin")
    raise HTTPException(401, "admin token or admin login required")


def _bundle(seed: int | None):
    try:
        from seed.generate import SEED_DEFAULT, generate
    except ImportError as exc:  # seed package missing in this deployment
        raise HTTPException(500, f"seed package not available in this deployment: {exc}") from exc
    return generate(SEED_DEFAULT if seed is None else seed)


@router.post("/reset-demo", dependencies=[Depends(require_admin)])
def reset_demo(seed: int | None = None, db: Session = Depends(get_db)) -> dict:
    t0 = time.perf_counter()
    counts = reset_and_load(db, _bundle(seed))
    return {"status": "ok", "seconds": round(time.perf_counter() - t0, 2), "loaded": counts}