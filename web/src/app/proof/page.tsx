import type { Metadata } from "next";
export const metadata: Metadata = { title: "Proof — Engine Performance" };
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from "recharts";

// Placeholder — real data from /api/eval/results once Hanu's eval/ lands
const BASELINE_DATA = [
  { name: "Status-Based (A)", precision: 0.0, recall: 0.0, f1: 0.0 },
  { name: "Keyword Match (B)", precision: 45, recall: 38, f1: 41 },
  { name: "TRACE (C)", precision: 82, recall: 76, f1: 79 },
];

const ABLATION_DATA = [
  { name: "Structural only", f1: 58 },
  { name: "Text only", f1: 61 },
  { name: "TRACE (both)", f1: 79 },
];

export default function ProofPage() {
  return (
    <div className="flex flex-col gap-6 animate-fade-in">
      <div>
        <h2 className="text-xl font-bold text-white">Proof — Engine Performance</h2>
        <p className="text-xs text-slate-500 mt-0.5">
          <span className="text-amber-400 font-medium">⚠ Placeholder</span> — replace with{" "}
          <code className="text-electric">eval/results.json</code> values once{" "}
          <code className="text-slate-400">python -m eval.run</code> completes.
          Numbers shown are illustrative only.
        </p>
      </div>

      <div className="glass rounded-xl p-5">
        <h3 className="mb-4 text-sm font-semibold text-slate-200">Baseline Comparison (F1 %)</h3>
        <p className="mb-4 text-xs text-slate-500 italic">
          Synthetic ground truth · Dev/test split by seed · Never tuned on test
        </p>
        <ResponsiveContainer width="100%" height={220}>
          <BarChart data={BASELINE_DATA}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
            <XAxis dataKey="name" tick={{ fill: "#64748b", fontSize: 11 }} />
            <YAxis domain={[0, 100]} tick={{ fill: "#64748b", fontSize: 11 }} />
            <Tooltip contentStyle={{ background: "#0a0f1e", border: "1px solid rgba(255,255,255,0.08)", borderRadius: 8, color: "#e2e8f0", fontSize: 12 }} />
            <Legend wrapperStyle={{ fontSize: 11, color: "#94a3b8" }} />
            <Bar dataKey="precision" name="Precision" fill="#334155" radius={[4, 4, 0, 0]} />
            <Bar dataKey="recall" name="Recall" fill="#0ea5e9" radius={[4, 4, 0, 0]} />
            <Bar dataKey="f1" name="F1" fill="#00e5ff" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <div className="glass rounded-xl p-5">
          <h3 className="mb-4 text-sm font-semibold text-slate-200">Ablation Study</h3>
          <ResponsiveContainer width="100%" height={160}>
            <BarChart data={ABLATION_DATA}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
              <XAxis dataKey="name" tick={{ fill: "#64748b", fontSize: 10 }} />
              <YAxis domain={[0, 100]} tick={{ fill: "#64748b", fontSize: 10 }} />
              <Tooltip contentStyle={{ background: "#0a0f1e", border: "1px solid rgba(255,255,255,0.08)", borderRadius: 8, color: "#e2e8f0", fontSize: 12 }} />
              <Bar dataKey="f1" name="F1 %" fill="#00e5ff" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="glass rounded-xl p-5">
          <h3 className="mb-4 text-sm font-semibold text-slate-200">Key Metrics</h3>
          <div className="flex flex-col gap-3 text-sm">
            {[
              { label: "Precision", value: "82%", note: "placeholder" },
              { label: "Recall", value: "76%", note: "placeholder" },
              { label: "F1 Score", value: "79%", note: "placeholder" },
              { label: "False alerts / 100 closures", value: "4.2", note: "placeholder" },
              { label: "Hard-cases accuracy", value: "68%", note: "placeholder" },
              { label: "Median earlier detection", value: "6 days", note: "placeholder" },
            ].map((m) => (
              <div key={m.label} className="flex items-center justify-between">
                <span className="text-slate-400">{m.label}</span>
                <div className="flex items-center gap-2">
                  <span className="font-semibold text-white">{m.value}</span>
                  <span className="text-[10px] italic text-amber-500">{m.note}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="glass rounded-xl p-5">
        <h3 className="mb-3 text-sm font-semibold text-slate-200">Honest Limitations</h3>
        <ul className="flex flex-col gap-2 text-xs text-slate-400 list-disc list-inside leading-relaxed">
          <li>All data is synthetic and seeded — ground truth is planted, not real production records.</li>
          <li>Weights are fit on a dev split and frozen; a real pilot would need recalibration on actual NC history.</li>
          <li>Text similarity uses TF-IDF / BM25; no transformer models (Vercel serverless constraint).</li>
          <li>Evaluation metrics will update automatically once <code className="text-electric">python -m eval.run</code> completes.</li>
        </ul>
      </div>
    </div>
  );
}
