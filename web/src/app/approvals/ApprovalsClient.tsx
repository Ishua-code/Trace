"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  AlertTriangle,
  Calendar,
  CheckCircle2,
  ChevronRight,
  ExternalLink,
  Hash,
  Play,
  ShieldCheck,
  XCircle,
} from "lucide-react";
import { StatusBadge } from "@/components/StatusBadge";
import { Timeline } from "@/components/Timeline";
import { EmptyState } from "@/components/EmptyState";
import { api, type AuditEvent } from "@/lib/api";
import { usePersona } from "@/lib/persona";
import { cn, formatDate, formatDateTime } from "@/lib/utils";
import type { ClosureReport, NC } from "@/lib/types";

type Decision = "approve" | "send_back" | "override";

const QUEUE_STATUSES = ["PENDING_HEAD_APPROVAL", "TRACE_REVIEW", "AUDITOR_VERIFIED"] as const;
const GOLDEN_NC = "NC-0412";

function message(e: unknown): string {
  return e instanceof Error ? e.message : String(e);
}

function VerdictBanner({ verdict }: { verdict: "CLEAR" | "VERIFY" | "HOLD" }) {
  const cfg = {
    HOLD: {
      label: "TRACE Verdict: HOLD",
      desc: "Engine detected unresolved failure links. Review before approving.",
      class: "border-red-500/40 bg-red-500/10 text-red-300 glow-hold",
      icon: <XCircle size={18} />,
    },
    VERIFY: {
      label: "TRACE Verdict: VERIFY",
      desc: "Engine found concerns requiring verification before closure.",
      class: "border-amber-500/40 bg-amber-500/10 text-amber-300 glow-verify",
      icon: <AlertTriangle size={18} />,
    },
    CLEAR: {
      label: "TRACE Verdict: CLEAR",
      desc: "Engine found no unresolved linked failures.",
      class: "border-emerald-500/40 bg-emerald-500/10 text-emerald-300 glow-clear",
      icon: <CheckCircle2 size={18} />,
    },
  }[verdict];

  return (
    <div className={cn("flex items-start gap-3 rounded-xl border p-4", cfg.class)}>
      {cfg.icon}
      <div>
        <p className="font-semibold">{cfg.label}</p>
        <p className="text-sm opacity-80">{cfg.desc}</p>
      </div>
    </div>
  );
}

