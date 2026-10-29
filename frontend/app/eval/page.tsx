import type { Metadata } from "next";
import EvalContent from "@/components/eval/EvalContent";

export const metadata: Metadata = {
  title: "Benchmark Results — Fixie",
  description:
    "Fixie evaluation benchmark: resolve rate, cost-per-fix, and per-instance comparison of single-shot baseline vs speculative branching.",
  openGraph: {
    title: "Fixie Benchmark Results",
    description:
      "Compare Fixie's single-shot baseline vs speculative branching on resolve rate and cost-per-fix across benchmark instances.",
    type: "website",
  },
};

export default function EvalPage() {
  return <EvalContent />;
}
