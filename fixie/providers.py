from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from itertools import count

from .models import CandidatePatch, Issue, TestResult


class Sandbox(ABC):
    @property
    @abstractmethod
    def id(self) -> str: ...

    @abstractmethod
    def fork(self, label: str) -> "Sandbox": ...

    @abstractmethod
    def apply(self, patch: CandidatePatch) -> None: ...

    @abstractmethod
    def run_reproduction(self, issue: Issue) -> TestResult: ...

    @abstractmethod
    def run_verification(self) -> TestResult: ...


class SandboxProvider(ABC):
    @abstractmethod
    def create(self, issue: Issue) -> Sandbox: ...


class PullRequestProvider(ABC):
    @abstractmethod
    def draft(self, issue: Issue, patch: CandidatePatch, evidence: dict) -> dict: ...


@dataclass
class FakeSandbox(Sandbox):
    sandbox_id: str
    applied_patch: CandidatePatch | None = None

    @property
    def id(self) -> str:
        return self.sandbox_id

    def fork(self, label: str) -> "FakeSandbox":
        return FakeSandbox(f"{self.id}:{label}")

    def apply(self, patch: CandidatePatch) -> None:
        self.applied_patch = patch

    def run_reproduction(self, issue: Issue) -> TestResult:
        return TestResult(False, 1, 1, 12, f"Reproduced issue #{issue.number}: {issue.title}")

    def run_verification(self) -> TestResult:
        if self.applied_patch is None:
            return TestResult(False, 1, 1, 1, "No candidate patch applied")
        # Deliberately deterministic fake semantics for local demos and tests.
        fails = 0 if "FIXIE_PASS" in self.applied_patch.diff else 1
        return TestResult(fails == 0, 3, fails, 18, "fake test suite completed")


class FakeSandboxProvider(SandboxProvider):
    def __init__(self) -> None:
        self._ids = count(1)

    def create(self, issue: Issue) -> FakeSandbox:
        return FakeSandbox(f"fake-{next(self._ids)}")


class FakePullRequestProvider(PullRequestProvider):
    def draft(self, issue: Issue, patch: CandidatePatch, evidence: dict) -> dict:
        return {
            "mode": "fake",
            "status": "draft",
            "repository": issue.repository,
            "title": f"Fix #{issue.number}: {issue.title}",
            "body": patch.rationale,
            "diff": patch.diff,
            "evidence": evidence,
        }


class ContreeSandbox(Sandbox):
    """Production adapter. Actual SDK calls are intentionally TODO(VERIFY)."""

    def __init__(self, remote_id: str) -> None:
        self._remote_id = remote_id

    @property
    def id(self) -> str:
        return self._remote_id

    def _client(self):
        # Lazy import keeps fake-only local development working without the SDK.
        import contree_sdk  # type: ignore[import-not-found]
        return contree_sdk

    def fork(self, label: str) -> "ContreeSandbox":
        self._client()
        raise NotImplementedError("TODO(VERIFY): map Contree sandbox fork API")

    def apply(self, patch: CandidatePatch) -> None:
        self._client()
        raise NotImplementedError("TODO(VERIFY): map Contree patch application API")

    def run_reproduction(self, issue: Issue) -> TestResult:
        self._client()
        raise NotImplementedError("TODO(VERIFY): map Contree command execution API")

    def run_verification(self) -> TestResult:
        self._client()
        raise NotImplementedError("TODO(VERIFY): map Contree command execution API")
