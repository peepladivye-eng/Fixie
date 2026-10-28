"use client";
import React, { useEffect, useState } from "react";
import Link from "next/link";
import dynamic from "next/dynamic";
import { ArrowLeft, AlertTriangle, Info, CheckCircle2, XCircle } from "lucide-react";

const EvalChart = dynamic(() => import("@/components/eval/EvalChart"), { ssr: false });

interface ModelUsage {
  input_tokens: number;
  output_tokens: number;
  cost_usd: number;
}

interface RunSummary {
  resolved: number;
  rounds: number;
  cost_usd: number;
  seconds: number;
  per_model?: Record<string, ModelUsage>;
}

interface InstanceResult {
  id: string;
  baseline: {
    resolved: boolean;
    cost_usd: number;
    seconds: number;
  };
  branching: {
    resolved: boolean;
    cost_usd: number;
    seconds: number;
  };
}

interface EvalData {
  synthetic: boolean;
  provider?: string;
  generated_at?: string;
  instances_total: number;
  baseline: RunSummary;
  branching: RunSummary;
  results: InstanceResult[];
}

export default function EvalPage() {
  const [data, setData] = useState<EvalData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("/eval.json")
      .then((res) => (res.ok ? res.json() : null))
      .then((d: EvalData | null) => {
        setData(d);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center p-8" style={{ background: "var(--background)", color: "var(--text)" }}>
        <p className="text-sm font-mono" style={{ color: "var(--text-muted)" }}>Loading evaluation benchmark…</p>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="min-h-screen p-8 max-w-4xl mx-auto" style={{ background: "var(--background)", color: "var(--text)" }}>
        <Link href="/" className="inline-flex items-center gap-1.5 text-xs font-mono mb-6" style={{ color: "var(--accent)" }}>
          <ArrowLeft size={14} /> Back to Home
        </Link>
        <p className="text-sm" style={{ color: "var(--text-muted)" }}>No evaluation dataset found in /eval.json.</p>
      </div>
    );
  }

  const total = data.instances_total || 1;
  const baseRate = data.baseline.resolved / total;
  const branchRate = data.branching.resolved / total;

  // Guard divide-by-zero: when resolved is 0 show "n/a" for cost per fix
  const baseCostPerFix = data.baseline.resolved > 0 ? data.baseline.cost_usd / data.baseline.resolved : null;
  const branchCostPerFix = data.branching.resolved > 0 ? data.branching.cost_usd / data.branching.resolved : null;
  const provider = data.provider ?? "Fake Local Provider";

  return (
    <div className="min-h-screen flex flex-col" style={{ background: "var(--background)", color: "var(--text)" }}>
      {/* Top navbar */}
      <header className="flex items-center justify-between px-6 py-4" style={{ borderBottom: "1px solid var(--border)" }}>
        <Link href="/" className="inline-flex items-center gap-2 text-xs font-mono outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)]" style={{ color: "var(--text)" }}>
          <ArrowLeft size={14} />
          <span>Home</span>
        </Link>
        <span className="text-xs font-mono" style={{ color: "var(--text-muted)" }}>Evaluation Benchmark Suite</span>
      </header>

      <main className="flex-1 max-w-5xl mx-auto w-full px-4 sm:px-6 py-8 flex flex-col gap-6">
        {/* Synthetic amber banner */}
        {data.synthetic && (
          <div
            className="flex items-center gap-3 p-4 rounded-xl font-medium text-sm"
            style={{
              background: "rgba(245, 165, 36, 0.12)",
              border: "1px solid var(--accent)",
              color: "var(--accent)",
            }}
            role="alert"
          >
            <AlertTriangle size={20} className="flex-shrink-0" />
            <span>Synthetic placeholder data, not a real result</span>
          </div>
        )}

        <div>
          <h1 className="text-2xl font-bold tracking-tight">Benchmark Performance</h1>
          <p className="text-sm mt-1" style={{ color: "var(--text-muted)" }}>
            Comparing Single-Shot Baseline vs Speculative Branching across {data.instances_total} test cases.
          </p>
        </div>

        {/* Metrics Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <div className="p-4 rounded-xl" style={{ background: "var(--surface)", border: "1px solid var(--border)" }}>
            <span className="text-xs font-mono" style={{ color: "var(--text-muted)" }}>Baseline Resolved</span>
            <p className="text-xl font-bold mt-1 font-mono" style={{ color: "var(--text)" }}>
              {data.baseline.resolved} / {total}
            </p>
            <span className="text-xs" style={{ color: "var(--text-muted)" }}>({(baseRate * 100).toFixed(0)}%)</span>
          </div>

          <div className="p-4 rounded-xl" style={{ background: "var(--surface)", border: "1px solid var(--border)" }}>
            <span className="text-xs font-mono" style={{ color: "var(--text-muted)" }}>Branching Resolved</span>
            <p className="text-xl font-bold mt-1 font-mono" style={{ color: "var(--accent)" }}>
              {data.branching.resolved} / {total}
            </p>
            <span className="text-xs" style={{ color: "var(--pass)" }}>({(branchRate * 100).toFixed(0)}%)</span>
          </div>

          <div className="p-4 rounded-xl" style={{ background: "var(--surface)", border: "1px solid var(--border)" }}>
            <span className="text-xs font-mono" style={{ color: "var(--text-muted)" }}>Baseline Cost/Fix</span>
            <p className="text-xl font-bold mt-1 font-mono" style={{ color: "var(--text)" }}>
              {baseCostPerFix !== null ? `$${baseCostPerFix.toFixed(4)}` : "n/a"}
            </p>
          </div>

          <div className="p-4 rounded-xl" style={{ background: "var(--surface)", border: "1px solid var(--border)" }}>
            <span className="text-xs font-mono" style={{ color: "var(--text-muted)" }}>Branching Cost/Fix</span>
            <p className="text-xl font-bold mt-1 font-mono" style={{ color: "var(--accent)" }}>
              {branchCostPerFix !== null ? `$${branchCostPerFix.toFixed(4)}` : "n/a"}
            </p>
          </div>
        </div>

        {/* Recharts chart */}
        <div className="p-5 rounded-xl" style={{ background: "var(--surface)", border: "1px solid var(--border)" }}>
          <h2 className="text-sm font-semibold mb-3">Resolve Rate & Cost Comparison</h2>
          <EvalChart
            baselineResolvedRate={baseRate}
            branchingResolvedRate={branchRate}
            baselineCostPerFix={baseCostPerFix}
            branchingCostPerFix={branchCostPerFix}
          />
        </div>

        {/* Per-instance Table */}
        <div className="rounded-xl overflow-hidden" style={{ background: "var(--surface)", border: "1px solid var(--border)" }}>
          <div className="p-4" style={{ borderBottom: "1px solid var(--border)" }}>
            <h2 className="text-sm font-semibold">Per-Instance Results</h2>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-xs text-left">
              <thead className="font-mono text-xs uppercase" style={{ background: "var(--background)", color: "var(--text-muted)" }}>
                <tr>
                  <th className="px-4 py-3">Instance ID</th>
                  <th className="px-4 py-3">Baseline</th>
                  <th className="px-4 py-3">Branching</th>
                  <th className="px-4 py-3">Baseline Cost</th>
                  <th className="px-4 py-3">Branching Cost</th>
                </tr>
              </thead>
              <tbody className="divide-y font-mono" style={{ borderColor: "var(--border)" }}>
                {data.results && data.results.length > 0 ? (
                  data.results.map((r) => (
                    <tr key={r.id} className="hover:bg-[var(--border)] transition-colors">
                      <td className="px-4 py-3 font-semibold">{r.id}</td>
                      <td className="px-4 py-3">
                        {r.baseline.resolved ? (
                          <span className="flex items-center gap-1" style={{ color: "var(--pass)" }}><CheckCircle2 size={13} /> Pass</span>
                        ) : (
                          <span className="flex items-center gap-1" style={{ color: "var(--fail)" }}><XCircle size={13} /> Fail</span>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        {r.branching.resolved ? (
                          <span className="flex items-center gap-1" style={{ color: "var(--pass)" }}><CheckCircle2 size={13} /> Pass</span>
                        ) : (
                          <span className="flex items-center gap-1" style={{ color: "var(--fail)" }}><XCircle size={13} /> Fail</span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-text-muted">${r.baseline.cost_usd.toFixed(4)}</td>
                      <td className="px-4 py-3 text-text-muted">${r.branching.cost_usd.toFixed(4)}</td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={5} className="px-4 py-6 text-center" style={{ color: "var(--text-muted)" }}>
                      Aggregate benchmark run: 12 instances ({data.baseline.resolved} baseline vs {data.branching.resolved} branching passed).
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Caveats Box */}
        <div
          className="p-5 rounded-xl flex items-start gap-3.5 text-xs leading-relaxed"
          style={{ background: "var(--surface)", border: "1px solid var(--border)" }}
        >
          <Info size={18} className="mt-0.5 flex-shrink-0" style={{ color: "var(--badge-blue)" }} />
          <div className="space-y-1.5" style={{ color: "var(--text-muted)" }}>
            <h3 className="font-semibold" style={{ color: "var(--text)" }}>Evaluation Caveats & Methodology</h3>
            <p>1. Models may have seen public benchmarks in training data prior to testing.</p>
            <p>2. The sample size is small ({data.instances_total} instances) and reflects preliminary experimental verification.</p>
            <p>3. Provider: <span className="font-mono text-text">{provider}</span> produced these metrics under test-run conditions.</p>
          </div>
        </div>
      </main>
    </div>
  );
}
