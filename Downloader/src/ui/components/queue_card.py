"""Queue item state, metadata, and actions."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtWidgets import QWidget

from src.domain.presets import getPreset
from src.services.platform_actions import open_parent

from . import queue_card_view
from .queue_card_state import (
    ACTIVE_STATES,
    action_description,
    action_text,
    engine_label,
    format_duration,
)


class QueueItemCard(QWidget):
    removeRequested = pyqtSignal(str)
    downloadRequested = pyqtSignal(str, str, str)
    cancelRequested = pyqtSignal(str)

    def __init__(self, url: str, config=None, preset_key: str | None = None, engine: str | None = None):
        super().__init__()
        self._url = url
        self._videoTitle = "Reading media information"
        self._state = ""
        self._file_path: Path | None = None
        default = preset_key or (config.get("defaultPreset") if config else None)
        self._presetKey = getPreset(default).key
        self._engine = engine or (config.get("downloadEngine", "auto") if config else "auto")
        queue_card_view.build(self)
        self.setPreset(self._presetKey)
        self.setEngine(self._engine)
        self.setStatus("fetching", "Reading media information")

    def getVideoTitle(self) -> str:
        return self._videoTitle

    def selectedPreset(self):
        return getPreset(self._presetKey)

    def selectedEngine(self) -> str:
        return self._engine

    def setEngine(self, engine: str) -> None:
        if self._state in ACTIVE_STATES or self._state == "completed":
            return
        self._engine = engine if engine in {"auto", "native", "yt-dlp"} else "auto"
        self._engineLabel.setText(f"Engine: {engine_label(self._engine)}")

    def setPreset(self, key: str) -> None:
        if self._state in ACTIVE_STATES or self._state == "completed":
            return
        preset = getPreset(key)
        self._presetKey = preset.key
        self._presetLabel.setText(preset.label)
        self._presetLabel.setAccessibleName(f"Selected download option: {preset.label}")

    def isDownloadable(self) -> bool:
        return self._state in {"ready", "failed", "cancelled"}

    def canQueueDownload(self) -> bool:
        return self.isDownloadable() or self._state == "fetching"

    def beginDownload(self) -> None:
        self._handle_action()

    def setActionEnabled(self, enabled: bool) -> None:
        self._btnDl.setEnabled(enabled)

    def setMeta(self, _url: str, metadata: dict) -> None:
        self._videoTitle = metadata.get("title", "Unknown title")
        self._title.setText(self._videoTitle)
        duration = format_duration(metadata.get("duration", 0))
        self._lblMeta.setText(f"{duration} · {metadata.get('uploader', 'Unknown creator')}")

    def setThumbnail(self, image: QImage | QPixmap | bytes) -> None:
        if isinstance(image, QImage):
            pixmap = QPixmap.fromImage(image)
        elif isinstance(image, bytes):
            pixmap = QPixmap()
            pixmap.loadFromData(image)
        elif isinstance(image, QPixmap):
            pixmap = image
        else:
            return
        if pixmap.isNull():
            return
        mode = Qt.AspectRatioMode.KeepAspectRatioByExpanding
        scaled = pixmap.scaled(self._thumb.size(), mode, Qt.TransformationMode.SmoothTransformation)
        self._thumb.setPixmap(scaled)
        self._thumb.setText("")

    def setStatus(self, state: str, message: str) -> None:
        changed = self._state != state
        self._state = state
        if state == "failed" and self._videoTitle == "Reading media information":
            self._videoTitle = "Unable to read media"
            self._title.setText(self._videoTitle)
            if self._lblMeta.text() == "Waiting for metadata":
                self._lblMeta.setText(self._url)
        self._lblStatus.setText(message)
        self._lblStatus.setProperty("status", state)
        if changed:
            self._lblStatus.style().unpolish(self._lblStatus)
            self._lblStatus.style().polish(self._lblStatus)
        self._btnDl.setText(action_text(state))
        self._btnDl.setEnabled(state != "fetching")
        self._btnDl.setAccessibleDescription(action_description(state))
        self._progress.setVisible(state in ACTIVE_STATES or state == "completed")
        self._progressText.setVisible(state in {"downloading", "processing"})

    def updateProgress(self, percent: float, speed: str, eta: str) -> None:
        self._progress.setValue(max(0, min(100, int(percent))))
        self._progressText.setText(f"{percent:.1f}% · {speed} · ETA {eta}")

    def finish(self, result) -> None:
        self._btnDl.setEnabled(True)
        self._file_path = result.file_path
        self._progress.setValue(100 if result.success else self._progress.value())
        failed = result.state.value.lower() == "failed" and result.error
        status_message = result.error if failed else result.state.value
        self.setStatus(result.state.value.lower(), status_message)

    def _handle_action(self) -> None:
        if self._state in ACTIVE_STATES:
            self.cancelRequested.emit(self._url)
        elif self._state == "completed" and self._file_path:
            if self._file_path.exists():
                if not open_parent(self._file_path):
                    self.setStatus("failed", "Could not open folder. File may have been moved or deleted.")
            else:
                self.setStatus("failed", "File no longer exists. It may have been moved or deleted.")
        else:
            self.setStatus("queued", "Waiting for a download slot")
            self.downloadRequested.emit(self._url, self._presetKey, self._engine)
