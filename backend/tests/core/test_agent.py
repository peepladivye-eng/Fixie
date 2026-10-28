"""Tests for Stage 2 agent components: context, output, scoring, branching, early exits, eval grading."""
from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path

import jsonschema
import pytest

from app.agent.context import build_context, extract_relevant_ast_snippets
from app.agent.loop import run_agent_loop
from app.agent.output import parse_pytest_failures, truncate_output
from app.agent.scoring import calculate_patch_score
from app.agent.steps.branch import run_branch_round, validate_diff
from app.agent.steps.reproduce import ReproductionError, run_reproduce
from eval.run_eval import grade_with_hidden_tests
from app.llm import FakeChatClient
from app.sandbox import LocalSandbox
from backend.tools.validate_events import load_schema


def test_context_selection_includes_buggy_function() -> None:
    fixtures_dir = Path(__file__).resolve().parents[1] / "core" / "fixtures" / "parse_duration"
    repo_dir = fixtures_dir / "repo"
    issue_text = "parse_duration('5s') should return 5 seconds"
    context = build_context(repo_dir, issue_text, "test_parse_duration failed", max_tokens=1000)
    assert "parse_duration" in context
    assert "def parse_duration" in context


def test_truncation_limits() -> None:
    text = "\n".join(f"line {i}" for i in range(200))
    truncated = truncate_output(text, max_head_lines=40, max_tail_lines=60, max_chars=4000)
    lines = truncated.splitlines()
    assert len(lines) <= 102
    assert "truncated" in truncated
    assert len(truncated) <= 4000


def test_compact_failure_summary() -> None:
    pytest_output = (
        "FAILED tests/test_parse_duration.py::test_seconds - AssertionError: assert 0 == 5\n"
        "tests/test_parse_duration.py:8: AssertionError: assert 0 == 5\n"
    )
    summary = parse_pytest_failures(pytest_output)
    assert summary["test_name"] == "tests/test_parse_duration.py::test_seconds"
    assert "AssertionError" in summary["assertion"]
    assert "tests/test_parse_duration.py:8" in summary["location"]


@pytest.mark.asyncio
async def test_not_reproduced_early_exit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FIXIE_ALLOW_LOCAL", "1")
    sandbox = LocalSandbox.open("fixture:parse_duration")
    try:
        # Running command that succeeds
        with pytest.raises(ReproductionError) as exc_info:
            await run_reproduce(sandbox, "python -c \"exit(0)\"")
        assert exc_info.value.code == "NOT_REPRODUCED"
    finally:
        sandbox.close()


@pytest.mark.asyncio
async def test_parallel_candidates_timing(monkeypatch: pytest.MonkeyPatch) -> None:
    """Three candidates with a 0.2s fake delay each finish well under 0.6s total."""
    monkeypatch.setenv("FIXIE_ALLOW_LOCAL", "1")
    sandbox = LocalSandbox.open("fixture:parse_duration")

    class DelayFakeClient:
        async def chat(self, role: str, messages: str, **kwargs):
            await asyncio.sleep(0.2)
            valid_diff = (
                "--- a/parse_duration.py\n"
                "+++ b/parse_duration.py\n"
                "@@ -1,3 +1,3 @@\n"
                "-# comment\n"
                "+# comment patched\n"
            )
            from app.llm import ChatResult
            return ChatResult(text=json.dumps({"diff": valid_diff}), model="fake", tier="super")

    events = []
    async def emit(t: str, d: dict):
        events.append((t, d))

    try:
        t0 = time.monotonic()
        await run_branch_round(
            base_sandbox=sandbox,
            strategies=["strat1", "strat2", "strat3"],
            client=DelayFakeClient(),
            test_command="python -c \"exit(0)\"",
            issue_text="test issue",
            root_cause="test root cause",
            context="code context",
            emit=emit,
        )
        elapsed = time.monotonic() - t0
        assert elapsed < 0.50, f"Expected well under 0.6s, took {elapsed}s"
    finally:
        sandbox.close()


@pytest.mark.asyncio
async def test_loser_cancellation_emits_branch_cancelled(monkeypatch: pytest.MonkeyPatch) -> None:
    """When a candidate passes, concurrent pending branches are cancelled."""
    monkeypatch.setenv("FIXIE_ALLOW_LOCAL", "1")
    sandbox = LocalSandbox.open("fixture:parse_duration")

    class MixedFakeClient:
        async def chat(self, role: str, messages: str, **kwargs):
            if "fast" in messages:
                # Fast winner
                await asyncio.sleep(0.01)
            else:
                # Slow loser
                await asyncio.sleep(0.3)
            valid_diff = (
                "--- a/parse_duration.py\n"
                "+++ b/parse_duration.py\n"
                "@@ -1,3 +1,3 @@\n"
                "-# comment\n"
                "+# comment patched\n"
            )
            from app.llm import ChatResult
            return ChatResult(text=json.dumps({"diff": valid_diff}), model="fake", tier="super")

    events = []
    async def emit(t: str, d: dict):
        events.append((t, d))

    try:
        await run_branch_round(
            base_sandbox=sandbox,
            strategies=["fast-winner", "slow-loser"],
            client=MixedFakeClient(),
            test_command="python -c \"exit(0)\"",
            issue_text="fast vs slow issue",
            root_cause="root cause",
            context="context",
            emit=emit,
        )
        cancelled_events = [d for t, d in events if t == "branch.cancelled"]
        assert len(cancelled_events) >= 1
    finally:
        sandbox.close()


