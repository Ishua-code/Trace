"""JWT auth: token creation, current-user lookup and role guards."""
from __future__ import annotations

import os
import time

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app import models as m
from app.db import get_db

ALGORITHM = "HS256"
TOKEN_TTL_SECONDS = 12 * 3600
ROLES = ("admin", "auditing_head", "auditor", "auditee")

bearer = HTTPBearer(auto_error=False)


def _secret() -> str:
    secret = os.environ.get("JWT_SECRET")
    if not secret:
        raise HTTPException(503, "JWT_SECRET is not configured")
    return secret


def create_token(user: m.User) -> str:
    now = int(time.time())
    payload = {"sub": str(user.id), "role": user.role, "iat": now, "exp": now + TOKEN_TTL_SECONDS}
    return jwt.encode(payload, _secret(), algorithm=ALGORITHM)


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> m.User:
    if creds is None:
        raise HTTPException(401, "missing bearer token")
    try:
        payload = jwt.decode(creds.credentials, _secret(), algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        raise HTTPException(401, "invalid or expired token")
    user = db.get(m.User, int(payload["sub"]))
    if user is None:
        raise HTTPException(401, "user no longer exists")
    return user


def require_role(*roles: str):
    """Use as: dependencies=[Depends(require_role('admin'))] or user = Depends(require_role('auditor','admin'))."""
    def dep(user: m.User = Depends(get_current_user)) -> m.User:
        if user.role not in roles:
            raise HTTPException(403, f"requires role: {', '.join(roles)}")
        return user
    return dep