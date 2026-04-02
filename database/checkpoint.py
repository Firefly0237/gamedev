from __future__ import annotations

import sqlite3

from langgraph.checkpoint.sqlite import SqliteSaver

from config.logger import logger
from config.settings import Settings


_checkpointer: SqliteSaver | None = None


def get_checkpointer() -> SqliteSaver:
    """
    Usage:
        graph = build_xxx_graph()
        compiled = graph.compile(checkpointer=get_checkpointer())
        result = compiled.invoke(
            state,
            config={"configurable": {"thread_id": "task_42"}},
        )
    """

    global _checkpointer

    if _checkpointer is None:
        conn = sqlite3.connect(str(Settings.DB_PATH), check_same_thread=False)
        _checkpointer = SqliteSaver(conn)
        logger.info("LangGraph Checkpointer 初始化完成 | DB=%s", Settings.DB_PATH)

    return _checkpointer
