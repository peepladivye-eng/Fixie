"""Tests for candidate failure visibility (garbage text and malformed diffs)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.agent.steps.branch import run_branch_round
from app.llm import ChatResult
from app.sandbox import LocalSandbox


@pytest.mark.asyncio
async def test_candidate_failure_visible_garbage_text(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FIXIE_ALLOW_LOCAL", "1")
    sandbox = LocalSandbox.open("fixture:parse_duration")

    class GarbageClient:
        async def chat(self, role: str, messages: str, **kwargs):
            return ChatResult(
                text="Totally unparseable garbage reply without diff AIzaSyD-1234567890abcdef123456789012345",
                model="fake",
                tier="super",
            )

    events: list[tuple[str, dict]] = []

    async def emit(t: str, d: dict):
        events.append((t, d))

    try:
        res = await run_branch_round(
            base_sandbox=sandbox,
            strategies=["minimal", "defensive"],
            client=GarbageClient(),
            test_command="python -c \"exit(0)\"",
            issue_text="garbage test",
            root_cause="root cause",
            context="context",
            emit=emit,
        )
        assert res["winner"] is None

        # Assert each candidate produces a branch.result
        branch_results = [d for t, d in events if t == "branch.result"]
        assert len(branch_results) == 2
        for br in branch_results:
            assert br["tests_passed"] is False
            assert br["diff_lines"] == 0

        # Assert each candidate produces a terminal.chunk explaining why
        stderr_chunks = [d for t, d in events if t == "terminal.chunk" and d.get("stream") == "stderr"]
        assert len(stderr_chunks) == 2
        for sc in stderr_chunks:
            assert "invalid diff" in sc["text"]
            assert "Totally unparseable garbage reply" in sc["text"]
            # Assert keys are stripped
            assert "AIzaSyD" not in sc["text"]
            assert "[REDACTED]" in sc["text"]
    finally:
        sandbox.close()


@pytest.mark.asyncio
async def test_candidate_failure_visible_malformed_diff(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FIXIE_ALLOW_LOCAL", "1")
    sandbox = LocalSandbox.open("fixture:parse_duration")

    class MalformedDiffClient:
        async def chat(self, role: str, messages: str, **kwargs):
            malformed = json.dumps({"diff": "--- not_a_repo/file.py\n+++ /etc/passwd\n@@ invalid @@"})
            return ChatResult(text=malformed, model="fake", tier="super")

    events: list[tuple[str, dict]] = []

    async def emit(t: str, d: dict):
        events.append((t, d))

    try:
        res = await run_branch_round(
            base_sandbox=sandbox,
            strategies=["minimal", "defensive"],
            client=MalformedDiffClient(),
            test_command="python -c \"exit(0)\"",
            issue_text="malformed diff test",
            root_cause="root cause",
            context="context",
            emit=emit,
        )
        assert res["winner"] is None

        # Assert each candidate produces a branch.result
        branch_results = [d for t, d in events if t == "branch.result"]
        assert len(branch_results) == 2
        for br in branch_results:
            assert br["tests_passed"] is False

        # Assert each candidate produces a terminal.chunk explaining why
        stderr_chunks = [d for t, d in events if t == "terminal.chunk" and d.get("stream") == "stderr"]
        assert len(stderr_chunks) == 2
        for sc in stderr_chunks:
            assert "invalid diff" in sc["text"]
            assert "patch must be a repository-relative unified diff" in sc["text"]
    finally:
        sandbox.close()
