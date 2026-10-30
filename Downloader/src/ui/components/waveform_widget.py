"""Interactive waveform visualizer with click-to-seek playhead and normalized bars."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QFontMetrics, QPainter, QPen
from PyQt6.QtWidgets import QApplication, QWidget

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

    def setPeaks(self, peaks: list[float], duration_sec: float = 0.0, section_text: str = "") -> None:
        raw = [max(0.0, float(p)) for p in peaks]
        top = max(raw, default=0.0)
        self._peaks = [max(0.06, min(1.0, p / top if top > 1e-6 else p)) for p in raw]
        self._duration_sec = max(0.0, float(duration_sec))
        self._seek_sec = min(self._seek_sec, max(0.0, self._duration_sec - 1.0)) if self._duration_sec > 0 else 0.0
        self._section_text = section_text
        self.update()

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
        _draw_background(painter, w, h, tokens)
        if not self._peaks:
            _draw_empty_state(painter, w, h, tokens)
            return
        played = key_hue(self._camelot, tokens["accent"])
        unplayed = key_tint(played, _theme()) if self._camelot else tokens["border_strong"]
        _draw_bars(painter, (self._peaks, self._played_count(), played, unplayed), w, h)
        _draw_midpoint(painter, w, h, (self._section_text, tokens))
        _draw_playhead(painter, w, h, (self._seek_sec, self._duration_sec), tokens)
        _draw_time_markers(painter, w, h, self._duration_sec, tokens)

    def _played_count(self) -> int:
        if self._duration_sec <= 0:
            return len(self._peaks) // 2
        return int(len(self._peaks) * self._seek_sec / self._duration_sec)


def _theme() -> str:
    app = QApplication.instance()
    return str(app.property("appTheme") or "light") if app else "light"


def _tokens() -> dict[str, str]:
    return palette(_theme())


def _draw_background(painter: QPainter, w: int, h: int, tokens: dict) -> None:
    painter.fillRect(0, 0, w, h, QColor(tokens["surface"]))
    painter.setPen(QPen(QColor(tokens["border"]), 1))
    painter.drawRoundedRect(0, 0, w - 1, h - 1, 5, 5)


def _draw_empty_state(painter: QPainter, w: int, h: int, tokens: dict) -> None:
    painter.setPen(QColor(tokens["text_subtle"]))
    painter.setFont(QFont("Segoe UI", 8))
    painter.drawText(0, 0, w, h, Qt.AlignmentFlag.AlignCenter, "Waveform preview loads on analysis (Click to seek)")


def _draw_bars(painter: QPainter, bars: tuple, w: int, h: int) -> None:
    peaks, played_count, played_hue, unplayed_hue = bars
    n = len(peaks)
    bar_width = max(2.0, (w - 16) / max(1, n))
    c1, c2 = QColor(played_hue), QColor(unplayed_hue)
    for i, p in enumerate(peaks):
        x = 8 + i * bar_width
        bar_h = max(3.0, p * (h - 24))
        y = (h / 2.0) - (bar_h / 2.0) + 2
        painter.fillRect(int(x), int(y), max(1, int(bar_width - 1.5)), int(bar_h), c1 if i < played_count else c2)


def _draw_midpoint(painter: QPainter, w: int, h: int, info: tuple) -> None:
    label, tokens = info
    mid = w // 2
    painter.setPen(QPen(QColor(tokens["text_subtle"]), 1, Qt.PenStyle.DashLine))
    painter.drawLine(mid, 4, mid, h - 4)
    font = QFont("Segoe UI", 7, QFont.Weight.Bold)
    painter.setFont(font)
    painter.setPen(QColor(tokens["text_muted"]))
    elided = QFontMetrics(font).elidedText(label or "1st Half | 2nd Half", Qt.TextElideMode.ElideRight, max(40, (w - mid) - 10))
    painter.drawText(mid + 5, 13, elided)


def _draw_playhead(painter: QPainter, w: int, h: int, timing: tuple, tokens: dict) -> None:
    seek_sec, duration = timing
    if duration <= 0:
        return
    px = int(8 + (seek_sec / duration) * max(1, w - 16))
    painter.setPen(QPen(QColor(tokens["text"]), 2))
    painter.drawLine(px, 2, px, h - 2)
    mins, secs = int(seek_sec // 60), int(seek_sec % 60)
    painter.setFont(QFont("Consolas", 7, QFont.Weight.Bold))
    painter.drawText(min(w - 52, max(10, px + 4)), 13, f"@{mins}:{secs:02d}")


def _draw_time_markers(painter: QPainter, w: int, h: int, duration: float, tokens: dict) -> None:
    if duration <= 0:
        return
    painter.setFont(QFont("Consolas", 7))
    painter.setPen(QColor(tokens["text_muted"]))
    painter.drawText(8, h - 5, "0:00")
    mins, secs = int(duration // 60), int(duration % 60)
    painter.drawText(w - 36, h - 5, f"{mins}:{secs:02d}")
