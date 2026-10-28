"use client";
import { motion, useReducedMotion } from "motion/react";
import type { RunState } from "@/lib/events";

interface Props {
  state: RunState;
  speed: 1 | 2 | 4;
  paused: boolean;
  onSpeed: (s: 1 | 2 | 4) => void;
  onTogglePause: () => void;
}

export default function RunHeader({ state, speed, paused, onSpeed, onTogglePause }: Props) {
  const prefersReduced = useReducedMotion();
  const statusLabel =
    state.status === "idle" ? "Waiting…"
    : state.status === "running" ? "Running"
    : state.status === "success" ? "Success"
    : state.status === "failed" ? "Failed"
    : state.status === "error" ? "Error"
    : "Unknown";

  const statusColor =
    state.status === "success" ? "var(--pass)"
    : state.status === "failed" || state.status === "error" ? "var(--fail)"
    : state.status === "running" ? "var(--accent)"
    : "var(--text-muted)";

  return (
    <header
      className="flex flex-wrap items-center gap-3 px-4 py-3"
      style={{ borderBottom: "1px solid var(--border)", background: "var(--surface)" }}
    >
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <motion.span
            className="inline-block w-2 h-2 rounded-full flex-shrink-0"
            style={{ background: statusColor }}
            animate={!prefersReduced && state.status === "running"
              ? { opacity: [1, 0.3, 1] }
              : { opacity: 1 }}
            transition={{ repeat: Infinity, duration: 1.2 }}
          />
          <h1 className="text-sm font-semibold truncate" style={{ color: "var(--text)" }}>
            {state.issue_title ?? state.run_id ?? "Loading…"}
          </h1>
          <span className="text-xs flex-shrink-0" style={{ color: statusColor }}>{statusLabel}</span>
        </div>
        {state.repo && (
          <p className="text-xs mt-0.5 truncate font-mono" style={{ color: "var(--text-muted)" }}>
            {state.repo}
          </p>
        )}
      </div>

      {/* Speed + pause controls */}
      <div className="flex items-center gap-1.5 text-xs font-mono flex-shrink-0" role="group" aria-label="Playback controls">
        {([1, 2, 4] as const).map((s) => (
          <button
            key={s}
            onClick={() => onSpeed(s)}
            aria-pressed={speed === s}
            className="rounded px-2 py-1 outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)]"
            style={{
              background: speed === s ? "var(--accent)" : "var(--border)",
              color: speed === s ? "var(--accent-foreground)" : "var(--text-muted)",
            }}
          >
            {s}×
          </button>
        ))}
        <button
          onClick={onTogglePause}
          aria-label={paused ? "Resume" : "Pause"}
          className="rounded px-2 py-1 outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)]"
          style={{ background: "var(--border)", color: "var(--text-muted)" }}
        >
          {paused ? "▶" : "⏸"}
        </button>
      </div>
    </header>
  );
}
