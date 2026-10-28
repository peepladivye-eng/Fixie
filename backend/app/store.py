"""Small SQLite persistence layer for runs and their event logs."""
from __future__ import annotations

import asyncio
import json
import sqlite3
from pathlib import Path
from typing import Any


class RunStore:
    def __init__(self, database_path: str | Path) -> None:
        self.path = Path(database_path)

    async def initialize(self) -> None:
        await asyncio.to_thread(self._initialize)

    def _connect(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS runs (
                    run_id TEXT PRIMARY KEY,
                    source TEXT NOT NULL,
                    mode TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    finished_at TEXT
                );
                CREATE TABLE IF NOT EXISTS events (
                    run_id TEXT NOT NULL,
                    seq INTEGER NOT NULL,
                    ts TEXT NOT NULL,
                    type TEXT NOT NULL,
                    data_json TEXT NOT NULL,
                    PRIMARY KEY (run_id, seq),
                    FOREIGN KEY (run_id) REFERENCES runs(run_id)
                );
                CREATE INDEX IF NOT EXISTS idx_events_run_seq ON events(run_id, seq);
                """
            )

    async def create_run(self, run: dict[str, Any]) -> None:
        await asyncio.to_thread(self._create_run, run)

    def _create_run(self, run: dict[str, Any]) -> None:
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO runs (run_id, source, mode, status, created_at) VALUES (?, ?, ?, ?, ?)",
                (run["run_id"], run["source"], run["mode"], run["status"], run["created_at"]),
            )

    async def append_event(self, event: dict[str, Any]) -> None:
        await asyncio.to_thread(self._append_event, event)

    def _append_event(self, event: dict[str, Any]) -> None:
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO events (run_id, seq, ts, type, data_json) VALUES (?, ?, ?, ?, ?)",
                (event["run_id"], event["seq"], event["ts"], event["type"], json.dumps(event["data"])),
            )
            if event["type"] == "run.finished":
                connection.execute(
                    "UPDATE runs SET status = ?, finished_at = ? WHERE run_id = ?",
                    (event["data"].get("status", "failed"), event["ts"], event["run_id"]),
                )

    async def get_run(self, run_id: str) -> dict[str, Any] | None:
        return await asyncio.to_thread(self._get_run, run_id)

    def _get_run(self, run_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM runs WHERE run_id = ?", (run_id,)).fetchone()
            if row is None:
                return None
            result = dict(row)
            result["events"] = self._events(connection, run_id, -1)
            return result

    async def events_after(self, run_id: str, after_seq: int) -> list[dict[str, Any]]:
        return await asyncio.to_thread(self._events_after, run_id, after_seq)

    def _events_after(self, run_id: str, after_seq: int) -> list[dict[str, Any]]:
        with self._connect() as connection:
            return self._events(connection, run_id, after_seq)

    @staticmethod
    def _events(connection: sqlite3.Connection, run_id: str, after_seq: int) -> list[dict[str, Any]]:
        rows = connection.execute(
            "SELECT run_id, seq, ts, type, data_json FROM events WHERE run_id = ? AND seq > ? ORDER BY seq",
            (run_id, after_seq),
        ).fetchall()
        return [
            {
                "run_id": row["run_id"],
                "seq": row["seq"],
                "ts": row["ts"],
                "type": row["type"],
                "data": json.loads(row["data_json"]),
            }
            for row in rows
        ]

    async def showcase(self) -> list[dict[str, Any]]:
        return await asyncio.to_thread(self._showcase)

    def _showcase(self) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT run_id, source, mode, status, created_at, finished_at FROM runs "
                "WHERE mode = 'replay' AND status = 'success' ORDER BY created_at DESC"
            ).fetchall()
            return [dict(row) for row in rows]
