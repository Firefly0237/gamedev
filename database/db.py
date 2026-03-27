from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from config.settings import get_settings


SCHEMA = """
CREATE TABLE IF NOT EXISTS task_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_type TEXT NOT NULL,
    status TEXT NOT NULL,
    input_payload TEXT NOT NULL,
    output_payload TEXT,
    execution_trace TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS project_context (
    project_root TEXT PRIMARY KEY,
    payload TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS pipeline_feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pipeline_name TEXT NOT NULL,
    status TEXT NOT NULL,
    feedback TEXT,
    metadata TEXT,
    created_at TEXT NOT NULL
);
"""


@dataclass(slots=True)
class TaskLogRecord:
    task_type: str
    status: str
    input_payload: dict[str, Any]
    output_payload: dict[str, Any] | None = None
    execution_trace: list[dict[str, Any]] | None = None


class DatabaseManager:
    def __init__(self, db_path: Path | None = None) -> None:
        self.db_path = db_path or get_settings().database_file
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_db()

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def init_db(self) -> None:
        with self.connection() as conn:
            conn.executescript(SCHEMA)

    def log_task(self, record: TaskLogRecord) -> int:
        now = datetime.now(timezone.utc).isoformat()
        with self.connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO task_logs (task_type, status, input_payload, output_payload, execution_trace, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    record.task_type,
                    record.status,
                    json.dumps(record.input_payload, ensure_ascii=False),
                    json.dumps(record.output_payload, ensure_ascii=False) if record.output_payload is not None else None,
                    json.dumps(record.execution_trace, ensure_ascii=False) if record.execution_trace is not None else None,
                    now,
                ),
            )
            return int(cursor.lastrowid)

    def list_recent_tasks(self, limit: int = 20) -> list[dict[str, Any]]:
        with self.connection() as conn:
            rows = conn.execute(
                "SELECT * FROM task_logs ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]

    def save_project_context(self, project_root: str, payload: dict[str, Any]) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self.connection() as conn:
            conn.execute(
                """
                INSERT INTO project_context (project_root, payload, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(project_root) DO UPDATE SET
                    payload = excluded.payload,
                    updated_at = excluded.updated_at
                """,
                (project_root, json.dumps(payload, ensure_ascii=False), now),
            )

    def get_project_context(self, project_root: str) -> dict[str, Any] | None:
        with self.connection() as conn:
            row = conn.execute(
                "SELECT payload FROM project_context WHERE project_root = ?",
                (project_root,),
            ).fetchone()
        if not row:
            return None
        return json.loads(row["payload"])

    def save_feedback(
        self,
        pipeline_name: str,
        status: str,
        feedback: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self.connection() as conn:
            conn.execute(
                """
                INSERT INTO pipeline_feedback (pipeline_name, status, feedback, metadata, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    pipeline_name,
                    status,
                    feedback,
                    json.dumps(metadata, ensure_ascii=False) if metadata else None,
                    now,
                ),
            )
