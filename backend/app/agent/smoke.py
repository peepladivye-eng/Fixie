from __future__ import annotations

import asyncio
import os

from app.llm import configured_client, max_tokens_for
from .runner import run_agent


async def _emit(event: str, data: dict) -> None:
    print(f"{event} {data}")


async def main() -> None:
    client = configured_client()
    print(f"provider={os.getenv('LLM_PROVIDER', 'fake')} model={getattr(client, 'model', 'configured')}")
    for role in ("triage", "reproduce", "diagnose", "patch"):
        print(f"role={role} max_tokens={max_tokens_for(role)}")
        if os.getenv("LLM_PROVIDER", "fake").lower() != "fake":
            result = client.chat(role, "Return the requested tiny JSON object.")
            print(f"model={result.model} input_tokens={result.input_tokens} output_tokens={result.output_tokens} latency_ms={result.latency_ms}")
    if os.getenv("SANDBOX_PROVIDER", "local").lower() == "local":
        await run_agent("fixture:parse_duration", _emit, {"k_branches": 1, "max_rounds": 1, "client": client})


if __name__ == "__main__":
    asyncio.run(main())
