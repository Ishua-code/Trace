import type { Metadata } from "next";
export const metadata: Metadata = { title: "Audit Log" };

import { MOCK_AUDIT_LOG } from "@/lib/mock-data";
import { Timeline } from "@/components/Timeline";
import { formatDateTime } from "@/lib/utils";
import { ShieldCheck } from "lucide-react";

export default function AuditLogPage() {
  const events = MOCK_AUDIT_LOG.map((e) => ({
    id: e.index,
    timestamp: e.created_at,
    title: e.event_type.replace(/_/g, " "),
    description: e.payload.nc_id
      ? `NC: ${e.payload.nc_id}  ·  Hash: ${e.hash.slice(0, 24)}…`
      : `Hash: ${e.hash.slice(0, 24)}…`,
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
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-white">Audit Log</h2>
          <p className="text-xs text-slate-500 mt-0.5">Hash-chained event trail — tamper detection</p>
        </div>
        <button
          id="verify-chain-btn"
          className="flex items-center gap-2 rounded-lg border border-electric/30 bg-electric/10 px-4 py-2 text-sm font-medium text-electric hover:bg-electric/20 transition-colors"
        >
          <ShieldCheck size={14} />
          Verify Chain
        </button>
      </div>

      <div className="glass rounded-xl p-6">
        <Timeline events={events} />
      </div>

      {/* Hash details table */}
      <div className="glass rounded-xl p-5">
        <h3 className="mb-4 text-sm font-semibold text-slate-200">Raw Log Entries</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-white/5 text-left text-slate-500">
                <th className="pb-2 pr-4">#</th>
                <th className="pb-2 pr-4">Event</th>
                <th className="pb-2 pr-4">Actor</th>
                <th className="pb-2 pr-4">Time</th>
                <th className="pb-2">Hash (truncated)</th>
              </tr>
            </thead>
            <tbody>
              {MOCK_AUDIT_LOG.map((e) => (
                <tr key={e.index} className="border-b border-white/5 hover:bg-slate-800/40">
                  <td className="py-2 pr-4 font-mono text-slate-500">{e.index}</td>
                  <td className="py-2 pr-4 text-slate-300">{e.event_type}</td>
                  <td className="py-2 pr-4 text-slate-400">{e.actor_id ?? "SYSTEM"}</td>
                  <td className="py-2 pr-4 text-slate-500">{formatDateTime(e.created_at)}</td>
                  <td className="py-2 font-mono text-electric">{e.hash.slice(0, 20)}…</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
