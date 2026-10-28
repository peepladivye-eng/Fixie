"""Replay stored JSONL event fixtures with their original cadence."""
from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Awaitable, Callable

_SAMPLE = [
    {"ts": "2026-01-01T00:00:00+00:00", "type": "run.started", "data": {"issue_title": "Replay sample", "repo": "fixie/demo", "mode": "replay"}},
    {"ts": "2026-01-01T00:00:00.020000+00:00", "type": "step.started", "data": {"step": "triage", "model_tier": "none"}},
    {"ts": "2026-01-01T00:00:00.040000+00:00", "type": "step.finished", "data": {"step": "triage", "duration_ms": 20, "ok": True}},
    {"ts": "2026-01-01T00:00:00.060000+00:00", "type": "run.finished", "data": {"status": "success", "total_cost_usd": 0.0, "total_seconds": 0.06}},
]


def _load(source: str) -> list[dict[str, Any]]:
    directory = Path(os.getenv("REPLAYS_DIR", Path(__file__).resolve().parents[2] / "replays"))
    candidate = directory / Path(source).name
    if not candidate.is_file():
        return _SAMPLE
    events: list[dict[str, Any]] = []
    for line in candidate.read_text(encoding="utf-8").splitlines():
        if line.strip():
            events.append(json.loads(line))
    return events or _SAMPLE


def _time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


async def run_replay(source: str, emit: Callable[[str, dict[str, Any]], Awaitable[None]], speed: float = 1.0) -> None:
    events = _load(source)
    multiplier = max(speed, 0.001)
    previous: datetime | None = None
    for event in events:
        current = _time(event["ts"])
        if previous is not None:
            await asyncio.sleep(max(0.0, (current - previous).total_seconds() / multiplier))
        await emit(event["type"], event["data"])
        previous = current
