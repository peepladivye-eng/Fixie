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

/** Returns true if the model name looks like a dev/fake provider. */
function isDevModel(model: string): boolean {
  const m = model.toLowerCase();
  return m.startsWith("fake") || m.includes("gemini");
}

export default function RunHeader({ state, speed, paused, onSpeed, onTogglePause }: Props) {
  const prefersReduced = useReducedMotion();
  const isReplay = state.mode === "replay";

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

  const hasDevModel = state.models_used.some(isDevModel);

  return (
    <header
      className="flex flex-col gap-2 px-4 py-3"
      style={{ borderBottom: "1px solid var(--border)", background: "var(--surface)" }}
    >
      {/* Row 1: title + controls */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
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

            {/* Recorded run badge — always visible in replay mode */}
            {isReplay && (
              <span
                className="text-xs font-mono px-2 py-0.5 rounded-full flex-shrink-0"
                style={{
                  background: "var(--background)",
                  border: "1px solid var(--border)",
                  color: "var(--text-muted)",
                }}
              >
                Recorded run
              </span>
            )}
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
      </div>

      {/* Row 2: model chips + dev warning — only when models are known */}
      {state.models_used.length > 0 && (
        <div className="flex flex-wrap items-center gap-1.5">
          <span className="text-xs" style={{ color: "var(--text-muted)" }}>Models:</span>
          {state.models_used.map((m) => (
            <span
              key={m}
              className="text-xs font-mono px-2 py-0.5 rounded"
              style={{
                background: "var(--background)",
                border: "1px solid var(--border)",
                color: "var(--text)",
              }}
            >
              {m}
            </span>
          ))}

          {/* Dev provider warning — never hidden if any fake/gemini model */}
          {hasDevModel && (
            <span
              className="text-xs font-semibold px-2 py-0.5 rounded"
              style={{
                background: "rgba(245, 165, 36, 0.15)",
                border: "1px solid var(--accent)",
                color: "var(--accent)",
              }}
              role="alert"
            >
              DEV PROVIDER, not a submission result
            </span>
          )}
        </div>
      )}
    </header>
  );
}
