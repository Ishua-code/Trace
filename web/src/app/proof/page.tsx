import { ChartNoAxesCombined } from "lucide-react";

export default function ProofPage() {
  return (
    <div className="flex flex-col gap-6 animate-fade-in">
      <div>
        <h2 className="text-xl font-bold text-white">Proof — Engine Performance</h2>
        <p className="mt-0.5 text-xs text-slate-400">
          Evaluation results will be shown here once the reproducible evaluation run publishes its results file.
        </p>
      </div>

      <section className="glass flex flex-col items-center gap-4 rounded-xl px-6 py-12 text-center" aria-live="polite">
        <ChartNoAxesCombined size={28} className="text-slate-500" aria-hidden="true" />
        <div>
          <h3 className="text-sm font-semibold text-slate-200">No evaluation results found</h3>
          <p className="mt-1 max-w-xl text-xs leading-relaxed text-slate-400">
            Baseline comparison, precision and recall, false alerts, ablations, hard cases, and time-travel replay will appear after <code className="text-electric">api/eval/results.json</code> is generated.
          </p>
        </div>
      </section>

      <div className="glass rounded-xl p-5">
        <h3 className="mb-3 text-sm font-semibold text-slate-200">Evaluation method</h3>
        <ul className="flex list-inside list-disc flex-col gap-2 text-xs leading-relaxed text-slate-400">
          <li>Demo records are synthetic; planted ground truth is not production evidence.</li>
          <li>Evaluation metrics should be computed by the evaluation code, with test data kept separate from tuning.</li>
          <li>TRACE provides explainable rule-based closure assurance, not a prediction guarantee.</li>
        </ul>
      </div>
    </div>
  );
}
