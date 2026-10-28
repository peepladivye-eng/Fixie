"use client";
import { useState } from "react";
import { motion, useReducedMotion } from "motion/react";
import { Copy, ExternalLink, Check } from "lucide-react";
import type { RunState } from "@/lib/events";

type Tab = "diff" | "evidence" | "root_cause" | "pr";

const TAB_LABELS: Record<Tab, string> = {
  diff: "Diff",
  evidence: "Evidence",
  root_cause: "Root Cause",
  pr: "PR",
};

export default function ResultPanel({ state }: { state: RunState }) {
  const [activeTab, setActiveTab] = useState<Tab>("diff");
  const [copied, setCopied] = useState(false);
  const prefersReduced = useReducedMotion();

  function handleCopy() {
    if (state.diff) {
      navigator.clipboard.writeText(state.diff).then(() => {
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      });
    }
  }

  const tabs: Tab[] = ["diff", "evidence", "root_cause", ...(state.pr_url ? (["pr"] as Tab[]) : [])];

  return (
    <div
      className="flex flex-col rounded-lg overflow-hidden"
      style={{ background: "var(--surface)", border: "1px solid var(--border)" }}
    >
      {/* Tab bar */}
      <div
        className="flex gap-1 px-3 pt-2 pb-0 overflow-x-auto flex-shrink-0"
        role="tablist"
        aria-label="Result panels"
      >
        {tabs.map((tab) => (
          <button
            key={tab}
            role="tab"
            aria-selected={activeTab === tab}
            onClick={() => setActiveTab(tab)}
            className="px-3 py-1.5 text-xs font-medium rounded-t-md whitespace-nowrap outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)]"
            style={{
              color: activeTab === tab ? "var(--accent)" : "var(--text-muted)",
              borderBottom: `2px solid ${activeTab === tab ? "var(--accent)" : "transparent"}`,
            }}
          >
            {TAB_LABELS[tab]}
          </button>
        ))}
      </div>

      <div style={{ height: "1px", background: "var(--border)" }} />

      <motion.div
        key={activeTab}
        initial={prefersReduced ? false : { opacity: 0, y: 4 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.15 }}
        className="flex-1 overflow-y-auto p-3 min-h-0"
        role="tabpanel"
      >
        {activeTab === "diff" && (
          <DiffTab diff={state.diff} onCopy={handleCopy} copied={copied} />
        )}
        {activeTab === "evidence" && (
          <EvidenceTab searches={state.searches} />
        )}
        {activeTab === "root_cause" && (
          <RootCauseTab rootCause={state.root_cause} />
        )}
        {activeTab === "pr" && state.pr_url && (
          <PrTab prUrl={state.pr_url} />
        )}
      </motion.div>
    </div>
  );
}

function DiffTab({ diff, onCopy, copied }: { diff: string | null; onCopy: () => void; copied: boolean }) {
  if (!diff) {
    return <p className="text-xs" style={{ color: "var(--text-muted)" }}>Diff will appear after deliver step.</p>;
  }
  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center justify-between">
        <span className="text-xs font-mono" style={{ color: "var(--text-muted)" }}>Unified diff</span>
        <button
          onClick={onCopy}
          className="flex items-center gap-1 rounded px-2 py-1 text-xs outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)]"
          style={{ background: "var(--border)", color: "var(--text-muted)" }}
          aria-label="Copy patch"
        >
          {copied ? <Check size={12} /> : <Copy size={12} />}
          {copied ? "Copied" : "Copy patch"}
        </button>
      </div>
      <pre
        className="text-xs overflow-x-auto rounded p-3 font-mono leading-5"
        style={{ background: "var(--background)", border: "1px solid var(--border)" }}
      >
        {diff.split("\n").map((line, i) => {
          const color = line.startsWith("+") ? "var(--pass)" : line.startsWith("-") ? "var(--fail)" : line.startsWith("@@") ? "var(--badge-blue)" : "var(--text)";
          return <span key={i} style={{ color, display: "block" }}>{line}</span>;
        })}
      </pre>
    </div>
  );
}

function EvidenceTab({ searches }: { searches: RunState["searches"] }) {
  if (searches.length === 0) {
    return <p className="text-xs" style={{ color: "var(--text-muted)" }}>No search evidence collected yet.</p>;
  }
  return (
    <ul className="flex flex-col gap-2">
      {searches.map((s, i) => (
        <li key={i} className="rounded p-2" style={{ background: "var(--background)", border: "1px solid var(--border)" }}>
          <a
            href={s.url}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-start gap-1.5 group text-sm outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)] rounded"
            style={{ color: s.used ? "var(--accent)" : "var(--text-muted)" }}
          >
            <ExternalLink size={12} className="mt-0.5 flex-shrink-0" />
            <span className="font-medium group-hover:underline">{s.title}</span>
          </a>
          <p className="text-xs mt-1 font-mono" style={{ color: "var(--text-muted)" }}>{s.query}</p>
        </li>
      ))}
    </ul>
  );
}

function RootCauseTab({ rootCause }: { rootCause: string | null }) {
  if (!rootCause) {
    return <p className="text-xs" style={{ color: "var(--text-muted)" }}>Root cause analysis will appear after diagnose step.</p>;
  }
  return (
    <div
      className="rounded p-3 text-sm font-mono leading-6 whitespace-pre-wrap"
      style={{ background: "var(--background)", border: "1px solid var(--border)", color: "var(--text)" }}
    >
      {rootCause}
    </div>
  );
}

function PrTab({ prUrl }: { prUrl: string }) {
  return (
    <div className="flex flex-col gap-3">
      <p className="text-sm" style={{ color: "var(--text)" }}>Pull request is ready.</p>
      <a
        href={prUrl}
        target="_blank"
        rel="noopener noreferrer"
        className="inline-flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-semibold outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)]"
        style={{ background: "var(--accent)", color: "var(--accent-foreground)" }}
      >
        <ExternalLink size={14} />
        Open PR
      </a>
    </div>
  );
}
