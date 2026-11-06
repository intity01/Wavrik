"""Queue item state, metadata, and actions."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtWidgets import QWidget

from src.domain.presets import getPreset
from src.services.platform_actions import open_parent
from src.ui.i18n import tr

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

    def __init__(self, url: str, config=None, preset_key: str | None = None, engine: str | None = None, lang: str = "en"):
        super().__init__()
        self._url, self._state, self._lang = url, "", lang
        self._videoTitle, self._file_path = tr("queue.reading_info", lang), None
        default = preset_key or (config.get("defaultPreset") if config else None)
        self._presetKey = getPreset(default).key
        self._engine = engine or (config.get("downloadEngine", "auto") if config else "auto")
        queue_card_view.build(self)
        self.setPreset(self._presetKey)
        self.setEngine(self._engine)
        self.setStatus("fetching", tr("queue.reading_info", lang))

    def getVideoTitle(self) -> str: return self._videoTitle
    def selectedPreset(self): return getPreset(self._presetKey)
    def selectedEngine(self) -> str: return self._engine

    def setLanguage(self, lang: str) -> None:
        p_lang, self._lang = self._lang, lang
        self._btnDl.setText(action_text(self._state, lang))
        self._btnDel.setText(tr("queue.action_remove", lang))
        self._engineLabel.setText(tr("queue.engine_label", lang).replace("{engine}", engine_label(self._engine)))
        if self._state == "fetching":
            self._lblStatus.setText(tr("queue.reading_info", lang))
            if self._videoTitle in {tr("queue.reading_info", p_lang), "Reading media information"}:
                self._videoTitle = tr("queue.reading_info", lang)
                self._title.setText(self._videoTitle)
        elif self._state == "queued":
            self._lblStatus.setText(tr("queue.waiting_slot", lang))
        elif self._state == "cancelled":
            self._lblStatus.setText(tr("queue.cancelling", lang))
        if self._lblMeta.text() in {tr("queue.waiting_metadata", p_lang), "Waiting for metadata"}:
            self._lblMeta.setText(tr("queue.waiting_metadata", lang))

    def setEngine(self, engine: str) -> None:
        if self._state not in ACTIVE_STATES and self._state != "completed":
            self._engine = engine if engine in {"auto", "native", "yt-dlp"} else "auto"
            self._engineLabel.setText(tr("queue.engine_label", self._lang).replace("{engine}", engine_label(self._engine)))

    def setPreset(self, key: str) -> None:
        if self._state not in ACTIVE_STATES and self._state != "completed":
            preset = getPreset(key)
            self._presetKey = preset.key
            self._presetLabel.setText(preset.label)
            self._presetLabel.setAccessibleName(f"Selected download option: {preset.label}")

    def isDownloadable(self) -> bool: return self._state in {"ready", "failed", "cancelled"}
    def canQueueDownload(self) -> bool: return self.isDownloadable() or self._state == "fetching"
    def beginDownload(self) -> None: self._handle_action()
    def setActionEnabled(self, enabled: bool) -> None: self._btnDl.setEnabled(enabled)

    def setMeta(self, _url: str, metadata: dict) -> None:
        self._videoTitle = metadata.get("title", "Unknown title")
        self._title.setText(self._videoTitle)
        duration = format_duration(metadata.get("duration", 0))
        self._lblMeta.setText(f"{duration} · {metadata.get('uploader', 'Unknown creator')}")

    def setThumbnail(self, image: QImage | QPixmap | bytes) -> None:
        if not (pixmap := _to_pixmap(image)) or pixmap.isNull():
            return
        mode = Qt.AspectRatioMode.KeepAspectRatioByExpanding
        scaled = pixmap.scaled(self._thumb.size(), mode, Qt.TransformationMode.SmoothTransformation)
        self._thumb.setPixmap(scaled)
        self._thumb.setText("")

    def setStatus(self, state: str, message: str) -> None:
        changed = self._state != state
        self._state = state
        if state == "failed" and self._videoTitle in {tr("queue.reading_info", self._lang), "Reading media information"}:
            self._videoTitle = tr("queue.unable_read", self._lang)
            self._title.setText(self._videoTitle)
            if self._lblMeta.text() in {tr("queue.waiting_metadata", self._lang), "Waiting for metadata"}:
                self._lblMeta.setText(self._url)
        self._lblStatus.setText(message)
        self._lblStatus.setProperty("status", state)
        if changed:
            self._lblStatus.style().unpolish(self._lblStatus)
            self._lblStatus.style().polish(self._lblStatus)
        self._btnDl.setText(action_text(state, self._lang))
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
        self.setStatus(result.state.value.lower(), result.error if failed else result.state.value)

    def _handle_action(self) -> None:
        if self._state in ACTIVE_STATES:
            self.cancelRequested.emit(self._url)
        elif self._state == "completed" and self._file_path:
            msg = tr("queue.missing_file_err" if not self._file_path.exists() else "queue.missing_folder_err", self._lang)
            if not self._file_path.exists() or not open_parent(self._file_path):
                self.setStatus("failed", msg)
        else:
            self.setStatus("queued", tr("queue.waiting_slot", self._lang))
            self.downloadRequested.emit(self._url, self._presetKey, self._engine)


def _to_pixmap(image: QImage | QPixmap | bytes) -> QPixmap | None:
    if isinstance(image, QImage):
        return QPixmap.fromImage(image)
    if isinstance(image, bytes):
        pm = QPixmap()
        pm.loadFromData(image)
        return pm
    return image if isinstance(image, QPixmap) else None
