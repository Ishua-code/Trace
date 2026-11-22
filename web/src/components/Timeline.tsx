import { type ReactNode } from "react";
import { formatDateTime } from "@/lib/utils";
import { cn } from "@/lib/utils";

interface TimelineEvent {
  id: string | number;
  timestamp: string;
  title: string;
  description?: string;
  actor?: string;
  icon?: ReactNode;
  variant?: "default" | "success" | "warning" | "danger" | "info" | "trace";
}

interface TimelineProps {
  events: TimelineEvent[];
  className?: string;
}

const variantStyles = {
  default: { dot: "bg-slate-500 border-slate-400", line: "border-slate-700" },
  success: { dot: "bg-emerald-500 border-emerald-400", line: "border-slate-700" },
  warning: { dot: "bg-amber-500 border-amber-400", line: "border-slate-700" },
  danger: { dot: "bg-red-500 border-red-400", line: "border-slate-700" },
  info: { dot: "bg-blue-500 border-blue-400", line: "border-slate-700" },
  trace: { dot: "bg-electric border-electric/70 shadow-lg shadow-electric/30", line: "border-slate-700" },
};

export function Timeline({ events, className }: TimelineProps) {
  return (
    <ol className={cn("relative flex flex-col", className)}>
      {events.map((event, i) => {
        const styles = variantStyles[event.variant ?? "default"];
        const isLast = i === events.length - 1;
        return (
          <li key={event.id} className="relative flex gap-4 pb-6 last:pb-0">
            {/* connector line */}
            {!isLast && (
              <div
                className={cn(
                  "absolute left-[11px] top-6 h-full border-l-2",
                  styles.line
                )}
              />
            )}

            {/* dot */}
            <div
              className={cn(
                "relative mt-1 flex h-6 w-6 shrink-0 items-center justify-center rounded-full border-2",
                styles.dot
              )}
            >
              {event.icon && (
                <span className="text-[10px] text-white">{event.icon}</span>
              )}
            </div>

            {/* content */}
            <div className="flex flex-col gap-0.5">
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-sm font-medium text-slate-200">{event.title}</span>
                {event.actor && (
                  <span className="text-xs text-slate-500">by {event.actor}</span>
                )}
              </div>
              {event.description && (
                <p className="text-xs leading-relaxed text-slate-400">{event.description}</p>
              )}
              <time className="text-xs text-slate-600">{formatDateTime(event.timestamp)}</time>
            </div>
          </li>
        );
      })}
    </ol>
  );
}
