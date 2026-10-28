"""SQLite persistence layer for runs and their event logs."""
from __future__ import annotations

import asyncio
import json
import os
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
                    finished_at TEXT,
                    issue_title TEXT,
                    repo TEXT,
                    total_cost_usd REAL DEFAULT 0.0,
                    total_seconds REAL DEFAULT 0.0
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
                """
                INSERT OR REPLACE INTO runs (
                    run_id, source, mode, status, created_at, finished_at,
                    issue_title, repo, total_cost_usd, total_seconds
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run["run_id"],
                    run["source"],
                    run["mode"],
                    run["status"],
                    run["created_at"],
                    run.get("finished_at"),
                    run.get("issue_title", ""),
                    run.get("repo", ""),
                    float(run.get("total_cost_usd", 0.0)),
                    float(run.get("total_seconds", 0.0)),
                ),
            )

    async def append_event(self, event: dict[str, Any]) -> None:
        await asyncio.to_thread(self._append_event, event)

    def _append_event(self, event: dict[str, Any]) -> None:
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO events (run_id, seq, ts, type, data_json) VALUES (?, ?, ?, ?, ?)",
                (event["run_id"], event["seq"], event["ts"], event["type"], json.dumps(event["data"])),
            )
            event_type = event["type"]
            data = event.get("data", {})
            if event_type == "run.started":
                connection.execute(
                    "UPDATE runs SET issue_title = ?, repo = ? WHERE run_id = ?",
                    (data.get("issue_title", ""), data.get("repo", ""), event["run_id"]),
                )
            elif event_type == "run.finished":
                connection.execute(
                    "UPDATE runs SET status = ?, finished_at = ?, total_cost_usd = ?, total_seconds = ? WHERE run_id = ?",
                    (
                        data.get("status", "failed"),
                        event["ts"],
                        float(data.get("total_cost_usd", 0.0)),
                        float(data.get("total_seconds", 0.0)),
                        event["run_id"],
                    ),
                )
            elif event_type == "run.error":
                connection.execute(
                    "UPDATE runs SET status = 'failed' WHERE run_id = ?",
                    (event["run_id"],),
                )

    async def get_run(self, run_id: str, include_events: bool = False) -> dict[str, Any] | None:
        return await asyncio.to_thread(self._get_run, run_id, include_events)

    def _get_run(self, run_id: str, include_events: bool = False) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM runs WHERE run_id = ?", (run_id,)).fetchone()
            if row is None:
                return None
            result = dict(row)
            result["id"] = result["run_id"]
            if include_events:
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
        replays_dir = Path(os.getenv("REPLAYS_DIR", Path(__file__).resolve().parents[2] / "replays"))
        showcase_path = replays_dir / "showcase.json"
        if showcase_path.is_file():
            try:
                return json.loads(showcase_path.read_text(encoding="utf-8"))
            except Exception:
                pass
        return []
