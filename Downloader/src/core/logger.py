"""Application logging without duplicate handlers."""

from __future__ import annotations

import logging
import sys
from datetime import UTC, datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path


class Logger:
    """Small facade over Python logging."""

    def __init__(self, logDir: Path | None = None, logLevel: str = "INFO"):
        self.logDir = logDir or Path.home() / ".MediaDownloaderPRO" / "logs"
        self.logDir.mkdir(parents=True, exist_ok=True)
        self.logFile = self.logDir / f"mdpro_{datetime.now(UTC):%Y%m%d}.log"
        self.logger = logging.getLogger(f"MediaDownloaderPRO:{self.logDir}")
        self.logger.propagate = False
        self.setLevel(logLevel)
        if not self.logger.handlers:
            self._add_handlers()

    def _add_handlers(self) -> None:
        file_handler = RotatingFileHandler(
            self.logFile, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
        )
        file_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        self.logger.addHandler(file_handler)
        if sys.stdout is not None:
            stream_handler = logging.StreamHandler(sys.stdout)
            stream_handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
            self.logger.addHandler(stream_handler)

    def setLevel(self, level: str) -> None:
        self.logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    def debug(self, message: str, **kwargs) -> None:
        self.logger.debug(message, **kwargs)

    def info(self, message: str, **kwargs) -> None:
        self.logger.info(message, **kwargs)

    def success(self, message: str, **kwargs) -> None:
        self.logger.info(message, **kwargs)

    def warning(self, message: str, **kwargs) -> None:
        self.logger.warning(message, **kwargs)

    def error(self, message: str, exc_info: bool = False, **kwargs) -> None:
        self.logger.error(message, exc_info=exc_info, **kwargs)

    def critical(self, message: str, exc_info: bool = False, **kwargs) -> None:
        self.logger.critical(message, exc_info=exc_info, **kwargs)
