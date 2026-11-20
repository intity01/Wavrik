"""Individual interactive lyric line widget for Karaoke display."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel


class LyricLineWidget(QFrame):
    clicked = pyqtSignal(float)

    def __init__(self, timestamp: float, text: str, parent=None):
        super().__init__(parent)
        self._timestamp = timestamp
        self._state = "upcoming"
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setObjectName("UpcomingLyricLine")
        self._init_ui(timestamp, text)

    def _init_ui(self, ts: float, text: str) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(10)
        mins, secs = int(ts // 60), int(ts % 60)
        self.timeLabel = QLabel(f"{mins:02d}:{secs:02d}", objectName="LyricTimestampBadge")
        self.textLabel = QLabel(text or "...", wordWrap=True)
        self.textLabel.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        layout.addWidget(self.timeLabel, 0)
        layout.addWidget(self.textLabel, 1)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self._timestamp)
        super().mousePressEvent(event)

    def setState(self, state: str) -> None:
        if self._state == state:
            return
        self._state = state
        name_map = {"active": "ActiveLyricLine", "upcoming": "UpcomingLyricLine", "past": "PastLyricLine"}
        self.setObjectName(name_map.get(state, "UpcomingLyricLine"))
        self.style().unpolish(self)
        self.style().polish(self)

    @property
    def timestamp(self) -> float:
        return self._timestamp
