import { type ReactNode } from "react";
import { cn } from "@/lib/utils";

interface EmptyStateProps {
  icon?: ReactNode;
  title: string;
  description?: string;
  action?: ReactNode;
  className?: string;
}

export function EmptyState({ icon, title, description, action, className }: EmptyStateProps) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center gap-4 rounded-xl border border-dashed border-white/10 bg-slate-900/30 px-6 py-16 text-center",
        className
      )}
    >
      {icon && <div className="text-5xl text-slate-600">{icon}</div>}
      <div className="flex flex-col gap-1">
        <p className="text-sm font-semibold text-slate-300">{title}</p>
        {description && <p className="text-xs text-slate-500">{description}</p>}
      </div>
      {action && <div>{action}</div>}
    </div>
  );
}

// Skeleton loader variants
interface SkeletonProps {
  className?: string;
}

export function Skeleton({ className }: SkeletonProps) {
  return (
    <div
      className={cn(
        "animate-pulse rounded-md bg-slate-800/60",
        className
      )}
    />
  );
}

export function KpiSkeleton() {
  return (
    <div className="flex flex-col gap-3 rounded-xl border border-white/5 bg-slate-900/60 p-5">
      <Skeleton className="h-3 w-24" />
      <Skeleton className="h-9 w-16" />
      <Skeleton className="h-3 w-20" />
    </div>
  );
}

export function TableSkeleton({ rows = 5, cols = 4 }: { rows?: number; cols?: number }) {
  return (
    <div className="flex flex-col gap-2">
      <div className="flex gap-4 rounded-t-xl border border-white/5 bg-slate-800/80 px-4 py-3">
        {Array.from({ length: cols }).map((_, i) => (
          <Skeleton key={i} className="h-3 flex-1" />
        ))}
      </div>
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="flex gap-4 border-b border-white/5 bg-slate-900/40 px-4 py-3">
          {Array.from({ length: cols }).map((_, j) => (
            <Skeleton key={j} className="h-3 flex-1" />
          ))}
        </div>
      ))}
    </div>
  );
}
