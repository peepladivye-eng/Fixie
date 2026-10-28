"use client";
import { motion, useReducedMotion } from "motion/react";
import { CheckCircle, XCircle, Clock, Loader2, Circle } from "lucide-react";
import type { RunState, StepName, ModelTier } from "@/lib/events";

const STEP_LABELS: Record<StepName, string> = {
  triage: "Triage",
  reproduce: "Reproduce",
  diagnose: "Diagnose",
  branch: "Branch",
  deliver: "Deliver",
};

const TIER_LABELS: Record<ModelTier, string> = {
  lightning: "⚡ Lightning",
  super: "🔥 Super",
  ultra: "🚀 Ultra",
  none: "—",
};

const STEP_ORDER: StepName[] = ["triage", "reproduce", "diagnose", "branch", "deliver"];

function TierBadge({ tier }: { tier: ModelTier | null }) {
  if (!tier || tier === "none") return null;
  return (
    <span
      className="rounded px-1.5 py-0.5 text-xs font-mono"
      style={{ background: "var(--surface)", color: "var(--text-muted)", border: "1px solid var(--border)" }}
    >
      {TIER_LABELS[tier]}
    </span>
  );
}

function StepIcon({ status }: { status: string }) {
  if (status === "completed") return <CheckCircle size={16} style={{ color: "var(--pass)" }} />;
  if (status === "failed") return <XCircle size={16} style={{ color: "var(--fail)" }} />;
  if (status === "running") return <Loader2 size={16} className="animate-spin" style={{ color: "var(--accent)" }} />;
  return <Circle size={16} style={{ color: "var(--text-muted)" }} />;
}

export default function Timeline({ state }: { state: RunState }) {
  const prefersReduced = useReducedMotion();

  return (
    <nav aria-label="Run steps" className="flex flex-col gap-2">
      {STEP_ORDER.map((name) => {
        const step = state.steps[name];
        const isActive = step.status === "running";
        return (
          <motion.div
            key={name}
            aria-live={isActive ? "polite" : undefined}
            aria-atomic="true"
            layout={!prefersReduced}
            initial={prefersReduced ? false : { opacity: 0, x: -8 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.2 }}
            className="flex items-center gap-3 rounded-lg px-3 py-2"
            style={{
              background: isActive ? "var(--surface)" : "transparent",
              border: `1px solid ${isActive ? "var(--accent)" : "var(--border)"}`,
              boxShadow: isActive ? "0 0 0 1px var(--accent)" : undefined,
            }}
          >
            <StepIcon status={step.status} />
            <div className="flex flex-col flex-1 min-w-0">
              <span
                className="text-sm font-medium"
                style={{ color: isActive ? "var(--accent)" : "var(--text)" }}
              >
                {STEP_LABELS[name]}
              </span>
              <div className="flex items-center gap-1.5 mt-0.5">
                <TierBadge tier={step.tier} />
                {step.duration > 0 && (
                  <span className="flex items-center gap-1 text-xs" style={{ color: "var(--text-muted)" }}>
                    <Clock size={11} />
                    {step.duration.toFixed(1)}s
                  </span>
                )}
              </div>
            </div>
          </motion.div>
        );
      })}
    </nav>
  );
}
