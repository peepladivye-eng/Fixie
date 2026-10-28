"""In-memory, per-process daily live-run limits. Replay is intentionally unlimited."""
from __future__ import annotations

import asyncio
import os
from collections import defaultdict
from datetime import date


class LiveRunLimiter:
    def __init__(self) -> None:
        self._day = date.today()
        self._global = 0
        self._per_ip: dict[str, int] = defaultdict(int)
        self._lock = asyncio.Lock()

    @staticmethod
    def _cap(name: str, default: int) -> int:
        try:
            return max(0, int(os.getenv(name, str(default))))
        except ValueError:
            return default

    async def reserve(self, ip: str) -> bool:
        async with self._lock:
            if self._day != date.today():
                self._day, self._global, self._per_ip = date.today(), 0, defaultdict(int)
            global_cap = self._cap("FIXIE_DAILY_LIVE_CAP", 25)
            ip_cap = self._cap("FIXIE_PER_IP_DAILY_LIVE_CAP", 5)
            if self._global >= global_cap or self._per_ip[ip] >= ip_cap:
                return False
            self._global += 1
            self._per_ip[ip] += 1
            return True

    async def daily_runs_left(self) -> int:
        async with self._lock:
            if self._day != date.today():
                self._day, self._global, self._per_ip = date.today(), 0, defaultdict(int)
            return max(0, self._cap("FIXIE_DAILY_LIVE_CAP", 25) - self._global)
