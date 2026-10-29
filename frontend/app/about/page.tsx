import type { Metadata } from "next";
import Link from "next/link";
import { ArrowLeft, Info } from "lucide-react";
import AboutTable from "@/components/about/AboutTable";
import ArchDiagram from "@/components/about/ArchDiagram";

export const metadata: Metadata = {
  title: "About — Fixie",
  description:
    "How Fixie works: Nebius Token Factory for LLM inference, Token Factory Sandboxes for VM isolation and speculative branching, and deterministic scoring — never a model call.",
  openGraph: {
    title: "About Fixie",
    description:
      "Architecture, provider stack, and limitations of Fixie — autonomous bug reproduction and speculative patch engine built on Nebius + NVIDIA.",
    type: "website",
  },
};

const limitations = [
  "Python and pytest repositories only (the current sandbox image ships Python 3.12 + pytest).",
  "Token Factory Sandboxes is in Beta; behaviour may change without notice.",
  "The public demo replays real saved runs — it does not spin up new sandboxes.",
  "Live runs are not enabled on the public site (NEXT_PUBLIC_API_URL is unset).",
];

export default function AboutPage() {
  return (
    <div
      className="min-h-screen flex flex-col"
      style={{ background: "var(--background)", color: "var(--text)" }}
    >
      {/* Nav */}
      <header
        className="flex items-center justify-between px-6 py-4"
        style={{ borderBottom: "1px solid var(--border)" }}
      >
        <Link
          href="/"
          className="inline-flex items-center gap-2 text-xs font-mono outline-none focus-visible:ring-2 focus-visible:ring-[var(--ring)]"
          style={{ color: "var(--text-muted)" }}
        >
          <ArrowLeft size={14} />
          Home
        </Link>
        <span className="text-xs font-mono font-bold" style={{ color: "var(--accent)" }}>
          Fixie / About
        </span>
      </header>

      <main className="flex-1 max-w-4xl mx-auto w-full px-4 sm:px-6 py-10 flex flex-col gap-10">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">About Fixie</h1>
          <p className="mt-2 text-sm leading-relaxed" style={{ color: "var(--text-muted)" }}>
            Fixie is an autonomous bug-reproduction and speculative patch engine built for the{" "}
            <span className="font-mono">Nebius × NVIDIA Global AI Hackathon, Track 1</span>.
          </p>
        </div>

        {/* Provider / model table */}
        <section aria-labelledby="provider-heading">
          <h2
            id="provider-heading"
            className="text-lg font-semibold mb-4"
          >
            How Fixie uses Nebius + NVIDIA
          </h2>
          <AboutTable />
        </section>

        {/* Architecture */}
        <section aria-labelledby="arch-heading">
          <h2 id="arch-heading" className="text-lg font-semibold mb-4">
            Architecture
          </h2>
          <ArchDiagram />
        </section>

        {/* Limitations */}
        <section aria-labelledby="limits-heading">
          <h2 id="limits-heading" className="text-lg font-semibold mb-4">
            Limitations
          </h2>
          <div
            className="p-5 rounded-xl flex items-start gap-3.5"
            style={{ background: "var(--surface)", border: "1px solid var(--border)" }}
          >
            <Info size={18} className="mt-0.5 flex-shrink-0" style={{ color: "var(--badge-blue)" }} />
            <ul className="space-y-2 text-sm leading-relaxed" style={{ color: "var(--text-muted)" }}>
              {limitations.map((l) => (
                <li key={l} className="flex items-start gap-2">
                  <span className="mt-1.5 w-1.5 h-1.5 rounded-full flex-shrink-0" style={{ background: "var(--text-muted)" }} />
                  {l}
                </li>
              ))}
            </ul>
          </div>
        </section>
      </main>
    </div>
  );
}
