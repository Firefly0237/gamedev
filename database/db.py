from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from config.settings import settings


@contextmanager
def get_connection(db_path: str | Path | None = None) -> Iterator[sqlite3.Connection]:
    target_path = Path(db_path or settings.db_path)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(target_path)
    connection.row_factory = sqlite3.Row
    try:
        yield connection
    finally:
        connection.close()


def init_db(db_path: str | Path | None = None) -> None:
    with get_connection(db_path) as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS execution_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pipeline_type TEXT NOT NULL,
                user_input TEXT NOT NULL,
                status TEXT NOT NULL,
                result_summary TEXT DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        connection.commit()


def save_execution_record(
    pipeline_type: str,
    user_input: str,
    status: str,
    result_summary: str = "",
    db_path: str | Path | None = None,
) -> int:
    init_db(db_path)
    with get_connection(db_path) as connection:
        cursor = connection.execute(
            """
            INSERT INTO execution_history (pipeline_type, user_input, status, result_summary)
            VALUES (?, ?, ?, ?)
            """,
            (pipeline_type, user_input, status, result_summary),
        )
        connection.commit()
        return int(cursor.lastrowid)


def list_execution_history(limit: int = 20, db_path: str | Path | None = None) -> list[dict]:
    init_db(db_path)
    with get_connection(db_path) as connection:
        rows = connection.execute(
            """
            SELECT id, pipeline_type, user_input, status, result_summary, created_at
            FROM execution_history
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    return [dict(row) for row in rows]
