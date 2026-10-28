"use client";
import { useEffect, useRef, useState } from "react";
import type { RunState, TerminalLine } from "@/lib/events";

// Minimal ANSI color codes support (foreground only)
const ANSI_RESET = /\x1b\[0m/g;
const ANSI_FG: Record<string, string> = {
  "30": "var(--text-muted)",
  "31": "var(--fail)",
  "32": "var(--pass)",
  "33": "var(--accent)",
  "34": "var(--badge-blue)",
  "35": "#C084FC",
  "36": "#67E8F9",
  "37": "var(--text)",
  "90": "var(--text-muted)",
  "91": "var(--fail)",
  "92": "var(--pass)",
  "93": "var(--accent)",
  "94": "var(--badge-blue)",
};

function ansiToSpans(text: string): { color?: string; text: string }[] {
  const segs: { color?: string; text: string }[] = [];
  const parts = text.replace(ANSI_RESET, "\x1b[0m").split(/(\x1b\[\d+m)/);
  let currentColor: string | undefined;
  for (const part of parts) {
    const m = part.match(/^\x1b\[(\d+)m$/);
    if (m) {
      currentColor = m[1] === "0" ? undefined : (ANSI_FG[m[1]] ?? undefined);
    } else if (part) {
      segs.push({ color: currentColor, text: part });
    }
  }
  return segs;
}

function TermLine({ line }: { line: TerminalLine }) {
  const segs = ansiToSpans(line.text);
  const baseColor = line.stream === "stderr" ? "var(--fail)" : undefined;
  return (
    <div className="whitespace-pre-wrap break-words leading-5 text-xs font-mono">
      {segs.map((s, i) => (
        <span key={i} style={{ color: s.color ?? baseColor ?? "var(--text)" }}>
          {s.text}
        </span>
      ))}
    </div>
  );
}

const ALL_BRANCHES = "all";

export default function Terminal({ state }: { state: RunState }) {
  const bottomRef = useRef<HTMLDivElement>(null);
  const branchIds = Object.keys(state.branches);
  const hasBranches = branchIds.length > 0;
  const [activeBranch, setActiveBranch] = useState<string>(ALL_BRANCHES);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [state.terminal]);

  const nullLines: TerminalLine[] = state.terminal["null"] ?? [];
  const branchLines: TerminalLine[] =
    activeBranch === ALL_BRANCHES
      ? branchIds.flatMap((id) => state.terminal[id] ?? []).sort((a, b) => a.ts.localeCompare(b.ts))
      : (state.terminal[activeBranch] ?? []);

  const visibleLines = activeBranch === ALL_BRANCHES
    ? [...nullLines, ...branchLines].sort((a, b) => a.ts.localeCompare(b.ts))
    : [...nullLines, ...branchLines];

  const currentStep = state.current_step ?? "—";

  return (
    <div
      className="flex flex-col rounded-lg overflow-hidden h-full"
      style={{ background: "var(--surface)", border: "1px solid var(--border)" }}
    >
      {/* sticky header */}
      <div
        className="flex items-center justify-between px-3 py-2 text-xs font-mono sticky top-0 z-10 flex-shrink-0"
        style={{ background: "var(--surface)", borderBottom: "1px solid var(--border)" }}
      >
        <span style={{ color: "var(--text-muted)" }}>
          $ <span style={{ color: "var(--accent)" }}>{currentStep}</span>
        </span>
      </div>

      {/* branch filter tabs */}
      {hasBranches && (
        <div
          className="flex gap-1 px-3 py-1.5 overflow-x-auto flex-shrink-0 text-xs"
          style={{ borderBottom: "1px solid var(--border)" }}
          role="tablist"
          aria-label="Branch filter"
        >
          {[ALL_BRANCHES, ...branchIds].map((id) => {
            const isActive = activeBranch === id;
            return (
              <button
                key={id}
                role="tab"
                aria-selected={isActive}
                onClick={() => setActiveBranch(id)}
                className="rounded px-2 py-0.5 font-mono whitespace-nowrap focus-visible:ring-2 focus-visible:ring-[var(--ring)] outline-none"
                style={{
                  background: isActive ? "var(--accent)" : "transparent",
                  color: isActive ? "var(--accent-foreground)" : "var(--text-muted)",
                  border: `1px solid ${isActive ? "var(--accent)" : "var(--border)"}`,
                }}
              >
                {id === ALL_BRANCHES ? "all" : id}
              </button>
            );
          })}
        </div>
      )}

      {/* scrollable log */}
      <div className="flex-1 overflow-y-auto px-3 py-2 min-h-0">
        {visibleLines.length === 0 ? (
          <p className="text-xs font-mono" style={{ color: "var(--text-muted)" }}>Waiting for output…</p>
        ) : (
          visibleLines.map((line, i) => <TermLine key={i} line={line} />)
        )}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
