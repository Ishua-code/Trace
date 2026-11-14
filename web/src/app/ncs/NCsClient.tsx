"use client";
import { useState } from "react";
import { type ColumnDef } from "@tanstack/react-table";
import { DataTable } from "@/components/DataTable";
import { StatusBadge } from "@/components/StatusBadge";
import { MOCK_NCS } from "@/lib/mock-data";
import { formatDate, daysOverdue } from "@/lib/utils";
import type { NC } from "@/lib/types";
import Link from "next/link";
import { Plus, Filter } from "lucide-react";
import { cn } from "@/lib/utils";

const STATUS_FILTERS = ["All", "OPEN", "IN_PROGRESS", "PENDING_HEAD_APPROVAL", "CLOSED", "REOPENED"];

const columns: ColumnDef<NC>[] = [
  {
    accessorKey: "id",
    header: "NC ID",
    cell: ({ getValue }) => (
      <Link
        href={`/ncs/${getValue<string>()}`}
        className="font-mono text-xs font-bold text-electric hover:underline"
      >
        {getValue<string>()}
      </Link>
    ),
  },
  {
    accessorKey: "title",
    header: "Title",
    cell: ({ getValue }) => (
      <span className="line-clamp-1 max-w-xs text-sm text-slate-200">{getValue<string>()}</span>
    ),
  },
  {
    accessorKey: "severity",
    header: "Severity",
    cell: ({ getValue }) => <StatusBadge value={getValue<string>()} />,
  },
  {
    accessorKey: "status",
    header: "Status",
    cell: ({ getValue }) => <StatusBadge value={getValue<string>()} />,
  },
  {
    accessorKey: "product",
    header: "Product",
    cell: ({ getValue }) => <span className="text-xs text-slate-400">{getValue<string>()}</span>,
  },
  {
    accessorKey: "raised_at",
    header: "Raised",
    cell: ({ getValue }) => (
      <span className="text-xs text-slate-400">{formatDate(getValue<string>())}</span>
    ),
  },
  {
    accessorKey: "target_date",
    header: "Target",
    cell: ({ row }) => {
      const nc = row.original;
      const od = nc.target_date ? daysOverdue(nc.target_date) : 0;
      return nc.target_date ? (
        <div className="flex flex-col">
          <span className="text-xs text-slate-400">{formatDate(nc.target_date)}</span>
          {od > 0 && nc.status !== "CLOSED" && (
            <span className="text-[10px] font-semibold text-red-400">{od}d overdue</span>
          )}
        </div>
      ) : (
        <span className="text-slate-600">—</span>
      );
    },
  },
  {
    id: "actions",
    header: "",
    cell: ({ row }) => (
      <Link
        href={`/ncs/${row.original.id}`}
        className="text-xs text-electric hover:underline"
      >
        View →
      </Link>
    ),
  },
];

export function NCsClient() {
  const [statusFilter, setStatusFilter] = useState("All");

  const filtered = statusFilter === "All"
    ? MOCK_NCS
    : MOCK_NCS.filter((nc) => nc.status === statusFilter);

  return (
    <div className="flex flex-col gap-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-white">Non-Conformances</h2>
          <p className="text-xs text-slate-500 mt-0.5">
            <span className="text-amber-400 font-medium">⚠ Synthetic data</span>
          </p>
        </div>
        <button
          id="raise-nc-btn"
          className="flex items-center gap-2 rounded-lg bg-electric px-4 py-2 text-sm font-semibold text-slate-900 hover:bg-electric-dim transition-colors"
        >
          <Plus size={14} />
          Raise NC
        </button>
      </div>

      {/* Status filter chips */}
      <div className="flex flex-wrap gap-2" role="group" aria-label="Filter by status">
        {STATUS_FILTERS.map((s) => (
          <button
            key={s}
            id={`filter-${s}`}
            onClick={() => setStatusFilter(s)}
            className={cn(
              "rounded-full border px-3 py-1 text-xs font-medium transition-all",
              statusFilter === s
                ? "border-electric/50 bg-electric/10 text-electric"
                : "border-white/10 text-slate-400 hover:border-white/20 hover:text-slate-200"
            )}
          >
            {s}
          </button>
        ))}
        <div className="ml-auto flex items-center gap-1 text-xs text-slate-500">
          <Filter size={12} />
          {filtered.length} records
        </div>
      </div>

      <div className="glass rounded-xl p-5">
        <DataTable
          columns={columns}
          data={filtered}
          searchPlaceholder="Search NCs…"
          searchKey="title"
          emptyState={
            <div className="flex flex-col items-center gap-2 text-slate-500">
              <span className="text-3xl">🎉</span>
              <span>No NCs with this status</span>
            </div>
          }
        />
      </div>
    </div>
  );
}
