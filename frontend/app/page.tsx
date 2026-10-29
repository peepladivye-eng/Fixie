import type { Metadata } from "next";
import HomeContent from "@/components/home/HomeContent";

export const metadata: Metadata = {
  title: "Fixie — Autonomous Bug Reproduction & Patch Engine",
  description:
    "Fixie reproduces GitHub bugs in an isolated sandbox, forks speculative patches across parallel branches, runs tests deterministically, and ships the winning verified fix.",
  openGraph: {
    title: "Fixie — Autonomous Bug Reproduction & Patch Engine",
    description:
      "Give Fixie a GitHub issue URL. It reproduces the bug, branches speculative patches in parallel, tests them, and delivers the winning diff.",
    type: "website",
  },
};

export default function HomePage() {
  return <HomeContent />;
}
