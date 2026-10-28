"""Agent loop orchestration: triage, reproduce, diagnose, branching, and delivery."""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Awaitable, Callable

from app.agent.context import build_context
from app.agent.steps.branch import get_strategies_for_round, run_branch_round
from app.agent.steps.diagnose import run_diagnose
from app.agent.steps.reproduce import ReproductionError, run_reproduce
from app.agent.steps.triage import TriageError, run_triage
from app.llm import (
    BudgetExceeded,
    ChatClient,
    ChatResult,
    configured_client,
    tier_for_role,
)
from app.sandbox import LocalSandbox
from app.search import TavilySearch

Emit = Callable[[str, dict[str, Any]], Awaitable[None]]


class UsageTrackingClient:
    """Wraps ChatClient to record and emit llm.usage for every model interaction."""

    def __init__(self, inner: ChatClient, emit: Emit, run_id: str = "run_default"):
        self.inner = inner
        self.emit = emit
        self.run_id = run_id
        self.total_cost_usd = 0.0

    async def chat(
        self,
        role: str,
        messages: Any,
        tools: list[dict[str, Any]] | None = None,
        run_id: str | None = None,
    ) -> ChatResult:
        actual_run_id = run_id or self.run_id
        result = await self.inner.chat(role, messages, tools=tools, run_id=actual_run_id)
        cost = 0.0 if getattr(result, "cached", False) else float(getattr(result, "cost_usd", 0.0))
        self.total_cost_usd += cost
        await self.emit(
            "llm.usage",
            {
                "model": str(getattr(result, "model", "default-model")),
                "input_tokens": int(getattr(result, "input_tokens", 0)),
                "output_tokens": int(getattr(result, "output_tokens", 0)),
                "cost_usd": round(cost, 6),
                "cached": bool(getattr(result, "cached", False)),
            },
        )
        return result


def _resolve_fixture(source: str) -> tuple[str, dict[str, Any]]:
    fixture_name = source.removeprefix("fixture:")
    roots = [
        Path(__file__).resolve().parents[2] / "tests" / "core" / "fixtures" / fixture_name,
        Path(__file__).resolve().parents[2] / "eval" / "fixtures" / fixture_name,
    ]
    if os.getenv("FIXIE_FIXTURES_DIR"):
        roots.insert(0, Path(os.environ["FIXIE_FIXTURES_DIR"]) / fixture_name)

    fixture_dir = next((r for r in roots if (r / "issue.md").is_file()), None)
    if fixture_dir is None:
        raise FileNotFoundError(f"Fixture not found: {source}")

    issue = (fixture_dir / "issue.md").read_text(encoding="utf-8")
    meta = json.loads((fixture_dir / "meta.json").read_text(encoding="utf-8"))
    return issue, meta


