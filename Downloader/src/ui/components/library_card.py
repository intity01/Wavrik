"""Compact library row with tabular columns for Title/Format, Key/Camelot/BPM, Status, and Actions."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from src.services.platform_actions import open_parent, open_path
from src.ui.i18n import tr
from src.ui.theme.key_colors import apply_key_property, key_index

from .controls import ElidedLabel, ToolButton

_AUDIO_EXTENSIONS = {".wav", ".mp3", ".flac", ".m4a", ".aac", ".ogg", ".opus"}


class LibraryCard(QWidget):
    redownloadRequested = pyqtSignal(str)
    openInAudioToolsRequested = pyqtSignal(str)

    def __init__(self, entry: dict, analysis: dict | None = None, parent=None):
        super().__init__(parent)
        self._entry, self._analysis, self._lang = entry, analysis or {}, "en"
        self._action_buttons: list[tuple[ToolButton, str]] = []
        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        card = QFrame(objectName="LibraryCard")
        outer.addWidget(card)
        row = QHBoxLayout(card)
        row.setContentsMargins(12, 8, 12, 8)
        row.setSpacing(12)
        row.addLayout(self._build_title_col(), 4)
        row.addWidget(self._build_harmony_col(), 0)
        self.status = QLabel(_status_text(entry), wordWrap=True)
        self.status.setProperty("status", entry.get("status", "failed"))
        row.addWidget(self.status, 2)
        self._add_actions(row)

    def _build_title_col(self) -> QVBoxLayout:
        col = QVBoxLayout()
        col.setSpacing(2)
        title = ElidedLabel(self._entry.get("title", "Untitled"), objectName="SectionTitle")
        self.metadata = ElidedLabel(_metadata_text(self._entry, self._analysis, self._lang), objectName="MutedText")
        col.addWidget(title)
        col.addWidget(self.metadata)
        return col

    def _build_harmony_col(self) -> QWidget:
        wrap = QWidget()
        wrap.setFixedWidth(186)
        lay = QHBoxLayout(wrap)
        lay.setContentsMargins(0, 0, 0, 0)
        self.harmonyBadge = QLabel(
            _harmony_text(self._entry, self._analysis, self._is_audio_entry(), self._lang),
            objectName="StepBadge" if self._analysis.get("key") else "NeutralBadge",
        )
        self.harmonyBadge.setProperty("keyIndex", key_index(self._analysis.get("camelot", "")))
        lay.addWidget(self.harmonyBadge)
        lay.addStretch(1)
        return wrap

    def setAnalysisResult(self, result: dict) -> None:
        self._analysis = result
        self.metadata.setText(_metadata_text(self._entry, self._analysis, self._lang))
        self.harmonyBadge.setText(_harmony_text(self._entry, self._analysis, self._is_audio_entry(), self._lang))
        self.harmonyBadge.setObjectName("StepBadge" if self._analysis.get("key") else "NeutralBadge")
        apply_key_property(self.harmonyBadge, self._analysis.get("camelot", ""))

    def setLanguage(self, lang: str) -> None:
        self._lang = lang
        for btn, k in self._action_buttons:
            btn.setText(tr(k, lang))
        self.metadata.setText(_metadata_text(self._entry, self._analysis, lang))
        self.harmonyBadge.setText(_harmony_text(self._entry, self._analysis, self._is_audio_entry(), lang))

    def _add_actions(self, row: QHBoxLayout) -> None:
        actions = QHBoxLayout()
        actions.setSpacing(6)
        if self._entry.get("status") == "completed" and self._entry.get("filePath"):
            if self._is_audio_entry():
                btn = ToolButton(tr("lib.btn_open_audio_tools", self._lang))
                btn.clicked.connect(self._open_audio_tools)
                self._action_buttons.append((btn, "lib.btn_open_audio_tools"))
                actions.addWidget(btn)
            for k, fn in (("lib.btn_open_file", self._open_file), ("lib.btn_show_in_folder", self._open_folder)):
                b = ToolButton(tr(k, self._lang))
                b.clicked.connect(fn)
                self._action_buttons.append((b, k))
                actions.addWidget(b)
        elif bool(self._entry.get("url", "")):
            retry = ToolButton(tr("lib.btn_download_again", self._lang))
            retry.clicked.connect(lambda: self.redownloadRequested.emit(self._entry.get("url", "")))
            self._action_buttons.append((retry, "lib.btn_download_again"))
            actions.addWidget(retry)
        row.addLayout(actions)

    def _is_audio_entry(self) -> bool:
        return self._entry.get("mediaType") == "audio" or Path(str(self._entry.get("filePath", ""))).suffix.lower() in _AUDIO_EXTENSIONS

    def _open_audio_tools(self) -> None:
        p = Path(self._entry.get("filePath", ""))
        self.openInAudioToolsRequested.emit(str(p)) if p.is_file() else self.status.setText(tr("lib.file_missing", self._lang))

    def _open_file(self) -> None:
        p = Path(self._entry.get("filePath", ""))
        open_path(p) if p.is_file() else self.status.setText(tr("lib.file_missing", self._lang))

    def _open_folder(self) -> None:
        p = Path(self._entry.get("filePath", ""))
        open_parent(p) if p.exists() else self.status.setText(tr("lib.file_missing", self._lang))


def _harmony_text(entry: dict, analysis: dict, is_audio: bool, lang: str = "en") -> str:
    if analysis.get("key"):
        return f"{analysis['key']} ({analysis.get('camelot', '--')}) · {float(analysis.get('bpm', 0.0)):.1f} BPM"
    return tr("lib.filter_audio" if is_audio else "lib.filter_video", lang)


def _metadata_text(entry: dict, analysis: dict, lang: str = "en") -> str:
    ts = entry.get("timestamp", "").replace("T", " ")[:16]
    base = f"{ts} · {entry.get('mediaType', 'unknown').title()} · {_format_size(int(entry.get('fileSize', 0) or 0), lang)}"
    if analysis.get("key"):
        conf = f" [{analysis['confidence']}%]" if analysis.get("confidence") else ""
        return f"{base} · Key: {analysis['key']} ({analysis.get('camelot', '--')}) · {float(analysis.get('bpm', 0.0)):.1f} BPM{conf}"
    return base


def _status_text(entry: dict) -> str:
    st, err = entry.get("status", "failed").title(), entry.get("error", "")
    return f"{st}: {err}" if err else st


def _format_size(size: int, lang: str = "en") -> str:
    if size <= 0:
        return tr("lib.size_unavailable", lang)
    val = float(size)
    for unit in ("B", "KB", "MB", "GB"):
        if val < 1024 or unit == "GB":
            return f"{val:.1f} {unit}"
        val /= 1024
    return tr("lib.size_unavailable", lang)
