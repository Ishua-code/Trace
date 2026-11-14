"use client";
import { use } from "react";
import { notFound } from "next/navigation";
import Link from "next/link";
import {
  ArrowLeft, Hash, Calendar, AlertTriangle, ExternalLink,
  FileText, CheckCircle2, XCircle, Clock, Zap,
} from "lucide-react";
import { MOCK_NCS, MOCK_CLOSURE_REPORT, MOCK_AUDIT_LOG } from "@/lib/mock-data";
import { StatusBadge } from "@/components/StatusBadge";
import { Timeline } from "@/components/Timeline";
import { formatDate, formatDateTime } from "@/lib/utils";

export default function NCDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const nc = MOCK_NCS.find((n) => n.id === decodeURIComponent(id));
  if (!nc) notFound();

  // Check if this NC has a closure report (golden scenario)
  const hasReport = nc.id === "NC-0412";
  const report = hasReport ? MOCK_CLOSURE_REPORT : null;

  const auditEvents = MOCK_AUDIT_LOG
    .filter((e) => (e.payload.nc_id as string) === nc.id)
    .map((e) => ({
      id: e.index,
      timestamp: e.created_at,
      title: e.event_type.replace(/_/g, " "),
      description: `Hash: ${e.hash.slice(0, 24)}…`,
      variant:
        e.event_type === "TRACE_VERDICT"
          ? ("trace" as const)
          : e.event_type === "HEAD_DECISION"
          ? ("info" as const)
          : e.event_type === "NC_RAISED"
          ? ("warning" as const)
          : ("default" as const),
    }));

  return (
    <div className="flex flex-col gap-6 animate-fade-in">
      {/* Back nav */}
      <div>
        <Link
          href="/ncs"
          className="inline-flex items-center gap-1.5 text-xs text-slate-400 hover:text-slate-200 transition-colors mb-4"
        >
          <ArrowLeft size={12} /> Back to Non-Conformances
        </Link>

        <div className="flex flex-wrap items-start gap-4 justify-between">
          <div>
            <div className="flex items-center gap-3 mb-1">
              <span className="font-mono text-2xl font-bold text-electric">{nc.id}</span>
              <StatusBadge value={nc.severity} />
              <StatusBadge value={nc.status} />
            </div>
            <h2 className="text-xl font-bold text-white">{nc.title}</h2>
          </div>

          {/* Quick actions */}
          <div className="flex gap-2 flex-wrap">
            {nc.status === "PENDING_HEAD_APPROVAL" && (
              <Link
                href="/approvals"
                className="flex items-center gap-2 rounded-lg bg-orange-500/10 border border-orange-500/30 px-4 py-2 text-sm font-medium text-orange-300 hover:bg-orange-500/20 transition-all"
              >
                <CheckCircle2 size={14} />
                Review in Approvals
              </Link>
            )}
            {hasReport && (
              <Link
                href="/graph"
                className="flex items-center gap-2 rounded-lg bg-electric/10 border border-electric/30 px-4 py-2 text-sm font-medium text-electric hover:bg-electric/20 transition-all"
              >
                <Zap size={14} />
                View TRACE Graph
              </Link>
            )}
          </div>
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        {/* Main detail */}
        <div className="flex flex-col gap-4 lg:col-span-2">
          {/* Description */}
          <div className="glass rounded-xl p-5">
            <h3 className="text-sm font-semibold text-slate-200 mb-3">Finding Description</h3>
            <p className="text-sm text-slate-300 leading-relaxed">{nc.description}</p>
          </div>

          {/* Metadata grid */}
          <div className="glass rounded-xl p-5">
            <h3 className="text-sm font-semibold text-slate-200 mb-4">Details</h3>
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
              {[
                { icon: <Hash size={12} />, label: "Product", value: nc.product },
                { icon: <Hash size={12} />, label: "Process", value: nc.process },
                { icon: <Hash size={12} />, label: "Line", value: nc.line ?? "—" },
                { icon: <Hash size={12} />, label: "Audit Type", value: nc.audit_type },
                { icon: <Hash size={12} />, label: "Machine", value: nc.machine ?? "—" },
                { icon: <Hash size={12} />, label: "Lot", value: nc.lot ?? "—" },
                { icon: <Hash size={12} />, label: "Defect Code", value: nc.defect_code ?? "—" },
                { icon: <Hash size={12} />, label: "Root Cause", value: nc.root_cause_category ?? "—" },
                { icon: <Calendar size={12} />, label: "Raised", value: formatDate(nc.raised_at) },
                { icon: <Calendar size={12} />, label: "Target Date", value: nc.target_date ? formatDate(nc.target_date) : "—" },
                { icon: <Calendar size={12} />, label: "Closed At", value: nc.closed_at ? formatDate(nc.closed_at) : "—" },
              ].map((f) => (
                <div key={f.label} className="flex flex-col gap-0.5">
                  <span className="flex items-center gap-1 text-[10px] text-slate-500 uppercase tracking-wide">
                    {f.icon} {f.label}
                  </span>
                  <span className="text-sm font-medium text-slate-200">{f.value}</span>
                </div>
              ))}
            </div>
          </div>

          {/* TRACE Closure Report — only for golden scenario */}
          {report && (
            <div className="glass rounded-xl p-5">
              <div className="mb-4 flex items-center gap-2">
                <div className="flex h-6 w-6 items-center justify-center rounded bg-electric/20 ring-1 ring-electric/40">
                  <span className="text-[10px] font-black text-electric">T</span>
                </div>
                <h3 className="text-sm font-semibold text-slate-200">TRACE Closure Risk Report</h3>
                <StatusBadge value={report.verdict} className="ml-auto" />
              </div>

              {/* Verdict banner */}
              <div className={`flex items-start gap-3 rounded-xl border p-4 mb-4 ${
                report.verdict === "HOLD"
                  ? "border-red-500/40 bg-red-500/10 text-red-300 glow-hold"
                  : report.verdict === "VERIFY"
                  ? "border-amber-500/40 bg-amber-500/10 text-amber-300 glow-verify"
                  : "border-emerald-500/40 bg-emerald-500/10 text-emerald-300 glow-clear"
              }`}>
                {report.verdict === "HOLD" ? <XCircle size={18} /> : report.verdict === "VERIFY" ? <AlertTriangle size={18} /> : <CheckCircle2 size={18} />}
                <div>
                  <p className="font-semibold">TRACE Verdict: {report.verdict}</p>
                  <p className="text-sm opacity-80">
                    {report.verdict === "HOLD"
                      ? "Engine detected unresolved failure links. Review before approving."
                      : report.verdict === "VERIFY"
                      ? "Engine found concerns requiring verification before closure."
                      : "Engine found no unresolved linked failures."}
                  </p>
                </div>
              </div>

              {/* Findings */}
              <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-2">
                Findings ({report.findings.length})
              </h4>
              <div className="flex flex-col gap-2 mb-4">
                {report.findings.map((f) => (
                  <div key={f.rule} className="flex gap-3 rounded-lg border border-white/5 bg-slate-800/40 p-3">
                    <span className="shrink-0 font-mono text-xs font-bold text-electric mt-0.5">{f.rule}</span>
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <StatusBadge value={f.severity} />
                        <span className="text-xs text-slate-300">{f.message}</span>
                      </div>
                      <div className="flex flex-wrap gap-1">
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

              {/* Linked NCs */}
              <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-2">
                Linked NCs ({report.links.length})
              </h4>
              <div className="flex flex-col gap-2">
                {report.links.map((link) => (
                  <div key={link.id} className="flex items-center justify-between rounded-lg border border-white/5 bg-slate-800/40 p-3">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs text-electric">{link.a}</span>
                      <span className="text-slate-600">→</span>
                      <span className="font-mono text-xs text-electric">{link.b}</span>
                    </div>
                    <div className="flex items-center gap-3 text-xs">
                      <span className="font-mono font-semibold text-slate-200">{(link.score * 100).toFixed(0)}%</span>
                      <Link href={`/graph?nc=${link.a}`} className="text-electric hover:underline flex items-center gap-1">
                        Graph <ExternalLink size={10} />
                      </Link>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Right sidebar */}
        <div className="flex flex-col gap-4">
          {/* Status card */}
          <div className="glass rounded-xl p-5">
            <h3 className="text-sm font-semibold text-slate-200 mb-3">Status</h3>
            <div className="flex flex-col gap-3">
              <div className="flex items-center justify-between">
                <span className="text-xs text-slate-500">Current Status</span>
                <StatusBadge value={nc.status} />
              </div>
              <div className="flex items-center justify-between">
                <span className="text-xs text-slate-500">Severity</span>
                <StatusBadge value={nc.severity} />
              </div>
              {nc.target_date && (
                <div className="flex items-center justify-between">
                  <span className="flex items-center gap-1 text-xs text-slate-500">
                    <Clock size={10} /> Target
                  </span>
                  <span className="text-xs font-medium text-slate-200">{formatDate(nc.target_date)}</span>
                </div>
              )}
            </div>
          </div>

          {/* Event log timeline */}
          {auditEvents.length > 0 && (
            <div className="glass rounded-xl p-5">
              <h3 className="text-sm font-semibold text-slate-200 mb-4 flex items-center gap-2">
                <FileText size={14} className="text-electric" />
                Event Timeline
              </h3>
              <Timeline events={auditEvents} />
              <Link
                href="/audit-log"
                className="mt-4 inline-flex items-center gap-1 text-xs text-electric hover:underline"
              >
                Full audit log <ExternalLink size={10} />
              </Link>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
