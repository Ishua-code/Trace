"""
TRACE contracts: shared Pydantic types for routers, services and the engine.

FROZEN. Changes need approval from Ishwarya (and Hanu for engine types).
Pure Pydantic, no web or DB imports, so the engine can use it safely.
"""
from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Optional, Protocol

from pydantic import BaseModel, Field


# ---------------------------------------------------------------- enums
class Role(str, Enum):
    admin = "admin"
    auditing_head = "auditing_head"
    auditor = "auditor"
    auditee = "auditee"


class AuditType(str, Enum):
    product = "product"
    revalidation = "revalidation"


class Severity(str, Enum):
    minor = "minor"
    major = "major"
    critical = "critical"


class NCStatus(str, Enum):
    OPEN = "OPEN"
    ASSIGNED = "ASSIGNED"
    ACTION_PLANNED = "ACTION_PLANNED"
    IN_PROGRESS = "IN_PROGRESS"
    EVIDENCE_SUBMITTED = "EVIDENCE_SUBMITTED"
    AUDITOR_VERIFIED = "AUDITOR_VERIFIED"
    REJECTED = "REJECTED"
    TRACE_REVIEW = "TRACE_REVIEW"
    PENDING_HEAD_APPROVAL = "PENDING_HEAD_APPROVAL"
    CLOSED = "CLOSED"
    REOPENED = "REOPENED"


class Verdict(str, Enum):
    CLEAR = "CLEAR"
    VERIFY = "VERIFY"
    HOLD = "HOLD"


class ChecklistResult(str, Enum):
    passed = "pass"
    failed = "fail"
    na = "na"


class ApprovalDecision(str, Enum):
    approve = "approve"
    send_back = "send_back"
    override = "override"


# ---------------------------------------------------------------- users
class User(BaseModel):
    id: int
    name: str
    email: str
    role: Role
    department_id: Optional[int] = None


class Department(BaseModel):
    id: int
    name: str


# ---------------------------------------------------------------- plan + schedule
class AuditPlan(BaseModel):
    id: int
    month: str = Field(description="YYYY-MM")
    uploaded_by: int
    created_at: datetime


class AuditSlot(BaseModel):
    id: int
    plan_id: int
    audit_date: date
    audit_type: AuditType
    process: str
    product: str
    line: Optional[str] = None
    auditor_id: int
    mandatory: bool = False
    completed: bool = False


class PlanRowError(BaseModel):
    row: int
    field: str
    message: str


class PlanUploadResult(BaseModel):
    plan_id: Optional[int] = None
    slots_created: int = 0
    errors: list[PlanRowError] = []


# ---------------------------------------------------------------- checklist + report
class ChecklistItem(BaseModel):
    id: int
    text: str


class Checklist(BaseModel):
    id: int
    audit_type: AuditType
    name: str
    items: list[ChecklistItem]


class ChecklistResponse(BaseModel):
    item_id: int
    result: ChecklistResult
    remarks: Optional[str] = None
    photo_url: Optional[str] = None


class AuditReport(BaseModel):
    id: int
    slot_id: int
    checklist_id: int
    responses: list[ChecklistResponse]
    submitted: bool = False
    submitted_at: Optional[datetime] = None


# ---------------------------------------------------------------- NC workflow
class NC(BaseModel):
    id: str = Field(description="e.g. NC-0412")
    report_id: Optional[int] = None
    audit_type: AuditType
    title: str
    description: str
    severity: Severity
    product: str
    process: str
    line: Optional[str] = None
    department_id: int
    machine: Optional[str] = None
    lot: Optional[str] = None
    defect_code: Optional[str] = None
    root_cause_category: Optional[str] = None
    status: NCStatus
    auditee_id: Optional[int] = None
    auditor_id: Optional[int] = None
    raised_at: datetime
    target_date: Optional[date] = None
    closed_at: Optional[datetime] = None
    # overdue / ageing are derived from target_date, never stored


