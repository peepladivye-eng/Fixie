"""Tests for Stage 1 & 2 backend foundation: LLM async client, cache, cassette, guards, and sandbox."""
from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from app.llm import (
    AsyncOpenAICompatibleClient,
    BudgetExceeded,
    CassetteChatClient,
    ChatResult,
    FakeChatClient,
    InputTooLarge,
    PersistentGuardsAndCache,
)
from app.sandbox import LocalSandbox


@pytest.mark.asyncio
async def test_cache_hit_costs_zero(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FIXIE_DB", str(tmp_path / "fixie.db"))
    import httpx

    calls = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        return httpx.Response(
            200,
            request=request,
            json={"choices": [{"message": {"content": "canned answer"}}], "usage": {"prompt_tokens": 100, "completion_tokens": 50}},
        )

    mock_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    client = AsyncOpenAICompatibleClient("fake", "https://llm.invalid", "key", client=mock_client)

    first = await client.chat("triage", "hello world")
    assert first.cost_usd > 0
    assert first.cached is False
    assert calls["count"] == 1

    second = await client.chat("triage", "hello world")
    assert second.cost_usd == 0.0
    assert second.cached is True
    assert calls["count"] == 1  # Network client was not called again!


@pytest.mark.asyncio
async def test_cassette_record_and_replay(tmp_path: Path) -> None:
    cassette_dir = tmp_path / "cassettes"
    cassette_client = CassetteChatClient(cassettes_dir=cassette_dir)

    recorded_result = ChatResult(
        text='{"fixed": true}',
        tool_calls=[],
        model="test-model",
        tier="super",
        input_tokens=20,
        output_tokens=10,
    )
    cassette_client.record("patch", "patch prompt", recorded_result)

    replayed = await cassette_client.chat("patch", "patch prompt")
    assert replayed.text == '{"fixed": true}'
    assert replayed.cached is True
    assert replayed.cost_usd == 0.0


@pytest.mark.asyncio
async def test_cassette_miss_errors(tmp_path: Path) -> None:
    cassette_client = CassetteChatClient(cassettes_dir=tmp_path / "empty_cassettes")
    with pytest.raises(RuntimeError, match="Cassette miss"):
        await cassette_client.chat("triage", "unrecorded prompt")


@pytest.mark.asyncio
async def test_preflight_refusal() -> None:
    fake_client = FakeChatClient()
    huge_prompt = "a" * (7000 * 4)  # triage cap is 6000 tokens
    with pytest.raises(InputTooLarge):
        await fake_client.chat("triage", huge_prompt)


@pytest.mark.asyncio
async def test_run_budget_abort(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FIXIE_DB", str(tmp_path / "fixie.db"))
    monkeypatch.setenv("RUN_BUDGET_USD", "0.0001")  # tiny budget

    fake_client = FakeChatClient()
    # First call will consume budget
    await fake_client.chat("triage", "call 1", run_id="run_budget_test")

    with pytest.raises(BudgetExceeded) as exc_info:
        await fake_client.chat("patch", "call 2", run_id="run_budget_test")
    assert exc_info.value.code == "RUN_BUDGET"


def test_hard_cap_and_call_cap_persist(tmp_path: Path) -> None:
    db_file = tmp_path / "guards.db"
    guards_1 = PersistentGuardsAndCache(db_file)
    guards_1.check_and_increment(0.05)
    guards_1.check_and_increment(0.05)

    # Re-instantiate in a new instance (simulating restart)
    guards_2 = PersistentGuardsAndCache(db_file)
    with guards_2._connect() as conn:
        spent = conn.execute("SELECT current_value FROM budget_guards WHERE guard_name = 'total_spent_usd'").fetchone()[0]
        calls = conn.execute("SELECT current_value FROM budget_guards WHERE guard_name = 'total_calls'").fetchone()[0]
    assert spent == 0.10
    assert calls == 2


def test_sandbox_fork_isolation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FIXIE_ALLOW_LOCAL", "1")
    sandbox = LocalSandbox.open("fixture:parse_duration")
    try:
        forks = sandbox.fork(2)
        assert len(forks) == 2

        fork_a, fork_b = forks[0], forks[1]
        fork_a.write_file("test_isolation.txt", "data_in_a")
        assert fork_a.read_file("test_isolation.txt") == "data_in_a"

        # Fork B must not see file written to Fork A
        with pytest.raises(FileNotFoundError):
            fork_b.read_file("test_isolation.txt")
    finally:
        sandbox.close()


@pytest.mark.asyncio
async def test_sandbox_parallel_runs(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FIXIE_ALLOW_LOCAL", "1")
    sandbox = LocalSandbox.open("fixture:parse_duration")
    try:
        forks = sandbox.fork(3)
        tasks = [f.async_run("python -c \"print('sandbox ok')\"") for f in forks]
        results = await asyncio.gather(*tasks)
        for res in results:
            assert res.returncode == 0
            assert "sandbox ok" in res.stdout
    finally:
        sandbox.close()
