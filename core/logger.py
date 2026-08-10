"""Centralized Logging Module for Video-Post framework."""
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from config import settings

LOGS_DIR = Path(settings.LOGS_DIR)
LOGS_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE_PATH = LOGS_DIR / "video_post.log"


def setup_logger(name: str = "video_post", level: str = settings.LOG_LEVEL) -> logging.Logger:
    """Setup and return a centralized logger instance with file and console handlers."""
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    if not logger.handlers:
        # File Handler with rotation (10MB max, 5 backups)
        file_handler = RotatingFileHandler(
            LOG_FILE_PATH, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
        )
        file_formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

        # Console Handler
        console_handler = logging.StreamHandler()
        console_formatter = logging.Formatter("[%(levelname)s] %(message)s")
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)

    return logger


logger = setup_logger()
