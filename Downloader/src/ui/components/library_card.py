"""Compact library row with tabular columns for Title/Format, Key/Camelot/BPM, Status, and Actions."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from src.services.platform_actions import open_parent, open_path
from src.ui.i18n import tr
from src.ui.theme.key_colors import apply_key_property, key_index

from .controls import ElidedLabel, ToolButton
from .library_card_text import harmony_text, metadata_text, status_text

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
        self.status = QLabel(status_text(entry, self._lang), wordWrap=True)
        self.status.setProperty("status", entry.get("status", "failed"))
        row.addWidget(self.status, 2)
        self._add_actions(row)

    def _build_title_col(self) -> QVBoxLayout:
        col = QVBoxLayout()
        col.setSpacing(2)
        title = ElidedLabel(self._entry.get("title", "Untitled"), objectName="SectionTitle")
        self.metadata = ElidedLabel(metadata_text(self._entry, self._analysis, self._lang), objectName="MutedText")
        col.addWidget(title)
        col.addWidget(self.metadata)
        return col

    def _build_harmony_col(self) -> QWidget:
        wrap = QWidget()
        wrap.setFixedWidth(186)
        lay = QHBoxLayout(wrap)
        lay.setContentsMargins(0, 0, 0, 0)
        self.harmonyBadge = QLabel(
            harmony_text(self._analysis, self._is_audio_entry(), self._lang),
            objectName="StepBadge" if self._analysis.get("key") else "NeutralBadge",
        )
        self.harmonyBadge.setProperty("keyIndex", key_index(self._analysis.get("camelot", "")))
        lay.addWidget(self.harmonyBadge)
        lay.addStretch(1)
        return wrap

    def setAnalysisResult(self, result: dict) -> None:
        self._analysis = result
        self.metadata.setText(metadata_text(self._entry, self._analysis, self._lang))
        self.harmonyBadge.setText(harmony_text(self._analysis, self._is_audio_entry(), self._lang))
        self.harmonyBadge.setObjectName("StepBadge" if self._analysis.get("key") else "NeutralBadge")
        apply_key_property(self.harmonyBadge, self._analysis.get("camelot", ""))

    def setLanguage(self, lang: str) -> None:
        self._lang = lang
        for btn, k in self._action_buttons:
            btn.setText(tr(k, lang))
        self.status.setText(status_text(self._entry, lang))
        self.metadata.setText(metadata_text(self._entry, self._analysis, lang))
        self.harmonyBadge.setText(harmony_text(self._analysis, self._is_audio_entry(), lang))

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
        if p.is_file():
            self.openInAudioToolsRequested.emit(str(p))
        else:
            self._show_missing()

    def _open_file(self) -> None:
        p = Path(self._entry.get("filePath", ""))
        if not p.is_file():
            self._show_missing()
        elif not open_path(p):
            open_parent(p)  # Unknown or unsafe file types are revealed in their folder, never executed.

    def _open_folder(self) -> None:
        p = Path(self._entry.get("filePath", ""))
        if p.exists():
            open_parent(p)
        else:
            self._show_missing()

    def _show_missing(self) -> None:
        self.status.setText(tr("lib.file_missing", self._lang))
