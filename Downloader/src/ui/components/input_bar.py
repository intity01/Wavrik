"""Validated URL entry and batch import."""

from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
)

from src.core.parser import normalizeUrl, parseImportFile
from src.ui.dialogs import get_open_file_path

from .controls import LineEdit, PrimaryPushButton, ToolButton


class InputBar(QFrame):
    urlAdded = pyqtSignal(str)
    urlsImported = pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("InputPanel")
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 12, 14, 10)
        root.setSpacing(6)
        root.addLayout(self._primary_row())
        root.addLayout(self._secondary_row())
        root.addWidget(_hint_label())
        self.errorLabel = QLabel()
        self.errorLabel.setObjectName("InlineError")
        self.errorLabel.hide()
        root.addWidget(self.errorLabel)

    def _primary_row(self) -> QHBoxLayout:
        primary_row = QHBoxLayout()
        primary_row.setSpacing(8)
        self.urlInput = LineEdit()
        self.urlInput.setPlaceholderText("Paste a public video or playlist URL")
        self.urlInput.setAccessibleName("Video or playlist URL")
        self.urlInput.setAccessibleDescription("Paste a public HTTP or HTTPS link to check before downloading.")
        self.urlInput.setClearButtonEnabled(True)
        self.urlInput.returnPressed.connect(self._add)
        add = PrimaryPushButton("Add to queue")
        add.setAccessibleName("Add URL to download queue")
        add.clicked.connect(self._add)
        primary_row.addWidget(self.urlInput, 1)
        primary_row.addWidget(add)
        return primary_row

    def _secondary_row(self) -> QHBoxLayout:
        secondary_row = QHBoxLayout()
        secondary_row.addStretch(1)
        paste = ToolButton("Paste from clipboard")
        paste.setAccessibleName("Paste URL from clipboard and add it to the queue")
        paste.clicked.connect(self._paste)
        import_button = ToolButton("Import .txt list")
        import_button.setAccessibleName("Import URLs from a text file")
        import_button.clicked.connect(self._import)
        secondary_row.addWidget(paste)
        secondary_row.addWidget(import_button)
        return secondary_row

    def _paste(self) -> None:
        clipboard = QApplication.clipboard()
        if clipboard:
            self.urlInput.setText(clipboard.text().strip())
            self._add()

    def _add(self) -> None:
        normalized = normalizeUrl(self.urlInput.text())
        if not normalized:
            self.showError("Enter a valid http or https URL.")
            return
        self.errorLabel.hide()
        self.urlAdded.emit(normalized)
        self.urlInput.clear()

    def _import(self) -> None:
        selected = get_open_file_path(self, "Import URL list", "Text files (*.txt)")
        path = str(selected).strip() if selected else ""
        if not path or path == ".":
            return
        urls = parseImportFile(path)
        if urls:
            self.errorLabel.hide()
            self.urlsImported.emit(urls)
        else:
            self.showError("No valid public URLs were found in that file.")

    def showError(self, message: str) -> None:
        self.errorLabel.setText(message)
        self.errorLabel.show()


def _hint_label() -> QLabel:
    hint = QLabel("We check each link before downloading starts.")
    hint.setObjectName("MutedText")
    return hint
