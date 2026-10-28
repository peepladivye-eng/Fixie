from __future__ import annotations

import argparse
import json
from pathlib import Path

from .models import CandidatePatch, Issue
from .orchestrator import FixieOrchestrator
from .providers import FakePullRequestProvider, FakeSandboxProvider


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Fixie using zero-cost fake providers.")
    parser.add_argument("--issue", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    issue = Issue.from_dict(json.loads(args.issue.read_text(encoding="utf-8")))
    candidates = [
        CandidatePatch("minimal", "# FIXIE_PASS\n# minimal candidate\n", "Apply the smallest safe parser fix."),
        CandidatePatch("alternative", "# candidate under evaluation\n", "Alternative parser fix for comparison."),
    ]
    report = FixieOrchestrator(FakeSandboxProvider(), FakePullRequestProvider()).run(issue, candidates)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "evidence.json").write_text(json.dumps(report.as_dict(), indent=2), encoding="utf-8")
    (args.output / "winner.diff").write_text(report.winner.candidate.diff, encoding="utf-8")
    (args.output / "pull-request.json").write_text(json.dumps(report.pull_request, indent=2), encoding="utf-8")
    print(f"Winner: {report.winner.candidate.name} ({report.winner.score})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