def test_scoring_order() -> None:
    # 1. Failing test gives score 0.0
    s_fail, key_fail = calculate_patch_score(tests_passed=False, diff_lines=2, sandbox_seconds=0.1)
    assert s_fail == 0.0

    # 2. Passing test gives > 0.0
    s_pass1, key_pass1 = calculate_patch_score(tests_passed=True, diff_lines=2, sandbox_seconds=0.1)
    assert s_pass1 > 0.8

    # 3. Smaller diff ranks higher
    s_pass_small_diff, key_small = calculate_patch_score(tests_passed=True, diff_lines=3, sandbox_seconds=1.0)
    s_pass_large_diff, key_large = calculate_patch_score(tests_passed=True, diff_lines=40, sandbox_seconds=1.0)
    assert key_small > key_large
    assert s_pass_small_diff > s_pass_large_diff


@pytest.mark.asyncio
async def test_adaptive_k_and_max_rounds(monkeypatch: pytest.MonkeyPatch) -> None:
    """Round 1 has K=2. If none passes, round 2 runs with K=3 (total 2 rounds max)."""
    monkeypatch.setenv("FIXIE_ALLOW_LOCAL", "1")

    round_counts = []
    class FailingRound1Client:
        call_count = 0
        async def chat(self, role: str, messages: str, **kwargs):
            FailingRound1Client.call_count += 1
            if FailingRound1Client.call_count <= 2:
                # Round 1 fails
                diff = "--- a/parse_duration.py\n+++ b/parse_duration.py\n@@ -1,1 +1,1 @@\n-# bad\n+# still bad\n"
            else:
                # Round 2 passes
                diff = "--- a/parse_duration.py\n+++ b/parse_duration.py\n@@ -3,5 +3,7 @@\n     if unit == \"m\":\n         return int(amount) * 60\n     if unit == \"h\":\n         return int(amount) * 3600\n+    if unit == \"s\":\n+        return int(amount)\n     raise ValueError(\"unsupported duration unit\")\n"
            from app.llm import ChatResult
            return ChatResult(text=json.dumps({"diff": diff}), model="fake", tier="super")

    events = []
    async def emit(t: str, d: dict):
        events.append((t, d))

    await run_agent_loop("fixture:parse_duration", emit, {"client": FailingRound1Client(), "max_rounds": 2})

    forked_events = [d for t, d in events if t == "branch.forked"]
    # Round 1: K=2, Round 2: K=3
    assert len(forked_events) == 2
    assert len(forked_events[0]["branches"]) == 2
    assert len(forked_events[1]["branches"]) == 3
    assert any(t == "branch.winner" for t, _ in events)


@pytest.mark.asyncio
async def test_run_budget_abort_emits_error_and_finished(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FIXIE_DB", str(tmp_path / "fixie.db"))
    monkeypatch.setenv("FIXIE_ALLOW_LOCAL", "1")
    monkeypatch.setenv("RUN_BUDGET_USD", "0.000001")  # tiny budget to trigger abort

    events = []
    async def emit(t: str, d: dict):
        events.append((t, d))

    await run_agent_loop("fixture:parse_duration", emit, {})

    types = [t for t, _ in events]
    assert "run.error" in types
    assert types[-1] == "run.finished"
    finished_data = next(d for t, d in events if t == "run.finished")
    assert finished_data["status"] == "failed"


@pytest.mark.asyncio
async def test_full_fake_run_events_validate_against_schema(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FIXIE_ALLOW_LOCAL", "1")

    events = []
    seq = 0
    schema = load_schema()
    validator = jsonschema.Draft7Validator(schema)

    async def emit(event_type: str, data: dict):
        nonlocal seq
        envelope = {
            "run_id": "test_fake_run",
            "seq": seq,
            "ts": "2026-10-28T10:00:00.000Z",
            "type": event_type,
            "data": data,
        }
        seq += 1
        errors = list(validator.iter_errors(envelope))
        assert len(errors) == 0, f"Schema error on {event_type}: {[e.message for e in errors]}"
        events.append(envelope)

    await run_agent_loop("fixture:parse_duration", emit, {})
    assert len(events) >= 8
    assert events[0]["type"] == "run.started"
    assert events[-1]["type"] == "run.finished"
    assert events[-1]["data"]["status"] == "success"


def test_eval_grades_with_hidden_tests() -> None:
    # 1. Invalid patch fails grading
    bad_diff = "--- a/parse_duration.py\n+++ b/parse_duration.py\n@@ -1,1 +1,1 @@\n-# c\n+# c\n"
    assert grade_with_hidden_tests("parse_duration", bad_diff) is False

    # 2. Correct patch passes hidden tests
    good_diff = (
        "--- a/parse_duration.py\n"
        "+++ b/parse_duration.py\n"
        "@@ -3,5 +3,7 @@\n"
        "     if unit == \"m\":\n"
        "         return int(amount) * 60\n"
        "     if unit == \"h\":\n"
        "         return int(amount) * 3600\n"
        "+    if unit == \"s\":\n"
        "+        return int(amount)\n"
        "     raise ValueError(\"unsupported duration unit\")\n"
    )
    assert grade_with_hidden_tests("parse_duration", good_diff) is True
