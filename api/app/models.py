"""SQLAlchemy tables. Shapes follow app/contracts.py. Schema changes need Ishwarya + Hanu."""
from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from sqlalchemy import (
    Boolean, CheckConstraint, Date, DateTime, Float, ForeignKey, Integer,
    String, Text, UniqueConstraint, func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


def _now():
    return mapped_column(DateTime(timezone=True), server_default=func.now())


# ---------------------------------------------------------------- people
class Department(Base):
    __tablename__ = "departments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(200), unique=True)
    role: Mapped[str] = mapped_column(String(30))  # admin|auditing_head|auditor|auditee
    password_hash: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    department_id: Mapped[Optional[int]] = mapped_column(ForeignKey("departments.id"), nullable=True)


class ProcessOwner(Base):
    """Process -> default auditee, used for NC auto-assignment."""
    __tablename__ = "process_owners"
    process: Mapped[str] = mapped_column(String(120), primary_key=True)
    auditee_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id"))


# ---------------------------------------------------------------- plan + schedule
class AuditPlan(Base):
    __tablename__ = "audit_plans"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    month: Mapped[str] = mapped_column(String(7))  # YYYY-MM
    uploaded_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = _now()


class AuditSlot(Base):
    __tablename__ = "audit_slots"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("audit_plans.id", ondelete="CASCADE"))
    audit_date: Mapped[date] = mapped_column(Date)
    audit_type: Mapped[str] = mapped_column(String(20))  # product|revalidation
    process: Mapped[str] = mapped_column(String(120))
    product: Mapped[str] = mapped_column(String(120))
    line: Mapped[Optional[str]] = mapped_column(String(60), nullable=True)
    auditor_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    mandatory: Mapped[bool] = mapped_column(Boolean, default=False)
    completed: Mapped[bool] = mapped_column(Boolean, default=False)


# ---------------------------------------------------------------- checklist + report
class Checklist(Base):
    __tablename__ = "checklists"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    audit_type: Mapped[str] = mapped_column(String(20))
    name: Mapped[str] = mapped_column(String(160))
    items: Mapped[list] = mapped_column(JSONB, default=list)  # [{id, text}]


class AuditReport(Base):
    __tablename__ = "audit_reports"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    slot_id: Mapped[int] = mapped_column(ForeignKey("audit_slots.id"))
    checklist_id: Mapped[int] = mapped_column(ForeignKey("checklists.id"))
    responses: Mapped[list] = mapped_column(JSONB, default=list)
    submitted: Mapped[bool] = mapped_column(Boolean, default=False)
    submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


# ---------------------------------------------------------------- NC workflow
class NC(Base):
    __tablename__ = "ncs"
    id: Mapped[str] = mapped_column(String(20), primary_key=True)  # NC-0412
    report_id: Mapped[Optional[int]] = mapped_column(ForeignKey("audit_reports.id"), nullable=True)
    audit_type: Mapped[str] = mapped_column(String(20))
    title: Mapped[str] = mapped_column(String(240))
    description: Mapped[str] = mapped_column(Text)
    severity: Mapped[str] = mapped_column(String(20))
    product: Mapped[str] = mapped_column(String(120))
    process: Mapped[str] = mapped_column(String(120))
    line: Mapped[Optional[str]] = mapped_column(String(60), nullable=True)
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id"))
    machine: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    lot: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    defect_code: Mapped[Optional[str]] = mapped_column(String(60), nullable=True)
    root_cause_category: Mapped[Optional[str]] = mapped_column(String(60), nullable=True)
    status: Mapped[str] = mapped_column(String(30), index=True)
    auditee_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    auditor_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"), nullable=True)
    raised_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    target_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    closed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class ActionPlan(Base):
    __tablename__ = "action_plans"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nc_id: Mapped[str] = mapped_column(ForeignKey("ncs.id", ondelete="CASCADE"), index=True)
    root_cause_category: Mapped[str] = mapped_column(String(60))
    corrective_action: Mapped[str] = mapped_column(Text)
    preventive_action: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    target_date: Mapped[date] = mapped_column(Date)
    applies_to_lines: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)  # proposal 5
    applies_to_products: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = _now()


