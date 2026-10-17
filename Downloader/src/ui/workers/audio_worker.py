"""Background workers for Audio Tools analysis and pitch rendering."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PyQt6.QtCore import QObject, QRunnable, pyqtSignal

from src.services.audio_analysis import analyze_audio_file
from src.services.audio_pitch import render_pitch_shift


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


class AnalyzeAudioWorker(QRunnable):
    def __init__(self, path: str | Path, signals: AudioToolSignals):
        super().__init__()
        self._path = Path(path)
        self._signals = signals

    def run(self) -> None:
        try:
            result = analyze_audio_file(self._path)
            result["filePath"] = str(self._path)
            self._signals.analyzed.emit(result)
        except Exception as exc:
            self._signals.error.emit(f"Analysis failed: {exc}")


class RenderPitchWorker(QRunnable):
    def __init__(self, job: PitchJob, signals: AudioToolSignals):
        super().__init__()
        self._job = job
        self._signals = signals

    def run(self) -> None:
        try:
            out = render_pitch_shift(
                self._job.source,
                self._job.target,
                self._job.semitones,
                self._job.engine,
                self._job.fmt,
                self._job.tempo_ratio,
            )
            self._signals.rendered.emit(str(out), self._job.is_preview)
        except Exception as exc:
            self._signals.error.emit(f"Pitch render failed: {exc}")
