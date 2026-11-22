/**
 * MSW-compatible mock data seeded from the TRACE golden scenario.
 * NC-0412 → linked to NC-0377, NC-0390 → Verdict HOLD
 * All data is SYNTHETIC — clearly labelled.
 */
import type {
  User,
  NC,
  KPIOverview,
  ClosureReport,
  Link,
  Notification,
  AuditSlot,
  EventLogEntry,
} from "./types";

// ---- personas ---------------------------------------------------------------
export const MOCK_USERS: User[] = [
  { id: 1, name: "Priya Nair", email: "priya@trace.dev", role: "auditing_head", department_id: 1 },
  { id: 2, name: "Ravi Kumar", email: "ravi@trace.dev", role: "auditor", department_id: 2 },
  { id: 3, name: "Deepa Menon", email: "deepa@trace.dev", role: "auditee", department_id: 3 },
  { id: 4, name: "Admin", email: "admin@trace.dev", role: "admin" },
];

// ---- NCs (golden scenario + supporting cast) --------------------------------
export const MOCK_NCS: NC[] = [
  {
    id: "NC-0412",
    audit_type: "product",
    title: "Brake drum bore burr on Line 2",
    description: "Burr detected on brake drum bore during dimension check. Deburring tool replaced.",
    severity: "major",
    product: "Brake Drum Assy",
    process: "Machining",
    line: "Line 2",
    department_id: 2,
    machine: "MCH-204",
    lot: "LOT-2024-089",
    defect_code: "DC-012",
    root_cause_category: "Tooling",
    status: "PENDING_HEAD_APPROVAL",
    auditee_id: 3,
    auditor_id: 2,
    raised_at: "2024-10-14T09:30:00Z",
    target_date: "2024-10-28",
  },
  {
    id: "NC-0377",
    audit_type: "product",
    title: "Sharp edge on brake component Line 4 — no tool-life tracking",
    description: "Sharp edge found on brake component. Root cause: tool-life threshold not defined.",
    severity: "major",
    product: "Brake Drum Assy",
    process: "Machining",
    line: "Line 4",
    department_id: 2,
    machine: "MCH-412",
    lot: "LOT-2024-071",
    defect_code: "DC-012",
    root_cause_category: "Tooling",
    status: "IN_PROGRESS",
    auditee_id: 3,
    auditor_id: 2,
    raised_at: "2024-09-02T11:00:00Z",
    target_date: "2024-09-30",
  },
  {
    id: "NC-0390",
    audit_type: "revalidation",
    title: "Heat treatment — tool change interval undefined",
    description: "Recurrence of burr defect post-closure. Tool change interval not in control plan.",
    severity: "critical",
    product: "Brake Drum Assy",
    process: "Heat Treatment",
    line: "Line 3",
    department_id: 3,
    machine: "HT-07",
    lot: "LOT-2024-078",
    defect_code: "DC-015",
    root_cause_category: "Tooling",
    status: "REOPENED",
    auditee_id: 3,
    auditor_id: 2,
    raised_at: "2024-09-20T14:00:00Z",
    target_date: "2024-10-15",
    closed_at: "2024-10-10T10:00:00Z",
  },
  {
    id: "NC-0401",
    audit_type: "product",
    title: "Dimension out-of-spec on Hub Flange",
    description: "OD measurement 0.3mm over tolerance.",
    severity: "minor",
    product: "Hub Flange",
    process: "Grinding",
    line: "Line 1",
    department_id: 2,
    status: "CLOSED",
    auditee_id: 3,
    auditor_id: 2,
    raised_at: "2024-09-10T08:00:00Z",
    target_date: "2024-09-25",
    closed_at: "2024-09-24T16:00:00Z",
  },
  {
    id: "NC-0415",
    audit_type: "product",
    title: "Surface finish failure — Wheel Hub",
    description: "Ra value exceeds spec at station 3.",
    severity: "minor",
    product: "Wheel Hub",
    process: "Finishing",
    line: "Line 5",
    department_id: 4,
    status: "ACTION_PLANNED",
    auditee_id: 3,
    auditor_id: 2,
    raised_at: "2024-10-20T10:00:00Z",
    target_date: "2024-11-05",
  },
  {
    id: "NC-0420",
    audit_type: "product",
    title: "Welding porosity on Axle Shaft",
    description: "Porosity found in weld bead — visual inspection fail.",
    severity: "critical",
    product: "Axle Shaft",
    process: "Welding",
    line: "Line 2",
    department_id: 5,
    status: "OPEN",
    raised_at: "2024-10-28T07:30:00Z",
    target_date: "2024-11-10",
  },
];

