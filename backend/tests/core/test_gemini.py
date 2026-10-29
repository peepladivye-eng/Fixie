"""Tests for Gemini dev-only provider integration."""
from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import httpx
import pytest

from app.llm import (
    AsyncOpenAICompatibleClient,
    calculate_cost,
    configured_client,
    get_guards_and_cache,
)


def test_models_json_gemini_config() -> None:
    models_path = Path(__file__).resolve().parents[2] / "app" / "models.json"
    data = json.loads(models_path.read_text(encoding="utf-8"))
    gemini = data.get("providers", {}).get("gemini", {})
    assert gemini.get("base_url") == "https://generativelanguage.googleapis.com/v1beta/openai"
    assert gemini.get("_note") == "names taken from the key's own list and a live latency test on 2026-10-30; 3.8-flash, 3.7-flash and flash-latest were overloaded"
    models = gemini.get("models", {})
    assert models.get("lightning") == "gemini-3.5-flash-lite"
    assert models.get("super") == "gemini-3.5-flash"
    assert models.get("ultra") == "gemini-3.5-flash"
    assert models.get("none") == "gemini-3.1-flash-lite"


def test_configured_client_gemini(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="GEMINI_API_KEY must be set"):
        configured_client()

    monkeypatch.setenv("GEMINI_API_KEY", "dev-secret-key-1234")
    client = configured_client()
    assert isinstance(client, AsyncOpenAICompatibleClient)
    assert client.provider == "gemini"
    assert client.api_key == "dev-secret-key-1234"
    assert client.base_url == "https://generativelanguage.googleapis.com/v1beta/openai"


def test_calculate_cost_zero_for_gemini() -> None:
    assert calculate_cost("lightning", 1000, 500, provider="gemini") == 0.0
    assert calculate_cost("super", 5000, 2000, provider="gemini") == 0.0
    assert calculate_cost("ultra", 10000, 4000, provider="gemini") == 0.0
    assert calculate_cost("gemini", 1000, 500) == 0.0


