"use client";
import { useState } from "react";
import {
  ShieldCheck, AlertTriangle, CheckCircle2, XCircle,
  ChevronRight, Hash, Calendar, ExternalLink,
} from "lucide-react";
import { StatusBadge } from "@/components/StatusBadge";
import { Timeline } from "@/components/Timeline";
import { EmptyState } from "@/components/EmptyState";
import { MOCK_NCS, MOCK_CLOSURE_REPORT, MOCK_AUDIT_LOG } from "@/lib/mock-data";
import { formatDate, formatDateTime } from "@/lib/utils";
import { cn } from "@/lib/utils";
import Link from "next/link";
import type { NC } from "@/lib/types";

type Decision = "approve" | "send_back" | "override" | null;

// Only NCs awaiting head approval
const PENDING = MOCK_NCS.filter((nc) => nc.status === "PENDING_HEAD_APPROVAL");

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
  onDecide,
}: {
  ncId: string;
  onDecide: (d: Decision) => void;
}) {
  const [decision, setDecision] = useState<Decision>(null);
  const [justification, setJustification] = useState("");
  const [submitted, setSubmitted] = useState(false);

  const submit = () => {
    if (!decision) return;
    if (decision === "override" && !justification.trim()) {
      alert("Justification required for Override.");
      return;
    }
    setSubmitted(true);
    onDecide(decision);
  };

  if (submitted) {
    return (
      <div className="flex items-center gap-2 rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-4 text-emerald-300">
        <CheckCircle2 size={16} />
        <span className="text-sm font-medium">Decision recorded and hash-chained in audit log.</span>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4 rounded-xl border border-white/10 bg-slate-900/60 p-5">
      <h4 className="text-sm font-semibold text-slate-200">Head Decision for {ncId}</h4>
      <div className="flex flex-wrap gap-2">
        {(["approve", "send_back", "override"] as const).map((d) => (
          <button
            key={d}
            id={`decision-${d}-${ncId}`}
            onClick={() => setDecision(d)}
            className={cn(
              "rounded-lg border px-4 py-2 text-sm font-medium transition-all",
              decision === d
                ? d === "approve"
                  ? "border-emerald-500 bg-emerald-500/20 text-emerald-300"
                  : d === "send_back"
                  ? "border-amber-500 bg-amber-500/20 text-amber-300"
                  : "border-red-500 bg-red-500/20 text-red-300"
                : "border-white/10 text-slate-400 hover:border-white/20 hover:text-slate-200"
            )}
          >
            {d === "approve" ? "✓ Approve" : d === "send_back" ? "↩ Send Back" : "⚠ Override"}
          </button>
        ))}
      </div>

      {decision === "override" && (
        <textarea
          id={`justification-${ncId}`}
          value={justification}
          onChange={(e) => setJustification(e.target.value)}
          placeholder="Justification required for override…"
          rows={3}
          className="w-full rounded-lg border border-white/10 bg-slate-800/60 px-3 py-2 text-sm text-slate-200 placeholder-slate-500 outline-none focus:border-electric/50"
        />
      )}

      <button
        id={`submit-decision-${ncId}`}
        disabled={!decision}
        onClick={submit}
        className="w-fit rounded-lg bg-electric px-5 py-2 text-sm font-semibold text-slate-900 transition-all hover:bg-electric-dim disabled:opacity-30"
      >
        Record Decision
      </button>
    </div>
  );
}

export function ApprovalsClient() {
  const [selected, setSelected] = useState<NC | null>(PENDING[0] ?? null);
  const [decided, setDecided] = useState<Decision>(null);
  const report = MOCK_CLOSURE_REPORT; // golden scenario

  const auditLogEvents = MOCK_AUDIT_LOG.map((e) => ({
    id: e.index,
    timestamp: e.created_at,
    title: e.event_type.replace(/_/g, " "),
    description: `Hash: ${e.hash.slice(0, 16)}…`,
    variant:
      e.event_type === "TRACE_VERDICT"
        ? ("trace" as const)
        : e.event_type === "HEAD_DECISION"
        ? ("info" as const)
        : ("default" as const),
  }));

  return (
    <div className="flex flex-col gap-6 animate-fade-in">
      {/* Header */}
      <div>
        <h2 className="text-xl font-bold text-white">Approval Cockpit</h2>
        <p className="text-xs text-slate-500 mt-0.5">Auditing Head final approval queue</p>
      </div>

      {PENDING.length === 0 ? (
        <EmptyState
          icon={<ShieldCheck />}
          title="No pending approvals"
          description="All NCs awaiting approval have been processed."
        />
      ) : (
        <div className="grid gap-4 lg:grid-cols-3">
          {/* Queue */}
          <div className="flex flex-col gap-2">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-500">
              Pending ({PENDING.length})
            </h3>
            {PENDING.map((nc) => (
              <button
                key={nc.id}
                id={`approval-queue-${nc.id}`}
                onClick={() => { setSelected(nc); setDecided(null); }}
                className={cn(
                  "flex flex-col gap-1.5 rounded-xl border p-4 text-left transition-all",
                  selected?.id === nc.id
                    ? "border-electric/40 bg-electric/5"
                    : "border-white/5 bg-slate-900/60 hover:border-white/10"
                )}
              >
                <div className="flex items-center justify-between">
                  <span className="font-mono text-xs font-bold text-electric">{nc.id}</span>
                  <StatusBadge value={nc.severity} />
                </div>
                <p className="text-sm font-medium text-slate-200 line-clamp-2">{nc.title}</p>
                <div className="flex items-center justify-between text-[10px] text-slate-500">
                  <span>{nc.product}</span>
                  <ChevronRight size={12} />
                </div>
              </button>
            ))}
          </div>

          {/* Detail panel */}
          {selected && (
            <div className="flex flex-col gap-4 lg:col-span-2">
              {/* NC info */}
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
                    { icon: <Hash size={10} />, label: "Line", value: selected.line ?? "—" },
                    { icon: <Calendar size={10} />, label: "Raised", value: formatDate(selected.raised_at) },
                    { icon: <Calendar size={10} />, label: "Target", value: selected.target_date ? formatDate(selected.target_date) : "—" },
                  ].map((f) => (
                    <div key={f.label} className="flex flex-col gap-0.5">
                      <span className="text-slate-500 flex items-center gap-1">{f.icon}{f.label}</span>
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
                  <span className="ml-auto text-[10px] text-slate-500">
                    {formatDateTime(report.generated_at)}
                  </span>
                </div>

                <VerdictBanner verdict={report.verdict} />

                {/* Findings */}
                <div className="mt-4 flex flex-col gap-3">
                  <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                    Findings ({report.findings.length})
                  </h4>
                  {report.findings.map((f) => (
                    <div
                      key={f.rule}
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
                            <span key={ref} className="rounded bg-slate-700 px-1.5 py-0.5 font-mono text-[10px] text-electric">
                              {ref}
                            </span>
                          ))}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>

                {/* Verification tasks */}
                <div className="mt-4 flex flex-col gap-3">
                  <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                    Verification Tasks ({report.tasks.length})
                  </h4>
                  {report.tasks.map((task, i) => (
                    <div
                      key={i}
                      className="flex items-start gap-3 rounded-lg border border-white/5 bg-slate-800/40 p-3"
                    >
                      <span
                        className={cn(
                          "mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full text-[10px] font-bold",
                          task.priority === 1 ? "bg-red-500/20 text-red-300" :
                          task.priority === 2 ? "bg-amber-500/20 text-amber-300" :
                          "bg-slate-700 text-slate-400"
                        )}
                      >
                        P{task.priority}
                      </span>
                      <div className="flex flex-col gap-0.5">
                        <p className="text-xs text-slate-300">{task.title}</p>
                        <StatusBadge value={task.suggested_owner_role} className="w-fit" />
                      </div>
                    </div>
                  ))}
                </div>

                {/* Linked NCs */}
                <div className="mt-4 flex flex-col gap-2">
                  <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                    Linked NCs ({report.links.length})
                  </h4>
                  {report.links.map((link) => (
                    <div
                      key={link.id}
                      className="flex items-center justify-between rounded-lg border border-white/5 bg-slate-800/40 p-3"
                    >
                      <div className="flex items-center gap-2">
                        <span className="font-mono text-xs text-electric">{link.a}</span>
                        <span className="text-slate-600">→</span>
                        <span className="font-mono text-xs text-electric">{link.b}</span>
                      </div>
                      <div className="flex items-center gap-3 text-xs">
                        <span className="text-slate-400">score</span>
                        <span className="font-mono font-semibold text-slate-200">
                          {(link.score * 100).toFixed(0)}%
                        </span>
                        <Link
                          href={`/graph?nc=${link.a}`}
                          className="text-electric hover:underline"
                        >
                          View graph →
                        </Link>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Decision form */}
              <DecisionForm ncId={selected.id} onDecide={setDecided} />

              {/* Audit log */}
              <div className="glass rounded-xl p-5">
                <h4 className="mb-4 text-sm font-semibold text-slate-200">Hash-Chained Audit Log</h4>
                <Timeline events={auditLogEvents} />
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
