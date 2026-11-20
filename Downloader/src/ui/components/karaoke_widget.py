"""Synchronized smooth-scrolling Karaoke widget subclassing QScrollArea."""

from __future__ import annotations

from PyQt6.QtCore import QEasingCurve, QPropertyAnimation, QTimer, Qt, pyqtSignal
from PyQt6.QtWidgets import QLabel, QScrollArea, QVBoxLayout, QWidget

from src.services.audio_lyrics import LyricLine, find_active_line_index
from src.ui.components.karaoke_line import LyricLineWidget


class KaraokeWidget(QScrollArea):
    seekRequested = pyqtSignal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("KaraokeScrollArea")
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._lines: list[LyricLine] = []
        self._timestamps: list[float] = []
        self._widgets: list[LyricLineWidget] = []
        self._active_idx = -1
        self._user_interacting = False
        self._init_content()
        self._init_animator()

    def _init_content(self) -> None:
        self._container = QWidget(objectName="KaraokeContent")
        self._layout = QVBoxLayout(self._container)
        self._layout.setContentsMargins(16, 20, 16, 20)
        self._layout.setSpacing(6)
        self.setWidget(self._container)
        self.clear()

    def _init_animator(self) -> None:
        self._anim = QPropertyAnimation(self.verticalScrollBar(), b"value", self)
        self._anim.setDuration(260)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._resume_timer = QTimer(self)
        self._resume_timer.setSingleShot(True)
        self._resume_timer.setInterval(2500)
        self._resume_timer.timeout.connect(self._reset_user_scroll)

    def setLyrics(self, lines: list[LyricLine]) -> None:
        self.clear()
        self._lines = list(lines)
        self._timestamps = [line.timestamp for line in self._lines]
        if not self._lines:
            lbl = QLabel("No lyrics loaded. Load an .lrc file or click Auto-Transcribe.", objectName="KaraokeEmptyText")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._layout.addWidget(lbl)
            return
        for line in self._lines:
            w = LyricLineWidget(line.timestamp, line.text, self._container)
            w.clicked.connect(self.seekRequested.emit)
            self._widgets.append(w)
            self._layout.addWidget(w)
        self._layout.addStretch(1)

    def onPositionChanged(self, sec: float) -> None:
        if not self._timestamps:
            return
        idx = find_active_line_index(self._timestamps, sec)
        if idx == self._active_idx:
            return
        self._update_line_states(idx)
        self._active_idx = idx
        if not self._user_interacting:
            self._scroll_to_active(idx)

    def _update_line_states(self, active_idx: int) -> None:
        for i, w in enumerate(self._widgets):
            w.setState("active" if i == active_idx else ("past" if i < active_idx else "upcoming"))

    def _scroll_to_active(self, idx: int) -> None:
        if not (0 <= idx < len(self._widgets)):
            return
        target_w = self._widgets[idx]
        vp_h = self.viewport().height()
        target_y = target_w.pos().y() + (target_w.height() // 2) - (vp_h // 2)
        clamped = max(0, min(self.verticalScrollBar().maximum(), target_y))
        self._anim.stop()
        self._anim.setStartValue(self.verticalScrollBar().value())
        self._anim.setEndValue(clamped)
        self._anim.start()

    def wheelEvent(self, event) -> None:
        self._user_interacting = True
        self._resume_timer.start()
        super().wheelEvent(event)

    def _reset_user_scroll(self) -> None:
        self._user_interacting = False
        if self._active_idx >= 0:
            self._scroll_to_active(self._active_idx)

    def clear(self) -> None:
        self._active_idx = -1
        self._lines, self._timestamps, self._widgets = [], [], []
        while self._layout.count():
            item = self._layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
