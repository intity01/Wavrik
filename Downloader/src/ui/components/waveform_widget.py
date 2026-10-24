"""Waveform mini-visualizer with normalized dynamic bars and elided section boundary."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont, QFontMetrics, QPainter, QPen
from PyQt6.QtWidgets import QWidget

from src.ui.theme.tokens import ACCENT, DARK


class WaveformWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("WaveformWidget")
        self.setFixedHeight(76)
        self._peaks: list[float] = []
        self._duration_sec: float = 0.0
        self._section_text: str = ""

    def setPeaks(self, peaks: list[float], duration_sec: float = 0.0, section_text: str = "") -> None:
        raw = [max(0.0, float(p)) for p in peaks]
        top = max(raw, default=0.0)
        self._peaks = [max(0.06, min(1.0, p / top if top > 1e-6 else p)) for p in raw]
        self._duration_sec = max(0.0, float(duration_sec))
        self._section_text = section_text
        self.update()

    def clear(self) -> None:
        self._peaks, self._duration_sec, self._section_text = [], 0.0, ""
        self.update()

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        _draw_background(painter, w, h)
        if not self._peaks:
            _draw_empty_state(painter, w, h)
            return
        _draw_bars(painter, self._peaks, w, h)
        _draw_midpoint(painter, w, h, self._section_text)
        _draw_time_markers(painter, w, h, self._duration_sec)


def _draw_background(painter: QPainter, w: int, h: int) -> None:
    painter.fillRect(0, 0, w, h, QColor(DARK["bg"]))
    painter.setPen(QPen(QColor(DARK["border"]), 1))
    painter.drawRoundedRect(0, 0, w - 1, h - 1, 5, 5)


def _draw_empty_state(painter: QPainter, w: int, h: int) -> None:
    painter.setPen(QColor(DARK["text_subtle"]))
    painter.setFont(QFont("Segoe UI", 8))
    painter.drawText(0, 0, w, h, Qt.AlignmentFlag.AlignCenter, "Waveform preview loads on analysis")


def _draw_bars(painter: QPainter, peaks: list[float], w: int, h: int) -> None:
    n = len(peaks)
    bar_width = max(2.0, (w - 16) / max(1, n))
    c1, c2 = QColor(ACCENT), QColor(DARK["text_muted"])
    for i, p in enumerate(peaks):
        x = 8 + i * bar_width
        bar_h = max(3.0, p * (h - 24))
        y = (h / 2.0) - (bar_h / 2.0) + 2
        painter.fillRect(int(x), int(y), max(1, int(bar_width - 1.5)), int(bar_h), c1 if i < n // 2 else c2)


def _draw_midpoint(painter: QPainter, w: int, h: int, label: str) -> None:
    mid = w // 2
    painter.setPen(QPen(QColor(DARK["warning"]), 1, Qt.PenStyle.DashLine))
    painter.drawLine(mid, 4, mid, h - 4)
    font = QFont("Segoe UI", 7, QFont.Weight.Bold)
    painter.setFont(font)
    painter.setPen(QColor(DARK["warning"]))
    avail = max(40, (w - mid) - 10)
    elided = QFontMetrics(font).elidedText(label or "1st Half | 2nd Half", Qt.TextElideMode.ElideRight, avail)
    painter.drawText(mid + 5, 13, elided)


def _draw_time_markers(painter: QPainter, w: int, h: int, duration: float) -> None:
    if duration <= 0:
        return
    painter.setFont(QFont("Consolas", 7))
    painter.setPen(QColor(DARK["text_muted"]))
    painter.drawText(8, h - 5, "0:00")
    mins, secs = int(duration // 60), int(duration % 60)
    painter.drawText(w - 36, h - 5, f"{mins}:{secs:02d}")
