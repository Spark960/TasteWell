"""SQLite snapshots for operator decisions; no credential or raw envelope storage."""

from __future__ import annotations

import sqlite3
from contextlib import closing
from pathlib import Path

from app.api.decisions import DecisionResult


DEFAULT_DB = Path(__file__).resolve().parents[2] / "data" / "decisions.sqlite"


class DecisionStore:
    def __init__(self, path: Path = DEFAULT_DB) -> None:
        self.path = path

    def _connect(self) -> sqlite3.Connection:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.path, timeout=5)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("""CREATE TABLE IF NOT EXISTS decisions (
            id TEXT PRIMARY KEY,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            document TEXT NOT NULL
        )""")
        return conn

    def save(self, result: DecisionResult) -> None:
        with closing(self._connect()) as conn:
            with conn:
                conn.execute("""INSERT INTO decisions (id, created_at, updated_at, document)
                    VALUES (?, ?, ?, ?) ON CONFLICT(id) DO UPDATE SET
                    updated_at=excluded.updated_at, document=excluded.document""",
                    (result.id, result.created_at, result.updated_at,
                     result.model_dump_json()))

    def get(self, decision_id: str) -> DecisionResult | None:
        with closing(self._connect()) as conn:
            row = conn.execute("SELECT document FROM decisions WHERE id=?",
                               (decision_id,)).fetchone()
        return DecisionResult.model_validate_json(row[0]) if row else None

    def list_recent(self, limit: int = 30) -> list[dict]:
        with closing(self._connect()) as conn:
            rows = conn.execute(
                "SELECT document FROM decisions ORDER BY updated_at DESC LIMIT ?",
                (min(max(limit, 1), 100),),
            ).fetchall()
        return [
            {
                "id": item.id,
                "venue_name": item.request.venue_name,
                "concept": item.request.concept,
                "region": item.request.region,
                "status": item.status,
                "source_mode": item.source_mode,
                "selected_option_id": item.selected_option_id,
                "has_outcome": item.outcome is not None,
                "updated_at": item.updated_at,
            }
            for row in rows
            if (item := DecisionResult.model_validate_json(row[0]))
        ]
