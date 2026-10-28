"use client";
import React from "react";
import Link from "next/link";
import { AlertCircle, AlertTriangle, Clock, RefreshCw, FileQuestion, ArrowRight } from "lucide-react";

export function LoadingSkeleton({ count = 3 }: { count?: number }) {
  return (
    <div className="w-full flex flex-col gap-3 p-4 animate-pulse" role="status" aria-label="Loading content">
      {Array.from({ length: count }).map((_, i) => (
        <div
          key={i}
          className="rounded-lg h-20"
          style={{ background: "var(--surface)", border: "1px solid var(--border)" }}
        />
      ))}
    </div>
  );
}

export function EmptyState({
  title = "No runs yet",
  description = "Start a reproduction run from the home page or choose a benchmark case.",
}: {
  title?: string;
  description?: string;
}) {
  return (
    <div
      className="flex flex-col items-center justify-center p-8 text-center rounded-xl my-6"
      style={{ background: "var(--surface)", border: "1px dashed var(--border)" }}
    >
      <div
        className="w-12 h-12 rounded-full flex items-center justify-center mb-3"
        style={{ background: "var(--background)", color: "var(--text-muted)" }}
      >
        <FileQuestion size={24} />
      </div>
      <h3 className="text-base font-semibold" style={{ color: "var(--text)" }}>{title}</h3>
      <p className="text-sm mt-1 max-w-sm" style={{ color: "var(--text-muted)" }}>{description}</p>
    </div>
  );
}

export function ErrorState({
  message = "An unexpected error occurred while executing the run.",
  onRetry,
}: {
  message?: string;
  onRetry?: () => void;
}) {
  return (
    <div
      className="flex flex-col items-center justify-center p-8 text-center rounded-xl"
      style={{ background: "var(--surface)", border: "1px solid var(--border)" }}
      role="alert"
    >
      <div
        className="w-12 h-12 rounded-full flex items-center justify-center mb-3"
        style={{ background: "var(--background)", color: "var(--fail)" }}
      >
        <AlertCircle size={24} />
      </div>
      <h3 className="text-base font-semibold" style={{ color: "var(--text)" }}>Something went wrong</h3>
      <p className="text-sm mt-1 max-w-md font-mono" style={{ color: "var(--text-muted)" }}>{message}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="mt-4 flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-semibold outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)] cursor-pointer"
          style={{ background: "var(--accent)", color: "var(--accent-foreground)" }}
        >
          <RefreshCw size={14} />
          Retry operation
        </button>
      )}
    </div>
  );
}

export function RateLimitState({ replayUrl = "/run/run_20261028_parse_duration" }: { replayUrl?: string }) {
  return (
    <div
      className="flex flex-col items-center justify-center p-8 text-center rounded-xl"
      style={{ background: "var(--surface)", border: "1px solid var(--border)" }}
    >
      <div
        className="w-12 h-12 rounded-full flex items-center justify-center mb-3"
        style={{ background: "var(--background)", color: "var(--accent)" }}
      >
        <AlertTriangle size={24} />
      </div>
      <h3 className="text-base font-semibold" style={{ color: "var(--text)" }}>Rate limit reached</h3>
      <p className="text-sm mt-1 max-w-md" style={{ color: "var(--text-muted)" }}>
        Live LLM quota or API rate limits were exhausted. You can inspect saved deterministic replays with zero token cost.
      </p>
      <Link
        href={replayUrl}
        className="mt-4 inline-flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-semibold outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)]"
        style={{ background: "var(--accent)", color: "var(--accent-foreground)" }}
      >
        <span>Switch to replay run</span>
        <ArrowRight size={14} />
      </Link>
    </div>
  );
}

export function BackendAsleepState() {
  return (
    <div
      className="flex flex-col items-center justify-center p-8 text-center rounded-xl"
      style={{ background: "var(--surface)", border: "1px solid var(--border)" }}
      aria-live="polite"
    >
      <div
        className="w-12 h-12 rounded-full flex items-center justify-center mb-3 animate-pulse"
        style={{ background: "var(--background)", color: "var(--accent)" }}
      >
        <Clock size={24} />
      </div>
      <h3 className="text-base font-semibold" style={{ color: "var(--text)" }}>Waking up sandbox…</h3>
      <p className="text-sm mt-1 max-w-md" style={{ color: "var(--text-muted)" }}>
        Cold container booting up. This usually takes 10–20 seconds when waking from idle sleep.
      </p>
    </div>
  );
}

export function NotFoundState({ id }: { id?: string }) {
  return (
    <div
      className="flex flex-col items-center justify-center p-8 text-center rounded-xl my-8"
      style={{ background: "var(--surface)", border: "1px solid var(--border)" }}
    >
      <div
        className="w-12 h-12 rounded-full flex items-center justify-center mb-3"
        style={{ background: "var(--background)", color: "var(--text-muted)" }}
      >
        <FileQuestion size={24} />
      </div>
      <h3 className="text-base font-semibold" style={{ color: "var(--text)" }}>404 — Not Found</h3>
      <p className="text-sm mt-1 max-w-md" style={{ color: "var(--text-muted)" }}>
        {id ? `The requested item (${id}) does not exist or has expired.` : "The page you requested could not be found."}
      </p>
      <Link
        href="/"
        className="mt-4 inline-flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-semibold outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)]"
        style={{ background: "var(--border)", color: "var(--text)" }}
      >
        Return to Home
      </Link>
    </div>
  );
}
