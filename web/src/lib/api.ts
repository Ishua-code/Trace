import type { paths } from "./generated/api-schema";

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
  if (!res.ok) throw new Error(`API ${path} -> ${res.status}`);
  return res.json() as Promise<T>;
}
const get = <T,>(p: string) => request<T>("GET", p);
const post = <T,>(p: string, b?: unknown) => request<T>("POST", p, b);
const patch = <T,>(p: string, b: unknown) => request<T>("PATCH", p, b);

export const api = {
  health: () => get<Json200<paths["/api/health"]["get"]>>("/api/health"),
  taxonomy: () => get<TaxonomyResponse>("/api/taxonomy"),

  // Auth
  personas: () => get<unknown[]>("/api/auth/personas"),
  login: (userId: number) =>
    post<{ access_token: string; user: unknown }>("/api/auth/login", { user_id: userId }),

  // KPIs
  kpi: () => get<import("./types").KPIOverview>("/api/kpis/overview"),

  // NCs (API returns {total, items}; we return the items array)
  ncList: async (params?: { status?: string; severity?: string }) => {
    const qs = new URLSearchParams(params as Record<string, string>).toString();
    const r = await get<{ total: number; items: import("./types").NC[] }>(`/api/ncs${qs ? `?${qs}` : ""}`);
    return r.items;
  },
  ncDetail: (id: string) => get<any>(`/api/ncs/${id}`),
  ncRaise: (payload: Partial<import("./types").NC>) =>
    post<import("./types").NC>("/api/ncs", payload),

  // Closure
  simulateClosure: (ncId: string) => post<any>(`/api/ncs/${ncId}/closure/simulate`),
  getClosure: (ncId: string) => get<any>(`/api/ncs/${ncId}/closure`),
  closureDecision: (ncId: string, payload: unknown) =>
    post<any>(`/api/ncs/${ncId}/closure/decision`, payload),
  completeTask: (taskId: number) => patch<any>(`/api/tasks/${taskId}`, { done: true }),

  // Admin / outbox
  outbox: () => get<any>("/api/outbox"),
  verifyChain: () => get<any>("/api/admin/verify-chain"),
  resetDemo: () => post<ResetDemoResponse>("/api/admin/reset-demo"),
};