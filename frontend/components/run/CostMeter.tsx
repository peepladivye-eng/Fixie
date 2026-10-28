"use client";
import { motion, useReducedMotion } from "motion/react";
import type { RunState, ModelTier } from "@/lib/events";

const TIER_COLORS: Record<ModelTier, string> = {
  lightning: "var(--badge-blue)",
  super: "var(--accent)",
  ultra: "#C084FC",
  none: "var(--border)",
};

const TIER_ORDER: ModelTier[] = ["lightning", "super", "ultra", "none"];

export default function CostMeter({ state }: { state: RunState }) {
  const prefersReduced = useReducedMotion();
  const total = state.cost_total;
  const elapsed = state.elapsed_seconds;

  const totalNonZero = Object.values(state.cost_by_tier).reduce((a, b) => a + b, 0);

  return (
    <div
      className="flex items-center gap-4 px-4 py-2 flex-wrap"
      style={{ background: "var(--surface)", borderTop: "1px solid var(--border)" }}
      aria-label="Cost and time meter"
    >
      {/* Dollars counter */}
      <div className="flex items-baseline gap-1 font-mono text-sm">
        <span style={{ color: "var(--text-muted)" }}>cost</span>
        <motion.span
          key={Math.floor(total * 1000)}
          initial={prefersReduced ? false : { opacity: 0.5, y: -4 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.2 }}
          style={{ color: "var(--accent)" }}
          className="font-semibold"
        >
          ${total.toFixed(4)}
        </motion.span>
      </div>

      {/* Seconds counter */}
      <div className="flex items-baseline gap-1 font-mono text-sm">
        <span style={{ color: "var(--text-muted)" }}>time</span>
        <motion.span
          key={Math.floor(elapsed)}
          initial={prefersReduced ? false : { opacity: 0.5, y: -4 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.2 }}
          style={{ color: "var(--text)" }}
          className="font-semibold"
        >
          {elapsed.toFixed(1)}s
        </motion.span>
      </div>

      {/* Segmented bar by tier */}
      {totalNonZero > 0 && (
        <div className="flex-1 min-w-24 flex rounded overflow-hidden h-2" style={{ background: "var(--border)" }}>
          {TIER_ORDER.map((tier) => {
            const cost = state.cost_by_tier[tier];
            if (cost <= 0) return null;
            const pct = (cost / totalNonZero) * 100;
            return (
              <motion.div
                key={tier}
                title={`${tier}: $${cost.toFixed(4)}`}
                initial={prefersReduced ? false : { scaleX: 0 }}
                animate={{ scaleX: 1 }}
                transition={{ duration: 0.4, ease: "easeOut" }}
                style={{
                  width: `${pct}%`,
                  background: TIER_COLORS[tier],
                  transformOrigin: "left",
                }}
              />
            );
          })}
        </div>
      )}

      {/* Tier legend */}
      <div className="flex gap-3">
        {TIER_ORDER.filter((t) => state.cost_by_tier[t] > 0).map((tier) => (
          <span key={tier} className="flex items-center gap-1 text-xs font-mono" style={{ color: "var(--text-muted)" }}>
            <span className="inline-block w-2 h-2 rounded-full" style={{ background: TIER_COLORS[tier] }} />
            {tier}
          </span>
        ))}
      </div>
    </div>
  );
}
