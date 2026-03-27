from __future__ import annotations

import logging
from pathlib import Path

from config.settings import get_settings


def configure_logging() -> None:
    settings = get_settings()
    log_file = Path(settings.logs_dir) / "gamedev.log"
    if logging.getLogger().handlers:
        return
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )


def get_logger(name: str) -> logging.Logger:
    configure_logging()
    return logging.getLogger(name)
