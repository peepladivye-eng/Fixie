from __future__ import annotations

import asyncio
import os
from pathlib import Path

import httpx
import pytest
from pydantic import BaseModel

from app.agent.json_output import validated_response
from app.agent.runner import run_agent
from app.github import GitHubClient, parse_issue_url
from app.llm import OpenAICompatibleClient, _response_text
from app.sandbox import LocalSandbox
from app.search import TavilySearch


class Reply(BaseModel):
    answer: int


def test_json_helper_recovers_fenced_reasoning() -> None:
    received = []

    def ask(prompt: str) -> str:
        received.append(prompt)
        return "reasoning before\n<think>private chain</think>\n```json\n{\"answer\": 7}\n```"

    assert validated_response(Reply, ask, "respond") == Reply(answer=7)
    assert len(received) == 1


def test_json_helper_retries_with_error() -> None:
    values = iter(["not json", '{"answer": 1}'])
    prompts = []
    result = validated_response(Reply, lambda prompt: (prompts.append(prompt), next(values))[1], "original")
    assert result.answer == 1
    assert "previous output was invalid" in prompts[1]


def test_local_sandbox_refuses_non_fixture(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FIXIE_ALLOW_LOCAL", "1")
    with pytest.raises(ValueError, match="only accepts"):
        LocalSandbox.open("https://github.com/acme/repo/issues/1")


def test_local_sandbox_requires_opt_in(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("FIXIE_ALLOW_LOCAL", raising=False)
    with pytest.raises(PermissionError):
        LocalSandbox.open("fixture:parse_duration")


def test_fake_agent_repairs_fixture(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FIXIE_ALLOW_LOCAL", "1")
    events = []

    async def emit(kind: str, data: dict) -> None:
        events.append((kind, data))

    asyncio.run(run_agent("fixture:parse_duration", emit, {"k_branches": 1}))
    assert any(kind == "branch.winner" for kind, _ in events)
    assert events[-1] == ("run.finished", {"status": "success", "total_cost_usd": 0.0, "total_seconds": 0.0})


def test_openai_tool_call_parsing() -> None:
    assert _response_text({"choices": [{"message": {"tool_calls": [{"function": {"arguments": '{"ok":true}'}}]}}]}) == '{"ok":true}'


def test_llm_retries_429(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        if calls["count"] == 1:
            return httpx.Response(429, request=request)
        return httpx.Response(200, request=request, json={"choices": [{"message": {"content": "{}"}}], "usage": {"prompt_tokens": 2, "completion_tokens": 1}})

    transport = httpx.MockTransport(handler)
    original = httpx.Client

    class MockClient:
        def __init__(self, **kwargs): self.client = original(transport=transport, **kwargs)
        def __enter__(self): return self.client
        def __exit__(self, *args): self.client.close()

    monkeypatch.setattr("app.llm.httpx.Client", MockClient)
    monkeypatch.setattr("app.llm.time.sleep", lambda _: None)
    result = OpenAICompatibleClient("https://llm.invalid", "not-logged", "model").chat("triage", "hello")
    assert result.text == "{}"
    assert calls["count"] == 2


def test_tavily_uses_local_cache_without_key(tmp_path: Path) -> None:
    client = TavilySearch(cache_dir=tmp_path)
    key = __import__("hashlib").sha256(b"query").hexdigest()
    (tmp_path / f"{key}.json").write_text('[{"title":"cached"}]', encoding="utf-8")
    assert client.search("query") == [{"title": "cached"}]


def test_parse_github_issue_url() -> None:
    assert parse_issue_url("https://github.com/o/r/issues/12") == ("o", "r", 12)


def test_github_issue_fetch_uses_rest_without_exposing_token() -> None:
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.url.path)
        return httpx.Response(200, request=request, json={"title": "Bug", "body": "details"})

    client = httpx.Client(base_url="https://api.github.com", transport=httpx.MockTransport(handler))
    github = GitHubClient(token="secret-not-logged", client=client)
    assert github.issue("https://github.com/o/r/issues/2") == {"owner": "o", "repo": "r", "number": 2, "title": "Bug", "body": "details"}
    assert seen == ["/repos/o/r/issues/2"]