class Evidence(Base):
    __tablename__ = "evidence"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nc_id: Mapped[str] = mapped_column(ForeignKey("ncs.id", ondelete="CASCADE"), index=True)
    file_url: Mapped[str] = mapped_column(Text)
    file_name: Mapped[str] = mapped_column(String(240))
    uploaded_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    uploaded_at: Mapped[datetime] = _now()
    has_before_after: Mapped[bool] = mapped_column(Boolean, default=False)


class Verification(Base):
    __tablename__ = "verifications"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nc_id: Mapped[str] = mapped_column(ForeignKey("ncs.id", ondelete="CASCADE"), index=True)
    auditor_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    accepted: Mapped[bool] = mapped_column(Boolean)
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    verified_at: Mapped[datetime] = _now()


class ClosureReport(Base):
    __tablename__ = "closure_reports"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nc_id: Mapped[str] = mapped_column(ForeignKey("ncs.id", ondelete="CASCADE"), index=True)
    verdict: Mapped[str] = mapped_column(String(10))  # CLEAR|VERIFY|HOLD
    findings: Mapped[list] = mapped_column(JSONB, default=list)
    generated_at: Mapped[datetime] = _now()


class VerificationTask(Base):
    """Generated once per closure report (agreement 10); later runs update the verdict only."""
    __tablename__ = "verification_tasks"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    closure_report_id: Mapped[int] = mapped_column(ForeignKey("closure_reports.id", ondelete="CASCADE"))
    nc_id: Mapped[str] = mapped_column(ForeignKey("ncs.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(300))
    priority: Mapped[int] = mapped_column(Integer)
    suggested_owner_role: Mapped[str] = mapped_column(String(30))
    done: Mapped[bool] = mapped_column(Boolean, default=False)


class Approval(Base):
    __tablename__ = "approvals"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nc_id: Mapped[str] = mapped_column(ForeignKey("ncs.id", ondelete="CASCADE"), index=True)
    head_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    decision: Mapped[str] = mapped_column(String(20))  # approve|send_back|override
    justification: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    closure_report_id: Mapped[Optional[int]] = mapped_column(ForeignKey("closure_reports.id"), nullable=True)
    event_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    decided_at: Mapped[datetime] = _now()


# ---------------------------------------------------------------- TRACE engine (Hanu, proposal 3)
class Link(Base):
    __tablename__ = "links"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    a: Mapped[str] = mapped_column(String(20), index=True)
    b: Mapped[str] = mapped_column(String(20), index=True)
    score: Mapped[float] = mapped_column(Float)
    signals: Mapped[list] = mapped_column(JSONB, default=list)
    confirmed: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    __table_args__ = (
        UniqueConstraint("a", "b", name="uq_links_a_b"),
        CheckConstraint("a < b", name="ck_links_a_lt_b"),
    )


class WeightDelta(Base):
    __tablename__ = "weight_deltas"
    name: Mapped[str] = mapped_column(String(60), primary_key=True)
    delta: Mapped[float] = mapped_column(Float, default=0.0)


class WeightUpdate(Base):
    __tablename__ = "weight_updates"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    link_id: Mapped[int] = mapped_column(ForeignKey("links.id", ondelete="CASCADE"))
    confirmed: Mapped[bool] = mapped_column(Boolean)
    at: Mapped[datetime] = _now()
    before: Mapped[dict] = mapped_column(JSONB)
    after: Mapped[dict] = mapped_column(JSONB)


# ---------------------------------------------------------------- notifications + audit log
class Notification(Base):
    __tablename__ = "notifications"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    to_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    kind: Mapped[str] = mapped_column(String(30))
    subject: Mapped[str] = mapped_column(String(240))
    body: Mapped[str] = mapped_column(Text)
    nc_id: Mapped[Optional[str]] = mapped_column(ForeignKey("ncs.id"), nullable=True)
    sent_at: Mapped[datetime] = _now()


class EventLog(Base):
    """Append-only, hash-chained: hash = sha256(prev_hash + canonical(event_type, actor, payload, created_at))."""
    __tablename__ = "event_log"
    index: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_type: Mapped[str] = mapped_column(String(60))
    actor_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    payload: Mapped[dict] = mapped_column(JSONB)
    prev_hash: Mapped[str] = mapped_column(String(64))
    hash: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = _now()
