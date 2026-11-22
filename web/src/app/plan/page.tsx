import type { Metadata } from "next";
export const metadata: Metadata = { title: "Risk Plan Heatmap" };
import { MOCK_NCS } from "@/lib/mock-data";

const MONTHS = ["May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov"];
const PROCESSES = ["Machining", "Heat Treatment", "Grinding", "Welding", "Finishing"];

// Simple score = count of NCs per process per month (synthetic)
function score(process: string, month: string) {
  const idx = MONTHS.indexOf(month);
  if (idx < 0) return 0;
  return Math.round(Math.random() * 3); // replaced by real data from /api/engine/plan-risk
}

function heatColor(s: number) {
  if (s === 0) return "#1e293b";
  if (s === 1) return "#166534";
  if (s === 2) return "#854d0e";
  return "#7f1d1d";
}

export default function PlanPage() {
  return (
    <div className="flex flex-col gap-6 animate-fade-in">
      <div>
        <h2 className="text-xl font-bold text-white">Risk-Adaptive Audit Plan</h2>
        <p className="text-xs text-slate-500 mt-0.5">
          <span className="text-amber-400 font-medium">⚠ Placeholder heatmap</span> — replace with{" "}
          <code className="text-electric">/api/engine/plan-risk</code> response.{" "}
          <span className="text-slate-600">🔒 Mandatory audits are locked and never displaced.</span>
        </p>
      </div>

      <div className="glass rounded-xl p-5 overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="text-left text-slate-500">
              <th className="pb-3 pr-4 font-semibold">Process</th>
              {MONTHS.map((m) => (
                <th key={m} className="pb-3 px-2 font-semibold">{m}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {PROCESSES.map((p) => (
              <tr key={p} className="border-t border-white/5">
                <td className="py-2 pr-4 font-medium text-slate-300">{p}</td>
                {MONTHS.map((m) => {
                  const s = score(p, m);
                  const locked = p === "Machining" && m === "Nov";
                  return (
                    <td key={m} className="px-2 py-2">
                      <div
                        className="flex h-10 w-14 items-center justify-center rounded-lg text-[10px] font-bold relative"
                        style={{ background: locked ? "#1e3a5f" : heatColor(s), color: "#e2e8f0" }}
                        title={locked ? "Mandatory — locked" : `Risk score: ${s}`}
                      >
                        {locked ? "🔒" : s || "·"}
                      </div>
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>

        <div className="mt-4 flex flex-wrap gap-4 text-[10px] text-slate-500">
          <div className="flex items-center gap-1.5"><span className="h-3 w-3 rounded" style={{background:"#166534"}} />Low risk</div>
          <div className="flex items-center gap-1.5"><span className="h-3 w-3 rounded" style={{background:"#854d0e"}} />Medium risk</div>
          <div className="flex items-center gap-1.5"><span className="h-3 w-3 rounded" style={{background:"#7f1d1d"}} />High risk</div>
          <div className="flex items-center gap-1.5"><span className="h-3 w-3 rounded" style={{background:"#1e3a5f"}} />🔒 Mandatory locked</div>
        </div>
      </div>
    </div>
  );
}
