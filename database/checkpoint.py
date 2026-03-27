from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from config.settings import settings


def init_checkpoint_db(db_path: str | Path | None = None) -> Path:
    target_path = Path(db_path or settings.checkpoint_db_path)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(target_path) as connection:
        connection.execute("PRAGMA journal_mode=WAL;")
    return target_path


def build_checkpoint_saver(db_path: str | Path | None = None) -> Any:
    try:
        from langgraph.checkpoint.sqlite import SqliteSaver
    except ImportError as exc:
        raise RuntimeError("请先安装 langgraph-checkpoint-sqlite。") from exc

    checkpoint_path = init_checkpoint_db(db_path)
    if hasattr(SqliteSaver, "from_conn_string"):
        return SqliteSaver.from_conn_string(str(checkpoint_path))
    if hasattr(SqliteSaver, "from_path"):
        return SqliteSaver.from_path(str(checkpoint_path))

    connection = sqlite3.connect(checkpoint_path, check_same_thread=False)
    return SqliteSaver(connection)