async def run_agent_loop(
    source: str,
    emit: Emit,
    options: dict[str, Any] | None = None,
) -> None:
    """Single entry point for the Fixie agent loop."""
    import sys
    py_dir = str(Path(sys.executable).parent)
    if py_dir not in os.environ.get("PATH", ""):
        os.environ["PATH"] = f"{py_dir}{os.pathsep}{os.environ.get('PATH', '')}"

    options = options or {}
    max_rounds = int(options.get("max_rounds", 2))
    showcase = bool(options.get("showcase", False))
    run_id = str(options.get("run_id") or "run_live")
    raw_client = options.get("client") or configured_client()
    tracking_client = UsageTrackingClient(raw_client, emit, run_id=run_id)

    run_start = time.monotonic()
    sandbox: LocalSandbox | None = None
    finished_emitted = False

    try:
        if source.startswith("https://github.com/"):
            raise RuntimeError("GitHub sources require verified GitHub provider")
        if source.startswith("instance:"):
            raise RuntimeError("instance sources are TODO(VERIFY)")

        issue_text, meta = _resolve_fixture(source)
        test_command = meta.get("test_cmd", "python -m pytest -q")

        await emit(
            "run.started",
            {
                "issue_title": str(meta.get("title", source)),
                "repo": source,
                "mode": "live",
            },
        )

        sandbox = LocalSandbox.open(source)

        # 1. Triage
        t0 = time.monotonic()
        await emit("step.started", {"step": "triage", "model_tier": tier_for_role("triage")})
        try:
            await run_triage(sandbox.workdir, issue_text, tracking_client, emit)
            await emit("step.finished", {"step": "triage", "duration_ms": max(0, int((time.monotonic() - t0) * 1000)), "ok": True})
        except TriageError as exc:
            await emit("step.finished", {"step": "triage", "duration_ms": max(0, int((time.monotonic() - t0) * 1000)), "ok": False})
            await emit("run.error", {"code": exc.code, "message": str(exc)})
            finished_emitted = True
            await emit("run.finished", {"status": "failed", "total_cost_usd": round(tracking_client.total_cost_usd, 6), "total_seconds": round(time.monotonic() - run_start, 4)})
            return

        # 2. Reproduce
        t0 = time.monotonic()
        await emit("step.started", {"step": "reproduce", "model_tier": tier_for_role("reproduce")})
        try:
            summary, checkpoint_b = await run_reproduce(sandbox, test_command, emit)
            await emit("step.finished", {"step": "reproduce", "duration_ms": max(0, int((time.monotonic() - t0) * 1000)), "ok": True})
        except ReproductionError as exc:
            await emit("step.finished", {"step": "reproduce", "duration_ms": max(0, int((time.monotonic() - t0) * 1000)), "ok": False})
            finished_emitted = True
            await emit("run.finished", {"status": "failed", "total_cost_usd": round(tracking_client.total_cost_usd, 6), "total_seconds": round(time.monotonic() - run_start, 4)})
            return

        failure_str = json.dumps(summary) if isinstance(summary, dict) else str(summary)

        # 3. Diagnose
        t0 = time.monotonic()
        await emit("step.started", {"step": "diagnose", "model_tier": tier_for_role("diagnose")})
        context_str = build_context(sandbox.workdir, issue_text, failure_str)
        if options.get("client") is None or hasattr(raw_client, "provider_name"):
            root_cause = await run_diagnose(issue_text, summary, context_str, tracking_client, emit, search_client=TavilySearch())
        else:
            root_cause = f"Diagnosed failure: {failure_str[:80]}"
        await emit("step.finished", {"step": "diagnose", "duration_ms": max(0, int((time.monotonic() - t0) * 1000)), "ok": True})

        # 4. Branching rounds (adaptive K)
        winner = None
        last_diff = ""

        for round_idx in range(1, max_rounds + 1):
            strategies = get_strategies_for_round(round_idx, showcase=showcase)
            t0 = time.monotonic()
            await emit("step.started", {"step": "branch", "model_tier": tier_for_role("branch")})

            round_res = await run_branch_round(
                base_sandbox=sandbox,
                strategies=strategies,
                client=tracking_client,
                test_command=test_command,
                issue_text=issue_text,
                root_cause=root_cause,
                context=context_str,
                emit=emit,
                failure_summary=failure_str if round_idx > 1 else "",
                previous_diff=last_diff if round_idx > 1 else "",
            )

            round_winner = round_res.get("winner")
            await emit(
                "step.finished",
                {
                    "step": "branch",
                    "duration_ms": max(0, int((time.monotonic() - t0) * 1000)),
                    "ok": round_winner is not None,
                },
            )

            if round_winner is not None:
                winner = round_winner
                break

            # Save failed candidate diff for retry prompt
            results = round_res.get("results", [])
            if results:
                last_diff = results[0].get("diff", "")

        # 5. Deliver
        if winner is not None:
            t0 = time.monotonic()
            await emit("step.started", {"step": "deliver", "model_tier": tier_for_role("deliver")})
            pr_url: str | None = None
            if os.getenv("GITHUB_TOKEN") and os.getenv("OPEN_PR", "").lower() in ("1", "true"):
                # TODO(VERIFY): create PR via GitHub client
                pr_url = "https://github.com/mock/repo/pull/1"

            await emit(
                "deliver.ready",
                {
                    "diff": winner.get("diff", ""),
                    "root_cause": root_cause,
                    "pr_url": pr_url,
                },
            )
            await emit(
                "step.finished",
                {
                    "step": "deliver",
                    "duration_ms": max(0, int((time.monotonic() - t0) * 1000)),
                    "ok": True,
                },
            )
            status = "success"
        else:
            status = "failed"

        finished_emitted = True
        await emit(
            "run.finished",
            {
                "status": status,
                "total_cost_usd": round(tracking_client.total_cost_usd, 6),
                "total_seconds": round(time.monotonic() - run_start, 4),
            },
        )

    except BudgetExceeded as exc:
        if not finished_emitted:
            await emit("run.error", {"code": exc.code, "message": str(exc)})
            finished_emitted = True
            await emit(
                "run.finished",
                {
                    "status": "failed",
                    "total_cost_usd": round(tracking_client.total_cost_usd, 6),
                    "total_seconds": round(time.monotonic() - run_start, 4),
                },
            )
    except Exception as exc:
        if not finished_emitted:
            await emit("run.error", {"code": "INTERNAL", "message": str(exc)})
            finished_emitted = True
            await emit(
                "run.finished",
                {
                    "status": "failed",
                    "total_cost_usd": round(tracking_client.total_cost_usd, 6),
                    "total_seconds": round(time.monotonic() - run_start, 4),
                },
            )
    finally:
        if sandbox is not None:
            sandbox.close()