// ---- KPI overview ----------------------------------------------------------
export const MOCK_KPI: KPIOverview = {
  plan_vs_completed_pct: 73.4,
  open_count: 8,
  overdue_count: 3,
  closed_count: 24,
  on_time_closure_pct: 81.2,
  avg_closure_lead_days: 11.4,
  ageing: { d0_7: 4, d8_14: 2, d15_30: 1, d30_plus: 1 },
  pending_approvals: 2,
  auditors: [
    { user_id: 2, name: "Ravi Kumar", open: 5, overdue: 2, closed: 18 },
  ],
  auditees: [
    { user_id: 3, name: "Deepa Menon", open: 5, overdue: 2, closed: 18 },
  ],
};

// ---- Closure report (golden scenario) --------------------------------------
export const MOCK_CLOSURE_REPORT: ClosureReport = {
  nc_id: "NC-0412",
  verdict: "HOLD",
  findings: [
    {
      rule: "R1",
      severity: "critical",
      message: "Unresolved connected NC-0377 (sharp edge, same tooling root cause) still open on Line 4.",
      evidence_refs: ["NC-0377", "ACTION-0377-01"],
    },
    {
      rule: "R3",
      severity: "major",
      message: "Same root-cause category 'Tooling' recurred after NC-0390 closure — control plan gap unresolved.",
      evidence_refs: ["NC-0390", "EVIDENCE-0390-02"],
    },
    {
      rule: "R5",
      severity: "major",
      message: "Evidence submitted for NC-0412 covers only Line 2; affected scope includes Line 4.",
      evidence_refs: ["EVIDENCE-0412-01"],
    },
  ],
  links: [
    {
      id: 1,
      a: "NC-0412",
      b: "NC-0377",
      score: 0.87,
      confirmed: null,
      signals: [
        { name: "same_product_family", value: 1, weight: 0.25, contribution: 0.25, evidence: "Both: Brake Drum Assy" },
        { name: "same_root_cause_cat", value: 1, weight: 0.2, contribution: 0.2, evidence: "Tooling" },
        { name: "text_similarity", value: 0.74, weight: 0.2, contribution: 0.148, evidence: "burr / sharp edge — domain synonym" },
        { name: "same_defect_code", value: 1, weight: 0.15, contribution: 0.15, evidence: "DC-012" },
        { name: "time_proximity", value: 0.6, weight: 0.1, contribution: 0.06, evidence: "42 days apart" },
        { name: "same_process", value: 1, weight: 0.1, contribution: 0.1, evidence: "Machining" },
      ],
    },
    {
      id: 2,
      a: "NC-0412",
      b: "NC-0390",
      score: 0.72,
      confirmed: null,
      signals: [
        { name: "same_product_family", value: 1, weight: 0.25, contribution: 0.25, evidence: "Both: Brake Drum Assy" },
        { name: "same_root_cause_cat", value: 1, weight: 0.2, contribution: 0.2, evidence: "Tooling" },
        { name: "recurrence_after_closure", value: 1, weight: 0.2, contribution: 0.2, evidence: "NC-0390 closed then reopened" },
        { name: "text_similarity", value: 0.52, weight: 0.2, contribution: 0.104, evidence: "burr / tool change interval" },
        { name: "time_proximity", value: 0.5, weight: 0.1, contribution: 0.05, evidence: "24 days apart" },
      ],
    },
  ],
  tasks: [
    {
      nc_id: "NC-0412",
      title: "Check tool-life counters on Lines 2 and 4; confirm threshold is set in control plan CP-07",
      priority: 1,
      suggested_owner_role: "auditor",
      done: false,
    },
    {
      nc_id: "NC-0412",
      title: "Sample 30 pieces from last 3 lots (LOT-2024-089, 071, 078) for burr inspection",
      priority: 1,
      suggested_owner_role: "auditee",
      done: false,
    },
    {
      nc_id: "NC-0412",
      title: "Update control plan CP-07 with tool change interval and sign off with QA head",
      priority: 2,
      suggested_owner_role: "auditee",
      done: false,
    },
  ],
  generated_at: "2024-10-29T10:00:00Z",
};

