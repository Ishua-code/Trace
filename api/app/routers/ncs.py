from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app import models as m
from app.auth import get_current_user
from app.db import get_db
from app.services.events import log_event
from app.services.nc_state import check_transition, next_states

router = APIRouter(prefix="/api/ncs", tags=["ncs"])


class StatusIn(BaseModel):
    status: str


@router.get("/{nc_id}/transitions")
def transitions(nc_id: str, db: Session = Depends(get_db), user: m.User = Depends(get_current_user)) -> dict:
    nc = db.get(m.NC, nc_id)
    if nc is None:
        raise HTTPException(404, "NC not found")
    return {"id": nc.id, "status": nc.status, "next": next_states(nc.status)}


@router.patch("/{nc_id}/status")
def change_status(nc_id: str, body: StatusIn, db: Session = Depends(get_db),
                  user: m.User = Depends(get_current_user)) -> dict:
    nc = db.get(m.NC, nc_id)
    if nc is None:
        raise HTTPException(404, "NC not found")
    if body.status == "CLOSED":
        raise HTTPException(409, "close through the Closure Gate endpoint (M2)")
    if user.role == "auditee" and nc.auditee_id != user.id:
        raise HTTPException(403, "not your NC")
    check_transition(nc.status, body.status, user.role)
    old = nc.status
    nc.status = body.status
    log_event(db, "nc.status_changed", user.id, {"nc_id": nc.id, "from": old, "to": body.status})
    db.commit()
    return {"id": nc.id, "from": old, "to": nc.status}