/**
 * Typed API client — calls NEXT_PUBLIC_API_URL.
 * Falls back to mock data when NEXT_PUBLIC_API_URL is not set (dev with MSW).
 */
const BASE = process.env.NEXT_PUBLIC_API_URL ?? "";

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`, { next: { revalidate: 30 } });
  if (!res.ok) throw new Error(`API ${path} → ${res.status}`);
  return res.json() as Promise<T>;
}

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`API ${path} → ${res.status}`);
  return res.json() as Promise<T>;
}

async function patch<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`API ${path} → ${res.status}`);
  return res.json() as Promise<T>;
}

export const api = {
  health: () => get<{ status: string }>("/api/health"),

  // KPIs
  kpi: () => get<import("./types").KPIOverview>("/api/kpi"),
  effortSaved: () => get<import("./types").EffortSaved[]>("/api/kpi/effort-saved"),

  // NCs
  ncList: (params?: { status?: string; severity?: string }) => {
    const qs = new URLSearchParams(params as Record<string, string>).toString();
    return get<import("./types").NC[]>(`/api/ncs${qs ? `?${qs}` : ""}`);
  },
  ncDetail: (id: string) => get<import("./types").NC>(`/api/ncs/${id}`),
  ncRaise: (payload: Partial<import("./types").NC>) =>
    post<import("./types").NC>("/api/ncs", payload),

  // TRACE engine
  findRelated: (ncId: string) =>
    get<import("./types").Link[]>(`/api/engine/related/${ncId}`),
  simulateClosure: (ncId: string) =>
    get<import("./types").ClosureReport>(`/api/engine/simulate/${ncId}`),
  planRisk: (month: string) =>
    get<import("./types").Recommendation[]>(`/api/engine/plan-risk?month=${month}`),
  recordFeedback: (linkId: number, confirmed: boolean) =>
    post<void>("/api/engine/feedback", { link_id: linkId, confirmed }),

  // Approvals
  pendingApprovals: () =>
    get<import("./types").NC[]>("/api/approvals/pending"),
  approve: (ncId: string, payload: { decision: string; justification?: string }) =>
    post<import("./types").Approval>(`/api/approvals/${ncId}`, payload),

  // Audit log
  auditLog: (limit = 50) =>
    get<import("./types").EventLogEntry[]>(`/api/audit-log?limit=${limit}`),
  verifyChain: () =>
    get<import("./types").ChainVerification>("/api/audit-log/verify"),

  // Notifications
  notifications: (userId: number) =>
    get<import("./types").Notification[]>(`/api/notifications?user_id=${userId}`),

  // Admin
  resetDemo: () => post<{ ok: boolean }>("/api/admin/reset-demo", {}),

  // Eval / proof
  evalResults: () => get<unknown>("/api/eval/results"),

  // Plan upload
  uploadPlan: (formData: FormData) =>
    fetch(`${BASE}/api/plans/upload`, { method: "POST", body: formData }).then(
      (r) => r.json() as Promise<import("./types").PlanUploadResult>
    ),

  // Verification tasks
  completeTask: (taskId: number) =>
    patch<import("./types").VerificationTask>(`/api/tasks/${taskId}`, { done: true }),
};
