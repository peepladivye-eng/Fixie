"""A zero-cost, deterministic stand-in for the agent runner."""
from __future__ import annotations

import asyncio
from typing import Any, Awaitable, Callable

Emit = Callable[[str, dict[str, Any]], Awaitable[None]]


async def run_agent(source: str, emit: Emit, options: dict | None = None) -> None:
    options = options or {}
    branches = max(1, int(options.get("k_branches", 3)))
    await emit("run.started", {"issue_title": "Fake issue: " + source, "repo": "fake/repository", "mode": "live"})
    for step in ("triage", "reproduce", "diagnose"):
        await emit("step.started", {"step": step, "model_tier": "lightning"})
        await asyncio.sleep(0.01)
        await emit("step.finished", {"step": step, "duration_ms": 10, "ok": True})
    await emit("llm.usage", {"model": "fake-lightning", "input_tokens": 120, "output_tokens": 40, "cost_usd": 0.0})
    await emit("step.started", {"step": "branch", "model_tier": "super"})
    strategies = ["guard-null", "fix-boundary", "minimal-regression"]
    branch_items = [{"id": f"candidate-{index + 1}", "strategy": strategies[index % len(strategies)]} for index in range(branches)]
    await emit("branch.forked", {"branches": branch_items})
    for index, branch in enumerate(branch_items):
        await emit("terminal.chunk", {"stream": "stdout", "text": "pytest: passed\n", "branch_id": branch["id"]})
        await emit("branch.result", {"branch_id": branch["id"], "tests_passed": True, "diff_lines": 3 + index, "sandbox_seconds": 0.01, "score": 1.0 - index / 10})
    await emit("step.finished", {"step": "branch", "duration_ms": 10 * branches, "ok": True})
    await emit("branch.winner", {"branch_id": branch_items[0]["id"]})
    await emit("step.started", {"step": "deliver", "model_tier": "none"})
    await emit("deliver.ready", {"diff": "--- a/example.py\n+++ b/example.py", "root_cause": "Synthetic regression", "pr_url": None})
    await emit("step.finished", {"step": "deliver", "duration_ms": 1, "ok": True})
    await emit("run.finished", {"status": "success", "total_cost_usd": 0.0, "total_seconds": 0.1})
