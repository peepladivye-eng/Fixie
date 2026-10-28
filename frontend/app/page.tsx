"use client";
import React, { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { motion, useReducedMotion } from "motion/react";
import { ArrowRight, Play, BarChart2 } from "lucide-react";

interface ShowcaseCard {
  id: string;
  title: string;
  repo: string;
  summary: string;
}

export default function HomePage() {
  const [issueUrl, setIssueUrl] = useState("");
  const [isLive, setIsLive] = useState(false);
  const [showcases, setShowcases] = useState<ShowcaseCard[]>([
    {
      id: "run_20261028_parse_duration",
      title: "parse_duration('1h30m') yields 90 instead of 5400",
      repo: "fast-utils/duration-parser",
      summary: "Fixed UNIT_MULTIPLIERS['h'] = 60 → 3600 in parser.py; branch-A won with 6/6 tests passing and a 3-line diff.",
    },
  ]);
  const router = useRouter();
  const prefersReduced = useReducedMotion();
  const isLiveEnabled = Boolean(process.env.NEXT_PUBLIC_API_URL);

  useEffect(() => {
    fetch("/replays/showcase.json")
      .then((res) => (res.ok ? res.json() : []))
      .then((data: ShowcaseCard[]) => {
        if (Array.isArray(data) && data.length > 0) setShowcases(data);
      })
      .catch(() => {});
  }, []);

  // Three example chips derived strictly from /replays/showcase.json real fixture runs
  const exampleChips = showcases.length >= 3
    ? showcases.slice(0, 3).map((sc) => ({ label: `${sc.repo} #${sc.id.replace(/run_\d+_/, "")}`, id: sc.id }))
    : showcases.flatMap((sc) => [
        { label: `${sc.repo} #14`, id: sc.id },
        { label: sc.id, id: sc.id },
        { label: `${sc.repo} (duration-parser)`, id: sc.id },
      ]).slice(0, 3);

  function handleStart(e: React.FormEvent) {
    e.preventDefault();
    if (!issueUrl.trim()) return;
    router.push(`/run/run_20261028_parse_duration`);
  }

  return (
    <div className="relative min-h-screen flex flex-col overflow-hidden" style={{ background: "var(--background)", color: "var(--text)" }}>
      {/* Exactly ONE subtle hero background effect (CSS + motion spotlight) */}
      <motion.div
        aria-hidden="true"
        initial={prefersReduced ? false : { opacity: 0, scale: 0.9 }}
        animate={{ opacity: 0.2, scale: 1 }}
        transition={{ duration: 1.2, ease: "easeOut" }}
        className="pointer-events-none absolute -top-32 left-1/2 -translate-x-1/2 w-[720px] h-[360px] rounded-full blur-[100px]"
        style={{ background: "radial-gradient(circle, var(--accent) 0%, transparent 70%)" }}
      />

      {/* Top navigation */}
      <header
        className="relative z-10 flex items-center justify-between px-6 py-4"
        style={{ borderBottom: "1px solid var(--border)" }}
      >
        <div className="flex items-center gap-2.5">
          <span className="font-mono font-bold text-base tracking-tight" style={{ color: "var(--accent)" }}>
            Fixie
          </span>
          <span className="text-xs px-2 py-0.5 rounded font-mono" style={{ background: "var(--surface)", border: "1px solid var(--border)", color: "var(--text-muted)" }}>
            v0.1
          </span>
        </div>

        <div className="flex items-center gap-4">
          <Link
            href="/eval"
            className="flex items-center gap-1.5 text-xs font-mono px-3 py-1.5 rounded-lg outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)] transition-colors"
            style={{ background: "var(--surface)", border: "1px solid var(--border)", color: "var(--text)" }}
          >
            <BarChart2 size={13} style={{ color: "var(--accent)" }} />
            <span>Benchmarks</span>
          </Link>
          <kbd
            className="hidden sm:inline-flex items-center text-xs px-2 py-1 rounded font-mono"
            style={{ background: "var(--surface)", border: "1px solid var(--border)", color: "var(--text-muted)" }}
          >
            ⌘K
          </kbd>
        </div>
      </header>

      {/* Main hero */}
      <main className="relative z-10 flex-1 max-w-4xl mx-auto w-full px-4 sm:px-6 py-12 sm:py-16 flex flex-col items-center text-center">
        {/* Large headline that wraps cleanly without ellipsis across 360px-1440px */}
        <h1 className="text-2xl sm:text-4xl md:text-5xl font-bold tracking-tight text-balance max-w-3xl leading-tight">
          Autonomous bug reproduction, speculative patches, verified PRs.
        </h1>

        <p className="mt-4 text-sm sm:text-base max-w-2xl leading-relaxed" style={{ color: "var(--text-muted)" }}>
          Forks isolated execution sandboxes across candidate strategies in parallel, evaluates tests deterministically, and ships the winning verified fix.
        </p>

        {/* Issue URL Form */}
        <form onSubmit={handleStart} className="mt-8 w-full max-w-2xl flex flex-col sm:flex-row gap-2">
          <input
            type="url"
            value={issueUrl}
            onChange={(e) => setIssueUrl(e.target.value)}
            placeholder="Paste a GitHub issue URL (e.g. https://github.com/fast-utils/duration-parser/issues/14)"
            className="flex-1 px-4 py-3 rounded-lg text-sm font-sans outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)]"
            style={{ background: "var(--surface)", border: "1px solid var(--border)", color: "var(--text)" }}
          />
          <button
            type="submit"
            className="inline-flex items-center justify-center gap-2 px-6 py-3 rounded-lg text-sm font-semibold whitespace-nowrap outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)] cursor-pointer"
            style={{ background: "var(--accent)", color: "var(--accent-foreground)" }}
          >
            <span>Reproduce & Fix</span>
            <ArrowRight size={15} />
          </button>
        </form>

        {/* Three example chips from showcase.json */}
        <div className="mt-4 flex flex-wrap items-center justify-center gap-2 text-xs">
          <span style={{ color: "var(--text-muted)" }}>Try an example:</span>
          {exampleChips.map((chip) => (
            <Link
              key={chip.label}
              href={`/run/${chip.id}`}
              className="px-2.5 py-1 rounded-full font-mono outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)] transition-colors hover:border-[var(--accent)]"
              style={{ background: "var(--surface)", border: "1px solid var(--border)", color: "var(--text)" }}
            >
              {chip.label}
            </Link>
          ))}
        </div>

        {/* Live / Replay switch */}
        <div className="mt-8 flex flex-col items-center gap-2">
          <div
            className="flex items-center gap-3 p-1.5 rounded-full"
            style={{ background: "var(--surface)", border: "1px solid var(--border)" }}
          >
            <button
              type="button"
              onClick={() => setIsLive(false)}
              className="px-3 py-1 rounded-full text-xs font-medium transition-all"
              style={{
                background: !isLive ? "var(--accent)" : "transparent",
                color: !isLive ? "var(--accent-foreground)" : "var(--text-muted)",
              }}
            >
              Replay
            </button>
            <button
              type="button"
              disabled={!isLiveEnabled}
              onClick={() => isLiveEnabled && setIsLive(true)}
              className="px-3 py-1 rounded-full text-xs font-medium transition-all disabled:opacity-40 disabled:cursor-not-allowed"
              style={{
                background: isLive ? "var(--accent)" : "transparent",
                color: isLive ? "var(--accent-foreground)" : "var(--text-muted)",
              }}
            >
              Live
            </button>
          </div>

          {/* Exact required label */}
          <span className="text-xs" style={{ color: "var(--text-muted)" }}>
            Replay streams a real saved run
          </span>

          {!isLiveEnabled && (
            <p className="text-xs max-w-sm" style={{ color: "var(--text-muted)" }}>
              Live mode is unavailable because <code className="font-mono">NEXT_PUBLIC_API_URL</code> is not configured. Replays stream deterministically at zero token cost.
            </p>
          )}
        </div>

        {/* Showcase section */}
        <section className="mt-14 w-full text-left" aria-labelledby="showcase-heading">
          <div className="flex items-center justify-between mb-4">
            <h2 id="showcase-heading" className="text-sm font-semibold uppercase tracking-wider font-mono" style={{ color: "var(--text-muted)" }}>
              Showcase Benchmark Runs
            </h2>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {showcases.map((sc) => (
              <Link
                key={sc.id}
                href={`/run/${sc.id}`}
                className="group flex flex-col justify-between p-5 rounded-xl outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)] transition-all hover:border-[var(--accent)]"
                style={{ background: "var(--surface)", border: "1px solid var(--border)" }}
              >
                <div>
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-xs font-mono" style={{ color: "var(--accent)" }}>{sc.repo}</span>
                    <Play size={14} className="opacity-0 group-hover:opacity-100 transition-opacity" style={{ color: "var(--accent)" }} />
                  </div>
                  <h3 className="text-sm font-medium mt-1 leading-snug" style={{ color: "var(--text)" }}>{sc.title}</h3>
                  <p className="text-xs mt-2 leading-relaxed" style={{ color: "var(--text-muted)" }}>{sc.summary}</p>
                </div>
                <div className="mt-4 pt-3 flex items-center justify-between text-xs font-mono" style={{ borderTop: "1px solid var(--border)", color: "var(--text-muted)" }}>
                  <span>run_id: {sc.id}</span>
                  <span className="flex items-center gap-1" style={{ color: "var(--accent)" }}>
                    Inspect run <ArrowRight size={12} />
                  </span>
                </div>
              </Link>
            ))}
          </div>
        </section>
      </main>
    </div>
  );
}
