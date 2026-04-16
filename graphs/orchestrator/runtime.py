from __future__ import annotations

import sqlite3

from langgraph.checkpoint.sqlite import SqliteSaver

from config.settings import Settings
from .supervisor import build_supervisor_graph


_graph = None
_conn = None


def get_graph():
    global _graph, _conn
    if _graph is None:
        _conn = sqlite3.connect(Settings.DB_PATH, check_same_thread=False)
        _graph = build_supervisor_graph(SqliteSaver(_conn))
    return _graph
