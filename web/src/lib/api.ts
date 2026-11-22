import type { paths } from "./generated/api-schema";
import type {
  ChainVerification,
  ClosureReport,
  EventLogEntry,
  KPIOverview,
  NC,
  Notification,
} from "./types";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "";

type Json200<Operation> = Operation extends {
  responses: { 200: { content: { "application/json": infer Response } } };
} ? Response : never;
type TaxonomyResponse = Json200<paths["/api/taxonomy"]["get"]>;
type ResetDemoResponse = Json200<paths["/api/admin/reset-demo"]["post"]>;

let TOKEN = "";
export function setToken(t: string) {
  TOKEN = t;
}

function headers(json = false): Record<string, string> {
  const h: Record<string, string> = {};
  if (json) h["Content-Type"] = "application/json";
  if (TOKEN) h["Authorization"] = `Bearer ${TOKEN}`;
  return h;
}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method,
    cache: "no-store",
    headers: headers(body !== undefined),
    ...(body === undefined ? {} : { body: JSON.stringify(body) }),
  });
  if (!res.ok) {
    let detail = "";
    try {
      const j = await res.json();
      detail = typeof j?.detail === "string" ? j.detail : JSON.stringify(j?.detail ?? j);
    } catch {
      /* body was not JSON */
    }
    throw new Error(detail ? `${detail} (${res.status})` : `API ${path} -> ${res.status}`);
  }
  return res.json() as Promise<T>;
}
const get = <T,>(p: string) => request<T>("GET", p);
const post = <T,>(p: string, b?: unknown) => request<T>("POST", p, b);
const patch = <T,>(p: string, b: unknown) => request<T>("PATCH", p, b);

/** Build ?a=1&b=2, skipping undefined / empty values. */
function qs(params?: Record<string, string | number | boolean | undefined | null>): string {
  if (!params) return "";
  const u = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== null && v !== "") u.set(k, String(v));
  }
  const s = u.toString();
  return s ? `?${s}` : "";
}

export interface NCQuery {
  q?: string;
  status?: string;
  severity?: string;
  process?: string;
  limit?: number;
  offset?: number;
}
export interface NCPage {
  total: number;
  items: NC[];
}
export type OutboxItem = Notification & { to_name?: string };
export type AuditEvent = EventLogEntry & { actor_name?: string | null };

export const api = {
  health: () => get<Json200<paths["/api/health"]["get"]>>("/api/health"),
  taxonomy: () => get<TaxonomyResponse>("/api/taxonomy"),

  // Auth
  personas: () => get<unknown[]>("/api/auth/personas"),
  login: (userId: number) =>
    post<{ access_token: string; user: unknown }>("/api/auth/login", { user_id: userId }),

  // KPIs
  kpi: () => get<KPIOverview>("/api/kpis/overview"),

  // NCs. ncList returns the items array; ncSearch returns {total, items} (for paging/search).
  ncList: async (params?: NCQuery) => {
    const r = await get<NCPage>(`/api/ncs${qs({ limit: 200, ...params })}`);
    return r.items;
  },
  ncSearch: (params?: NCQuery) => get<NCPage>(`/api/ncs${qs({ limit: 50, ...params })}`),
  ncDetail: (id: string) => get<any>(`/api/ncs/${id}`),
  ncRaise: (payload: Partial<NC>) => post<NC>("/api/ncs", payload),

  // NC lifecycle
  addActionPlan: (
    ncId: string,
    payload: {
      root_cause_category: string;
      corrective_action: string;
      preventive_action?: string;
      target_date: string;
      applies_to_lines?: string[];
    },
  ) => post<any>(`/api/ncs/${ncId}/action-plan`, payload),
  addEvidence: (
    ncId: string,
    payload: { file_name: string; file_url: string; has_before_after?: boolean },
  ) => post<any>(`/api/ncs/${ncId}/evidence`, payload),
  verifyNc: (ncId: string, payload: { accepted: boolean; comment?: string }) =>
    post<any>(`/api/ncs/${ncId}/verify`, payload),

  // Approvals: NCs waiting for the Auditing Head
  pendingApprovals: async () => {
    const r = await get<NCPage>(`/api/ncs${qs({ status: "PENDING_HEAD_APPROVAL", limit: 200 })}`);
    return r.items;
  },

  // Closure Gate
  simulateClosure: (ncId: string) => post<any>(`/api/ncs/${ncId}/closure/simulate`),
  getClosure: (ncId: string) => get<any>(`/api/ncs/${ncId}/closure`),
  /** Closure report plus the related links (the backend keeps links on the NC detail). */
  closureWithLinks: async (ncId: string, simulate = false): Promise<ClosureReport> => {
    const report = simulate
      ? await post<any>(`/api/ncs/${ncId}/closure/simulate`)
      : await get<any>(`/api/ncs/${ncId}/closure`);
    const detail = await get<any>(`/api/ncs/${ncId}`);
    return { ...report, links: detail.links ?? [] } as ClosureReport;
  },
  closureDecision: (
    ncId: string,
    payload: { decision: "approve" | "send_back" | "override"; justification?: string },
  ) => post<any>(`/api/ncs/${ncId}/closure/decision`, payload),
  completeTask: (taskId: number) => patch<any>(`/api/tasks/${taskId}`, { done: true }),
  reopenTask: (taskId: number) => patch<any>(`/api/tasks/${taskId}`, { done: false }),

  // Notifications / Outbox (array of items)
  outbox: () => get<any>("/api/outbox"),
  notifications: async (params?: { kind?: string; nc_id?: string; limit?: number }) => {
    const r = await get<{ total: number; items: OutboxItem[] }>(`/api/outbox${qs({ limit: 200, ...params })}`);
    return r.items;
  },

  // Escalation (Auditing Head / admin)
  runEscalation: (dryRun = false, l2AfterDays = 7) =>
    post<{
      dry_run: boolean;
      today: string;
      created: Record<string, number>;
      total_created: number;
      skipped_existing: number;
    }>(`/api/jobs/escalate${qs({ dry_run: dryRun, l2_after_days: l2AfterDays })}`),

  // Audit log (array of events, newest first)
  auditLog: async (params?: { event_type?: string; nc_id?: string; limit?: number; offset?: number }) => {
    const r = await get<{ total: number; items: AuditEvent[] }>(`/api/audit-log${qs({ limit: 100, ...params })}`);
    return r.items;
  },
  auditLogPage: (params?: { event_type?: string; nc_id?: string; limit?: number; offset?: number }) =>
    get<{ total: number; items: AuditEvent[] }>(`/api/audit-log${qs({ limit: 50, ...params })}`),

  // Chain check: backend says {valid, checked, broken_at_index}; the UI expects {ok, first_broken_index}.
  verifyChain: async (): Promise<ChainVerification & { valid: boolean; checked?: number }> => {
    const r = await get<{ valid: boolean; checked?: number; broken_at_index?: number | null }>(
      "/api/admin/verify-chain",
    );
    return {
      ...r,
      ok: r.valid,
      first_broken_index: r.broken_at_index ?? undefined,
    };
  },

  // Admin (the reset call needs the X-Admin-Token header, so the UI does not expose it by default)
  resetDemo: () => post<ResetDemoResponse>("/api/admin/reset-demo"),
};
