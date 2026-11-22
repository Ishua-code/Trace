"use client";
import { use, useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { api } from "@/lib/api";
import { usePersona } from "@/lib/persona";
import { StatusBadge } from "@/components/StatusBadge";
import { formatDate } from "@/lib/utils";

export default function NCDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id: rawId } = use(params);
  const id = decodeURIComponent(rawId);
  const { user } = usePersona();
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [d, setD] = useState<any>(null);
  const [error, setError] = useState("");
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);
  const [text, setText] = useState("");

  const load = useCallback(() => {
    api.ncDetail(id).then(setD).catch((e) => setError(String(e)));
  }, [id]);

  useEffect(() => { load(); }, [load, user]);

  async function simulate() {
    setBusy(true); setMsg("");
    try {
      await api.simulateClosure(id);
      await load();
    } catch (e) {
      setMsg(String(e).includes("503")
        ? "TRACE engine closure check is not ready yet (503)."
        : String(e));
    }
    setBusy(false);
  }

  async function decide(decision: "approve" | "override" | "send_back") {
    setBusy(true); setMsg("");
    try {
      await api.closureDecision(id, { decision, justification: text });
      setText("");
      await load();
      setMsg("Decision saved.");
    } catch (e) {
      setMsg(String(e));
    }
    setBusy(false);
  }

  async function doneTask(taskId: number) {
    try { await api.completeTask(taskId); await load(); } catch (e) { setMsg(String(e)); }
  }

  if (!d) return <div className="p-6 text-slate-400">{error || "Loading..."}</div>;

  const nc = d.nc;
  const closure = d.closure;
  const report = closure?.report ?? closure;
  const verdict: string | undefined = report?.verdict;
  const findings: any[] = report?.findings ?? [];
  const tasks: any[] = report?.tasks ?? closure?.tasks ?? d.tasks ?? [];
  const isHead = user.role === "auditing_head";
  const canSimulate = nc.status !== "CLOSED" && (isHead || user.role === "admin" || user.role === "auditor");

  const fields: [string, string][] = [
    ["Product", nc.product], ["Process", nc.process], ["Line", nc.line ?? "-"],
    ["Machine", nc.machine ?? "-"], ["Lot", nc.lot ?? "-"], ["Defect", nc.defect_code ?? "-"],
    ["Root cause", nc.root_cause_category ?? "-"], ["Raised", formatDate(nc.raised_at)],
    ["Target", nc.target_date ? formatDate(nc.target_date) : "-"],
  ];

  const box = "glass rounded-xl p-5";
  return (
    <div className="flex flex-col gap-4 animate-fade-in">
      <Link href="/ncs" className="inline-flex items-center gap-1.5 text-xs text-slate-400 hover:text-slate-200">
        <ArrowLeft size={12} /> Back to Non-Conformances
      </Link>

      <div>
        <div className="flex items-center gap-3 mb-1">
          <span className="font-mono text-2xl font-bold text-electric">{nc.id}</span>
          <StatusBadge value={nc.severity} />
          <StatusBadge value={nc.status} />
        </div>
        <h2 className="text-xl font-bold text-white">{nc.title}</h2>
        <p className="mt-2 text-sm text-slate-300">{nc.description}</p>
      </div>

      <div className={box}>
        <h3 className="text-sm font-semibold text-slate-200 mb-3">Details</h3>
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
          {fields.map(([k, v]) => (
            <div key={k}>
              <div className="text-[10px] uppercase text-slate-500">{k}</div>
              <div className="text-sm text-slate-200">{v}</div>
            </div>
          ))}
        </div>
      </div>

      <div className={box}>
        <h3 className="text-sm font-semibold text-slate-200 mb-3">Workflow record</h3>
        <ul className="text-sm text-slate-300 flex flex-col gap-2">
          {d.actions.map((a: any) => <li key={a.id}>Action plan: {a.corrective_action} (due {formatDate(a.target_date)})</li>)}
          {d.evidence.map((e: any) => <li key={e.id}>Evidence: {e.file_name}</li>)}
          {d.verifications.map((v: any) => <li key={v.id}>Auditor verification: {v.accepted ? "accepted" : "rejected"}. {v.comment}</li>)}
        </ul>
      </div>

      <div className={box}>
        <h3 className="text-sm font-semibold text-slate-200 mb-3">TRACE linked failures ({d.links.length})</h3>
        <div className="flex flex-col gap-3">
          {d.links.map((l: any) => {
            const other = l.a === nc.id ? l.b : l.a;
            const top = [...l.signals].filter((s: any) => s.contribution > 0.5)
              .sort((x: any, y: any) => y.contribution - x.contribution).slice(0, 4);
            return (
              <div key={l.id} className="rounded-lg border border-white/5 bg-slate-800/40 p-3">
                <div className="flex justify-between">
                  <Link href={`/ncs/${other}`} className="font-mono text-xs font-bold text-electric hover:underline">{other}</Link>
                  <span className="font-mono text-xs text-slate-200">{(l.score * 100).toFixed(1)}%</span>
                </div>
                <ul className="mt-2 text-[11px] text-slate-400 list-disc pl-4">
                  {top.map((s: any) => <li key={s.name}>{s.evidence}</li>)}
                </ul>
              </div>
            );
          })}
        </div>
      </div>

      <div className={box}>
        <div className="mb-3 flex items-center gap-3">
          <h3 className="text-sm font-semibold text-slate-200">Closure check</h3>
          {verdict && <StatusBadge value={verdict} />}
          {canSimulate && (
            <button onClick={simulate} disabled={busy}
              className="ml-auto rounded-lg bg-electric px-4 py-2 text-sm font-semibold text-slate-900 disabled:opacity-50">
              {busy ? "Working..." : closure ? "Re-run closure check" : "Simulate closure"}
            </button>
          )}
        </div>
        {msg && <p className="mb-3 text-xs text-amber-300">{msg}</p>}
        {!closure && <p className="text-xs text-slate-500">No closure check run yet.</p>}

        {findings.map((f, i) => (
          <div key={i} className="mb-2 rounded-lg border border-white/5 bg-slate-800/40 p-3 text-xs text-slate-300">
            <span className="mr-2 font-mono font-bold text-electric">{f.rule}</span>{f.message}
          </div>
        ))}

        {tasks.length > 0 && (
          <div className="mt-3">
            <h4 className="mb-2 text-xs font-semibold uppercase text-slate-500">Verification tasks</h4>
            {tasks.map((t) => (
              <div key={t.id ?? t.title} className="mb-2 flex items-center justify-between rounded-lg border border-white/5 p-3 text-xs text-slate-300">
                <span>{t.title}</span>
                {t.done ? <span className="text-emerald-400">done</span> : (
                  <button onClick={() => t.id && doneTask(t.id)} className="text-electric hover:underline">Mark done</button>
                )}
              </div>
            ))}
          </div>
        )}

        {isHead && closure && nc.status !== "CLOSED" && (
          <div className="mt-4 border-t border-white/10 pt-4">
            <h4 className="mb-2 text-xs font-semibold uppercase text-slate-500">Head decision</h4>
            <textarea value={text} onChange={(e) => setText(e.target.value)}
              placeholder="Type the justification or reason (at least 15 characters for override)"
              className="w-full rounded-lg border border-white/10 bg-slate-900 p-2 text-sm text-slate-200" rows={3} />
            <div className="mt-2 flex gap-2">
              <button disabled={busy} onClick={() => decide("approve")} className="rounded-lg bg-emerald-600 px-3 py-2 text-sm text-white disabled:opacity-50">Approve</button>
              <button disabled={busy || text.trim().length < 15} onClick={() => decide("override")} className="rounded-lg bg-red-600 px-3 py-2 text-sm text-white disabled:opacity-50">Override and close</button>
              <button disabled={busy || !text.trim()} onClick={() => decide("send_back")} className="rounded-lg bg-slate-600 px-3 py-2 text-sm text-white disabled:opacity-50">Send back</button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}