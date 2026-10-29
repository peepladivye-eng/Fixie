"""Async, resilient, provider-agnostic chat client with caching, cassettes, and budget guards."""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import sqlite3
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

import httpx

logger = logging.getLogger(__name__)

_MODELS_PATH = Path(__file__).with_name("models.json")
_MODELS: dict[str, Any] = json.loads(_MODELS_PATH.read_text(encoding="utf-8"))
CASSETTES_DIR = Path(__file__).resolve().parents[1] / "cassettes"


class InputTooLarge(ValueError):
    """Raised when prompt input tokens exceed the configured role cap."""


class BudgetExceeded(RuntimeError):
    """Raised when spending or call count exceeds hard caps or run budget."""
    def __init__(self, code: str, message: str = ""):
        super().__init__(message or code)
        self.code = code


@dataclass(frozen=True)
class ChatResult:
    text: str
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    model: str = "fake-local"
    tier: str = "lightning"
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    cached: bool = False
    latency_ms: int = 0

    def __await__(self):
        async def _coro():
            return self
        return _coro().__await__()


# Backward compatibility alias
LLMResult = ChatResult


class ChatClient(Protocol):
    async def chat(
        self,
        role: str,
        messages: str | list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        run_id: str | None = None,
    ) -> ChatResult: ...


def max_tokens_for(role: str) -> int:
    try:
        return int(_MODELS["roles"][role]["max_tokens"])
    except KeyError as error:
        raise ValueError(f"unknown LLM role: {role}") from error


def tier_for_role(role: str) -> str:
    if os.getenv("USE_ULTRA", "false").lower() in ("1", "true", "yes"):
        return "ultra"
    return _MODELS["roles"].get(role, {}).get("tier", "lightning")


def input_cap_for(role: str) -> int:
    return int(_MODELS["roles"].get(role, {}).get("input_cap_tokens", 8000))


def calculate_cost(tier: str, input_tokens: int, output_tokens: int, provider: str = "") -> float:
    if provider.lower() == "gemini" or tier.lower() == "gemini":
        return 0.0
    prices = _MODELS.get("prices_per_1m", {}).get(tier, {"input": 0.0, "output": 0.0})
    input_cost = (input_tokens / 1_000_000.0) * float(prices.get("input", 0.0))
    output_cost = (output_tokens / 1_000_000.0) * float(prices.get("output", 0.0))
    return round(input_cost + output_cost, 6)


def _response_text_and_tools(payload: dict[str, Any]) -> tuple[str, list[dict[str, Any]]]:
    choice = payload.get("choices", [{}])[0]
    message = choice.get("message", {})
    content = message.get("content") or ""
    tool_calls: list[dict[str, Any]] = []

    raw_tools = message.get("tool_calls") or []
    for tc in raw_tools:
        fn = tc.get("function", {})
        tool_calls.append({
            "id": tc.get("id", ""),
            "name": fn.get("name", ""),
            "arguments": fn.get("arguments", "{}"),
        })

    if not content and tool_calls:
        content = tool_calls[0].get("arguments", "")

    function_call = message.get("function_call") or {}
    if not content and function_call:
        content = function_call.get("arguments", "")

    return content, tool_calls


def _response_text(payload: dict[str, Any]) -> str:
    text, _ = _response_text_and_tools(payload)
    if not text:
        raise ValueError("OpenAI-compatible response contains no message content or tool call")
    return text


def _normalize_messages(messages: str | list[dict[str, Any]]) -> list[dict[str, Any]]:
    if isinstance(messages, str):
        return [{"role": "user", "content": messages}]
    return messages


