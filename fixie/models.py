from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class Issue:
    number: int
    title: str
    body: str
    repository: str

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "Issue":
        return cls(
            number=int(value["number"]),
            title=str(value["title"]),
            body=str(value.get("body", "")),
            repository=str(value["repository"]),
        )


@dataclass(frozen=True)
class CandidatePatch:
    name: str
    diff: str
    rationale: str


@dataclass(frozen=True)
class TestResult:
    passed: bool
    total: int
    failed: int
    duration_ms: int
    output: str

    @property
    def pass_rate(self) -> float:
        return (self.total - self.failed) / self.total if self.total else 0.0


@dataclass(frozen=True)
class Evaluation:
    candidate: CandidatePatch
    sandbox_id: str
    reproduction: TestResult
    verification: TestResult
    score: float


@dataclass(frozen=True)
class RunReport:
    issue: Issue
    source_sandbox_id: str
    evaluations: tuple[Evaluation, ...]
    winner: Evaluation
    pull_request: dict[str, Any]
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)
