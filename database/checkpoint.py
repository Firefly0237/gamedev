import sqlite3

from config.logger import logger
from config.settings import Settings
from langgraph.checkpoint.sqlite import SqliteSaver


_checkpointer = None
_checkpoint_conn = None


def get_checkpointer() -> SqliteSaver:
    global _checkpointer, _checkpoint_conn

    if _checkpointer is None:
        _checkpoint_conn = sqlite3.connect(Settings.DB_PATH, check_same_thread=False)
        _checkpointer = SqliteSaver(_checkpoint_conn)
        logger.info("Checkpoint 初始化")

    return _checkpointer
