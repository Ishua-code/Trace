import { type ReactNode } from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-semibold transition-colors",
  {
    variants: {
      variant: {
        default: "bg-slate-700 text-slate-200",
        // NC status badges
        OPEN: "bg-amber-500/20 text-amber-300 border border-amber-500/30",
        ASSIGNED: "bg-blue-500/20 text-blue-300 border border-blue-500/30",
        ACTION_PLANNED: "bg-violet-500/20 text-violet-300 border border-violet-500/30",
        IN_PROGRESS: "bg-cyan-500/20 text-cyan-300 border border-cyan-500/30",
        EVIDENCE_SUBMITTED: "bg-indigo-500/20 text-indigo-300 border border-indigo-500/30",
        AUDITOR_VERIFIED: "bg-teal-500/20 text-teal-300 border border-teal-500/30",
        REJECTED: "bg-red-500/20 text-red-300 border border-red-500/30",
        TRACE_REVIEW: "bg-electric/20 text-electric border border-electric/30",
        PENDING_HEAD_APPROVAL: "bg-orange-500/20 text-orange-300 border border-orange-500/30",
        CLOSED: "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30",
        REOPENED: "bg-red-600/20 text-red-400 border border-red-600/30",
        // Severity
        minor: "bg-slate-500/20 text-slate-300 border border-slate-500/30",
        major: "bg-amber-500/20 text-amber-300 border border-amber-500/30",
        critical: "bg-red-500/20 text-red-300 border border-red-500/30",
        // Verdict
        CLEAR: "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30",
        VERIFY: "bg-amber-500/20 text-amber-300 border border-amber-500/30",
        HOLD: "bg-red-500/20 text-red-300 border border-red-500/30",
        // Roles
        auditing_head: "bg-violet-500/20 text-violet-300",
        auditor: "bg-blue-500/20 text-blue-300",
        auditee: "bg-cyan-500/20 text-cyan-300",
        admin: "bg-slate-500/20 text-slate-300",
      },
    },
    defaultVariants: { variant: "default" },
  }
);

type BadgeVariant = NonNullable<VariantProps<typeof badgeVariants>["variant"]>;

interface StatusBadgeProps {
  value: string;
  className?: string;
  icon?: ReactNode;
}

export function StatusBadge({ value, className, icon }: StatusBadgeProps) {
  return (
    <span className={cn(badgeVariants({ variant: value as BadgeVariant }), className)}>
      {icon}
      {value.replace(/_/g, " ")}
    </span>
  );
}
