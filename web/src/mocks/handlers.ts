import { http, HttpResponse } from "msw";
import {
  MOCK_AUDIT_LOG,
  MOCK_CLOSURE_REPORT,
  MOCK_KPI,
  MOCK_NCS,
  MOCK_NOTIFICATIONS,
  MOCK_USERS,
} from "../lib/mock-data";
import type { NC } from "../lib/types";

const demoClosures = new Map<string, typeof MOCK_CLOSURE_REPORT>();
const demoStatuses = new Map<string, NC["status"]>();
const completedTasks = new Set<number>();

function closureFor(ncId: string) {
  const report = demoClosures.get(ncId);
  if (!report) return null;
  return {
    ...report,
    nc_id: ncId,
    tasks: report.tasks.map((task, index) => ({
      ...task,
      id: index + 1,
      done: completedTasks.has(index + 1),
    })),
  };
}

const taxonomy = {
  products: ["Brake Drum Assy", "Hub Flange", "Wheel Hub", "Axle Shaft"],
  lines: ["Line 1", "Line 2", "Line 3", "Line 4", "Line 5"],
  departments: [
    { id: 1, name: "Quality" },
    { id: 2, name: "Machining" },
    { id: 3, name: "Heat Treatment" },
  ],
  processes: [
    { name: "Machining", department_id: 2 },
    { name: "Heat Treatment", department_id: 3 },
    { name: "Grinding", department_id: 2 },
  ],
  root_causes: [{ code: "TOOLING", label: "Tooling" }, { code: "METHOD", label: "Method" }],
  defect_codes: [{ code: "DC-012", label: "Burr / sharp edge" }, { code: "DC-015", label: "Process recurrence" }],
};

