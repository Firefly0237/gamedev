from __future__ import annotations

import logging
import sys
from datetime import datetime
from pathlib import Path

from config.settings import Settings


def _setup_logger(name: str = "GameDev") -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    Settings.ensure_dirs()

    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    console_level = getattr(logging, Settings.LOG_LEVEL.upper(), logging.INFO)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(console_level)
    console_handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s │ %(levelname)-7s │ %(message)s",
            datefmt="%H:%M:%S",
        )
    )

    log_date = datetime.now().strftime("%Y-%m-%d")
    log_file = Path(Settings.LOG_DIR) / f"gamedev_{log_date}.log"
    file_handler = logging.FileHandler(log_file, mode="a", encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s │ %(levelname)-7s │ %(name)s.%(funcName)s:%(lineno)d │ %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    logger.info("日志系统启动 | 级别=%s | 文件=%s", logging.getLevelName(console_level), log_file)
    return logger


logger = _setup_logger()
