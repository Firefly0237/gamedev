from __future__ import annotations

from pathlib import Path
from typing import Any

from config.settings import get_settings

try:
    from langgraph.checkpoint.sqlite import SqliteSaver
except Exception:  # pragma: no cover - optional dependency surface
    SqliteSaver = None  # type: ignore[assignment]


def create_checkpointer(db_path: Path | None = None) -> Any | None:
    if SqliteSaver is None:
        return None
    settings = get_settings()
    target = db_path or settings.checkpoint_file
    target.parent.mkdir(parents=True, exist_ok=True)
    return SqliteSaver.from_conn_string(str(target))
