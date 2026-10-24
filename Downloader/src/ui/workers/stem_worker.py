"""Background worker for Hybrid AI/DSP stem separation."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QObject, QRunnable, pyqtSignal

from src.services.audio_stems import separate_stems


class StemSignals(QObject):
    separated = pyqtSignal(str, str, str)
    error = pyqtSignal(str)


class StemSeparationWorker(QRunnable):
    def __init__(self, source: str | Path, output_dir: str | Path | None, mode: str, signals: StemSignals):
        super().__init__()
        self._source = Path(source)
        self._output_dir = Path(output_dir) if output_dir else None
        self._mode = mode
        self._signals = signals

    def run(self) -> None:
        try:
            res = separate_stems(self._source, self._output_dir, self._mode)
            self._signals.separated.emit(str(res.vocals_path), str(res.instrumental_path), res.mode_used)
        except Exception as exc:
            self._signals.error.emit(f"Stem separation failed: {exc}")
