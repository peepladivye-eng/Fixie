"""Owner-run smoke checks for configured LLM and ConTree providers.

Official references consulted:
  * https://github.com/nebius/contree-sdk (Quick Start, Client configuration,
    Sessions and Versioning). Client profile support and package version remain
    TODO(VERIFY) against the owner's installed SDK.
  * https://docs.nvidia.com/nim/large-language-models/1.10.0/reasoning-model.html
    (Reasoning Mode; system prompt).
  * https://catalog.ngc.nvidia.com/orgs/nim/nvidia/models/nemotron-3-super-120b-a12b
    (Nemotron 3 reasoning toggle; model serving docs, TODO(VERIFY) applicability
    to hosted API model IDs).
  * https://api.studio.nebius.ai/docs (OpenAI-compatible API; reasoning toggle
    TODO(VERIFY) for selected hosted models).
"""
from __future__ import annotations

import argparse
import asyncio
import os
import time
from dataclasses import dataclass
from typing import Any

import httpx


@dataclass
class Check:
    name: str
    passed: bool
    detail: str


CHECKS: list[Check] = []


def record(name: str, passed: bool, detail: str = "") -> None:
    CHECKS.append(Check(name, passed, detail))


def env_required(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Required environment variable {name} is not set")
    return value


def env_optional_key(name: str) -> str:
    """Empty placeholders allow setup before credentials have been issued."""
    return os.getenv(name, "").strip()


def provider_config(provider: str) -> tuple[str, str, dict[str, str]]:
    if provider == "nvidia":
        # TODO(VERIFY): endpoint and credential env var for NVIDIA hosted API.
        return (
            os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1"),
            env_optional_key("NVIDIA_API_KEY"),
            {},
        )
    if provider == "nebius":
        # TODO(VERIFY): confirm credential env var and endpoint for the owner's account.
        return (
            os.getenv("NEBIUS_BASE_URL", "https://api.tokenfactory.nebius.com/v1/"),
            env_optional_key("NEBIUS_API_KEY"),
            {},
        )
    if provider == "gemini":
        return (
            os.getenv("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai"),
            env_optional_key("GEMINI_API_KEY"),
            {},
        )
    raise ValueError("LLM_PROVIDER must be nvidia, nebius, or gemini")


async def request_json(
    client: httpx.AsyncClient, method: str, url: str, **kwargs: Any
) -> tuple[int, Any, str]:
    try:
        response = await client.request(method, url, **kwargs)
        response.raise_for_status()
        return response.status_code, response.json(), ""
    except httpx.HTTPStatusError as exc:
        return exc.response.status_code, None, exc.response.text
    except Exception as exc:  # Preserve provider/network error text verbatim.
        return 0, None, str(exc)


async def llm_checks(args: argparse.Namespace) -> None:
    provider = os.getenv("LLM_PROVIDER", "").lower()
    if provider not in {"nvidia", "nebius", "gemini"}:
        record("LLM configuration", False, "LLM_PROVIDER must be nvidia, nebius, or gemini")
        return
    try:
        base_url, api_key, extra_headers = provider_config(provider)
        base_url = base_url.rstrip("/")
    except Exception as exc:
        record("LLM configuration", False, str(exc))
        return

    if not api_key:
        record(f"{provider} API key", False, "credential is unset; set it in the process environment before owner run")
        print(f"{provider} API key is unset; model API checks skipped")
        return

    headers = {"Authorization": f"Bearer {api_key}", **extra_headers}
    models: list[str] = []
    async with httpx.AsyncClient(timeout=60.0, headers=headers) as client:
        status, payload, error = await request_json(client, "GET", f"{base_url}/models")
        if error:
            print(f"models error: {error}")
            record("list models", False, error)
        else:
            models = [item.get("id", "") for item in payload.get("data", [])]
            filtered = [model for model in models if "nemotron" in model.lower()]
            print("nemotron models:")
            for model in filtered:
                print(model)
            record("list models", True, f"HTTP {status}; {len(filtered)} Nemotron IDs")

        for label, model in (("lightning", args.lightning), ("super", args.super), ("ultra", args.ultra)):
            if not model:
                continue
            started = time.perf_counter()
            status, payload, error = await request_json(
                client,
                "POST",
                f"{base_url}/chat/completions",
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": "Reply with OK."}],
                    "max_tokens": 20,
                },
            )
            latency_ms = (time.perf_counter() - started) * 1000
            if error:
                print(f"model={model} input_tokens=? output_tokens=? latency_ms={latency_ms:.1f} error={error}")
                record(f"chat {label}", False, error)
                continue
            usage = payload.get("usage", {})
            print(
                f"model={model} input_tokens={usage.get('prompt_tokens', '?')} "
                f"output_tokens={usage.get('completion_tokens', '?')} latency_ms={latency_ms:.1f}"
            )
            record(f"chat {label}", True, f"HTTP {status}")

            # NVIDIA's published reasoning controls are model-specific; attempt
            # one documented off mode per supplied ID and report exact response.
            if provider == "nvidia":
                reasoning_args: dict[str, Any] = {
                    "model": model,
                    "messages": [
                        {"role": "system", "content": "detailed thinking off"},
                        {"role": "user", "content": "Reply with OK."},
                    ],
                    "max_tokens": 20,
                    "temperature": 0,
                }
                if "nemotron-3" in model.lower():
                    reasoning_args["extra_body"] = {"chat_template_kwargs": {"enable_thinking": False}}
                status, reasoning_payload, reasoning_error = await request_json(
                    client,
                    "POST",
                    f"{base_url}/chat/completions",
                    json=reasoning_args,
                )
                if reasoning_error:
                    print(f"reasoning_off model={model} error={reasoning_error}")
                    record(f"reasoning off {label}", False, reasoning_error)
                else:
                    print(f"reasoning_off model={model} response={reasoning_payload}")
                    record(f"reasoning off {label}", True, f"HTTP {status}")


