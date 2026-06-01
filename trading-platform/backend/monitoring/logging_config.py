import json
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
LOG_DIR = PROJECT_ROOT / "logs"
PLATFORM_LOG = LOG_DIR / "platform.log"
LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


class MetadataFormatter(logging.Formatter):
    """Format log records with optional metadata appended as JSON."""

    def format(self, record: logging.LogRecord) -> str:
        message = super().format(record)
        metadata = getattr(record, "metadata", None)
        if metadata:
            try:
                message = f"{message} | metadata={json.dumps(metadata, default=str, sort_keys=True)}"
            except Exception:
                message = f"{message} | metadata={metadata}"
        return message


def configure_logging(level: int = logging.INFO) -> logging.Logger:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("platform")
    logger.setLevel(level)
    logger.propagate = False

    formatter = MetadataFormatter(fmt=LOG_FORMAT, datefmt=DATE_FORMAT)
    existing_types = {type(handler) for handler in logger.handlers}

    if logging.StreamHandler not in existing_types:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    if RotatingFileHandler not in existing_types:
        file_handler = RotatingFileHandler(
            PLATFORM_LOG,
            maxBytes=10 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def log_with_metadata(logger: logging.Logger, level: int, message: str, metadata: dict[str, Any] | None = None) -> None:
    logger.log(level, message, extra={"metadata": metadata or {}})
