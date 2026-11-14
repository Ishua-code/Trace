"""Demo login (persona switch) and current-user endpoint."""
from __future__ import annotations

import os

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app import models as m
from app.auth import create_token, get_current_user
from app.db import get_db

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _demo_mode() -> bool:
    return os.environ.get("DEMO_MODE", "").lower() == "true"


class LoginIn(BaseModel):
    user_id: int


def _user_out(u: m.User) -> dict:
    return {"id": u.id, "name": u.name, "email": u.email, "role": u.role, "department_id": u.department_id}


@router.get("/personas")
def personas(db: Session = Depends(get_db)) -> list[dict]:
    if not _demo_mode():
        raise HTTPException(404, "not found")
    return [_user_out(u) for u in db.query(m.User).order_by(m.User.id).all()]


@router.post("/login")
def login(body: LoginIn, db: Session = Depends(get_db)) -> dict:
    if not _demo_mode():
        raise HTTPException(404, "not found")
    user = db.get(m.User, body.user_id)
    if user is None:
        raise HTTPException(404, "unknown user")
    return {"access_token": create_token(user), "token_type": "bearer", "user": _user_out(user)}


@router.get("/me")
def me(user: m.User = Depends(get_current_user)) -> dict:
    return _user_out(user)