function DecisionForm({
  ncId,
  verdict,
  openTasks,
  onDone,
}: {
  ncId: string;
  verdict: string;
  openTasks: number;
  onDone: (summary: string) => void;
}) {
  const [decision, setDecision] = useState<Decision | null>(null);
  const [justification, setJustification] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const gateOpen = verdict !== "CLEAR" && openTasks > 0;

  async function submit() {
    if (!decision) return;
    const text = justification.trim();
    if (decision === "send_back" && !text) {
      setError("Please give a reason for sending the NC back.");
      return;
    }
    if (decision === "override" && text.length < 15) {
      setError("An override needs a typed justification of at least 15 characters.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      const r = await api.closureDecision(ncId, { decision, justification: text || undefined });
      onDone(
        `${r.id} is now ${r.status} (decision: ${r.decision}, TRACE verdict: ${r.verdict}, open tasks: ${r.open_tasks}). ` +
          `Recorded in the hash-chained audit log.`,
      );
    } catch (e) {
      setError(message(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex flex-col gap-4 rounded-xl border border-white/10 bg-slate-900/60 p-5">
      <h4 className="text-sm font-semibold text-slate-200">Head Decision for {ncId}</h4>

      {gateOpen && (
        <p className="rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-xs text-amber-300">
          The gate is {verdict} with {openTasks} open verification task(s). Approve is blocked until they are done.
          To close now, use Override with a typed justification.
        </p>
      )}

      <div className="flex flex-wrap gap-2">
        {(["approve", "send_back", "override"] as const).map((d) => (
          <button
            key={d}
            id={`decision-${d}-${ncId}`}
            onClick={() => {
              setDecision(d);
              setError("");
            }}
            className={cn(
              "rounded-lg border px-4 py-2 text-sm font-medium transition-all",
              decision === d
                ? d === "approve"
                  ? "border-emerald-500 bg-emerald-500/20 text-emerald-300"
                  : d === "send_back"
                  ? "border-amber-500 bg-amber-500/20 text-amber-300"
                  : "border-red-500 bg-red-500/20 text-red-300"
                : "border-white/10 text-slate-400 hover:border-white/20 hover:text-slate-200",
            )}
          >
            {d === "approve" ? "Approve" : d === "send_back" ? "Send Back" : "Override"}
          </button>
        ))}
      </div>

      {(decision === "override" || decision === "send_back") && (
        <textarea
          id={`justification-${ncId}`}
          value={justification}
          onChange={(e) => setJustification(e.target.value)}
          placeholder={
            decision === "override"
              ? "Justification for the override (at least 15 characters)..."
              : "Reason for sending the NC back..."
          }
          rows={3}
          className="w-full rounded-lg border border-white/10 bg-slate-800/60 px-3 py-2 text-sm text-slate-200 placeholder-slate-500 outline-none focus:border-electric/50"
        />
      )}

      {error && <p className="text-xs text-red-400">{error}</p>}

      <button
        id={`submit-decision-${ncId}`}
        disabled={!decision || busy}
        onClick={submit}
        className="w-fit rounded-lg bg-electric px-5 py-2 text-sm font-semibold text-slate-900 transition-all hover:bg-electric-dim disabled:opacity-30"
      >
        {busy ? "Recording..." : "Record Decision"}
      </button>
    </div>
  );
}

export function ApprovalsClient() {
  const { user } = usePersona();
  const [queue, setQueue] = useState<NC[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [report, setReport] = useState<ClosureReport | null>(null);
  const [reportError, setReportError] = useState("");
  const [simulating, setSimulating] = useState(false);
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [lastResult, setLastResult] = useState("");

  const isHead = user.role === "auditing_head" || user.role === "admin";
  const canSimulate = isHead || user.role === "auditor";

  const loadQueue = useCallback(async () => {
    setError("");
    try {
      const lists = await Promise.all(QUEUE_STATUSES.map((s) => api.ncList({ status: s, limit: 50 })));
      const all = lists.flat();
      all.sort((a, b) => {
        if (a.id === GOLDEN_NC) return -1;
        if (b.id === GOLDEN_NC) return 1;
        return QUEUE_STATUSES.indexOf(a.status as (typeof QUEUE_STATUSES)[number]) -
          QUEUE_STATUSES.indexOf(b.status as (typeof QUEUE_STATUSES)[number]);
      });
      setQueue(all);
      setSelectedId((cur) => (cur && all.some((n) => n.id === cur) ? cur : all[0]?.id ?? null));
    } catch (e) {
      setError(message(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadQueue();
  }, [loadQueue, user.id]);

  const selected = useMemo(() => queue.find((n) => n.id === selectedId) ?? null, [queue, selectedId]);
  const selectedStatus = selected?.status;

  const loadReport = useCallback(async (ncId: string) => {
    setReportError("");
    try {
      setReport(await api.closureWithLinks(ncId));
    } catch (e) {
      setReport(null);
      const msg = message(e);
      if (!msg.includes("404")) setReportError(msg);
    }
  }, []);

  const loadEvents = useCallback(async (ncId: string) => {
    try {
      setEvents(await api.auditLog({ nc_id: ncId, limit: 20 }));
    } catch {
      setEvents([]);
    }
  }, []);

  useEffect(() => {
    if (!selectedId) {
      setReport(null);
      setEvents([]);
      return;
    }
    setReport(null);
    if (selectedStatus === "PENDING_HEAD_APPROVAL") loadReport(selectedId);
    loadEvents(selectedId);
  }, [selectedId, selectedStatus, loadReport, loadEvents]);

  async function simulate() {
    if (!selected) return;
    setSimulating(true);
    setReportError("");
    try {
      setReport(await api.closureWithLinks(selected.id, true));
      await loadQueue();
      await loadEvents(selected.id);
    } catch (e) {
      setReportError(message(e));
    } finally {
      setSimulating(false);
    }
  }

  async function toggleTask(taskId: number | undefined, done: boolean) {
    if (taskId == null || !selected) return;
    try {
      if (done) await api.reopenTask(taskId);
      else await api.completeTask(taskId);
      await loadReport(selected.id);
      await loadEvents(selected.id);
    } catch (e) {
      setReportError(message(e));
    }
  }

  async function afterDecision(summary: string) {
    setLastResult(summary);
    await loadQueue();
  }

  const timeline = useMemo(
    () =>
      events.map((e) => ({
        id: e.index,
        timestamp: e.created_at,
        title: e.event_type.replace(/[._]/g, " "),
        description: `${e.actor_name ?? (e.actor_id != null ? `user ${e.actor_id}` : "system")} | Hash: ${e.hash.slice(0, 16)}...`,
        variant:
          e.event_type === "closure.simulated"
            ? ("trace" as const)
            : e.event_type.startsWith("closure.")
            ? ("info" as const)
            : ("default" as const),
      })),
    [events],
  );

  const openTasks = report ? report.tasks.filter((t) => !t.done).length : 0;

  return (
    <div className="flex flex-col gap-6 animate-fade-in">
      <div>
        <h2 className="text-xl font-bold text-white">Approval Cockpit</h2>
        <p className="text-xs text-slate-500 mt-0.5">
          Closure Gate: TRACE simulates the closure, the Auditing Head decides
        </p>
      </div>

      {lastResult && (
        <div className="flex items-start gap-2 rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-4 text-sm text-emerald-300">
          <CheckCircle2 size={16} className="mt-0.5 shrink-0" />
          <span>{lastResult}</span>
        </div>
      )}

      {loading && <p className="text-sm text-slate-400">Loading the approval queue...</p>}
      {error && <p className="text-sm text-red-400">Could not load the queue: {error}</p>}

      {!loading && !error && queue.length === 0 ? (
        <EmptyState
          icon={<ShieldCheck />}
          title="Nothing waiting for closure review"
          description="No NCs are auditor-verified or pending head approval."
        />
      ) : (
        !loading && (
          <div className="grid gap-4 lg:grid-cols-3">
            {/* Queue */}
            <div className="flex flex-col gap-2">
              <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                Closure queue ({queue.length})
              </h3>
              {queue.map((nc) => (
                <button
                  key={nc.id}
                  id={`approval-queue-${nc.id}`}
                  onClick={() => {
                    setSelectedId(nc.id);
                    setLastResult("");
                  }}
                  className={cn(
                    "flex flex-col gap-1.5 rounded-xl border p-4 text-left transition-all",
                    selectedId === nc.id
                      ? "border-electric/40 bg-electric/5"
                      : "border-white/5 bg-slate-900/60 hover:border-white/10",
                  )}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-xs font-bold text-electric">{nc.id}</span>
                    <StatusBadge value={nc.severity} />
                  </div>
                  <p className="text-sm font-medium text-slate-200 line-clamp-2">{nc.title}</p>
                  <div className="flex items-center justify-between text-[10px] text-slate-500">
                    <span>
                      {nc.product} | {nc.status.replace(/_/g, " ")}
                    </span>
                    <ChevronRight size={12} />
                  </div>
                </button>
              ))}
            </div>

            {/* Detail panel */}
            {selected && (
              <div className="flex flex-col gap-4 lg:col-span-2">
                <div className="glass rounded-xl p-5">
                  <div className="mb-4 flex items-start justify-between gap-4">
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <span className="font-mono text-lg font-bold text-electric">{selected.id}</span>
                        <StatusBadge value={selected.status} />
                        <StatusBadge value={selected.severity} />
                      </div>
                      <h3 className="text-base font-semibold text-white">{selected.title}</h3>
                      <p className="text-sm text-slate-400 mt-1">{selected.description}</p>
                    </div>
                    <Link
                      href={`/ncs/${selected.id}`}
                      className="shrink-0 text-xs text-electric hover:underline flex items-center gap-1"
                    >
                      Full NC <ExternalLink size={10} />
                    </Link>
                  </div>
                  <div className="grid grid-cols-2 gap-3 text-xs sm:grid-cols-3">
                    {[
                      { icon: <Hash size={10} />, label: "Product", value: selected.product },
                      { icon: <Hash size={10} />, label: "Process", value: selected.process },
                      { icon: <Hash size={10} />, label: "Line", value: selected.line ?? "-" },
                      { icon: <Calendar size={10} />, label: "Raised", value: formatDate(selected.raised_at) },
                      {
                        icon: <Calendar size={10} />,
                        label: "Target",
                        value: selected.target_date ? formatDate(selected.target_date) : "-",
                      },
                    ].map((f) => (
                      <div key={f.label} className="flex flex-col gap-0.5">
                        <span className="text-slate-500 flex items-center gap-1">
                          {f.icon}
                          {f.label}
                        </span>
                        <span className="text-slate-200 font-medium">{f.value}</span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* TRACE Closure Risk Report */}
                <div className="glass rounded-xl p-5">
                  <div className="mb-4 flex items-center gap-2">
                    <div className="flex h-6 w-6 items-center justify-center rounded bg-electric/20 ring-1 ring-electric/40">
                      <span className="text-[10px] font-black text-electric">T</span>
                    </div>
                    <h3 className="text-sm font-semibold text-slate-200">TRACE Closure Risk Report</h3>
                    {report && (
                      <span className="ml-auto text-[10px] text-slate-500">
                        {formatDateTime(report.generated_at)}
                      </span>
                    )}
                  </div>

                  {reportError && <p className="mb-3 text-xs text-red-400">{reportError}</p>}

                  {!report && selected.status !== "PENDING_HEAD_APPROVAL" && (
                    <div className="flex flex-col items-start gap-3">
                      <p className="text-sm text-slate-400">
                        The auditor has verified this NC. Run the TRACE closure simulation to see what could still go
                        wrong if it is closed now.
                      </p>
                      {canSimulate ? (
                        <button
                          id={`simulate-${selected.id}`}
                          onClick={simulate}
                          disabled={simulating}
                          className="flex items-center gap-2 rounded-lg bg-electric px-5 py-2 text-sm font-semibold text-slate-900 transition-all hover:bg-electric-dim disabled:opacity-40"
                        >
                          <Play size={14} />
                          {simulating ? "Simulating..." : "Run TRACE closure simulation"}
                        </button>
                      ) : (
                        <p className="text-xs text-slate-500">Only audit staff can run the simulation.</p>
                      )}
                    </div>
                  )}

                  {report && (
                    <>
                      <VerdictBanner verdict={report.verdict} />

                      <div className="mt-4 flex flex-col gap-3">
                        <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                          Findings ({report.findings.length})
                        </h4>
                        {report.findings.length === 0 && (
                          <p className="text-xs text-slate-500">No findings.</p>
                        )}
                        {report.findings.map((f, i) => (
                          <div
                            key={`${f.rule}-${i}`}
                            className="flex gap-3 rounded-lg border border-white/5 bg-slate-800/40 p-3"
                          >
                            <span className="shrink-0 font-mono text-xs font-bold text-electric mt-0.5">{f.rule}</span>
                            <div className="flex flex-col gap-1">
                              <div className="flex items-center gap-2">
                                <StatusBadge value={f.severity} />
                                <span className="text-xs text-slate-300">{f.message}</span>
                              </div>
                              <div className="flex flex-wrap gap-1 mt-1">
                                {f.evidence_refs.map((ref) => (
                                  <span
                                    key={ref}
                                    className="rounded bg-slate-700 px-1.5 py-0.5 font-mono text-[10px] text-electric"
                                  >
                                    {ref}
                                  </span>
                                ))}
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>

                      <div className="mt-4 flex flex-col gap-3">
                        <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                          Verification Tasks ({report.tasks.length}, {openTasks} open)
                        </h4>
                        {report.tasks.map((task, i) => (
                          <div
                            key={task.id ?? i}
                            className="flex items-start gap-3 rounded-lg border border-white/5 bg-slate-800/40 p-3"
                          >
                            <span
                              className={cn(
                                "mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-[10px] font-bold",
                                task.priority === 1
                                  ? "bg-red-500/20 text-red-300"
                                  : task.priority === 2
                                  ? "bg-amber-500/20 text-amber-300"
                                  : "bg-slate-700 text-slate-400",
                              )}
                            >
                              P{task.priority}
                            </span>
                            <div className="flex flex-1 flex-col gap-0.5">
                              <p className={cn("text-xs text-slate-300", task.done && "line-through opacity-60")}>
                                {task.title}
                              </p>
                              <StatusBadge value={task.suggested_owner_role} className="w-fit" />
                            </div>
                            {isHead && (
                              <button
                                id={`task-${task.id}`}
                                onClick={() => toggleTask(task.id, task.done)}
                                className={cn(
                                  "shrink-0 rounded-md border px-2.5 py-1 text-[11px] font-medium transition-colors",
                                  task.done
                                    ? "border-emerald-500/40 bg-emerald-500/10 text-emerald-300"
                                    : "border-white/10 text-slate-400 hover:text-slate-200",
                                )}
                              >
                                {task.done ? "Done" : "Mark done"}
                              </button>
                            )}
                          </div>
                        ))}
                      </div>

                      <div className="mt-4 flex flex-col gap-2">
                        <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                          Linked NCs ({report.links.length})
                        </h4>
                        {report.links.map((link, i) => (
                          <div
                            key={link.id ?? i}
                            className="flex items-center justify-between rounded-lg border border-white/5 bg-slate-800/40 p-3"
                          >
                            <div className="flex items-center gap-2">
                              <span className="font-mono text-xs text-electric">{link.a}</span>
                              <span className="text-slate-600">-</span>
                              <span className="font-mono text-xs text-electric">{link.b}</span>
                            </div>
                            <div className="flex items-center gap-3 text-xs">
                              <span className="text-slate-400">score</span>
                              <span className="font-mono font-semibold text-slate-200">
                                {(link.score * 100).toFixed(0)}%
                              </span>
                              <Link href={`/graph?nc=${link.a}`} className="text-electric hover:underline">
                                View graph
                              </Link>
                            </div>
                          </div>
                        ))}
                      </div>
                    </>
                  )}
                </div>

                {/* Decision */}
                {report && selected.status === "PENDING_HEAD_APPROVAL" && isHead && (
                  <DecisionForm
                    key={selected.id}
                    ncId={selected.id}
                    verdict={report.verdict}
                    openTasks={openTasks}
                    onDone={afterDecision}
                  />
                )}
                {report && selected.status === "PENDING_HEAD_APPROVAL" && !isHead && (
                  <p className="text-xs text-slate-500">Only the Auditing Head can record the decision.</p>
                )}

                {/* Audit log for this NC */}
                <div className="glass rounded-xl p-5">
                  <h4 className="mb-4 text-sm font-semibold text-slate-200">
                    Hash-Chained Audit Log for {selected.id}
                  </h4>
                  {timeline.length === 0 ? (
                    <p className="text-xs text-slate-500">No events recorded for this NC yet.</p>
                  ) : (
                    <Timeline events={timeline} />
                  )}
                </div>
              </div>
            )}
          </div>
        )
      )}
    </div>
  );
}
