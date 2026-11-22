"use client";
import type { Metadata } from "next";
import { useState, useRef } from "react";
import { Upload, FileSpreadsheet, CheckCircle2, XCircle, AlertTriangle, Download } from "lucide-react";
import { cn } from "@/lib/utils";

// Sample CSV template content (shown for download)
const SAMPLE_CSV = `audit_date,audit_type,process,product,line,auditor_id,mandatory
2024-11-01,product,Machining,Brake Drum Assy,Line 2,2,true
2024-11-02,revalidation,Heat Treatment,Brake Drum Assy,Line 3,2,true
2024-11-05,product,Grinding,Hub Flange,Line 1,2,false
2024-11-08,product,Welding,Axle Shaft,Line 2,2,false
2024-11-12,product,Finishing,Wheel Hub,Line 5,2,false
`;

interface ValidationError {
  row: number;
  field: string;
  message: string;
}

type UploadState = "idle" | "dragging" | "preview" | "uploading" | "success" | "error";

export default function UploadPage() {
  const [state, setState] = useState<UploadState>("idle");
  const [fileName, setFileName] = useState("");
  const [rows, setRows] = useState<string[][]>([]);
  const [errors, setErrors] = useState<ValidationError[]>([]);
  const fileRef = useRef<HTMLInputElement>(null);

  const downloadSample = () => {
    const blob = new Blob([SAMPLE_CSV], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "trace_audit_plan_sample.csv";
    a.click();
    URL.revokeObjectURL(url);
  };

  const parseCSV = (text: string): string[][] => {
    return text
      .trim()
      .split("\n")
      .map((line) => line.split(",").map((cell) => cell.trim()));
  };

  const validateRows = (parsed: string[][]): ValidationError[] => {
    const errs: ValidationError[] = [];
    const header = parsed[0];
    const required = ["audit_date", "audit_type", "process", "product", "auditor_id"];
    required.forEach((field) => {
      if (!header.includes(field)) {
        errs.push({ row: 0, field, message: `Required column "${field}" is missing` });
      }
    });
    parsed.slice(1).forEach((row, i) => {
      const dateIdx = header.indexOf("audit_date");
      const typeIdx = header.indexOf("audit_type");
      if (dateIdx >= 0 && row[dateIdx] && !/^\d{4}-\d{2}-\d{2}$/.test(row[dateIdx])) {
        errs.push({ row: i + 2, field: "audit_date", message: `Invalid date format: ${row[dateIdx]}` });
      }
      if (typeIdx >= 0 && row[typeIdx] && !["product", "revalidation"].includes(row[typeIdx])) {
        errs.push({ row: i + 2, field: "audit_type", message: `Must be "product" or "revalidation"` });
      }
    });
    return errs;
  };

  const handleFile = (file: File) => {
    if (!file.name.match(/\.(csv|xlsx)$/i)) {
      setErrors([{ row: 0, field: "file", message: "Only .csv or .xlsx files are accepted." }]);
      setState("error");
      return;
    }
    setFileName(file.name);
    const reader = new FileReader();
    reader.onload = (e) => {
      const text = (e.target?.result as string) ?? "";
      const parsed = parseCSV(text);
      setRows(parsed);
      const errs = validateRows(parsed);
      setErrors(errs);
      setState("preview");
    };
    reader.readAsText(file);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setState("idle");
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  };

  const handleSubmit = () => {
    if (errors.length > 0) return;
    setState("uploading");
    // Simulate upload — wired to /api/plans/upload in production
    setTimeout(() => setState("success"), 1200);
  };

  return (
    <div className="flex flex-col gap-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-white">Upload Audit Plan</h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Upload a monthly audit schedule as CSV or XLSX. Wired to{" "}
            <code className="text-electric">/api/plans/upload</code> once backend is live.
          </p>
        </div>
        <button
          id="download-sample-btn"
          onClick={downloadSample}
          className="flex items-center gap-2 rounded-lg border border-white/10 bg-slate-800/60 px-4 py-2 text-sm text-slate-300 hover:border-electric/40 hover:text-white transition-all"
        >
          <Download size={14} />
          Sample CSV
        </button>
      </div>

      {/* Required columns reference */}
      <div className="glass rounded-xl p-5">
        <h3 className="text-sm font-semibold text-slate-200 mb-3">Required Columns</h3>
        <div className="flex flex-wrap gap-2">
          {["audit_date (YYYY-MM-DD)", "audit_type (product|revalidation)", "process", "product", "auditor_id"].map((col) => (
            <span key={col} className="rounded-full border border-electric/30 bg-electric/10 px-2.5 py-0.5 font-mono text-[10px] text-electric">
              {col}
            </span>
          ))}
          <span className="text-[10px] text-slate-500 ml-1 self-center">Optional: line, mandatory, lot</span>
        </div>
      </div>

      {/* Drop zone */}
      {(state === "idle" || state === "dragging") && (
        <div
          onDragOver={(e) => { e.preventDefault(); setState("dragging"); }}
          onDragLeave={() => setState("idle")}
          onDrop={handleDrop}
          onClick={() => fileRef.current?.click()}
          id="upload-dropzone"
          className={cn(
            "flex flex-col items-center justify-center gap-4 rounded-xl border-2 border-dashed p-16 cursor-pointer transition-all",
            state === "dragging"
              ? "border-electric/60 bg-electric/5"
              : "border-white/10 hover:border-white/20 hover:bg-slate-800/20"
          )}
        >
          <div className={cn(
            "flex h-16 w-16 items-center justify-center rounded-2xl transition-all",
            state === "dragging" ? "bg-electric/20 ring-1 ring-electric/40" : "bg-slate-800"
          )}>
            <Upload size={28} className={state === "dragging" ? "text-electric" : "text-slate-500"} />
          </div>
          <div className="text-center">
            <p className="text-sm font-medium text-slate-200">
              {state === "dragging" ? "Drop to upload" : "Drag & drop or click to browse"}
            </p>
            <p className="mt-1 text-xs text-slate-500">.csv or .xlsx, max 5 MB</p>
          </div>
          <input
            ref={fileRef}
            type="file"
            accept=".csv,.xlsx"
            className="hidden"
            onChange={(e) => { const f = e.target.files?.[0]; if (f) handleFile(f); }}
          />
        </div>
      )}

      {/* Preview table */}
      {state === "preview" && rows.length > 0 && (
        <div className="flex flex-col gap-4">
          <div className="glass rounded-xl p-5">
            <div className="mb-4 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <FileSpreadsheet size={16} className="text-electric" />
                <h3 className="text-sm font-semibold text-slate-200">{fileName}</h3>
                <span className="text-xs text-slate-500">· {rows.length - 1} rows</span>
              </div>
              <button
                onClick={() => { setState("idle"); setRows([]); setErrors([]); setFileName(""); }}
                className="text-xs text-slate-500 hover:text-slate-300 transition-colors"
              >
                × Clear
              </button>
            </div>

            {/* Preview table */}
            <div className="overflow-x-auto rounded-xl border border-white/5">
              <table className="w-full text-xs">
                <thead>
                  <tr className="bg-slate-800/80 border-b border-white/5">
                    {rows[0]?.map((h, i) => (
                      <th key={i} className="px-3 py-2 text-left font-semibold uppercase tracking-wider text-slate-400">
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {rows.slice(1, 6).map((row, i) => (
                    <tr key={i} className="border-b border-white/5 bg-slate-900/40 hover:bg-slate-800/40 transition-colors">
                      {row.map((cell, j) => (
                        <td key={j} className="px-3 py-2 text-slate-300">{cell || "—"}</td>
                      ))}
                    </tr>
                  ))}
                  {rows.length > 7 && (
                    <tr>
                      <td colSpan={rows[0]?.length} className="px-3 py-2 text-center text-xs text-slate-500 italic">
                        …{rows.length - 6} more rows
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* Validation errors */}
          {errors.length > 0 ? (
            <div className="rounded-xl border border-red-500/30 bg-red-500/10 p-5">
              <div className="flex items-center gap-2 mb-3">
                <XCircle size={16} className="text-red-400" />
                <h3 className="text-sm font-semibold text-red-300">Validation Errors ({errors.length})</h3>
              </div>
              <div className="flex flex-col gap-2">
                {errors.map((err, i) => (
                  <div key={i} className="flex items-start gap-3 text-xs text-red-300">
                    <span className="rounded bg-red-500/20 px-1.5 py-0.5 font-mono font-bold shrink-0">Row {err.row}</span>
                    <span><span className="font-semibold">{err.field}:</span> {err.message}</span>
                  </div>
                ))}
              </div>
              <p className="mt-3 text-xs text-red-400/60">Fix the errors above and re-upload the file.</p>
            </div>
          ) : (
            <div className="flex items-center gap-3 rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-4">
              <CheckCircle2 size={16} className="text-emerald-400" />
              <div>
                <p className="text-sm font-semibold text-emerald-300">Validation passed</p>
                <p className="text-xs text-emerald-400/60">{rows.length - 1} slots ready to create</p>
              </div>
              <button
                id="submit-plan-btn"
                onClick={handleSubmit}
                className="ml-auto rounded-lg bg-electric px-5 py-2 text-sm font-semibold text-slate-900 hover:bg-electric-dim transition-all"
              >
                Upload Plan
              </button>
            </div>
          )}
        </div>
      )}

      {/* Uploading */}
      {state === "uploading" && (
        <div className="flex flex-col items-center gap-4 rounded-xl border border-white/10 bg-slate-900/60 p-16">
          <div className="h-10 w-10 animate-spin rounded-full border-2 border-electric/30 border-t-electric" />
          <p className="text-sm text-slate-300">Uploading audit plan…</p>
        </div>
      )}

      {/* Success */}
      {state === "success" && (
        <div className="flex flex-col items-center gap-4 rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-16 glow-clear">
          <CheckCircle2 size={48} className="text-emerald-400" />
          <div className="text-center">
            <p className="text-lg font-bold text-emerald-300">Plan uploaded successfully</p>
            <p className="mt-1 text-sm text-emerald-400/60">
              {rows.length - 1} audit slots created for the schedule.
            </p>
          </div>
          <button
            id="upload-another-btn"
            onClick={() => { setState("idle"); setRows([]); setErrors([]); setFileName(""); }}
            className="rounded-lg border border-emerald-500/30 px-4 py-2 text-sm text-emerald-300 hover:bg-emerald-500/10 transition-all"
          >
            Upload Another
          </button>
        </div>
      )}

      {/* Error */}
      {state === "error" && (
        <div className="flex flex-col items-center gap-4 rounded-xl border border-red-500/30 bg-red-500/10 p-10">
          <AlertTriangle size={36} className="text-red-400" />
          <div className="text-center">
            {errors.map((e, i) => <p key={i} className="text-sm text-red-300">{e.message}</p>)}
          </div>
          <button
            onClick={() => { setState("idle"); setErrors([]); }}
            className="rounded-lg border border-red-500/30 px-4 py-2 text-sm text-red-300 hover:bg-red-500/10 transition-all"
          >
            Try Again
          </button>
        </div>
      )}
    </div>
  );
}
