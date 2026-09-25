"""Background workers for GitHub update checks and downloads."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QObject, QRunnable, pyqtSignal

from src.core.updater import UpdateError


class UpdateSignals(QObject):
    checked = pyqtSignal(object)
    downloaded = pyqtSignal(str)
    progress = pyqtSignal(int)
    error = pyqtSignal(str)


class CheckUpdateWorker(QRunnable):
    def __init__(self, manager, signals: UpdateSignals):
        super().__init__()
        self._manager = manager
        self._signals = signals

    def run(self) -> None:
        try:
            self._signals.checked.emit(self._manager.checkForUpdates())
        except UpdateError as exc:
            self._signals.error.emit(str(exc))


class DownloadUpdateWorker(QRunnable):
    def __init__(self, manager, info, output_dir: Path, signals: UpdateSignals):
        super().__init__()
        self._manager = manager
        self._info = info
        self._outputDir = output_dir
        self._signals = signals

    def run(self) -> None:
        try:
            path = self._manager.downloadVerified(
                self._info,
                self._outputDir,
                self._signals.progress.emit,
            )
            self._signals.downloaded.emit(str(path))
        except UpdateError as exc:
            self._signals.error.emit(str(exc))
