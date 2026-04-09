import logging
from pathlib import Path

from config.settings import Settings


log_dir = Path(Settings.LOG_DIR)
log_dir.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger("GameDev")
logger.setLevel(getattr(logging, Settings.LOG_LEVEL.upper(), logging.INFO))
logger.propagate = False

if not logger.handlers:
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] %(message)s",
            datefmt="%H:%M:%S",
        )
    )

    file_handler = logging.FileHandler(log_dir / "gamedev.log", encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s [%(levelname)s] %(name)s:%(funcName)s:%(lineno)d - %(message)s"
        )
    )

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
