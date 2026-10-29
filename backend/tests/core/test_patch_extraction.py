"""Tests for B8 reliable patch extraction, integrity rules, and legacy diff normalisation."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.agent.loop import run_agent_loop
from app.agent.runner import validate_diff
from app.agent.steps.branch import normalise_diff_headers, run_branch_round
from app.llm import ChatResult, FakeChatClient
from app.sandbox import LocalSandbox


@pytest.mark.asyncio
async def test_fenced_json_reply_is_applied(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FIXIE_ALLOW_LOCAL", "1")
    sandbox = LocalSandbox.open("fixture:parse_duration")

    class FencedClient:
        async def chat(self, role: str, messages: str, **kwargs):
            payload = {
                "edits": [
                    {
                        "path": "parse_duration.py",
                        "old": '    raise ValueError("unsupported duration unit")',
                        "new": '    if unit == "s":\n        return int(amount)\n    raise ValueError("unsupported duration unit")',
                    }
                ],
                "summary": "Support seconds",
            }
            return ChatResult(
                text=f"```json\n{json.dumps(payload)}\n```",
                model="fake",
                tier="super",
            )

    events: list[tuple[str, dict]] = []

    async def emit(t: str, d: dict):
        events.append((t, d))

    try:
        res = await run_branch_round(
            base_sandbox=sandbox,
            strategies=["minimal"],
            client=FencedClient(),
            test_command="python -m pytest -q",
            issue_text="parse seconds",
            root_cause="no seconds",
            context="context",
            emit=emit,
        )
        assert res["winner"] is not None
        winner = res["winner"]
        assert winner["tests_passed"] is True
        # Verify generated diff passes validate_diff
        validated = validate_diff(winner["diff"])
        assert "--- a/parse_duration.py" in validated
        assert "+++ b/parse_duration.py" in validated
    finally:
        sandbox.close()


@pytest.mark.asyncio
async def test_edits_missing_old_snippet_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FIXIE_ALLOW_LOCAL", "1")
    sandbox = LocalSandbox.open("fixture:parse_duration")

    class MissingOldClient:
        async def chat(self, role: str, messages: str, **kwargs):
            return ChatResult(
                text=json.dumps({
                    "edits": [{"path": "parse_duration.py", "old": "def not_found():", "new": "def fixed():"}],
                    "summary": "missing snippet",
                }),
                model="fake",
                tier="super",
            )

    events: list[tuple[str, dict]] = []

    async def emit(t: str, d: dict):
        events.append((t, d))

    try:
        res = await run_branch_round(
            base_sandbox=sandbox,
            strategies=["minimal"],
            client=MissingOldClient(),
            test_command="python -m pytest -q",
            issue_text="test",
            root_cause="test",
            context="context",
            emit=emit,
        )
        assert res["winner"] is None
        stderr_chunks = [d for t, d in events if t == "terminal.chunk" and d.get("stream") == "stderr"]
        assert len(stderr_chunks) == 1
        assert "snippet 'old' not found in 'parse_duration.py'" in stderr_chunks[0]["text"]
    finally:
        sandbox.close()


@pytest.mark.asyncio
async def test_edits_ambiguous_old_snippet_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FIXIE_ALLOW_LOCAL", "1")
    sandbox = LocalSandbox.open("fixture:parse_duration")

    class AmbiguousOldClient:
        async def chat(self, role: str, messages: str, **kwargs):
            return ChatResult(
                text=json.dumps({
                    "edits": [{"path": "parse_duration.py", "old": '    if unit == "', "new": '    if unit == "x"'}],
                    "summary": "ambiguous snippet",
                }),
                model="fake",
                tier="super",
            )

    events: list[tuple[str, dict]] = []

    async def emit(t: str, d: dict):
        events.append((t, d))

    try:
        res = await run_branch_round(
            base_sandbox=sandbox,
            strategies=["minimal"],
            client=AmbiguousOldClient(),
            test_command="python -m pytest -q",
            issue_text="test",
            root_cause="test",
            context="context",
            emit=emit,
        )
        assert res["winner"] is None
        stderr_chunks = [d for t, d in events if t == "terminal.chunk" and d.get("stream") == "stderr"]
        assert len(stderr_chunks) == 1
        assert "appears 2 times (must be unique)" in stderr_chunks[0]["text"]
    finally:
        sandbox.close()


@pytest.mark.asyncio
async def test_edit_to_test_file_rejected_integrity_rule(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FIXIE_ALLOW_LOCAL", "1")
    sandbox = LocalSandbox.open("fixture:parse_duration")

    class TestTamperingClient:
        async def chat(self, role: str, messages: str, **kwargs):
            return ChatResult(
                text=json.dumps({
                    "edits": [{"path": "tests/test_parse_duration.py", "old": "assert False", "new": "assert True"}],
                    "summary": "modify tests",
                }),
                model="fake",
                tier="super",
            )

    events: list[tuple[str, dict]] = []

    async def emit(t: str, d: dict):
        events.append((t, d))

    try:
        res = await run_branch_round(
            base_sandbox=sandbox,
            strategies=["minimal"],
            client=TestTamperingClient(),
            test_command="python -m pytest -q",
            issue_text="test",
            root_cause="test",
            context="context",
            emit=emit,
        )
        assert res["winner"] is None
        stderr_chunks = [d for t, d in events if t == "terminal.chunk" and d.get("stream") == "stderr"]
        assert len(stderr_chunks) == 1
        assert "integrity rule: modifying test file" in stderr_chunks[0]["text"]
    finally:
        sandbox.close()


@pytest.mark.asyncio
async def test_legacy_diff_without_prefixes_normalised_and_applies(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FIXIE_ALLOW_LOCAL", "1")
    sandbox = LocalSandbox.open("fixture:parse_duration")

    legacy_raw = (
        "--- parse_duration.py\n"
        "+++ parse_duration.py\n"
        "@@ -3,5 +3,7 @@\n"
        "     if unit == \"m\":\n"
        "         return int(amount) * 60\n"
        "     if unit == \"h\":\n"
        "         return int(amount) * 3600\n"
        "+    if unit == \"s\":\n"
        "+        return int(amount)\n"
        "     raise ValueError(\"unsupported duration unit\")\n"
    )

    class LegacyClient:
        async def chat(self, role: str, messages: str, **kwargs):
            return ChatResult(
                text=json.dumps({"diff": legacy_raw, "summary": "legacy diff"}),
                model="fake",
                tier="super",
            )

    events: list[tuple[str, dict]] = []

    async def emit(t: str, d: dict):
        events.append((t, d))

    try:
        res = await run_branch_round(
            base_sandbox=sandbox,
            strategies=["minimal"],
            client=LegacyClient(),
            test_command="python -m pytest -q",
            issue_text="test",
            root_cause="test",
            context="context",
            emit=emit,
        )
        assert res["winner"] is not None
        winner = res["winner"]
        assert winner["tests_passed"] is True
        assert winner["diff"].startswith("--- a/parse_duration.py")
        assert "\n+++ b/parse_duration.py" in winner["diff"]
    finally:
        sandbox.close()


@pytest.mark.asyncio
async def test_full_fake_run_reaches_branch_winner(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FIXIE_ALLOW_LOCAL", "1")
    events: list[dict] = []

    async def emit(event_type: str, data: dict):
        events.append({"type": event_type, "data": data})

    await run_agent_loop("fixture:parse_duration", emit, {"client": FakeChatClient("fake")})
    assert any(e["type"] == "branch.winner" for e in events)
    assert events[-1]["type"] == "run.finished"
    assert events[-1]["data"]["status"] == "success"
