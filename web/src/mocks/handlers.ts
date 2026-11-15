import { http, HttpResponse } from "msw";
import {
  MOCK_AUDIT_LOG,
  MOCK_CLOSURE_REPORT,
  MOCK_KPI,
  MOCK_NCS,
  MOCK_NOTIFICATIONS,
} from "../lib/mock-data";

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
  http.get("*/api/taxonomy", () => HttpResponse.json(taxonomy)),
  http.post("*/api/admin/reset-demo", () => HttpResponse.json({ ok: true, source: "synthetic mock" })),
  http.get("*/api/admin/verify-chain", () => HttpResponse.json({ ok: true, first_broken_index: null })),
  http.get("*/api/kpi", () => HttpResponse.json(MOCK_KPI)),
  http.get("*/api/kpi/effort-saved", () => HttpResponse.json([
    { metric: "NC logging", manual_baseline_minutes: 25, measured_minutes: 3, is_estimate: true },
    { metric: "Reporting", manual_baseline_minutes: 60, measured_minutes: 8, is_estimate: true },
  ])),
  http.get("*/api/ncs", ({ request }) => {
    const url = new URL(request.url);
    const status = url.searchParams.get("status");
    const severity = url.searchParams.get("severity");
    return HttpResponse.json(MOCK_NCS.filter((nc) => (!status || nc.status === status) && (!severity || nc.severity === severity)));
  }),
  http.get("*/api/ncs/:id", ({ params }) => {
    const nc = MOCK_NCS.find((item) => item.id === params.id);
    return nc ? HttpResponse.json(nc) : HttpResponse.json({ detail: "NC not found in synthetic demo data" }, { status: 404 });
  }),
  http.post("*/api/ncs", async ({ request }) => {
    const payload = await request.json() as Record<string, unknown>;
    return HttpResponse.json({ ...payload, id: payload.id ?? "NC-DEMO", status: "OPEN", raised_at: new Date().toISOString() }, { status: 201 });
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
  http.patch("*/api/tasks/:id", ({ params }) => HttpResponse.json({ id: Number(params.id), nc_id: "NC-0412", title: "Demo verification task", priority: 1, suggested_owner_role: "auditor", done: true })),
];