class ActionPlan(BaseModel):
    id: int
    nc_id: str
    root_cause_category: str
    corrective_action: str
    preventive_action: Optional[str] = None
    owner_id: int
    target_date: date
    created_at: datetime


class Evidence(BaseModel):
    id: int
    nc_id: str
    file_url: str
    file_name: str
    uploaded_by: int
    uploaded_at: datetime
    has_before_after: bool = False


class Verification(BaseModel):
    id: int
    nc_id: str
    auditor_id: int
    accepted: bool
    comment: Optional[str] = None
    verified_at: datetime


class Approval(BaseModel):
    id: int
    nc_id: str
    head_id: int
    decision: ApprovalDecision
    justification: Optional[str] = Field(
        default=None, description="Required when decision is override"
    )
    closure_report_id: Optional[int] = None
    event_hash: Optional[str] = None
    decided_at: datetime


# ---------------------------------------------------------------- TRACE engine types
class Signal(BaseModel):
    name: str
    value: float
    weight: float
    contribution: float
    evidence: str


class Link(BaseModel):
    id: Optional[int] = None
    a: str
    b: str
    score: float
    signals: list[Signal]
    confirmed: Optional[bool] = Field(
        default=None, description="Auditor feedback; None = not reviewed"
    )


class Finding(BaseModel):
    rule: str = Field(description="R1..R7")
    severity: Severity
    message: str
    evidence_refs: list[str] = Field(description="NC / evidence / action ids")


class VerificationTask(BaseModel):
    id: Optional[int] = None
    nc_id: str
    title: str
    priority: int = Field(ge=1, le=3, description="1 = highest")
    suggested_owner_role: Role
    done: bool = False


class ClosureReport(BaseModel):
    id: Optional[int] = None
    nc_id: str
    verdict: Verdict
    findings: list[Finding]
    links: list[Link] = []
    tasks: list[VerificationTask] = []
    generated_at: datetime


class Recommendation(BaseModel):
    process: str
    month: str
    risk_score: float
    explanation: str
    locked: bool = Field(
        default=False, description="Mandatory scheduled audits are locked, never displaced"
    )


# ---------------------------------------------------------------- audit log
class EventLogEntry(BaseModel):
    index: int
    event_type: str
    actor_id: Optional[int] = None
    payload: dict
    prev_hash: str
    hash: str
    created_at: datetime


class ChainVerification(BaseModel):
    ok: bool
    first_broken_index: Optional[int] = None


# ---------------------------------------------------------------- notifications
class Notification(BaseModel):
    id: int
    to_user_id: int
    kind: str = Field(description="reminder | escalation_l1 | escalation_l2 | assignment")
    subject: str
    body: str
    nc_id: Optional[str] = None
    sent_at: datetime


# ---------------------------------------------------------------- KPIs (always derived)
class AgeingBuckets(BaseModel):
    d0_7: int
    d8_14: int
    d15_30: int
    d30_plus: int


class PersonStatus(BaseModel):
    user_id: int
    name: str
    open: int
    overdue: int
    closed: int


class KPIOverview(BaseModel):
    plan_vs_completed_pct: float
    open_count: int
    overdue_count: int
    closed_count: int
    on_time_closure_pct: float
    avg_closure_lead_days: float
    ageing: AgeingBuckets
    pending_approvals: int
    auditors: list[PersonStatus] = []
    auditees: list[PersonStatus] = []


class EffortSaved(BaseModel):
    metric: str
    manual_baseline_minutes: float = Field(description="Documented assumption")
    measured_minutes: float
    is_estimate: bool = True


# ---------------------------------------------------------------- engine interface (frozen)
class TraceEngine(Protocol):
    def find_related(self, nc_id: str) -> list[Link]: ...

    def simulate_closure(self, nc_id: str) -> ClosureReport: ...

    def plan_risk(self, month: str) -> list[Recommendation]: ...

    def record_feedback(self, link_id: int, confirmed: bool) -> None: ...