async def contree_checks() -> None:
    try:
        from contree_client.httpx import ContreeAsyncClient
        from contree_sdk import Contree
    except Exception as exc:
        record("ConTree import", False, str(exc))
        return

    try:
        # TODO(VERIFY): SDK README profile auth behavior and token factory URL.
        client_context = ContreeAsyncClient.from_profile()
        async with client_context as api_client:
            contree = Contree(api_client)
            image = await contree.images.use("python:3.11-slim")
            result = await image.run(shell="python -V")
            print(f"python stdout={result.stdout}")
            image_id = getattr(result, "uuid", "TODO(VERIFY: result image id field)")
            print(f"image_id={image_id}")
            record("ConTree python image", getattr(result, "exit_code", 0) == 0, str(image_id))

            for name, command in (
                ("pip network", "pip download --no-deps --dest /tmp six"),
                ("git network", "git ls-remote https://github.com/pallets/click"),
            ):
                network_result = await result.run(shell=command)
                print(f"{name} exit_code={network_result.exit_code}")
                record(name, network_result.exit_code == 0, f"exit_code={network_result.exit_code}")

            try:
                branches = await asyncio.gather(
                    result.run(shell="python -c 'print(\"branch one\")'"),
                    result.run(shell="python -c 'print(\"branch two\")'"),
                    result.run(shell="python -c 'print(\"branch three\")'"),
                )
                for index, branch in enumerate(branches, 1):
                    print(f"fork_{index} id={getattr(branch, 'uuid', 'TODO(VERIFY)')} stdout={branch.stdout}")
                record("ConTree fork", True)
            except Exception as exc:
                print(f"fork exception: {exc}")
                record("ConTree fork", False, str(exc))
                sessions = [image.session() for _ in range(3)]
                session_results = await asyncio.gather(
                    *(session.run(shell=f"python -c 'print(\"session {i}\")'") for i, session in enumerate(sessions, 1)),
                    return_exceptions=True,
                )
                for index, session_result in enumerate(session_results, 1):
                    if isinstance(session_result, Exception):
                        print(f"session_{index} exception={session_result}")
                    else:
                        print(f"session_{index} id={getattr(session_result, 'uuid', 'TODO(VERIFY)')} stdout={session_result.stdout}")
                record("ConTree sessions fallback", not any(isinstance(item, Exception) for item in session_results))
    except Exception as exc:
        print(f"ConTree exception: {exc}")
        record("ConTree sandbox", False, str(exc))


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lightning")
    parser.add_argument("--super")
    parser.add_argument("--ultra")
    args = parser.parse_args()

    await llm_checks(args)
    sandbox_provider = os.getenv("SANDBOX_PROVIDER", "").lower()
    if sandbox_provider == "contree":
        await contree_checks()
    elif sandbox_provider == "none":
        record("ConTree sandbox", True, "skipped by SANDBOX_PROVIDER=none")
    else:
        record("SANDBOX_PROVIDER", False, "must be contree or none")

    print("\nCHECK | RESULT | DETAIL")
    for check in CHECKS:
        print(f"{check.name} | {'PASS' if check.passed else 'FAIL'} | {check.detail}")


if __name__ == "__main__":
    asyncio.run(main())