def _estimate_tokens(messages: list[dict[str, Any]]) -> int:
    total_chars = sum(len(str(m.get("content", ""))) for m in messages)
    return max(1, total_chars // 4)


class PersistentGuardsAndCache:
    """SQLite-backed response cache and budget guards surviving restarts."""

    def __init__(self, db_path: Path | str | None = None):
        if db_path is None:
            db_path = os.getenv("FIXIE_DB", str(Path(__file__).resolve().parents[1] / "fixie.db"))
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS llm_cache (
                    cache_key TEXT PRIMARY KEY,
                    response_json TEXT NOT NULL,
                    created_at REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS budget_guards (
                    guard_name TEXT PRIMARY KEY,
                    current_value REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS run_spending (
                    run_id TEXT PRIMARY KEY,
                    spent_usd REAL NOT NULL
                );
                """
            )
            # Initialize guards if missing
            conn.execute("INSERT OR IGNORE INTO budget_guards VALUES ('total_spent_usd', 0.0)")
            conn.execute("INSERT OR IGNORE INTO budget_guards VALUES ('total_calls', 0)")
            conn.commit()

    def get_cache(self, key: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute("SELECT response_json FROM llm_cache WHERE cache_key = ?", (key,)).fetchone()
            if row:
                return json.loads(row["response_json"])
        return None

    def put_cache(self, key: str, value: dict[str, Any]) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO llm_cache (cache_key, response_json, created_at) VALUES (?, ?, ?)",
                (key, json.dumps(value), time.time()),
            )
            conn.commit()

    def check_and_increment(self, cost_usd: float, run_id: str | None = None) -> None:
        hard_cap_usd = float(os.getenv("HARD_CAP_USD", "50.0"))
        call_cap = int(os.getenv("CALL_CAP", "5000"))
        run_budget_usd = float(os.getenv("RUN_BUDGET_USD", "0.08"))

        with self._connect() as conn:
            total_spent = float(conn.execute("SELECT current_value FROM budget_guards WHERE guard_name = 'total_spent_usd'").fetchone()[0])
            total_calls = int(conn.execute("SELECT current_value FROM budget_guards WHERE guard_name = 'total_calls'").fetchone()[0])

            if total_spent + cost_usd > hard_cap_usd:
                raise BudgetExceeded("BUDGET_EXCEEDED", f"Hard spending cap exceeded: {total_spent + cost_usd} > {hard_cap_usd}")
            if total_calls + 1 > call_cap:
                raise BudgetExceeded("CALL_CAP_EXCEEDED", f"Call cap exceeded: {total_calls + 1} > {call_cap}")

            if run_id:
                row = conn.execute("SELECT spent_usd FROM run_spending WHERE run_id = ?", (run_id,)).fetchone()
                run_spent = float(row[0]) if row else 0.0
                if run_spent + cost_usd > run_budget_usd:
                    raise BudgetExceeded("RUN_BUDGET", f"Run budget exceeded for {run_id}: {run_spent + cost_usd} > {run_budget_usd}")
                conn.execute(
                    "INSERT OR REPLACE INTO run_spending (run_id, spent_usd) VALUES (?, ?)",
                    (run_id, run_spent + cost_usd),
                )

            conn.execute("UPDATE budget_guards SET current_value = current_value + ? WHERE guard_name = 'total_spent_usd'", (cost_usd,))
            conn.execute("UPDATE budget_guards SET current_value = current_value + 1 WHERE guard_name = 'total_calls'")
            conn.commit()


_guards_and_cache: PersistentGuardsAndCache | None = None


def get_guards_and_cache() -> PersistentGuardsAndCache:
    global _guards_and_cache
    env_db = os.getenv("FIXIE_DB")
    target_path = Path(env_db) if env_db else Path(__file__).resolve().parents[1] / "fixie.db"
    if _guards_and_cache is None or _guards_and_cache.db_path.resolve() != target_path.resolve():
        _guards_and_cache = PersistentGuardsAndCache(target_path)
    return _guards_and_cache


def _compute_key(provider: str, model: str, messages: list[dict[str, Any]], params: dict[str, Any]) -> str:
    raw = json.dumps({"provider": provider, "model": model, "messages": messages, "params": params}, sort_keys=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class FakeChatClient:
    """Deterministic, no-network fake client returning realistic responses."""
    def __init__(self, provider_name: str = "fake"):
        self.provider_name = provider_name
        self.model = "fake-local"

    def chat(
        self,
        role: str,
        messages: str | list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        run_id: str | None = None,
    ) -> ChatResult:
        normalized = _normalize_messages(messages)
        cap = input_cap_for(role)
        tokens = _estimate_tokens(normalized)
        if tokens > cap:
            raise InputTooLarge(f"Input tokens ({tokens}) exceeds role '{role}' cap ({cap})")

        tier = tier_for_role(role)
        model = _MODELS["providers"]["fake"]["models"].get(tier, "fake-lightning")
        started = time.monotonic()

        canned = {
            "triage": '{"summary":"Duration parser rejects seconds","risk":"low"}',
            "reproduce": '{"command":"python -m pytest -q","expected":"a seconds test fails"}',
            "diagnose": '{"root_cause":"The parser handles minutes and hours but not seconds."}',
            "patch": '{"edits":[{"path":"parse_duration.py","old":"    raise ValueError(\\"unsupported duration unit\\")","new":"    if unit == \\"s\\":\\n        return int(amount)\\n    raise ValueError(\\"unsupported duration unit\\")"}],"summary":"Handle seconds explicitly."}',
            "patch_alt": '{"edits":[{"path":"parse_duration.py","old":"    raise ValueError(\\"unsupported duration unit\\")","new":"    if unit == \\"s\\":\\n        return int(amount)\\n    raise ValueError(\\"unsupported duration unit\\")"}],"summary":"Handle seconds explicitly."}',
            "deliver": '{"pr_title":"Fix duration parser for seconds","summary":"Added support for second unit."}',
        }
        text = canned.get(role, "{}")
        output_tokens = max(1, len(text) // 4)
        cost = calculate_cost(tier, tokens, output_tokens)

        # Check guards
        get_guards_and_cache().check_and_increment(cost, run_id=run_id)

        latency_ms = int((time.monotonic() - started) * 1000)
        return ChatResult(
            text=text,
            tool_calls=[],
            model=model,
            tier=tier,
            input_tokens=tokens,
            output_tokens=output_tokens,
            cost_usd=cost,
            cached=False,
            latency_ms=latency_ms,
        )


class CassetteChatClient:
    """Cassette store client. Plays recorded responses; raises error on miss."""
    def __init__(self, cassettes_dir: Path = CASSETTES_DIR):
        self.cassettes_dir = cassettes_dir
        self.cassettes_dir.mkdir(parents=True, exist_ok=True)

    def _file_path(self, key: str) -> Path:
        return self.cassettes_dir / f"{key}.json"

    async def chat(
        self,
        role: str,
        messages: str | list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        run_id: str | None = None,
    ) -> ChatResult:
        normalized = _normalize_messages(messages)
        cap = input_cap_for(role)
        tokens = _estimate_tokens(normalized)
        if tokens > cap:
            raise InputTooLarge(f"Input tokens ({tokens}) exceeds role '{role}' cap ({cap})")

        tier = tier_for_role(role)
        model = f"cassette-{tier}"
        params = {"max_tokens": max_tokens_for(role), "temperature": 0}
        key = _compute_key("cassette", model, normalized, params)

        cassette_file = self._file_path(key)
        if not cassette_file.is_file():
            raise RuntimeError(f"Cassette miss for key: {key} (role={role})")

        data = json.loads(cassette_file.read_text(encoding="utf-8"))
        return ChatResult(
            text=data.get("text", ""),
            tool_calls=data.get("tool_calls", []),
            model=data.get("model", model),
            tier=tier,
            input_tokens=data.get("input_tokens", tokens),
            output_tokens=data.get("output_tokens", 0),
            cost_usd=0.0,
            cached=True,
            latency_ms=0,
        )

    def record(self, role: str, messages: str | list[dict[str, Any]], result: ChatResult) -> str:
        normalized = _normalize_messages(messages)
        tier = tier_for_role(role)
        model = f"cassette-{tier}"
        params = {"max_tokens": max_tokens_for(role), "temperature": 0}
        key = _compute_key("cassette", model, normalized, params)
        data = {
            "text": result.text,
            "tool_calls": result.tool_calls,
            "model": result.model,
            "tier": result.tier,
            "input_tokens": result.input_tokens,
            "output_tokens": result.output_tokens,
        }
        self._file_path(key).write_text(json.dumps(data, indent=2), encoding="utf-8")
        return key


def _format_error(error: Exception | None) -> str:
    if error is None:
        return "Unknown error"
    exc_type = type(error).__name__
    if isinstance(error, httpx.HTTPStatusError):
        code = error.response.status_code
        phrase = error.response.reason_phrase or ""
        msg = f"{code} {phrase}".strip()
        return f"{exc_type} {msg}"
    if isinstance(error, httpx.TimeoutException):
        return exc_type
    msg = str(error).strip()
    return f"{exc_type} {msg}".strip()


class AsyncOpenAICompatibleClient:
    """Async OpenAI-compatible client for NVIDIA NIM, Nebius Token Factory, and Gemini."""

    def __init__(
        self,
        provider: str,
        base_url: str,
        api_key: str,
        timeout_seconds: float | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.provider = provider
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        env_timeout = os.getenv("LLM_TIMEOUT_S")
        if env_timeout:
            try:
                self.timeout_seconds = float(env_timeout)
            except ValueError:
                self.timeout_seconds = 120.0
        elif timeout_seconds is not None:
            self.timeout_seconds = float(timeout_seconds)
        else:
            self.timeout_seconds = 120.0
        self._external_client = client

    async def chat(
        self,
        role: str,
        messages: str | list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        run_id: str | None = None,
    ) -> ChatResult:
        normalized = _normalize_messages(messages)
        ceiling = max_tokens_for(role)
        tier = tier_for_role(role)
        cap = input_cap_for(role)
        tokens = _estimate_tokens(normalized)
        if tokens > cap:
            raise InputTooLarge(f"Input tokens ({tokens}) exceeds cap ({cap}) for role '{role}'")

        models_map = _MODELS.get("providers", {}).get(self.provider, {}).get("models", {})
        model = models_map.get(tier, "default-model")
        params: dict[str, Any] = {"max_tokens": ceiling, "temperature": 0}
        if self.provider != "gemini":
            reasoning_effort = _MODELS.get("roles", {}).get(role, {}).get("reasoning_effort", "none")
            if reasoning_effort:
                params["reasoning_effort"] = reasoning_effort

        cache_store = get_guards_and_cache()
        cache_key = _compute_key(self.provider, model, normalized, params)
        cached_entry = cache_store.get_cache(cache_key)
        if cached_entry:
            return ChatResult(
                text=cached_entry.get("text", ""),
                tool_calls=cached_entry.get("tool_calls", []),
                model=model,
                tier=tier,
                input_tokens=cached_entry.get("input_tokens", tokens),
                output_tokens=cached_entry.get("output_tokens", 0),
                cost_usd=0.0,
                cached=True,
                latency_ms=0,
            )

        payload_req: dict[str, Any] = {
            "model": model,
            "messages": normalized,
            "max_tokens": ceiling,
            "temperature": 0,
        }
        if self.provider != "gemini":
            reasoning_effort = _MODELS.get("roles", {}).get(role, {}).get("reasoning_effort", "none")
            if reasoning_effort:
                payload_req["reasoning_effort"] = reasoning_effort
        # TODO(VERIFY): Confirm reasoning parameter name for provider (e.g. reasoning_effort="none")
        if tools:
            payload_req["tools"] = tools

        delays = [2.0, 4.0]
        max_attempts = 3
        last_error: Exception | None = None
        for attempt in range(max_attempts):
            started = time.monotonic()
            try:
                if self._external_client:
                    response = await self._external_client.post(
                        f"{self.base_url}/chat/completions",
                        headers={"Authorization": f"Bearer {self.api_key}"},
                        json=payload_req,
                    )
                else:
                    async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                        response = await client.post(
                            f"{self.base_url}/chat/completions",
                            headers={"Authorization": f"Bearer {self.api_key}"},
                            json=payload_req,
                        )

                response.raise_for_status()

                payload = response.json()
                text, tool_calls = _response_text_and_tools(payload)
                usage = payload.get("usage", {})
                in_tok = int(usage.get("prompt_tokens", tokens))
                out_tok = int(usage.get("completion_tokens", len(text) // 4))
                cost = calculate_cost(tier, in_tok, out_tok, provider=self.provider)

                # Check and apply budget guards
                cache_store.check_and_increment(cost, run_id=run_id)

                latency_ms = int((time.monotonic() - started) * 1000)
                result = ChatResult(
                    text=text,
                    tool_calls=tool_calls,
                    model=model,
                    tier=tier,
                    input_tokens=in_tok,
                    output_tokens=out_tok,
                    cost_usd=cost,
                    cached=False,
                    latency_ms=latency_ms,
                )

                # Save to cache
                cache_store.put_cache(cache_key, {
                    "text": text,
                    "tool_calls": tool_calls,
                    "input_tokens": in_tok,
                    "output_tokens": out_tok,
                })

                return result
            except httpx.HTTPStatusError as error:
                if error.response.status_code != 503 and error.response.status_code != 429 and error.response.status_code < 500:
                    raise
                last_error = error
            except httpx.TimeoutException as error:
                last_error = error

            if attempt < len(delays):
                await asyncio.sleep(delays[attempt])

        raise RuntimeError(f"LLM request failed after {max_attempts} attempts: {_format_error(last_error)}")


# Compatibility wrapper for synchronous test cases if any
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
                result = LLMResult(
                    _response_text(payload),
                    [],
                    self.model,
                    "lightning",
                    int(usage.get("prompt_tokens", 0)),
                    int(usage.get("completion_tokens", 0)),
                    0.0,
                    False,
                    int((time.monotonic() - started) * 1000),
                )
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


def configured_client() -> ChatClient:
    provider = os.getenv("LLM_PROVIDER", "fake").lower()
    if provider == "fake":
        return FakeChatClient("fake")
    if provider == "cassette":
        return CassetteChatClient()

    # Providers: nvidia, nebius, gemini
    key_name = {
        "nebius": "NEBIUS_API_KEY",
        "nvidia": "NVIDIA_API_KEY",
        "gemini": "GEMINI_API_KEY",
    }.get(provider)
    if key_name is None:
        raise ValueError(f"unsupported LLM_PROVIDER: {provider}")

    api_key = os.getenv(key_name)
    if not api_key:
        raise RuntimeError(f"{key_name} must be set for LLM_PROVIDER={provider}")

    provider_info = _MODELS.get("providers", {}).get(provider, {})
    # TODO(VERIFY): Confirm live base URLs for nvidia, nebius, and gemini endpoints
    default_url = provider_info.get("base_url", "")
    base_url = os.getenv("LLM_BASE_URL", default_url)
    return AsyncOpenAICompatibleClient(provider, base_url, api_key)
