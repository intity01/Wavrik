"""Library row with file, folder, Key/BPM badge, and Audio Tools actions."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from src.services.platform_actions import open_parent, open_path

from .controls import ToolButton

_AUDIO_EXTENSIONS = {".wav", ".mp3", ".flac", ".m4a", ".aac", ".ogg", ".opus"}


class LibraryCard(QWidget):
    redownloadRequested = pyqtSignal(str)
    openInAudioToolsRequested = pyqtSignal(str)

    def __init__(self, entry: dict, analysis: dict | None = None, parent=None):
        super().__init__(parent)
        self._entry = entry
        self._analysis = analysis or {}
        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        card = QFrame(objectName="LibraryCard")
        outer.addWidget(card)
        content = QVBoxLayout(card)
        content.setContentsMargins(14, 12, 14, 12)
        labels = QVBoxLayout()
        title = QLabel(entry.get("title", "Untitled"), objectName="SectionTitle")
        title.setWordWrap(True)
        self.metadata = QLabel(self._metadata_text(), objectName="MutedText")
        self.status = QLabel(self._status_text())
        self.status.setProperty("status", entry.get("status", "failed"))
        for w in (title, self.metadata, self.status):
            labels.addWidget(w)
        content.addLayout(labels)
        self._add_actions(content)

    def setAnalysisResult(self, result: dict) -> None:
        self._analysis = result
        self.metadata.setText(self._metadata_text())

    def _add_actions(self, content: QVBoxLayout) -> None:
        actions = QHBoxLayout()
        actions.addStretch(1)
        if self._entry.get("status") == "completed" and self._entry.get("filePath"):
            self._add_file_actions(actions)
        elif bool(self._entry.get("url", "")):
            self._add_retry_action(actions)
        content.addLayout(actions)

    def _add_file_actions(self, actions: QHBoxLayout) -> None:
        if self._is_audio_entry():
            tools_btn = ToolButton("Open in Audio Tools")
            tools_btn.setAccessibleDescription("Send this audio file to Audio Tools")
            tools_btn.clicked.connect(self._open_audio_tools)
            actions.addWidget(tools_btn)
        open_file, open_folder = ToolButton("Open file"), ToolButton("Show in folder")
        open_file.setAccessibleDescription("Open the media file")
        open_folder.setAccessibleDescription("Open the folder that contains the file")
        open_file.clicked.connect(self._open_file)
        open_folder.clicked.connect(self._open_folder)
        actions.addWidget(open_file)
        actions.addWidget(open_folder)

    def _is_audio_entry(self) -> bool:
        if self._entry.get("mediaType") == "audio":
            return True
        return Path(str(self._entry.get("filePath", ""))).suffix.lower() in _AUDIO_EXTENSIONS

    def _add_retry_action(self, actions: QHBoxLayout) -> None:
        retry = ToolButton("Download again")
        retry.setAccessibleDescription("Add this URL back to the download queue")
        retry.clicked.connect(lambda: self.redownloadRequested.emit(self._entry.get("url", "")))
        actions.addWidget(retry)

    def _metadata_text(self) -> str:
        timestamp = self._entry.get("timestamp", "").replace("T", " ")[:16]
        media_type = self._entry.get("mediaType", "unknown").title()
        size = _format_size(int(self._entry.get("fileSize", 0) or 0))
        base = f"{timestamp} · {media_type} · {size}"
        if self._analysis.get("key"):
            k = self._analysis["key"]
            cam = self._analysis.get("camelot", "--")
            bpm = float(self._analysis.get("bpm", 0.0))
            conf = self._analysis.get("confidence", "")
            c_tag = f" [{conf}%]" if conf else ""
            return f"{base} · Key: {k} ({cam}) · {bpm:.1f} BPM{c_tag}"
        return base

    def _status_text(self) -> str:
        status = self._entry.get("status", "failed").title()
        error = self._entry.get("error", "")
        return f"{status}: {error}" if error else status

    def _open_audio_tools(self) -> None:
        path = Path(self._entry.get("filePath", ""))
        if not path.is_file():
            self.status.setText("File is no longer available at the saved location")
            return
        self.openInAudioToolsRequested.emit(str(path))

    def _open_file(self) -> None:
        path = Path(self._entry.get("filePath", ""))
        if not path.is_file():
            self.status.setText("File is no longer available at the saved location")
            return
        open_path(path)

    def _open_folder(self) -> None:
        path = Path(self._entry.get("filePath", ""))
        if not path.exists():
            self.status.setText("File is no longer available at the saved location")
            return
        open_parent(path)


def _format_size(size: int) -> str:
    if size <= 0:
        return "Size unavailable"
    value = float(size)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            return f"{value:.1f} {unit}"
        value /= 1024
    return "Size unavailable"
