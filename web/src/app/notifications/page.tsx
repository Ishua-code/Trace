import type { Metadata } from "next";
export const metadata: Metadata = { title: "Notifications" };
import { MOCK_NOTIFICATIONS } from "@/lib/mock-data";
import { Bell } from "lucide-react";
import { formatDateTime } from "@/lib/utils";
import { cn } from "@/lib/utils";

const KIND_STYLES: Record<string, string> = {
  reminder: "border-amber-500/30 bg-amber-500/10 text-amber-300",
  escalation_l1: "border-orange-500/30 bg-orange-500/10 text-orange-300",
  escalation_l2: "border-red-500/30 bg-red-500/10 text-red-300",
  assignment: "border-blue-500/30 bg-blue-500/10 text-blue-300",
};

export default function NotificationsPage() {
  return (
    <div className="flex flex-col gap-6 animate-fade-in">
      <div className="flex items-center gap-2">
        <Bell size={18} className="text-electric" />
        <h2 className="text-xl font-bold text-white">Notifications</h2>
      </div>

      <div className="flex flex-col gap-3">
        {MOCK_NOTIFICATIONS.map((n) => (
          <div
            key={n.id}
            className={cn(
              "flex flex-col gap-1.5 rounded-xl border p-4",
              KIND_STYLES[n.kind] ?? "border-white/10 text-slate-300"
            )}
          >
            <div className="flex items-start justify-between gap-4">
              <span className="text-sm font-semibold">{n.subject}</span>
              <div className="flex items-center gap-2 shrink-0">
                <span className="rounded-full border border-current px-2 py-0.5 text-[10px] font-semibold uppercase">
                  {n.kind.replace(/_/g, " ")}
                </span>
                {n.nc_id && (
                  <span className="font-mono text-xs opacity-70">{n.nc_id}</span>
                )}
              </div>
            </div>
            <p className="text-xs opacity-80">{n.body}</p>
            <time className="text-[10px] opacity-50">{formatDateTime(n.sent_at)}</time>
          </div>
        ))}
      </div>
    </div>
  );
}
