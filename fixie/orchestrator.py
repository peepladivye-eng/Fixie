from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from .models import CandidatePatch, Evaluation, Issue, RunReport
from .providers import PullRequestProvider, SandboxProvider


class FixieOrchestrator:
    def __init__(self, sandboxes: SandboxProvider, pull_requests: PullRequestProvider) -> None:
        self.sandboxes = sandboxes
        self.pull_requests = pull_requests

    @staticmethod
    def score(reproduction_failed: bool, verification) -> float:
        # A candidate must retain a reproduced baseline; passing checks dominates.
        return round((80.0 * verification.pass_rate) + (20.0 if reproduction_failed else 0.0) - verification.duration_ms / 1000, 3)

    def _evaluate(self, source, issue: Issue, candidate: CandidatePatch) -> Evaluation:
        sandbox = source.fork(candidate.name)
        reproduction = sandbox.run_reproduction(issue)
        sandbox.apply(candidate)
        verification = sandbox.run_verification()
        return Evaluation(candidate, sandbox.id, reproduction, verification, self.score(not reproduction.passed, verification))

    def run(self, issue: Issue, candidates: list[CandidatePatch]) -> RunReport:
        if not candidates:
            raise ValueError("At least one candidate patch is required")
        source = self.sandboxes.create(issue)
        with ThreadPoolExecutor(max_workers=len(candidates)) as pool:
            evaluations = tuple(pool.map(lambda item: self._evaluate(source, issue, item), candidates))
        winner = max(evaluations, key=lambda result: (result.score, result.candidate.name))
        evidence = {
            "winner": winner.candidate.name,
            "score": winner.score,
            "reproduction": winner.reproduction.__dict__,
            "verification": winner.verification.__dict__,
        }
        pr = self.pull_requests.draft(issue, winner.candidate, evidence)
        return RunReport(issue, source.id, evaluations, winner, pr, {"provider_mode": "fake"})
