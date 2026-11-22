"use client";
import { type ReactNode, useEffect, useRef, useState } from "react";
import { cn } from "@/lib/utils";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";

interface KpiTileProps {
  label: string;
  value: number | string;
  unit?: string;
  trend?: "up" | "down" | "flat";
  trendLabel?: string;
  /** If true, up = good (green). If false, up = bad (red). Default true. */
  upIsGood?: boolean;
  icon?: ReactNode;
  onClick?: () => void;
  className?: string;
  /** Animate counting from 0 to value */
  animate?: boolean;
  highlight?: "warn" | "danger" | "success";
}

function useCountUp(target: number, duration = 1200, animate = true) {
  const [current, setCurrent] = useState(animate ? 0 : target);
  const raf = useRef<number | null>(null);
  useEffect(() => {
    if (!animate) return;
    const start = performance.now();
    const step = (now: number) => {
      const pct = Math.min((now - start) / duration, 1);
      const eased = 1 - Math.pow(1 - pct, 3); // ease-out cubic
      setCurrent(target * eased);
      if (pct < 1) raf.current = requestAnimationFrame(step);
    };
    raf.current = requestAnimationFrame(step);
    return () => { if (raf.current) cancelAnimationFrame(raf.current); };
  }, [target, duration, animate]);
  return animate ? current : target;
}

export function KpiTile({
  label,
  value,
  unit,
  trend,
  trendLabel,
  upIsGood = true,
  icon,
  onClick,
  className,
  animate = true,
  highlight,
}: KpiTileProps) {
  const isNumeric = typeof value === "number";
  const animated = useCountUp(isNumeric ? value : 0, 1200, animate && isNumeric);

  const displayValue = isNumeric
    ? animated % 1 !== 0
      ? animated.toFixed(1)
      : Math.round(animated).toString()
    : value;

  const trendColor =
    trend === "flat"
      ? "text-slate-400"
      : trend === "up"
      ? upIsGood ? "text-emerald-400" : "text-red-400"
      : upIsGood ? "text-red-400" : "text-emerald-400";

  const TrendIcon = trend === "up" ? TrendingUp : trend === "down" ? TrendingDown : Minus;

  const highlightClass =
    highlight === "danger"
      ? "border-red-500/40 bg-red-500/5"
      : highlight === "warn"
      ? "border-amber-500/40 bg-amber-500/5"
      : highlight === "success"
      ? "border-emerald-500/40 bg-emerald-500/5"
      : "border-white/5";

  return (
    <div
      role={onClick ? "button" : undefined}
      tabIndex={onClick ? 0 : undefined}
      onClick={onClick}
      onKeyDown={onClick ? (e) => e.key === "Enter" && onClick() : undefined}
      className={cn(
        "relative flex flex-col gap-3 rounded-xl border bg-slate-900/60 p-5",
        "backdrop-blur-sm transition-all duration-200",
        onClick && "cursor-pointer hover:border-electric/40 hover:bg-slate-800/60 hover:shadow-lg hover:shadow-electric/5",
        highlightClass,
        className
      )}
    >
      {/* header */}
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium uppercase tracking-widest text-slate-400">{label}</span>
        {icon && <span className="text-slate-500">{icon}</span>}
      </div>

      {/* value */}
      <div className="flex items-end gap-1">
        <span className="text-3xl font-bold tabular-nums text-white">{displayValue}</span>
        {unit && <span className="mb-1 text-sm text-slate-400">{unit}</span>}
      </div>

      {/* trend */}
      {trend && (
        <div className={cn("flex items-center gap-1 text-xs font-medium", trendColor)}>
          <TrendIcon size={12} />
          {trendLabel}
        </div>
      )}
    </div>
  );
}
