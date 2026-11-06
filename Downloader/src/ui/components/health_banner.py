"""Show a readiness warning only when FFmpeg is unavailable."""

from __future__ import annotations

from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel

from src.core.runtime import find_ffmpeg
from src.ui.i18n import tr


class HealthBanner(QFrame):
    def __init__(self, _download_path: str, parent=None):
        super().__init__(parent)
        self._ready = bool(find_ffmpeg())
        self.setObjectName("HealthWarning")
        self._title = QLabel(tr("health.ffmpeg_title", "en"), objectName="SectionTitle")
        self._detail = QLabel(tr("health.ffmpeg_desc", "en"), objectName="MutedText", wordWrap=True)
        if self._ready:
            self.hide()
            return
        row = QHBoxLayout(self)
        row.setContentsMargins(12, 9, 12, 9)
        row.addWidget(self._title)
        row.addWidget(self._detail, 1)

    def setLanguage(self, lang: str) -> None:
        self._title.setText(tr("health.ffmpeg_title", lang))
        self._detail.setText(tr("health.ffmpeg_desc", lang))

    def setDownloadPath(self, _path: str) -> None:
        return
