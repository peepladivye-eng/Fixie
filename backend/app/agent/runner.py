from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any, Awaitable, Callable

from pydantic import BaseModel

from app.llm import ChatClient, configured_client
from app.sandbox import LocalSandbox
from .json_output import validated_response

Emit = Callable[[str, dict[str, Any]], Awaitable[None]]
PROMPTS = Path(__file__).with_name("prompts")


class Triage(BaseModel):
    summary: str
    risk: str


class Reproduction(BaseModel):
    command: str
    expected: str


class Diagnosis(BaseModel):
    root_cause: str


class Patch(BaseModel):
    diff: str
    summary: str


def validate_diff(diff: str) -> str:
    if not diff.startswith("--- a/") or "\n+++ b/" not in diff or "\n@@" not in diff:
        raise ValueError("patch must be a repository-relative unified diff")
    for line in diff.splitlines():
        if line.startswith(("--- ", "+++ ")) and (".." in line or line.startswith(("--- /", "+++ /"))):
            raise ValueError("patch contains an unsafe path")
    return diff


def _prompt(role: str, issue: str) -> str:
    return (PROMPTS / f"{role}.txt").read_text(encoding="utf-8").format(issue=issue)


def _ask(client: ChatClient, role: str, issue: str, schema: type[BaseModel]) -> BaseModel:
    return validated_response(schema, lambda prompt: client.chat(role, prompt).text, _prompt(role, issue))


async def run_agent(source: str, emit: Emit, options: dict | None = None) -> None:
    options = options or {}
    if source.startswith("https://github.com/"):
        raise RuntimeError("GitHub sources require the verified GitHub provider and are disabled for local runs")
    if source.startswith("instance:"):
        raise RuntimeError("instance sources are TODO(VERIFY)")
    sandbox = LocalSandbox.open(source)
    try:
        fixture_root = Path(__file__).resolve().parents[2] / "tests" / "core" / "fixtures" / source.removeprefix("fixture:")
        if not fixture_root.exists():
            roots = [Path(__import__("os").getenv("FIXIE_FIXTURES_DIR", ""))] if __import__("os").getenv("FIXIE_FIXTURES_DIR") else [Path(__file__).resolve().parents[2] / "eval" / "fixtures", fixture_root]
            fixture_root = next(root / source.removeprefix("fixture:") for root in roots if (root / source.removeprefix("fixture:") / "issue.md").is_file())
        issue = (fixture_root / "issue.md").read_text(encoding="utf-8")
        meta = json.loads((fixture_root / "meta.json").read_text(encoding="utf-8"))
        client = options.get("client") or configured_client()
        await emit("run.started", {"issue_title": meta["title"], "repo": source, "mode": "live"})
        outputs: dict[str, BaseModel] = {}
        for role, schema in (("triage", Triage), ("reproduce", Reproduction), ("diagnose", Diagnosis)):
            await emit("step.started", {"step": role, "model_tier": client.model if hasattr(client, "model") else "configured"})
            outputs[role] = _ask(client, role, issue, schema)
            await emit("llm.usage", {"model": client.model if hasattr(client, "model") else "configured", "input_tokens": 0, "output_tokens": 0, "cost_usd": 0.0})
            await emit("step.finished", {"step": role, "duration_ms": 0, "ok": True})
        baseline = sandbox.run(meta["test_cmd"])
        await emit("terminal.chunk", {"stream": "stdout", "text": baseline.stdout + baseline.stderr, "branch_id": "baseline"})
        branches = sandbox.fork(max(1, int(options.get("k_branches", 1))))
        await emit("branch.forked", {"branches": [{"id": f"candidate-{i + 1}", "strategy": "llm-patch"} for i in range(len(branches))]})
        candidates = []
        for index, branch in enumerate(branches):
            patch = _ask(client, "patch", issue, Patch)
            diff = validate_diff(patch.diff)
            applied = branch.apply_diff(diff)
            tested = branch.run(meta["test_cmd"]) if applied.returncode == 0 else applied
            score = 1.0 if tested.returncode == 0 else 0.0
            candidates.append((score, index, patch, tested))
            await emit("branch.result", {"branch_id": f"candidate-{index + 1}", "tests_passed": tested.returncode == 0, "diff_lines": len(diff.splitlines()), "sandbox_seconds": 0.0, "score": score})
        winner = max(candidates, key=lambda item: (item[0], -item[1]))
        if winner[0] == 0:
            raise RuntimeError("no candidate passed visible tests")
        await emit("branch.winner", {"branch_id": f"candidate-{winner[1] + 1}"})
        await emit("deliver.ready", {"diff": winner[2].diff, "root_cause": outputs["diagnose"].root_cause, "pr_url": None})
        await emit("run.finished", {"status": "success", "total_cost_usd": 0.0, "total_seconds": 0.0})
    finally:
        sandbox.close()
