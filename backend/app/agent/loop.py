"""Agent loop orchestration stub. Full implementation in B2."""
from __future__ import annotations

from typing import Any, Awaitable, Callable

Emit = Callable[[str, dict[str, Any]], Awaitable[None]]


async def run_agent_loop(
    source: str,
    emit: Emit,
    options: dict[str, Any] | None = None,
) -> None:
    """Agent loop entry point. Stub implementation raising NotImplementedError until B2."""
    raise NotImplementedError("run_agent_loop is implemented in Stage 3 (B2)")