@pytest.mark.asyncio
async def test_gemini_cache_isolation_from_nebius(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FIXIE_DB", str(tmp_path / "fixie.db"))

    gemini_calls = {"count": 0}
    nebius_calls = {"count": 0}

    def gemini_handler(request: httpx.Request) -> httpx.Response:
        gemini_calls["count"] += 1
        return httpx.Response(
            200,
            request=request,
            json={"choices": [{"message": {"content": "from-gemini"}}], "usage": {"prompt_tokens": 10, "completion_tokens": 5}},
        )

    def nebius_handler(request: httpx.Request) -> httpx.Response:
        nebius_calls["count"] += 1
        return httpx.Response(
            200,
            request=request,
            json={"choices": [{"message": {"content": "from-nebius"}}], "usage": {"prompt_tokens": 10, "completion_tokens": 5}},
        )

    gemini_client = AsyncOpenAICompatibleClient(
        "gemini",
        "https://generativelanguage.googleapis.com/v1beta/openai",
        "gemini-key",
        client=httpx.AsyncClient(transport=httpx.MockTransport(gemini_handler)),
    )
    nebius_client = AsyncOpenAICompatibleClient(
        "nebius",
        "https://api.tokenfactory.nebius.com/v1/",
        "nebius-key",
        client=httpx.AsyncClient(transport=httpx.MockTransport(nebius_handler)),
    )

    # 1. First call to gemini populates the gemini cache entry
    res_gemini = await gemini_client.chat("triage", "prompt-cache-check")
    assert res_gemini.text == "from-gemini"
    assert res_gemini.cached is False
    assert gemini_calls["count"] == 1

    # 2. Subsequent call to gemini hits the cache
    res_gemini_cached = await gemini_client.chat("triage", "prompt-cache-check")
    assert res_gemini_cached.text == "from-gemini"
    assert res_gemini_cached.cached is True
    assert gemini_calls["count"] == 1

    # 3. Call to nebius with identical role and prompt does NOT use the gemini cache
    res_nebius = await nebius_client.chat("triage", "prompt-cache-check")
    assert res_nebius.text == "from-nebius"
    assert res_nebius.cached is False
    assert nebius_calls["count"] == 1


@pytest.mark.asyncio
async def test_mock_transport_headers_and_reasoning_effort(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FIXIE_DB", str(tmp_path / "fixie.db"))
    recorded_requests: list[dict[str, Any]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content.decode("utf-8"))
        recorded_requests.append({
            "url": str(request.url),
            "headers": dict(request.headers),
            "body": body,
        })
        return httpx.Response(
            200,
            request=request,
            json={"choices": [{"message": {"content": "{}"}}], "usage": {"prompt_tokens": 10, "completion_tokens": 5}},
        )

    transport = httpx.MockTransport(handler)

    # Test Gemini provider
    gemini_client = AsyncOpenAICompatibleClient(
        "gemini",
        "https://generativelanguage.googleapis.com/v1beta/openai",
        "gemini-secret-token",
        client=httpx.AsyncClient(transport=transport),
    )
    await gemini_client.chat("triage", "test gemini request")

    assert len(recorded_requests) == 1
    gemini_req = recorded_requests[0]
    assert gemini_req["url"].endswith("/chat/completions")
    assert gemini_req["headers"].get("authorization") == "Bearer gemini-secret-token"
    assert "reasoning_effort" not in gemini_req["body"]
    assert "max_tokens" in gemini_req["body"]

    # Test Nebius provider
    nebius_client = AsyncOpenAICompatibleClient(
        "nebius",
        "https://api.tokenfactory.nebius.com/v1/",
        "nebius-secret-token",
        client=httpx.AsyncClient(transport=transport),
    )
    await nebius_client.chat("triage", "test nebius request")

    assert len(recorded_requests) == 2
    nebius_req = recorded_requests[1]
    assert nebius_req["url"].endswith("/chat/completions")
    assert nebius_req["headers"].get("authorization") == "Bearer nebius-secret-token"
    assert "reasoning_effort" in nebius_req["body"]
    assert nebius_req["body"]["reasoning_effort"] == "none"
    assert "max_tokens" in nebius_req["body"]


def test_timeout_default_and_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LLM_TIMEOUT_S", raising=False)
    client = AsyncOpenAICompatibleClient("gemini", "https://api.test", "key")
    assert client.timeout_seconds == 120.0

    monkeypatch.setenv("LLM_TIMEOUT_S", "45.0")
    client_env = AsyncOpenAICompatibleClient("gemini", "https://api.test", "key")
    assert client_env.timeout_seconds == 45.0


@pytest.mark.asyncio
async def test_retry_on_503_and_readable_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FIXIE_DB", str(tmp_path / "fixie.db"))
    sleep_calls: list[float] = []

    async def fake_sleep(secs: float) -> None:
        sleep_calls.append(secs)

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)

    # 1. Three 503 responses give the readable error
    call_count = 0

    def handler_503(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        return httpx.Response(503, request=request, extensions={"reason_phrase": b"UNAVAILABLE"})

    client_failing = AsyncOpenAICompatibleClient(
        "gemini",
        "https://generativelanguage.googleapis.com/v1beta/openai",
        "secret-gemini-token",
        client=httpx.AsyncClient(transport=httpx.MockTransport(handler_503)),
    )

    with pytest.raises(RuntimeError) as exc_info:
        await client_failing.chat("triage", "prompt-fail")

    err_msg = str(exc_info.value)
    assert "LLM request failed after 3 attempts: HTTPStatusError 503 UNAVAILABLE" in err_msg
    assert "secret-gemini-token" not in err_msg
    assert call_count == 3
    assert sleep_calls == [2.0, 4.0]

    # 2. One 503 then a 200 succeeds
    sleep_calls.clear()
    attempt = 0

    def handler_recover(request: httpx.Request) -> httpx.Response:
        nonlocal attempt
        attempt += 1
        if attempt == 1:
            return httpx.Response(503, request=request, extensions={"reason_phrase": b"UNAVAILABLE"})
        return httpx.Response(
            200,
            request=request,
            json={"choices": [{"message": {"content": "ok"}}], "usage": {"prompt_tokens": 10, "completion_tokens": 5}},
        )

    client_recovering = AsyncOpenAICompatibleClient(
        "gemini",
        "https://generativelanguage.googleapis.com/v1beta/openai",
        "secret-gemini-token",
        client=httpx.AsyncClient(transport=httpx.MockTransport(handler_recover)),
    )

    result = await client_recovering.chat("triage", "prompt-recover")
    assert result.text == "ok"
    assert attempt == 2
    assert sleep_calls == [2.0]

