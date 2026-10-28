"""Run persistence and replay store backed by SQLite."""

import sqlite3
import json
from typing import List, Dict, Any, Optional
from pathlib import Path


class RunStore:
    """SQLite-backed persistence for runs and events."""

    def __init__(self, db_path: str = "fixie.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS runs (
                    id TEXT PRIMARY KEY,
                    source TEXT,
                    mode TEXT,
                    status TEXT,
                    issue_title TEXT,
                    repo TEXT,
                    total_cost_usd REAL,
                    total_seconds REAL,
                    created_at TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS events (
                    run_id TEXT,
                    seq INTEGER,
                    ts TEXT,
                    type TEXT,
                    data_json TEXT,
                    PRIMARY KEY (run_id, seq)
                )
                """
            )
            conn.commit()

    def save_run(self, run_meta: Dict[str, Any]) -> None:
        """Upsert run metadata."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO runs (id, source, mode, status, issue_title, repo, total_cost_usd, total_seconds, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_meta["id"],
                    run_meta.get("source", ""),
                    run_meta.get("mode", "replay"),
                    run_meta.get("status", "running"),
                    run_meta.get("issue_title", ""),
                    run_meta.get("repo", ""),
                    run_meta.get("total_cost_usd", 0.0),
                    run_meta.get("total_seconds", 0.0),
                    run_meta.get("created_at", ""),
                ),
            )
            conn.commit()

    def append_event(self, event: Dict[str, Any]) -> None:
        """Append an event to the run log."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO events (run_id, seq, ts, type, data_json)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    event["run_id"],
                    event["seq"],
                    event["ts"],
                    event["type"],
                    json.dumps(event["data"]),
                ),
            )
            conn.commit()

    def get_events(self, run_id: str, after_seq: Optional[int] = None) -> List[Dict[str, Any]]:
        """Retrieve events for a run ordered by sequence number."""
        with sqlite3.connect(self.db_path) as conn:
            query = "SELECT run_id, seq, ts, type, data_json FROM events WHERE run_id = ?"
            params: list[Any] = [run_id]
            if after_seq is not None:
                query += " AND seq > ?"
                params.append(after_seq)
            query += " ORDER BY seq ASC"
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()
            return [
                {
                    "run_id": r[0],
                    "seq": r[1],
                    "ts": r[2],
                    "type": r[3],
                    "data": json.loads(r[4]),
                }
                for r in rows
            ]
