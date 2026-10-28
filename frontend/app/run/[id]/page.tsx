"use client";
import { use, useState } from "react";
import { useRunState } from "@/lib/useRunState";
import dynamic from "next/dynamic";
import Timeline from "@/components/run/Timeline";
import Terminal from "@/components/run/Terminal";
import ResultPanel from "@/components/run/ResultPanel";
import CostMeter from "@/components/run/CostMeter";
import RunHeader from "@/components/run/RunHeader";
import { AlertTriangle, RotateCcw } from "lucide-react";
import type { RunState } from "@/lib/events";

// BranchBoard uses @xyflow/react which requires the browser
const BranchBoard = dynamic(() => import("@/components/run/BranchBoard"), { ssr: false });

function LoadingSkeleton() {
  return (
    <div
      className="flex-1 grid gap-4 p-4 animate-pulse"
      style={{ gridTemplateColumns: "minmax(0,240px) 1fr minmax(0,280px)" }}
    >
      {[0, 1, 2].map((i) => (
        <div key={i} className="rounded-lg h-64" style={{ background: "var(--surface)" }} />
      ))}
    </div>
  );
}

function ErrorState({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div className="flex-1 flex flex-col items-center justify-center gap-4 p-8">
      <AlertTriangle size={32} style={{ color: "var(--fail)" }} />
      <p className="text-sm font-mono text-center" style={{ color: "var(--text)" }}>{message}</p>
      <button
        onClick={onRetry}
        className="flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-semibold outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)]"
        style={{ background: "var(--accent)", color: "var(--accent-foreground)" }}
      >
        <RotateCcw size={14} />
        Retry
      </button>
    </div>
  );
}

function RunNotFound({ id }: { id: string }) {
  return (
    <div className="flex-1 flex flex-col items-center justify-center gap-3 p-8">
      <AlertTriangle size={32} style={{ color: "var(--text-muted)" }} />
      <p className="text-sm" style={{ color: "var(--text-muted)" }}>
        Run <code className="font-mono">{id}</code> not found.
      </p>
    </div>
  );
}

type MobileTab = "terminal" | "branches" | "results";

function MobileTabs({ state }: { state: RunState }) {
  const [tab, setTab] = useState<MobileTab>("terminal");
  return (
    <div className="flex flex-col flex-1 min-h-0 overflow-hidden">
      <div
        className="flex gap-1 px-3 py-1.5 flex-shrink-0 overflow-x-auto"
        style={{ borderBottom: "1px solid var(--border)" }}
        role="tablist"
      >
        {(["terminal", "branches", "results"] as const).map((t) => (
          <button
            key={t}
            role="tab"
            aria-selected={tab === t}
            onClick={() => setTab(t)}
            className="px-3 py-1 text-xs font-medium whitespace-nowrap outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)]"
            style={{
              color: tab === t ? "var(--accent)" : "var(--text-muted)",
              borderBottom: `2px solid ${tab === t ? "var(--accent)" : "transparent"}`,
            }}
          >
            {t.charAt(0).toUpperCase() + t.slice(1)}
          </button>
        ))}
      </div>
      <div className="flex-1 min-h-0 overflow-hidden p-3">
        {tab === "terminal" && <Terminal state={state} />}
        {tab === "branches" && <BranchBoard state={state} />}
        {tab === "results" && <ResultPanel state={state} />}
      </div>
    </div>
  );
}

function RunView({ runId }: { runId: string }) {
  const { state, loading, fatalError, speed, paused, changeSpeed, togglePause } = useRunState(runId);

  if (loading && state.status === "idle") return <LoadingSkeleton />;
  if (fatalError?.includes("not found")) return <RunNotFound id={runId} />;
  if (fatalError) return <ErrorState message={fatalError} onRetry={() => window.location.reload()} />;

  return (
    <div className="flex flex-col h-full w-full overflow-hidden">
      {/* Fixed Header */}
      <div className="flex-shrink-0">
        <RunHeader state={state} speed={speed} paused={paused} onSpeed={changeSpeed} onTogglePause={togglePause} />
      </div>

      {/* Middle: 3 columns on desktop, tabs on mobile */}
      <div className="flex-1 min-h-0 w-full overflow-hidden flex flex-col lg:flex-row">
        {/* Left Column: Timeline (scrolls internally) */}
        <aside
          className="lg:w-60 xl:w-64 flex-shrink-0 h-full overflow-y-auto p-3 hidden lg:block"
          style={{ borderRight: "1px solid var(--border)" }}
          aria-label="Step timeline"
        >
          <Timeline state={state} />
        </aside>

        {/* Mobile: tabbed layout */}
        <div className="lg:hidden flex-1 flex flex-col min-h-0 overflow-hidden">
          <MobileTabs state={state} />
        </div>

        {/* Center & Right Columns on Desktop */}
        <div className="hidden lg:flex flex-1 min-w-0 min-h-0 h-full overflow-hidden">
          {/* Center Column: Terminal (scrolls internally) */}
          <main className="flex-1 h-full p-3 min-h-0 min-w-0 overflow-hidden flex flex-col">
            <Terminal state={state} />
          </main>

          {/* Right Column: Branch Board + Result Panel (scrolls internally) */}
          <aside
            className="w-80 xl:w-96 flex-shrink-0 h-full flex flex-col p-3 gap-3 min-h-0 overflow-hidden"
            style={{ borderLeft: "1px solid var(--border)" }}
          >
            <div className="flex-shrink-0 h-[260px] overflow-hidden">
              <BranchBoard state={state} />
            </div>
            <div className="flex-1 min-h-0 overflow-hidden flex flex-col">
              <ResultPanel state={state} />
            </div>
          </aside>
        </div>
      </div>

      {/* Fixed bottom cost meter */}
      <div className="flex-shrink-0">
        <CostMeter state={state} />
      </div>
    </div>
  );
}

export default function RunPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  return (
    <div
      className="flex flex-col h-dvh max-h-dvh w-full overflow-hidden"
      style={{ background: "var(--background)", color: "var(--text)" }}
    >
      <RunView runId={id} />
    </div>
  );
}
