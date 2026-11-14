/**
 * TypeScript mirror of api/app/contracts.py (frozen).
 * Keep in sync manually — do NOT auto-generate until openapi.json lands.
 */

// ---- enums -----------------------------------------------------------------
export type Role = "admin" | "auditing_head" | "auditor" | "auditee";
export type AuditType = "product" | "revalidation";
export type Severity = "minor" | "major" | "critical";
export type NCStatus =
  | "OPEN"
  | "ASSIGNED"
  | "ACTION_PLANNED"
  | "IN_PROGRESS"
  | "EVIDENCE_SUBMITTED"
  | "AUDITOR_VERIFIED"
  | "REJECTED"
  | "TRACE_REVIEW"
  | "PENDING_HEAD_APPROVAL"
  | "CLOSED"
  | "REOPENED";
export type Verdict = "CLEAR" | "VERIFY" | "HOLD";
export type ChecklistResult = "pass" | "fail" | "na";
export type ApprovalDecision = "approve" | "send_back" | "override";

// ---- users -----------------------------------------------------------------
export interface User {
  id: number;
  name: string;
  email: string;
  role: Role;
  department_id?: number;
}

export interface Department {
  id: number;
  name: string;
}

// ---- plan + schedule -------------------------------------------------------
export interface AuditPlan {
  id: number;
  month: string; // YYYY-MM
  uploaded_by: number;
  created_at: string;
}

export interface AuditSlot {
  id: number;
  plan_id: number;
  audit_date: string;
  audit_type: AuditType;
  process: string;
  product: string;
  line?: string;
  auditor_id: number;
  mandatory: boolean;
  completed: boolean;
}

export interface PlanRowError {
  row: number;
  field: string;
  message: string;
}

export interface PlanUploadResult {
  plan_id?: number;
  slots_created: number;
  errors: PlanRowError[];
}

// ---- checklist + report ----------------------------------------------------
export interface ChecklistItem {
  id: number;
  text: string;
}

export interface Checklist {
  id: number;
  audit_type: AuditType;
  name: string;
  items: ChecklistItem[];
}

export interface ChecklistResponse {
  item_id: number;
  result: ChecklistResult;
  remarks?: string;
  photo_url?: string;
}

export interface AuditReport {
  id: number;
  slot_id: number;
  checklist_id: number;
  responses: ChecklistResponse[];
  submitted: boolean;
  submitted_at?: string;
}

// ---- NC workflow -----------------------------------------------------------
export interface NC {
  id: string; // e.g. NC-0412
  report_id?: number;
  audit_type: AuditType;
  title: string;
  description: string;
  severity: Severity;
  product: string;
  process: string;
  line?: string;
  department_id: number;
  machine?: string;
  lot?: string;
  defect_code?: string;
  root_cause_category?: string;
  status: NCStatus;
  auditee_id?: number;
  auditor_id?: number;
  raised_at: string;
  target_date?: string;
  closed_at?: string;
}

export interface ActionPlan {
  id: number;
  nc_id: string;
  root_cause_category: string;
  corrective_action: string;
  preventive_action?: string;
  owner_id: number;
  target_date: string;
  created_at: string;
}

export interface Evidence {
  id: number;
  nc_id: string;
  file_url: string;
  file_name: string;
  uploaded_by: number;
  uploaded_at: string;
  has_before_after: boolean;
}

export interface Verification {
  id: number;
  nc_id: string;
  auditor_id: number;
  accepted: boolean;
  comment?: string;
  verified_at: string;
}

export interface Approval {
  id: number;
  nc_id: string;
  head_id: number;
  decision: ApprovalDecision;
  justification?: string;
  closure_report_id?: number;
  event_hash?: string;
  decided_at: string;
}

// ---- TRACE engine types ----------------------------------------------------
export interface Signal {
  name: string;
  value: number;
  weight: number;
  contribution: number;
  evidence: string;
}

export interface Link {
  id?: number;
  a: string;
  b: string;
  score: number;
  signals: Signal[];
  confirmed?: boolean | null;
}

export interface Finding {
  rule: string; // R1..R7
  severity: Severity;
  message: string;
  evidence_refs: string[];
}

export interface VerificationTask {
  id?: number;
  nc_id: string;
  title: string;
  priority: 1 | 2 | 3;
  suggested_owner_role: Role;
  done: boolean;
}

export interface ClosureReport {
  id?: number;
  nc_id: string;
  verdict: Verdict;
  findings: Finding[];
  links: Link[];
  tasks: VerificationTask[];
  generated_at: string;
}

export interface Recommendation {
  process: string;
  month: string;
  risk_score: number;
  explanation: string;
  locked: boolean;
}

// ---- audit log -------------------------------------------------------------
export interface EventLogEntry {
  index: number;
  event_type: string;
  actor_id?: number;
  payload: Record<string, unknown>;
  prev_hash: string;
  hash: string;
  created_at: string;
}

export interface ChainVerification {
  ok: boolean;
  first_broken_index?: number;
}

// ---- notifications ---------------------------------------------------------
export interface Notification {
  id: number;
  to_user_id: number;
  kind: "reminder" | "escalation_l1" | "escalation_l2" | "assignment";
  subject: string;
  body: string;
  nc_id?: string;
  sent_at: string;
}

// ---- KPIs ------------------------------------------------------------------
export interface AgeingBuckets {
  d0_7: number;
  d8_14: number;
  d15_30: number;
  d30_plus: number;
}

export interface PersonStatus {
  user_id: number;
  name: string;
  open: number;
  overdue: number;
  closed: number;
}

export interface KPIOverview {
  plan_vs_completed_pct: number;
  open_count: number;
  overdue_count: number;
  closed_count: number;
  on_time_closure_pct: number;
  avg_closure_lead_days: number;
  ageing: AgeingBuckets;
  pending_approvals: number;
  auditors: PersonStatus[];
  auditees: PersonStatus[];
}

export interface EffortSaved {
  metric: string;
  manual_baseline_minutes: number;
  measured_minutes: number;
  is_estimate: boolean;
}
