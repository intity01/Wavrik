"""Small shared helpers for independent download sessions."""

from __future__ import annotations


class DownloadCancelled(Exception):
    """Raised from a progress hook to stop one job."""


def log_error(logger, message: str) -> None:
    if logger:
        logger.error(message)
