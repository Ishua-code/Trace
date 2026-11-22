"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Bell, Play } from "lucide-react";
import { api, type OutboxItem } from "@/lib/api";
import { usePersona } from "@/lib/persona";
import { cn, formatDateTime } from "@/lib/utils";

const KIND_STYLES: Record<string, string> = {
  reminder: "border-amber-500/30 bg-amber-500/10 text-amber-300",
  escalation_l1: "border-orange-500/30 bg-orange-500/10 text-orange-300",
  escalation_l2: "border-red-500/30 bg-red-500/10 text-red-300",
  assignment: "border-blue-500/30 bg-blue-500/10 text-blue-300",
};

const FILTERS: { key: string; label: string }[] = [
  { key: "all", label: "All" },
  { key: "reminder", label: "Reminders" },
  { key: "escalation_l1", label: "Escalation L1" },
  { key: "escalation_l2", label: "Escalation L2" },
];

const MAX_SHOWN = 150;

function message(e: unknown): string {
  return e instanceof Error ? e.message : String(e);
}

export default function NotificationsClient() {
  const { user } = usePersona();
  const [items, setItems] = useState<OutboxItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [filter, setFilter] = useState("all");
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      setItems(await api.notifications());
    } catch (e) {
      setError(message(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load, user.id]);

  const counts = useMemo(() => {
    const c: Record<string, number> = { all: items.length };
    for (const n of items) c[n.kind] = (c[n.kind] ?? 0) + 1;
    return c;
  }, [items]);

  const shown = useMemo(
    () => (filter === "all" ? items : items.filter((n) => n.kind === filter)),
    [items, filter],
  );

  const canRun = user.role === "auditing_head" || user.role === "admin";

  async function runNow() {
    setRunning(true);
    setResult("");
    try {
      const r = await api.runEscalation(false);
      const c = r.created;
      setResult(
        `Escalation run complete: ${r.total_created} new (T-3: ${c["T-3"] ?? 0}, due: ${c["DUE"] ?? 0}, ` +
          `L1: ${c["L1"] ?? 0}, L2: ${c["L2"] ?? 0}); ${r.skipped_existing} already sent.`,
      );
      await load();
    } catch (e) {
      setResult(`Could not run escalation: ${message(e)}`);
    } finally {
      setRunning(false);
    }
  }

  return (
    <div className="flex flex-col gap-6 animate-fade-in">
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-2">
          <Bell size={18} className="text-electric" />
          <h2 className="text-xl font-bold text-white">Notifications</h2>
          <span className="text-xs text-slate-500">Outbox ({counts.all ?? 0})</span>
        </div>
        {canRun && (
          <button
            id="run-escalation-btn"
            onClick={runNow}
            disabled={running}
            className="flex items-center gap-2 rounded-lg border border-electric/30 bg-electric/10 px-4 py-2 text-sm font-medium text-electric hover:bg-electric/20 transition-colors disabled:opacity-50"
          >
            <Play size={14} />
            {running ? "Running..." : "Run escalation now"}
          </button>
        )}
      </div>

      {result && (
        <div className="rounded-lg border border-white/10 bg-slate-800/40 px-4 py-3 text-xs text-slate-300">
          {result}
        </div>
      )}

      <div className="flex flex-wrap gap-2">
        {FILTERS.map((f) => (
          <button
            key={f.key}
            onClick={() => setFilter(f.key)}
            className={cn(
              "rounded-full border px-3 py-1 text-xs font-medium transition-colors",
              filter === f.key
                ? "border-electric/40 bg-electric/10 text-electric"
                : "border-white/10 text-slate-400 hover:text-slate-200",
            )}
          >
            {f.label} ({counts[f.key] ?? 0})
          </button>
        ))}
      </div>

      {loading && <p className="text-sm text-slate-400">Loading notifications...</p>}
      {error && <p className="text-sm text-red-400">Could not load notifications: {error}</p>}
      {!loading && !error && shown.length === 0 && (
        <p className="text-sm text-slate-500">
          No notifications yet. Use "Run escalation now" to generate reminders and escalations.
        </p>
      )}

      <div className="flex flex-col gap-3">
        {shown.slice(0, MAX_SHOWN).map((n) => (
          <div
            key={n.id}
            className={cn(
              "flex flex-col gap-1.5 rounded-xl border p-4",
              KIND_STYLES[n.kind] ?? "border-white/10 text-slate-300",
            )}
          >
            <div className="flex items-start justify-between gap-4">
              <span className="text-sm font-semibold">{n.subject}</span>
              <div className="flex items-center gap-2 shrink-0">
                <span className="rounded-full border border-current px-2 py-0.5 text-[10px] font-semibold uppercase">
                  {n.kind.replace(/_/g, " ")}
                </span>
                {n.nc_id && <span className="font-mono text-xs opacity-70">{n.nc_id}</span>}
              </div>
            </div>
            <p className="text-xs opacity-80">{n.body}</p>
            <div className="flex items-center justify-between text-[10px] opacity-60">
              <span>To: {n.to_name ?? `user ${n.to_user_id}`}</span>
              <time>{formatDateTime(n.sent_at)}</time>
            </div>
          </div>
        ))}
      </div>

      {shown.length > MAX_SHOWN && (
        <p className="text-xs text-slate-500">
          Showing the newest {MAX_SHOWN} of {shown.length}. Use the filters to narrow the list.
        </p>
      )}
    </div>
  );
}