// ---- Notifications ---------------------------------------------------------
export const MOCK_NOTIFICATIONS: Notification[] = [
  {
    id: 1,
    to_user_id: 3,
    kind: "reminder",
    subject: "Action overdue: NC-0377",
    body: "Your corrective action for NC-0377 is 29 days overdue. Please update status.",
    nc_id: "NC-0377",
    sent_at: "2024-10-29T08:00:00Z",
  },
  {
    id: 2,
    to_user_id: 1,
    kind: "escalation_l2",
    subject: "Escalation: NC-0390 unresolved",
    body: "NC-0390 (critical) has been reopened and remains unresolved for 14 days.",
    nc_id: "NC-0390",
    sent_at: "2024-10-28T09:00:00Z",
  },
  {
    id: 3,
    to_user_id: 3,
    kind: "assignment",
    subject: "New NC assigned: NC-0412",
    body: "NC-0412 (Brake drum bore burr) has been assigned to you. Target: 28 Oct.",
    nc_id: "NC-0412",
    sent_at: "2024-10-14T09:35:00Z",
  },
];

// ---- Audit slots (today's schedule) ----------------------------------------
export const MOCK_SLOTS: AuditSlot[] = [
  {
    id: 1, plan_id: 1, audit_date: "2024-10-29", audit_type: "product",
    process: "Machining", product: "Brake Drum Assy", line: "Line 2",
    auditor_id: 2, mandatory: true, completed: true,
  },
  {
    id: 2, plan_id: 1, audit_date: "2024-10-29", audit_type: "product",
    process: "Grinding", product: "Hub Flange", line: "Line 1",
    auditor_id: 2, mandatory: false, completed: false,
  },
  {
    id: 3, plan_id: 1, audit_date: "2024-10-29", audit_type: "revalidation",
    process: "Heat Treatment", product: "Brake Drum Assy", line: "Line 3",
    auditor_id: 2, mandatory: true, completed: false,
  },
];

// ---- Audit log entries (hash-chained) --------------------------------------
export const MOCK_AUDIT_LOG: EventLogEntry[] = [
  {
    index: 0,
    event_type: "NC_RAISED",
    actor_id: 2,
    payload: { nc_id: "NC-0412", severity: "major" },
    prev_hash: "0000000000000000",
    hash: "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f60001",
    created_at: "2024-10-14T09:30:00Z",
  },
  {
    index: 1,
    event_type: "NC_ASSIGNED",
    actor_id: 2,
    payload: { nc_id: "NC-0412", auditee_id: 3 },
    prev_hash: "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f60001",
    hash: "b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a10002",
    created_at: "2024-10-14T09:35:00Z",
  },
  {
    index: 2,
    event_type: "TRACE_VERDICT",
    actor_id: undefined,
    payload: { nc_id: "NC-0412", verdict: "HOLD", linked_ncs: ["NC-0377", "NC-0390"] },
    prev_hash: "b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a10002",
    hash: "c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b20003",
    created_at: "2024-10-29T10:00:00Z",
  },
  {
    index: 3,
    event_type: "HEAD_DECISION",
    actor_id: 1,
    payload: { nc_id: "NC-0412", decision: "send_back", justification: "TRACE HOLD: resolve NC-0377 first" },
    prev_hash: "c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b20003",
    hash: "d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c30004",
    created_at: "2024-10-29T14:00:00Z",
  },
];
