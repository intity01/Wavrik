"""Background worker for batch audio processing."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QObject, QRunnable, pyqtSignal

from src.services.audio_batch import BatchJobConfig, process_batch_file


class BatchAudioSignals(QObject):
    itemProcessed = pyqtSignal(int, int, str)
    finished = pyqtSignal(int, int)
    error = pyqtSignal(str)


class BatchAudioWorker(QRunnable):
    def __init__(self, sources: list[Path], cfg: BatchJobConfig, signals: BatchAudioSignals, keys: dict[str, str] | None = None):
        super().__init__()
        self._sources = list(sources)
        self._cfg = cfg
        self._signals = signals
        self._keys = keys or {}
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    def run(self) -> None:
        total = len(self._sources)
        succeeded, failed = 0, 0
        for idx, src in enumerate(self._sources):
            if self._cancelled:
                break
            try:
                known_key = self._keys.get(str(src), "C major")
                process_batch_file(src, self._cfg, known_key)
                succeeded += 1
                self._signals.itemProcessed.emit(idx + 1, total, src.name)
            except Exception as exc:
                failed += 1
                self._signals.error.emit(f"Failed {src.name}: {exc}")
        self._signals.finished.emit(succeeded, failed)
