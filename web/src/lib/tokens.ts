/**
 * TRACE design tokens.
 * Electric accent: #00E5FF (cyan-400 family) — confident, industrial.
 * Deep slate background. Clear red/amber/green for HOLD/VERIFY/CLEAR.
 *
 * Usage in Tailwind 4: define in globals.css using @theme
 */

export const tokens = {
  colors: {
    electric: "#00E5FF",
    "electric-dim": "#00B8D4",
    // verdict colours
    hold: "#ef4444",    // red-500
    verify: "#f59e0b",  // amber-500
    clear: "#10b981",   // emerald-500
    // severity colours
    critical: "#ef4444",
    major: "#f59e0b",
    minor: "#64748b",
  },
} as const;
