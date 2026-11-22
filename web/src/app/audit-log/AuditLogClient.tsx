"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { ShieldCheck } from "lucide-react";
import { Timeline } from "@/components/Timeline";
import { api, type AuditEvent } from "@/lib/api";
import { formatDateTime } from "@/lib/utils";

type Variant = "trace" | "info" | "warning" | "default";

function variantFor(eventType: string): Variant {
  if (eventType === "closure.simulated") return "trace";
  if (eventType.startsWith("closure.")) return "info";
  if (eventType === "nc.created") return "warning";
  return "default";
}

function message(e: unknown): string {
  return e instanceof Error ? e.message : String(e);
}

export default function AuditLogClient() {
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [checking, setChecking] = useState(false);
  const [chain, setChain] = useState<{ ok: boolean; text: string } | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const page = await api.auditLogPage({ limit: 100 });
      setEvents(page.items);
      setTotal(page.total);
    } catch (e) {
      setError(message(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function verify() {
    setChecking(true);
    setChain(null);
    try {
      const r = await api.verifyChain();
      setChain(
        r.ok
          ? { ok: true, text: `Chain valid: ${r.checked ?? total} events checked, no tampering detected.` }
          : { ok: false, text: `Chain BROKEN at event #${r.first_broken_index ?? "?"}.` },
      );
    } catch (e) {
      setChain({ ok: false, text: `Could not verify the chain: ${message(e)}` });
    } finally {
      setChecking(false);
    }
  }

  const timeline = useMemo(
    () =>
      events.map((e) => ({
        id: e.index,
        timestamp: e.created_at,
        title: e.event_type.replace(/[._]/g, " "),
        description: e.payload && e.payload.nc_id
          ? `NC: ${String(e.payload.nc_id)} | Hash: ${e.hash.slice(0, 24)}...`
          : `Hash: ${e.hash.slice(0, 24)}...`,
        variant: variantFor(e.event_type),
      })),
    [events],
  );

  return (
    <div className="flex flex-col gap-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-white">Audit Log</h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Hash-chained event trail, tamper detection ({total} events)
          </p>
        </div>
        <button
          id="verify-chain-btn"
          onClick={verify}
          disabled={checking}
          className="flex items-center gap-2 rounded-lg border border-electric/30 bg-electric/10 px-4 py-2 text-sm font-medium text-electric hover:bg-electric/20 transition-colors disabled:opacity-50"
        >
          <ShieldCheck size={14} />
          {checking ? "Verifying..." : "Verify Chain"}
        </button>
      </div>

      {chain && (
        <div
          className={
            chain.ok
              ? "rounded-lg border border-emerald-500/30 bg-emerald-500/10 px-4 py-3 text-xs text-emerald-300"
              : "rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-xs text-red-300"
          }
        >
          {chain.text}
        </div>
      )}

      {loading && <p className="text-sm text-slate-400">Loading audit log...</p>}
      {error && <p className="text-sm text-red-400">Could not load the audit log: {error}</p>}
      {!loading && !error && events.length === 0 && (
        <p className="text-sm text-slate-500">
          No events yet. Events appear when NCs are created, verified, closed or escalated.
        </p>
      )}

      {events.length > 0 && (
        <>
          <div className="glass rounded-xl p-6">
            <Timeline events={timeline} />
          </div>

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
                  {events.map((e) => (
                    <tr key={e.index} className="border-b border-white/5 hover:bg-slate-800/40">
                      <td className="py-2 pr-4 font-mono text-slate-500">{e.index}</td>
                      <td className="py-2 pr-4 text-slate-300">{e.event_type}</td>
                      <td className="py-2 pr-4 text-slate-400">
                        {e.actor_name ?? (e.actor_id != null ? `user ${e.actor_id}` : "SYSTEM")}
                      </td>
                      <td className="py-2 pr-4 text-slate-500">{formatDateTime(e.created_at)}</td>
                      <td className="py-2 font-mono text-electric">{e.hash.slice(0, 20)}...</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
