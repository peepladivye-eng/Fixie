"""Resilient, provider-agnostic chat clients. Fake is the default."""
from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

import httpx

logger = logging.getLogger(__name__)
_MODELS = json.loads((Path(__file__).with_name("models.yaml")).read_text(encoding="utf-8"))


@dataclass(frozen=True)
class LLMResult:
    text: str
    model: str
    input_tokens: int
    output_tokens: int
    latency_ms: int


class ChatClient(Protocol):
    def chat(self, role: str, prompt: str) -> LLMResult: ...


def max_tokens_for(role: str) -> int:
    try:
        return int(_MODELS["roles"][role]["max_tokens"])
    except KeyError as error:
        raise ValueError(f"unknown LLM role: {role}") from error


def _response_text(payload: dict[str, Any]) -> str:
    """Support plain content and OpenAI-compatible function/tool calls."""
    choice = payload.get("choices", [{}])[0]
    message = choice.get("message", {})
    content = message.get("content")
    if isinstance(content, str) and content:
        return content
    tool_calls = message.get("tool_calls") or []
    if tool_calls:
        arguments = tool_calls[0].get("function", {}).get("arguments", "")
        if isinstance(arguments, str):
            return arguments
        return json.dumps(arguments)
    function_call = message.get("function_call") or {}
    arguments = function_call.get("arguments")
    if arguments:
        return arguments if isinstance(arguments, str) else json.dumps(arguments)
    raise ValueError("OpenAI-compatible response contains no message content or tool call")


class OpenAICompatibleClient:
    def __init__(self, base_url: str, api_key: str, model: str, timeout_seconds: float = 30.0) -> None:
        self.base_url, self.api_key, self.model, self.timeout_seconds = base_url.rstrip("/"), api_key, model, timeout_seconds

    def chat(self, role: str, prompt: str) -> LLMResult:
        ceiling = max_tokens_for(role)
        last_error: Exception | None = None
        for attempt in range(3):
            started = time.monotonic()
            try:
                with httpx.Client(timeout=self.timeout_seconds) as client:
                    response = client.post(
                        f"{self.base_url}/chat/completions",
                        headers={"Authorization": f"Bearer {self.api_key}"},
                        json={"model": self.model, "messages": [{"role": "user", "content": prompt}], "max_tokens": ceiling},
                    )
                if response.status_code == 429 or response.status_code >= 500:
                    raise httpx.HTTPStatusError("retryable response", request=response.request, response=response)
                response.raise_for_status()
                payload = response.json()
                usage = payload.get("usage", {})
                result = LLMResult(_response_text(payload), self.model, int(usage.get("prompt_tokens", 0)), int(usage.get("completion_tokens", 0)), int((time.monotonic() - started) * 1000))
                logger.info("llm_usage role=%s model=%s input_tokens=%s output_tokens=%s latency_ms=%s", role, result.model, result.input_tokens, result.output_tokens, result.latency_ms)
                return result
            except httpx.HTTPStatusError as error:
                if error.response.status_code != 429 and error.response.status_code < 500:
                    raise
                last_error = error
            except httpx.TimeoutException as error:
                last_error = error
            if attempt < 2:
                time.sleep(0.25 * (2**attempt))
        raise RuntimeError(f"LLM request failed after retries: {last_error}")


class FakeChatClient:
    """No-network client used unless LLM_PROVIDER explicitly selects another provider."""
    model = "fake-local"

    def chat(self, role: str, prompt: str) -> LLMResult:
        responses = {
            "triage": '{"summary":"Duration parser rejects seconds","risk":"low"}',
            "reproduce": '{"command":"python -m pytest -q","expected":"a seconds test fails"}',
            "diagnose": '{"root_cause":"The parser handles minutes and hours but not seconds."}',
            "patch": '{"diff":"--- a/parse_duration.py\\n+++ b/parse_duration.py\\n@@ -3,5 +3,7 @@\\n     if unit == \\"m\\":\\n         return int(amount) * 60\\n     if unit == \\"h\\":\\n         return int(amount) * 3600\\n+    if unit == \\"s\\":\\n+        return int(amount)\\n     raise ValueError(\\"unsupported duration unit\\")\\n","summary":"Handle seconds explicitly."}',
        }
        text = responses.get(role, "{}")
        return LLMResult(text, self.model, len(prompt) // 4, len(text) // 4, 0)


def configured_client() -> ChatClient:
    provider = os.getenv("LLM_PROVIDER", "fake").lower()
    if provider == "fake":
        return FakeChatClient()
    key_name = {"nebius": "NEBIUS_API_KEY", "nvidia": "NVIDIA_API_KEY"}.get(provider)
    if key_name is None:
        raise ValueError(f"unsupported LLM_PROVIDER: {provider}")
    api_key = os.getenv(key_name)
    if not api_key:
        raise RuntimeError(f"{key_name} must be set for LLM_PROVIDER={provider}")
    base_url = os.getenv("LLM_BASE_URL")
    model = os.getenv("LLM_MODEL")
    if not base_url or not model:
        raise RuntimeError("LLM_BASE_URL and LLM_MODEL are required for non-fake providers")
    return OpenAICompatibleClient(base_url, api_key, model)
