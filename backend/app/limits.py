"""SQLite-persisted daily live-run limiter and concurrency slot manager."""
from __future__ import annotations

import asyncio
import os
import sqlite3
from datetime import date
from pathlib import Path


class LiveRunLimiter:
    """Daily live-run limiter persisting counts across process restarts in SQLite."""

    def __init__(self, db_path: Path | str | None = None) -> None:
        if db_path is None:
            db_path = os.getenv("FIXIE_DB", str(Path(__file__).resolve().parents[1] / "fixie.db"))
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = asyncio.Lock()
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS live_run_limits (
                    day TEXT NOT NULL,
                    key TEXT NOT NULL,
                    count INTEGER NOT NULL,
                    PRIMARY KEY (day, key)
                );
                """
            )
            conn.commit()

    @staticmethod
    def _cap(name: str, default: int) -> int:
        try:
            return max(0, int(os.getenv(name, str(default))))
        except ValueError:
            return default

    async def reserve(self, ip: str) -> bool:
        async with self._lock:
            return await asyncio.to_thread(self._reserve_sync, ip)

    def _reserve_sync(self, ip: str) -> bool:
        today = date.today().isoformat()
        global_cap = self._cap("FIXIE_DAILY_LIVE_CAP", 25)
        ip_cap = self._cap("FIXIE_PER_IP_DAILY_LIVE_CAP", 5)

        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute("SELECT count FROM live_run_limits WHERE day = ? AND key = '__global__'", (today,))
            row_g = cur.fetchone()
            global_count = row_g[0] if row_g else 0

            cur.execute("SELECT count FROM live_run_limits WHERE day = ? AND key = ?", (today, ip))
            row_ip = cur.fetchone()
            ip_count = row_ip[0] if row_ip else 0

            if global_count >= global_cap or ip_count >= ip_cap:
                return False

            cur.execute(
                "INSERT INTO live_run_limits (day, key, count) VALUES (?, '__global__', 1) "
                "ON CONFLICT(day, key) DO UPDATE SET count = count + 1",
                (today,),
            )
            cur.execute(
                "INSERT INTO live_run_limits (day, key, count) VALUES (?, ?, 1) "
                "ON CONFLICT(day, key) DO UPDATE SET count = count + 1",
                (today, ip),
            )
            conn.commit()
            return True

    async def daily_runs_left(self) -> int:
        async with self._lock:
            return await asyncio.to_thread(self._daily_runs_left_sync)

    def _daily_runs_left_sync(self) -> int:
        today = date.today().isoformat()
        global_cap = self._cap("FIXIE_DAILY_LIVE_CAP", 25)
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute("SELECT count FROM live_run_limits WHERE day = ? AND key = '__global__'", (today,))
            row = cur.fetchone()
            global_count = row[0] if row else 0
            return max(0, global_cap - global_count)


class LiveRunSlots:
    """Process-local concurrency guard for live sandbox executions."""

    def __init__(self) -> None:
        self.active = 0
        self._lock = asyncio.Lock()

    async def acquire(self) -> bool:
        async with self._lock:
            try:
                maximum = max(1, int(os.getenv("FIXIE_MAX_CONCURRENT_LIVE", "2")))
            except ValueError:
                maximum = 2
            if self.active >= maximum:
                return False
            self.active += 1
            return True

    async def release(self) -> None:
        async with self._lock:
            self.active = max(0, self.active - 1)
