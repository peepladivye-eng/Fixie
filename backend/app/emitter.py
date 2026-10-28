"""Event-envelope creation, persistence and SSE fan-out."""
from __future__ import annotations

import asyncio
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, AsyncIterator

from .store import RunStore


class EventEmitter:
    def __init__(self, store: RunStore, run_id: str) -> None:
        self.store = store
        self.run_id = run_id
        self._seq = -1
        self._subscribers: set[asyncio.Queue[dict[str, Any]]] = set()
        self._lock = asyncio.Lock()

    async def initialize(self) -> None:
        prior = await self.store.events_after(self.run_id, -1)
        self._seq = prior[-1]["seq"] if prior else -1

    async def emit(self, event_type: str, data: dict[str, Any]) -> None:
        async with self._lock:
            self._seq += 1
            event = {
                "run_id": self.run_id,
                "seq": self._seq,
                "ts": datetime.now(timezone.utc).isoformat(),
                "type": event_type,
                "data": data,
            }
            await self.store.append_event(event)
            for subscriber in tuple(self._subscribers):
                subscriber.put_nowait(event)

    async def subscribe(self, last_seq: int) -> AsyncIterator[dict[str, Any]]:
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        async with self._lock:
            buffered = await self.store.events_after(self.run_id, last_seq)
            self._subscribers.add(queue)
        try:
            for event in buffered:
                yield event
            while True:
                yield await queue.get()
        finally:
            self._subscribers.discard(queue)
