"""Background worker for Hybrid AI/DSP stem separation."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import QObject, QRunnable, pyqtSignal

from src.services.audio_stems import separate_stems
from src.services.audio_stems_4stem import separate_4stems


class StemSignals(QObject):
    separated = pyqtSignal(str, str, str)
    error = pyqtSignal(str)


class Stem4Signals(QObject):
    separated = pyqtSignal(str, str, str, str, str)
    error = pyqtSignal(str)


class StemSeparationWorker(QRunnable):
    def __init__(self, source: str | Path, output_dir: str | Path | None, mode: str, signals: StemSignals):
        super().__init__()
        self._source = Path(source)
        self._output_dir = Path(output_dir) if output_dir else None
        self._mode = mode
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
            res = separate_stems(self._source, self._output_dir, self._mode, cancel_check=lambda: self._cancelled)
            if self._cancelled:
                return
            self._signals.separated.emit(str(res.vocals_path), str(res.instrumental_path), res.mode_used)
        except Exception as exc:
            if not self._cancelled:
                self._signals.error.emit(f"Stem separation failed: {exc}")


class Stem4SeparationWorker(QRunnable):
    def __init__(self, source: str | Path, output_dir: str | Path | None, mode: str, signals: Stem4Signals):
        super().__init__()
        self._source = Path(source)
        self._output_dir = Path(output_dir) if output_dir else None
        self._mode = mode
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
            res = separate_4stems(self._source, self._output_dir, self._mode, cancel_check=lambda: self._cancelled)
            if self._cancelled:
                return
            self._signals.separated.emit(
                str(res.vocals_path),
                str(res.drums_path),
                str(res.bass_path),
                str(res.other_path),
                res.mode_used,
            )
        except Exception as exc:
            if not self._cancelled:
                self._signals.error.emit(f"4-stem separation failed: {exc}")
