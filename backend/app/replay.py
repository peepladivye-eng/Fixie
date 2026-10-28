"""Replay stored JSONL event fixtures with their original cadence."""
from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Awaitable, Callable


def resolve_replay_path(source: str) -> Path:
    directory = Path(os.getenv("REPLAYS_DIR", Path(__file__).resolve().parents[2] / "replays")).resolve()

    # Prevent path traversal: only use basename
    clean_name = Path(source).name
    if clean_name.startswith("instance:"):
        clean_name = clean_name.removeprefix("instance:")

    candidates = [
        directory / clean_name,
        directory / f"{clean_name}.jsonl",
    ]
    if clean_name in ("sample", "sample_run", "run_20261028_parse_duration"):
        candidates.append(directory / "sample_run.jsonl")

    for candidate in candidates:
        try:
            resolved = candidate.resolve()
            if resolved.is_file() and resolved.parent == directory:
                return resolved
        except (ValueError, OSError):
            continue

    raise FileNotFoundError(f"Replay not found for source: '{source}' in {directory}")


def load_replay_events(source: str) -> list[dict[str, Any]]:
    path = resolve_replay_path(source)
    events: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            events.append(json.loads(line))
    return events


def _time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


async def run_replay(source: str, emit: Callable[[str, dict[str, Any]], Awaitable[None]], speed: float = 1.0) -> None:
    events = load_replay_events(source)
    multiplier = max(speed, 0.001)
    previous: datetime | None = None
    for event in events:
        current = _time(event["ts"])
        if previous is not None:
            delay = max(0.0, (current - previous).total_seconds() / multiplier)
            if delay > 0:
                await asyncio.sleep(delay)
        await emit(event["type"], event["data"])
        previous = current
