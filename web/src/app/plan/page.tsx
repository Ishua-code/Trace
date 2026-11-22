import { CalendarDays, LockKeyhole } from "lucide-react";

export default function PlanPage() {
  return (
    <div className="flex flex-col gap-6 animate-fade-in">
      <div>
        <h2 className="text-xl font-bold text-white">Risk-Adaptive Audit Plan</h2>
        <p className="mt-0.5 text-xs text-slate-400">
          Plan recommendations will use the live TRACE risk-planning API. Mandatory audits remain protected.
        </p>
      </div>
      <section className="glass flex flex-col items-center gap-4 rounded-xl px-6 py-12 text-center" aria-live="polite">
        <CalendarDays size={28} className="text-slate-500" aria-hidden="true" />
        <div>
          <h3 className="text-sm font-semibold text-slate-200">Risk plan data is not available yet</h3>
          <p className="mt-1 max-w-lg text-xs leading-relaxed text-slate-400">
            The API does not currently provide monthly process risk recommendations. This view will populate when that endpoint is ready.
          </p>
        </div>
        <div className="flex items-center gap-2 rounded-lg border border-blue-500/20 bg-blue-500/5 px-3 py-2 text-xs text-blue-200">
          <LockKeyhole size={13} aria-hidden="true" /> Mandatory audits are never displaced by recommendations.
        </div>
      </section>
    </div>
  );
}
