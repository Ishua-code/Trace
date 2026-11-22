"use client";
import { useCallback, useState, useEffect } from "react";
import {
  BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from "recharts";
import {
  AlertTriangle, CheckCircle2, Clock, TrendingUp, Users,
  ShieldCheck, FileText, RefreshCw,
} from "lucide-react";
import { KpiTile } from "@/components/KpiTile";
import { KpiSkeleton } from "@/components/EmptyState";
import { StatusBadge } from "@/components/StatusBadge";
import { api } from "@/lib/api";
import { usePersona } from "@/lib/persona";
import type { KPIOverview, NC } from "@/lib/types";
import { formatDate, daysOverdue } from "@/lib/utils";
import Link from "next/link";

const tooltipStyle = {
  contentStyle: {
    background: "#0a0f1e",
    border: "1px solid rgba(255,255,255,0.08)",
    borderRadius: "8px",
    color: "#e2e8f0",
    fontSize: "12px",
  },
  cursor: { fill: "rgba(0,229,255,0.05)" },
};

export function DashboardClient() {
  const { user } = usePersona();
  const [kpi, setKpi] = useState<KPIOverview | null>(null);
  const [recentNcs, setRecentNcs] = useState<NC[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    setError("");
    try {
      const [overview, ncs] = await Promise.all([api.kpi(), api.ncList()]);
      setKpi(overview);
      setRecentNcs(ncs.slice(0, 5));
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const initial = window.setTimeout(() => void refresh(), 0);
    const timer = window.setInterval(() => void refresh(), 30_000);
    return () => {
      window.clearTimeout(initial);
      window.clearInterval(timer);
    };
  }, [refresh, user]);

  if (!kpi) {
    return (
      <div className="glass flex flex-col items-center gap-3 rounded-xl p-8 text-center">
        <p role={error ? "alert" : "status"} className="text-sm text-slate-400">
          {error || "Loading live dashboard data…"}
        </p>
        {error && <button onClick={() => void refresh()} className="rounded-lg border border-white/10 px-3 py-2 text-xs text-slate-200 hover:border-electric/40">Try again</button>}
      </div>
    );
  }

  const AGEING_DATA = [
    { name: "0-7 days", value: kpi.ageing.d0_7, color: "#10b981" },
    { name: "8-14 days", value: kpi.ageing.d8_14, color: "#f59e0b" },
    { name: "15-30 days", value: kpi.ageing.d15_30, color: "#ef4444" },
    { name: "30+ days", value: kpi.ageing.d30_plus, color: "#7f1d1d" },
  ];

  return (
    <div className="flex flex-col gap-6 animate-fade-in">
      {/* ── Page header ── */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-white">Management Dashboard</h2>
          <p className="text-xs text-slate-500 mt-0.5">
            <span className="text-amber-400 font-medium">⚠ Synthetic data</span> — seeded demo dataset
          </p>
        </div>
        <div className="flex gap-2">
          <button onClick={() => void refresh()} className="flex items-center gap-2 rounded-lg border border-white/10 px-3 py-2 text-xs text-slate-300 hover:border-electric/40" aria-label="Refresh dashboard">
            <RefreshCw size={13} /> Refresh
          </button>
          <Link
            href="/approvals"
            className="flex items-center gap-2 rounded-lg border border-orange-500/30 bg-orange-500/10 px-4 py-2 text-sm font-medium text-orange-300 transition-all hover:bg-orange-500/20"
          >
            <ShieldCheck size={14} />
            {kpi.pending_approvals} Pending Approvals
          </Link>
        </div>
      </div>

      {/* ── KPI tiles ── */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 xl:grid-cols-4 stagger">
        {loading ? (
          Array.from({ length: 8 }).map((_, i) => <KpiSkeleton key={i} />)
        ) : (
          <>
            <KpiTile
              label="Plan vs Completed"
              value={kpi.plan_vs_completed_pct}
              unit="%"
              icon={<FileText size={16} />}
              trend="up"
              trendLabel="vs last month"
              highlight={kpi.plan_vs_completed_pct >= 80 ? "success" : "warn"}
            />
            <KpiTile
              label="Open NCs"
              value={kpi.open_count}
              icon={<AlertTriangle size={16} />}
              highlight="warn"
              onClick={() => window.location.assign("/ncs?status=OPEN")}
            />
            <KpiTile
              label="Overdue NCs"
              value={kpi.overdue_count}
              icon={<Clock size={16} />}
              trend="down"
              trendLabel="1 less than last week"
              upIsGood={false}
              highlight={kpi.overdue_count > 0 ? "danger" : "success"}
              onClick={() => window.location.assign("/ncs?overdue=true")}
            />
            <KpiTile
              label="Closed NCs"
              value={kpi.closed_count}
              icon={<CheckCircle2 size={16} />}
              trend="up"
              trendLabel="vs last month"
              highlight="success"
            />
            <KpiTile
              label="On-Time Closure"
              value={kpi.on_time_closure_pct}
              unit="%"
              icon={<TrendingUp size={16} />}
              highlight={kpi.on_time_closure_pct >= 80 ? "success" : "warn"}
            />
            <KpiTile
              label="Avg Closure Lead"
              value={kpi.avg_closure_lead_days}
              unit="days"
              icon={<Clock size={16} />}
            />
            <KpiTile
              label="Pending Approvals"
              value={kpi.pending_approvals}
              icon={<ShieldCheck size={16} />}
              highlight={kpi.pending_approvals > 0 ? "warn" : "success"}
              onClick={() => window.location.assign("/approvals")}
            />
            <KpiTile
              label="Active Auditors"
              value={kpi.auditors.length}
              icon={<Users size={16} />}
            />
          </>
        )}
      </div>

      {/* ── Charts row ── */}
      <div className="grid gap-4 lg:grid-cols-3">
        {/* Current workload, derived from the live KPI response */}
        <div className="glass rounded-xl p-5 lg:col-span-2">
          <div className="mb-4 flex items-center justify-between">
            <h3 className="text-sm font-semibold text-slate-200">Current NC Workload</h3>
            <span className="text-[10px] text-slate-500">Live API totals</span>
          </div>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={[{ name: "Open", value: kpi.open_count }, { name: "Overdue", value: kpi.overdue_count }, { name: "Closed", value: kpi.closed_count }]}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
              <XAxis dataKey="name" stroke="#475569" tick={{ fill: "#64748b", fontSize: 11 }} />
              <YAxis stroke="#475569" tick={{ fill: "#64748b", fontSize: 11 }} />
              <Tooltip contentStyle={tooltipStyle.contentStyle} />
              <Bar dataKey="value" name="NCs" fill="#00e5ff" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* NC Ageing donut */}
        <div className="glass rounded-xl p-5">
          <div className="mb-4 flex items-center justify-between">
            <h3 className="text-sm font-semibold text-slate-200">NC Ageing Buckets</h3>
            <span className="text-[10px] text-slate-500 italic">synthetic</span>
          </div>
          <ResponsiveContainer width="100%" height={160}>
            <PieChart>
              <Pie
                data={AGEING_DATA}
                cx="50%"
                cy="50%"
                innerRadius={45}
                outerRadius={70}
                paddingAngle={3}
                dataKey="value"
              >
                {AGEING_DATA.map((entry, i) => (
                  <Cell key={i} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip contentStyle={tooltipStyle.contentStyle} />
            </PieChart>
          </ResponsiveContainer>
          <div className="mt-2 flex flex-wrap gap-2">
            {AGEING_DATA.map((d) => (
              <div key={d.name} className="flex items-center gap-1 text-xs text-slate-400">
                <span className="h-2 w-2 rounded-full" style={{ background: d.color }} />
                {d.name}: <strong className="text-slate-200">{d.value}</strong>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* ── Effort saved + recent NCs ── */}
      <div className="grid gap-4 lg:grid-cols-3">
        <div className="glass rounded-xl p-5 lg:col-span-1">
          <h3 className="mb-2 text-sm font-semibold text-slate-200">Effort Saved</h3>
          <p className="text-xs leading-relaxed text-slate-400">This estimate will appear when measured workflow timings and the documented manual baseline are available from the API.</p>
          <span className="mt-3 inline-flex rounded-full border border-amber-500/20 bg-amber-500/5 px-2 py-1 text-[10px] text-amber-300">No measured estimate available</span>
        </div>

        {/* Recent NCs */}
        <div className="glass rounded-xl p-5 lg:col-span-2">
          <div className="mb-4 flex items-center justify-between">
            <h3 className="text-sm font-semibold text-slate-200">Recent Non-Conformances</h3>
            <Link href="/ncs" className="text-xs text-electric hover:underline">View all →</Link>
          </div>
          <div className="flex flex-col divide-y divide-white/5">
          {recentNcs.map((nc) => {
              const overdue = nc.target_date ? daysOverdue(nc.target_date) : 0;
              return (
                <Link
                  key={nc.id}
                  href={`/ncs/${nc.id}`}
                  className="flex items-center justify-between gap-4 py-3 transition-colors hover:bg-slate-800/40 -mx-5 px-5"
                >
                  <div className="flex flex-col gap-0.5 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs font-semibold text-electric shrink-0">{nc.id}</span>
                      <span className="truncate text-xs text-slate-300">{nc.title}</span>
                    </div>
                    <span className="text-[10px] text-slate-500">
                      {nc.product} · {nc.process} · Raised {formatDate(nc.raised_at)}
                    </span>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    {overdue > 0 && nc.status !== "CLOSED" && (
                      <span className="text-[10px] font-medium text-red-400">{overdue}d overdue</span>
                    )}
                    <StatusBadge value={nc.severity} />
                    <StatusBadge value={nc.status} />
                  </div>
                </Link>
              );
            })}
            {recentNcs.length === 0 && <p className="py-6 text-center text-xs text-slate-500">No recent non-conformances.</p>}
          </div>
        </div>
      </div>

      {/* ── Auditor / Auditee status ── */}
      <div className="grid gap-4 md:grid-cols-2">
        {[
          { label: "Auditor Status", items: kpi.auditors },
          { label: "Auditee Status", items: kpi.auditees },
        ].map(({ label, items }) => (
          <div key={label} className="glass rounded-xl p-5">
            <h3 className="mb-4 text-sm font-semibold text-slate-200">{label}</h3>
            <div className="flex flex-col gap-3">
              {items.map((p) => (
                <div key={p.user_id} className="flex items-center justify-between gap-4">
                  <div className="flex items-center gap-2">
                    <div className="flex h-7 w-7 items-center justify-center rounded-full bg-slate-700 text-xs font-bold text-slate-300">
                      {p.name[0]}
                    </div>
                    <span className="text-sm text-slate-300">{p.name}</span>
                  </div>
                  <div className="flex gap-3 text-xs">
                    <span className="text-amber-400">{p.open} open</span>
                    <span className="text-red-400">{p.overdue} overdue</span>
                    <span className="text-emerald-400">{p.closed} closed</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
