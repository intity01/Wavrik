"""Background worker for audio tag reads, online lookups, and tag writes."""

from __future__ import annotations

import logging
import subprocess
from collections.abc import Callable
from typing import Any

from PyQt6.QtCore import QObject, QRunnable, pyqtSignal

_LOG = logging.getLogger(__name__)
OP_LOAD, OP_DETECT, OP_APPLY = "load", "detect", "apply"
_ACTIONS = {OP_LOAD: "read the existing tags", OP_DETECT: "detect tags", OP_APPLY: "save the tags"}


class AudioTagSignals(QObject):
    succeeded = pyqtSignal(str, object)
    failed = pyqtSignal(str, str)


def describe_tag_error(operation: str, exc: BaseException) -> str:
    action = _ACTIONS.get(operation, "complete the operation")
    if isinstance(exc, FileNotFoundError):
        return f"Could not {action}: the audio file or FFmpeg was not found."
    if isinstance(exc, subprocess.TimeoutExpired):
        return f"Could not {action}: the operation timed out."
    return f"Could not {action}. Check that FFmpeg is installed and the file is writable."


class AudioTagWorker(QRunnable):
    def __init__(self, operation: str, task: Callable[[], Any], signals: AudioTagSignals):
        super().__init__()
        self._operation = operation
        self._task = task
        self._signals = signals
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    def is_cancelled(self) -> bool:
        return self._cancelled

    def run(self) -> None:
        if self._cancelled:
            return
        try:
            result = self._task()
        except Exception as exc:
            _LOG.warning("Audio tag %s failed", self._operation, exc_info=True)
            if not self._cancelled:
                self._signals.failed.emit(self._operation, describe_tag_error(self._operation, exc))
            return
        if not self._cancelled:
            self._signals.succeeded.emit(self._operation, result)
