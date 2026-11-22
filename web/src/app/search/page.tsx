"use client";
import type { Metadata } from "next";
import { useState, useMemo } from "react";
import { Search, Filter, Download, FileText, AlertTriangle } from "lucide-react";
import Link from "next/link";
import { MOCK_NCS, MOCK_AUDIT_LOG } from "@/lib/mock-data";
import { StatusBadge } from "@/components/StatusBadge";
import { formatDate } from "@/lib/utils";
import { cn } from "@/lib/utils";

type SearchCategory = "ncs" | "events" | "all";

export default function SearchPage() {
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState<SearchCategory>("all");
  const [severityFilter, setSeverityFilter] = useState("all");

  const normalised = query.toLowerCase().trim();

  const matchedNCs = useMemo(() => {
    if (!normalised) return MOCK_NCS;
    return MOCK_NCS.filter((nc) => {
      const fields = [nc.id, nc.title, nc.description, nc.product, nc.process,
        nc.line, nc.machine, nc.lot, nc.defect_code, nc.root_cause_category, nc.status];
      return fields.some((f) => f?.toLowerCase().includes(normalised));
    }).filter((nc) => severityFilter === "all" || nc.severity === severityFilter);
  }, [normalised, severityFilter]);

  const matchedEvents = useMemo(() => {
    if (!normalised) return MOCK_AUDIT_LOG;
    return MOCK_AUDIT_LOG.filter((e) => {
      const payload = JSON.stringify(e.payload).toLowerCase();
      return e.event_type.toLowerCase().includes(normalised) || payload.includes(normalised);
    });
  }, [normalised]);

  const totalResults = (category === "ncs" ? matchedNCs.length : 0)
    + (category === "events" ? matchedEvents.length : 0)
    + (category === "all" ? matchedNCs.length + matchedEvents.length : 0);

  const exportCSV = () => {
    const header = ["NC ID", "Title", "Severity", "Status", "Product", "Process", "Raised"];
    const rows = matchedNCs.map((nc) => [
      nc.id, nc.title, nc.severity, nc.status, nc.product, nc.process, formatDate(nc.raised_at),
    ]);
    const csv = [header, ...rows].map((r) => r.join(",")).join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `trace_search_${Date.now()}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="flex flex-col gap-6 animate-fade-in">
      <div>
        <h2 className="text-xl font-bold text-white">Global Search</h2>
        <p className="text-xs text-slate-500 mt-0.5">Search NCs, audit events, evidence — wired to <code className="text-electric">/api/search</code> once backend lands</p>
      </div>

      {/* Search bar */}
      <div className="glass rounded-xl p-4">
        <div className="relative">
          <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
          <input
            id="global-search-input"
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search NC IDs, descriptions, products, processes, events…"
            className="w-full rounded-lg border border-white/10 bg-slate-800/60 py-2.5 pl-9 pr-4 text-sm text-slate-200 placeholder-slate-500 outline-none focus:border-electric/50 focus:ring-1 focus:ring-electric/30 transition-all"
            autoFocus
          />
        </div>

        {/* Filters row */}
        <div className="mt-3 flex flex-wrap items-center gap-3">
          {/* Category tabs */}
          <div className="flex gap-1 rounded-lg border border-white/10 bg-slate-900 p-0.5">
            {(["all", "ncs", "events"] as SearchCategory[]).map((cat) => (
              <button
                key={cat}
                id={`search-cat-${cat}`}
                onClick={() => setCategory(cat)}
                className={cn(
                  "rounded-md px-3 py-1 text-xs font-medium transition-all",
                  category === cat
                    ? "bg-electric/20 text-electric"
                    : "text-slate-400 hover:text-slate-200"
                )}
              >
                {cat === "all" ? "All" : cat === "ncs" ? "NCs" : "Events"}
              </button>
            ))}
          </div>

          {/* Severity filter */}
          {(category === "all" || category === "ncs") && (
            <div className="flex gap-1">
              {["all", "minor", "major", "critical"].map((s) => (
                <button
                  key={s}
                  id={`search-sev-${s}`}
                  onClick={() => setSeverityFilter(s)}
                  className={cn(
                    "flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs font-medium transition-all",
                    severityFilter === s
                      ? "border-electric/50 bg-electric/10 text-electric"
                      : "border-white/10 text-slate-400 hover:border-white/20 hover:text-slate-200"
                  )}
                >
                  <Filter size={9} />
                  {s}
                </button>
              ))}
            </div>
          )}

          <div className="ml-auto flex items-center gap-2 text-xs text-slate-500">
            {normalised && <span>{totalResults} results</span>}
            {matchedNCs.length > 0 && (
              <button
                id="export-search-btn"
                onClick={exportCSV}
                className="flex items-center gap-1 rounded-lg border border-white/10 bg-slate-800/60 px-3 py-1.5 text-slate-400 hover:text-slate-200 transition-colors"
              >
                <Download size={12} />
                CSV
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Results */}
      {!normalised && (
        <div className="text-center py-12 text-slate-500">
          <Search size={40} className="mx-auto mb-3 opacity-30" />
          <p className="text-sm">Type to search across NCs and audit events</p>
          <p className="text-xs mt-1 opacity-60">Synthetic data — {MOCK_NCS.length} NCs, {MOCK_AUDIT_LOG.length} events</p>
        </div>
      )}

      {normalised && (
        <div className="flex flex-col gap-4">
          {/* NCs section */}
          {(category === "all" || category === "ncs") && (
            <div className="flex flex-col gap-3">
              <div className="flex items-center gap-2">
                <AlertTriangle size={14} className="text-amber-400" />
                <h3 className="text-sm font-semibold text-slate-200">Non-Conformances</h3>
                <span className="text-xs text-slate-500">({matchedNCs.length})</span>
              </div>
              {matchedNCs.length === 0 ? (
                <div className="glass rounded-xl p-6 text-center text-xs text-slate-500">No NCs matched</div>
              ) : (
                <div className="glass rounded-xl divide-y divide-white/5">
                  {matchedNCs.map((nc) => (
                    <Link
                      key={nc.id}
                      href={`/ncs/${nc.id}`}
                      className="flex items-center justify-between gap-4 p-4 hover:bg-slate-800/40 transition-colors -mx-0 first:rounded-t-xl last:rounded-b-xl"
                    >
                      <div className="flex flex-col gap-0.5 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-xs font-bold text-electric shrink-0">{nc.id}</span>
                          <span className="truncate text-sm text-slate-200">{nc.title}</span>
                        </div>
                        <span className="text-[10px] text-slate-500">
                          {nc.product} · {nc.process}{nc.line ? ` · ${nc.line}` : ""} · Raised {formatDate(nc.raised_at)}
                        </span>
                      </div>
                      <div className="flex items-center gap-2 shrink-0">
                        <StatusBadge value={nc.severity} />
                        <StatusBadge value={nc.status} />
                      </div>
                    </Link>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Events section */}
          {(category === "all" || category === "events") && (
            <div className="flex flex-col gap-3">
              <div className="flex items-center gap-2">
                <FileText size={14} className="text-electric" />
                <h3 className="text-sm font-semibold text-slate-200">Audit Events</h3>
                <span className="text-xs text-slate-500">({matchedEvents.length})</span>
              </div>
              {matchedEvents.length === 0 ? (
                <div className="glass rounded-xl p-6 text-center text-xs text-slate-500">No events matched</div>
              ) : (
                <div className="glass rounded-xl divide-y divide-white/5">
                  {matchedEvents.map((e) => (
                    <div key={e.index} className="flex items-start justify-between gap-4 p-4">
                      <div className="flex flex-col gap-0.5 min-w-0">
                        <div className="flex items-center gap-2">
                          <span
                            className={cn(
                              "rounded-full px-2 py-0.5 text-[10px] font-semibold",
                              e.event_type === "TRACE_VERDICT"
                                ? "bg-electric/20 text-electric"
                                : e.event_type === "HEAD_DECISION"
                                ? "bg-blue-500/20 text-blue-300"
                                : "bg-slate-700 text-slate-300"
                            )}
                          >
                            {e.event_type.replace(/_/g, " ")}
                          </span>
                          {typeof e.payload.nc_id === "string" && (
                            <Link href={`/ncs/${String(e.payload.nc_id)}`} className="font-mono text-xs text-electric hover:underline">
                              {String(e.payload.nc_id)}
                            </Link>
                          )}
                        </div>
                        <span className="text-[10px] font-mono text-slate-500 truncate">
                          Hash: {e.hash.slice(0, 32)}…
                        </span>
                      </div>
                      <time className="text-[10px] text-slate-500 shrink-0">{formatDate(e.created_at)}</time>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
