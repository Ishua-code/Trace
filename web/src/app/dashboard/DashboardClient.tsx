"use client";
import { useState, useEffect } from "react";
import {
  AreaChart, Area, BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
} from "recharts";
import {
  AlertTriangle, CheckCircle2, Clock, TrendingUp, Users,
  ShieldCheck, FileText, Zap,
} from "lucide-react";
import { KpiTile } from "@/components/KpiTile";
import { KpiSkeleton } from "@/components/EmptyState";
import { StatusBadge } from "@/components/StatusBadge";
import { api } from "@/lib/api";
import { usePersona } from "@/lib/persona";
import type { KPIOverview, NC } from "@/lib/types";
import { formatDate, daysOverdue } from "@/lib/utils";
import Link from "next/link";

// ---- Mock trend data (synthetic — clearly labelled) -----------------------
const TREND_DATA = [
  { month: "May", open: 12, closed: 8, overdue: 4 },
  { month: "Jun", open: 9, closed: 14, overdue: 3 },
  { month: "Jul", open: 11, closed: 10, overdue: 5 },
  { month: "Aug", open: 7, closed: 13, overdue: 2 },
  { month: "Sep", open: 10, closed: 11, overdue: 4 },
  { month: "Oct", open: 8, closed: 15, overdue: 3 },
];

const EFFORT_DATA = [
  { metric: "NC Logging", manual: 25, trace: 3 },
  { metric: "Follow-up", manual: 40, trace: 5 },
  { metric: "Reporting", manual: 60, trace: 8 },
  { metric: "Escalation", manual: 20, trace: 2 },
];

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
  const loading = false;

  useEffect(() => {
    api.kpi().then(setKpi).catch((e) => setError(String(e)));
    api.ncList().then((l) => setRecentNcs(l.slice(0, 5))).catch(() => {});
  }, [user]);

  if (!kpi) {
    return <div className="p-6 text-slate-400">{error || "Loading real data..."}</div>;
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
        {/* NC Trend */}
        <div className="glass rounded-xl p-5 lg:col-span-2">
          <div className="mb-4 flex items-center justify-between">
            <h3 className="text-sm font-semibold text-slate-200">NC Trend (6 months)</h3>
            <span className="text-[10px] text-slate-500 italic">synthetic data</span>
          </div>
          <ResponsiveContainer width="100%" height={200}>
            <AreaChart data={TREND_DATA}>
              <defs>
                <linearGradient id="gOpen" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#f59e0b" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="gClosed" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
              <XAxis dataKey="month" stroke="#475569" tick={{ fill: "#64748b", fontSize: 11 }} />
              <YAxis stroke="#475569" tick={{ fill: "#64748b", fontSize: 11 }} />
              <Tooltip contentStyle={tooltipStyle.contentStyle} />
              <Legend wrapperStyle={{ fontSize: 11, color: "#94a3b8" }} />
              <Area type="monotone" dataKey="open" stroke="#f59e0b" fill="url(#gOpen)" strokeWidth={2} name="Open" />
              <Area type="monotone" dataKey="closed" stroke="#10b981" fill="url(#gClosed)" strokeWidth={2} name="Closed" />
            </AreaChart>
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
        {/* Effort saved bar chart */}
        <div className="glass rounded-xl p-5">
          <div className="mb-4 flex items-center gap-2">
            <Zap size={14} className="text-electric" />
            <h3 className="text-sm font-semibold text-slate-200">Effort Saved (est. min/NC)</h3>
          </div>
          <span className="mb-3 block text-[10px] text-slate-500 italic">
            Manual baseline documented assumption — SYNTHETIC
          </span>
          <ResponsiveContainer width="100%" height={160}>
            <BarChart data={EFFORT_DATA} barCategoryGap="30%">
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
              <XAxis dataKey="metric" stroke="#475569" tick={{ fill: "#64748b", fontSize: 10 }} />
              <YAxis stroke="#475569" tick={{ fill: "#64748b", fontSize: 10 }} />
              <Tooltip contentStyle={tooltipStyle.contentStyle} />
              <Bar dataKey="manual" name="Manual" fill="#334155" radius={[4, 4, 0, 0]} />
              <Bar dataKey="trace" name="TRACE" fill="#00e5ff" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
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
