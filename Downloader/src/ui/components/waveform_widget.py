"""Interactive waveform visualizer with spectrogram, beat grid, and seek playhead."""

from __future__ import annotations

import numpy as np
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPainter
from PyQt6.QtWidgets import QApplication, QWidget

from src.services.audio_beat_grid import compute_beat_grid, get_adaptive_grid_markers
from src.ui.components.waveform_renderers import (
    draw_background,
    draw_bars,
    draw_beat_grid,
    draw_empty_state,
    draw_midpoint,
    draw_playhead,
    draw_spectrogram,
    draw_time_markers,
)
from src.ui.theme.key_colors import key_hue
from src.ui.theme.tokens import key_tint, palette


class WaveformWidget(QWidget):
    seekRequested = pyqtSignal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("WaveformWidget")
        self.setFixedHeight(78)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._peaks: list[float] = []
        self._duration_sec: float = 0.0
        self._seek_sec: float = 0.0
        self._section_text: str = ""
        self._camelot: str = ""
        self._spectrogram: np.ndarray | None = None
        self._beat_grid: dict | None = None

    def setPeaks(self, peaks: list[float], duration_sec: float = 0.0, section_text: str = "") -> None:
        raw = [max(0.0, float(p)) for p in peaks]
        top = max(raw, default=0.0)
        self._peaks = [max(0.06, min(1.0, p / top if top > 1e-6 else p)) for p in raw]
        self._duration_sec = max(0.0, float(duration_sec))
        self._seek_sec = min(self._seek_sec, max(0.0, self._duration_sec - 1.0)) if self._duration_sec > 0 else 0.0
        self._section_text = section_text
        self.update()

    def setSpectrogram(self, spec: np.ndarray | None) -> None:
        self._spectrogram = spec
        self.update()

    def setBeatGrid(self, grid: dict | None) -> None:
        self._beat_grid = grid
        self.update()

    def setBpm(self, bpm: float) -> None:
        if self._duration_sec > 0.0:
            first_beat = float(self._beat_grid.get("first_beat_sec", 0.0)) if self._beat_grid else 0.0
            self._beat_grid = compute_beat_grid(bpm, self._duration_sec, first_beat)
            self.update()

    def beatGrid(self) -> dict | None:
        return self._beat_grid

    def setKeyCamelot(self, camelot: str) -> None:
        """Color the played part of the waveform with the hue of the track's Camelot key."""
        self._camelot = camelot or ""
        self.update()

    def setSeekPosition(self, sec: float) -> None:
        self._seek_sec = max(0.0, min(sec, max(0.0, self._duration_sec)))
        self.update()

    def seekPosition(self) -> float:
        return self._seek_sec

    def clear(self) -> None:
        self._peaks, self._duration_sec, self._seek_sec, self._section_text = [], 0.0, 0.0, ""
        self._spectrogram, self._beat_grid = None, None
        self.update()

    def mousePressEvent(self, event) -> None:
        if self._duration_sec > 0 and event.button() == Qt.MouseButton.LeftButton:
            ratio = max(0.0, min(1.0, (event.position().x() - 8.0) / max(1.0, self.width() - 16.0)))
            self._seek_sec = round(ratio * self._duration_sec, 1)
            self.update()
            self.seekRequested.emit(self._seek_sec)

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h, tokens = self.width(), self.height(), _tokens()
        draw_background(painter, w, h, tokens)
        if not self._peaks and (self._spectrogram is None or self._spectrogram.size == 0):
            draw_empty_state(painter, w, h, tokens)
            return
        if self._spectrogram is not None and self._spectrogram.size > 0:
            draw_spectrogram(painter, self._spectrogram, w, h, tokens)
        if self._beat_grid is not None and self._duration_sec > 0.0:
            markers = get_adaptive_grid_markers(self._beat_grid, w - 16, self._duration_sec)
            draw_beat_grid(painter, markers, self._duration_sec, w, h, tokens)
        if self._peaks:
            played = key_hue(self._camelot, tokens["accent"])
            unplayed = key_tint(played, _theme()) if self._camelot else tokens["border_strong"]
            draw_bars(painter, (self._peaks, self._played_count(), played, unplayed), w, h)
        draw_midpoint(painter, w, h, (self._section_text, tokens))
        draw_playhead(painter, w, h, (self._seek_sec, self._duration_sec), tokens)
        draw_time_markers(painter, w, h, self._duration_sec, tokens)

    def _played_count(self) -> int:
        if self._duration_sec <= 0:
            return len(self._peaks) // 2
        return int(len(self._peaks) * self._seek_sec / self._duration_sec)


def _theme() -> str:
    app = QApplication.instance()
    return str(app.property("appTheme") or "light") if app else "light"


def _tokens() -> dict[str, str]:
    return palette(_theme())
