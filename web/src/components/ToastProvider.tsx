"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { CheckCircle2, Info, TriangleAlert, X } from "lucide-react";
import { cn } from "@/lib/utils";

type ToastKind = "success" | "error" | "info";
interface ToastItem { id: number; title: string; description?: string; kind: ToastKind }
interface ToastContextValue { toast: (item: Omit<ToastItem, "id">) => void }

const ToastContext = createContext<ToastContextValue | null>(null);
let nextToastId = 0;

export function useToast() {
  const value = useContext(ToastContext);
  if (!value) throw new Error("useToast must be used inside ToastProvider");
  return value;
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([]);
  const dismiss = useCallback((id: number) => setItems((current) => current.filter((item) => item.id !== id)), []);
  const toast = useCallback((item: Omit<ToastItem, "id">) => {
    const id = ++nextToastId;
    setItems((current) => [...current.slice(-3), { ...item, id }]);
  }, []);

  useEffect(() => {
    if (!items.length) return;
    const timers = items.map((item) => window.setTimeout(() => dismiss(item.id), 5000));
    return () => timers.forEach(window.clearTimeout);
  }, [items, dismiss]);

  const context = useMemo(() => ({ toast }), [toast]);
  return (
    <ToastContext.Provider value={context}>
      {children}
      <div className="pointer-events-none fixed right-4 top-16 z-[120] flex w-[min(24rem,calc(100vw-2rem))] flex-col gap-2" aria-live="polite" aria-relevant="additions">
        {items.map((item) => {
          const Icon = item.kind === "success" ? CheckCircle2 : item.kind === "error" ? TriangleAlert : Info;
          return (
            <div key={item.id} role={item.kind === "error" ? "alert" : "status"} className="pointer-events-auto flex items-start gap-3 rounded-xl border border-white/10 bg-slate-900 p-4 text-slate-100 shadow-xl">
              <Icon size={18} className={cn("mt-0.5 shrink-0", item.kind === "success" ? "text-clear" : item.kind === "error" ? "text-hold" : "text-electric")} aria-hidden="true" />
              <div className="min-w-0 flex-1">
                <p className="text-sm font-semibold">{item.title}</p>
                {item.description && <p className="mt-1 text-xs text-slate-400">{item.description}</p>}
              </div>
              <button type="button" onClick={() => dismiss(item.id)} className="rounded p-1 text-slate-400 hover:bg-slate-800 hover:text-white" aria-label="Dismiss notification"><X size={14} /></button>
            </div>
          );
        })}
      </div>
    </ToastContext.Provider>
  );
}
