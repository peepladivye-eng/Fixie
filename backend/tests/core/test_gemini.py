"""Tests for Gemini dev-only provider integration."""
from __future__ import annotations

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
    assert gemini.get("_note") == "dev only, TODO(VERIFY) model names in AI Studio"
    models = gemini.get("models", {})
    assert models.get("lightning") == "gemini-2.5-flash-lite"
    assert models.get("super") == "gemini-2.5-flash"
    assert models.get("ultra") == "gemini-2.5-flash"
    assert models.get("none") == "gemini-2.5-flash-lite"


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