export const handlers = [
  http.get("*/api/health", () => HttpResponse.json({ status: "ok" })),
  http.get("*/api/auth/personas", () => HttpResponse.json(MOCK_USERS)),
  http.post("*/api/auth/login", async ({ request }) => {
    const { user_id } = await request.json() as { user_id?: number };
    const user = MOCK_USERS.find((item) => item.id === user_id);
    return user
      ? HttpResponse.json({ access_token: `synthetic-demo-token-${user.id}`, token_type: "bearer", user })
      : HttpResponse.json({ detail: "Unknown demo persona" }, { status: 404 });
  }),
  http.get("*/api/taxonomy", () => HttpResponse.json(taxonomy)),
  http.post("*/api/admin/reset-demo", () => HttpResponse.json({ ok: true, source: "synthetic mock" })),
  http.get("*/api/admin/verify-chain", () => HttpResponse.json({ ok: true, first_broken_index: null })),
  http.get("*/api/kpis/overview", () => HttpResponse.json(MOCK_KPI)),
  http.get("*/api/kpi/effort-saved", () => HttpResponse.json([
    { metric: "NC logging", manual_baseline_minutes: 25, measured_minutes: 3, is_estimate: true },
    { metric: "Reporting", manual_baseline_minutes: 60, measured_minutes: 8, is_estimate: true },
  ])),
  http.get("*/api/ncs", ({ request }) => {
    const url = new URL(request.url);
    const status = url.searchParams.get("status");
    const severity = url.searchParams.get("severity");
    const items = MOCK_NCS
      .map((nc) => ({ ...nc, status: demoStatuses.get(nc.id) ?? nc.status }))
      .filter((nc) => (!status || nc.status === status) && (!severity || nc.severity === severity));
    return HttpResponse.json({ total: items.length, items });
  }),
  http.get("*/api/ncs/:id", ({ params }) => {
    const nc = MOCK_NCS.find((item) => item.id === params.id);
    if (!nc) return HttpResponse.json({ detail: "NC not found in synthetic demo data" }, { status: 404 });
    const closure = closureFor(nc.id);
    return HttpResponse.json({
      nc: { ...nc, status: demoStatuses.get(nc.id) ?? nc.status },
      actions: [],
      evidence: [],
      verifications: [],
      links: nc.id === "NC-0412" ? MOCK_CLOSURE_REPORT.links : [],
      closure,
    });
  }),
  http.post("*/api/ncs", async ({ request }) => {
    const payload = await request.json() as Record<string, unknown>;
    return HttpResponse.json({ ...payload, id: payload.id ?? "NC-DEMO", status: "OPEN", raised_at: new Date().toISOString() }, { status: 201 });
  }),
  http.post("*/api/ncs/:id/closure/simulate", ({ params }) => {
    const ncId = typeof params.id === "string" ? params.id : params.id?.[0] ?? "";
    if (ncId !== "NC-0412") {
      return HttpResponse.json({ detail: "Synthetic closure scenario is available for NC-0412 only" }, { status: 404 });
    }
    demoClosures.set(ncId, MOCK_CLOSURE_REPORT);
    demoStatuses.set(ncId, "PENDING_HEAD_APPROVAL");
    return HttpResponse.json(closureFor(ncId));
  }),
  http.get("*/api/ncs/:id/closure", ({ params }) => {
    const ncId = typeof params.id === "string" ? params.id : params.id?.[0] ?? "";
    const report = closureFor(ncId);
    return report
      ? HttpResponse.json(report)
      : HttpResponse.json({ detail: "No synthetic closure report yet" }, { status: 404 });
  }),
  http.post("*/api/ncs/:id/closure/decision", async ({ params, request }) => {
    const ncId = typeof params.id === "string" ? params.id : params.id?.[0] ?? "";
    const payload = await request.json() as { decision?: "approve" | "send_back" | "override"; justification?: string };
    const report = closureFor(ncId);
    if (!report) return HttpResponse.json({ detail: "Run the closure simulation first" }, { status: 409 });
    const justification = payload.justification?.trim() ?? "";
    if (payload.decision === "send_back" && !justification) {
      return HttpResponse.json({ detail: "Sending back needs a reason" }, { status: 422 });
    }
    if (payload.decision === "override" && justification.length < 15) {
      return HttpResponse.json({ detail: "Override needs at least 15 characters" }, { status: 422 });
    }
    const openTasks = report.tasks.filter((task) => !task.done).length;
    if (payload.decision === "approve" && report.verdict !== "CLEAR" && openTasks > 0) {
      return HttpResponse.json({ detail: `Gate is ${report.verdict} with ${openTasks} open verification tasks` }, { status: 409 });
    }
    const status: NC["status"] = payload.decision === "send_back" ? "REOPENED" : "CLOSED";
    demoStatuses.set(ncId, status);
    return HttpResponse.json({ id: ncId, status, decision: payload.decision, verdict: report.verdict, open_tasks: openTasks });
  }),
  http.patch("*/api/tasks/:id", ({ params }) => {
    const taskId = Number(params.id);
    completedTasks.add(taskId);
    return HttpResponse.json({ id: taskId, done: true });
  }),
  http.get("*/api/engine/related/:id", ({ params }) => HttpResponse.json(MOCK_CLOSURE_REPORT.links.filter((link) => link.a === params.id || link.b === params.id))),
  http.get("*/api/engine/simulate/:id", ({ params }) => HttpResponse.json({ ...MOCK_CLOSURE_REPORT, nc_id: params.id })),
  http.get("*/api/engine/plan-risk", () => HttpResponse.json([
    { process: "Machining", month: new Date().toISOString().slice(0, 7), risk_score: 0.82, explanation: "Synthetic demo ranking from recurring tool-related findings.", locked: true },
  ])),
  http.post("*/api/engine/feedback", () => new HttpResponse(null, { status: 204 })),
  http.get("*/api/approvals/pending", () => HttpResponse.json(MOCK_NCS.filter((nc) => nc.status === "PENDING_HEAD_APPROVAL"))),
  http.post("*/api/approvals/:id", async ({ params, request }) => {
    const payload = await request.json() as Record<string, unknown>;
    return HttpResponse.json({ id: 1, nc_id: params.id, head_id: 1, decision: payload.decision ?? "send_back", justification: payload.justification, decided_at: new Date().toISOString(), event_hash: "synthetic-demo-hash" });
  }),
  http.get("*/api/audit-log", ({ request }) => {
    const limit = Number(new URL(request.url).searchParams.get("limit") ?? 50);
    return HttpResponse.json(MOCK_AUDIT_LOG.slice(0, limit));
  }),
  http.get("*/api/admin/verify-chain", () => HttpResponse.json({ ok: true, first_broken_index: null })),
  http.get("*/api/notifications", ({ request }) => {
    const userId = new URL(request.url).searchParams.get("user_id");
    return HttpResponse.json(MOCK_NOTIFICATIONS.filter((item) => !userId || String(item.to_user_id) === userId));
  }),
  http.get("*/api/eval/results", () => HttpResponse.json({ detail: "Evaluation results are not available in this API snapshot." }, { status: 404 })),
  http.post("*/api/plans/upload", () => HttpResponse.json({ plan_id: 1, slots_created: 0, errors: [] })),
];
