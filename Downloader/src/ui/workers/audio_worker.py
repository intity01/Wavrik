"""Background workers for Audio Tools analysis and pitch rendering."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PyQt6.QtCore import QObject, QRunnable, pyqtSignal

from src.services.audio_analysis import analyze_audio_file
from src.services.audio_pitch import render_audio_clip


class AudioToolSignals(QObject):
    analyzed = pyqtSignal(dict)
    rendered = pyqtSignal(str, bool)
    error = pyqtSignal(str)


@dataclass(frozen=True)
class PitchJob:
    source: Path
    target: Path
    semitones: int
    engine: str = "r3_finer"
    fmt: str = "wav"
    is_preview: bool = False
    tempo_ratio: float = 1.0
    start_sec: float = 0.0


class AnalyzeAudioWorker(QRunnable):
    def __init__(self, path: str | Path, signals: AudioToolSignals):
        super().__init__()
        self._path = Path(path)
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
            result = analyze_audio_file(self._path)
            if self._cancelled:
                return
            result["filePath"] = str(self._path)
            self._signals.analyzed.emit(result)
        except Exception as exc:
            if not self._cancelled:
                self._signals.error.emit(f"Analysis failed: {exc}")


class RenderPitchWorker(QRunnable):
    def __init__(self, job: PitchJob, signals: AudioToolSignals):
        super().__init__()
        self._job = job
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
            max_dur = 25.0 if self._job.is_preview else 0.0
            start = self._job.start_sec if self._job.is_preview else 0.0
            opts = (self._job.engine, self._job.fmt, self._job.tempo_ratio, max_dur, start)
            out = render_audio_clip(
                self._job.source, self._job.target, self._job.semitones, opts,
                cancel_check=lambda: self._cancelled,
            )
            if self._cancelled:
                return
            self._signals.rendered.emit(str(out), self._job.is_preview)
        except Exception as exc:
            if not self._cancelled:
                self._signals.error.emit(f"Pitch render failed: {exc}")
