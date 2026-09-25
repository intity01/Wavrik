"""Show a readiness warning only when FFmpeg is unavailable."""

from __future__ import annotations

from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel

from src.core.runtime import find_ffmpeg


class HealthBanner(QFrame):
    def __init__(self, _download_path: str, parent=None):
        super().__init__(parent)
        self._ready = bool(find_ffmpeg())
        self.setObjectName("HealthWarning")
        if self._ready:
            self.hide()
            return
        row = QHBoxLayout(self)
        row.setContentsMargins(12, 9, 12, 9)
        title = QLabel("FFmpeg needs attention")
        title.setObjectName("SectionTitle")
        detail = QLabel("Place ffmpeg.exe beside RunApp.bat before downloading audio or merged video.")
        detail.setObjectName("MutedText")
        detail.setWordWrap(True)
        row.addWidget(title)
        row.addWidget(detail, 1)

    def setDownloadPath(self, _path: str) -> None:
        return
