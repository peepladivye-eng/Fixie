import type { Metadata } from "next";
import RunView from "@/components/run/RunView";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ id: string }>;
}): Promise<Metadata> {
  const { id } = await params;
  return {
    title: `Run ${id} — Fixie`,
    description: `Replay of Fixie run ${id}: speculative patch generation, parallel branch selection, and deterministic test verification.`,
    openGraph: {
      title: `Run ${id} — Fixie`,
      description: `Watch how Fixie reproduces the bug, forks patches in parallel, tests them deterministically, and delivers the winning diff.`,
      type: "website",
    },
  };
}

export default async function RunPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return (
    <div
      className="flex flex-col h-dvh max-h-dvh w-full overflow-hidden"
      style={{ background: "var(--background)", color: "var(--text)" }}
    >
      <RunView runId={id} />
    </div>
  );
}
