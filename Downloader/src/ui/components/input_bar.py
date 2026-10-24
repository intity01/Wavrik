"""Dense URL entry bar without instructional bloat or STEP pills."""

from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QApplication, QFrame, QHBoxLayout, QLabel, QVBoxLayout

from src.core.parser import normalizeUrl, parseImportFile
from src.ui.dialogs import get_open_file_path
from src.ui.i18n import tr

from .controls import LineEdit, PrimaryPushButton, ToolButton


class InputBar(QFrame):
    urlAdded = pyqtSignal(str)
    urlsImported = pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("InputPanel")
        root = QVBoxLayout(self)
        root.setContentsMargins(10, 8, 10, 8)
        root.setSpacing(6)
        root.addLayout(self._primary_row())
        self.errorLabel = QLabel(objectName="InlineError")
        self.errorLabel.hide()
        root.addWidget(self.errorLabel)

    def _primary_row(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(6)
        self.urlInput = LineEdit()
        self.urlInput.setPlaceholderText(tr("dl.url_placeholder", "en"))
        self.urlInput.setAccessibleName("Video or playlist URL")
        self.urlInput.setAccessibleDescription("Paste a public HTTP or HTTPS link to check before downloading.")
        self.urlInput.setClearButtonEnabled(True)
        self.urlInput.returnPressed.connect(self._add)
        self.pasteButton = ToolButton("Paste from clipboard")
        self.pasteButton.setAccessibleName("Paste URL from clipboard and add it to the queue")
        self.pasteButton.clicked.connect(self._paste)
        self.importButton = ToolButton("Import .txt list")
        self.importButton.setAccessibleName("Import URLs from a text file")
        self.importButton.clicked.connect(self._import)
        self.addButton = PrimaryPushButton("Add to queue")
        self.addButton.setAccessibleName("Add URL to download queue")
        self.addButton.clicked.connect(self._add)
        row.addWidget(self.urlInput, 1)
        row.addWidget(self.pasteButton)
        row.addWidget(self.importButton)
        row.addWidget(self.addButton)
        return row

    def setLanguage(self, lang: str) -> None:
        self.urlInput.setPlaceholderText(tr("dl.url_placeholder", lang))

    def _paste(self) -> None:
        if (clipboard := QApplication.clipboard()) and (text := clipboard.text().strip()):
            self.urlInput.setText(text)
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
        if (sel := get_open_file_path(self, "Import URL list", "Text files (*.txt)")) and sel.is_file():
            if (urls := parseImportFile(str(sel))):
                self.errorLabel.hide()
                self.urlsImported.emit(urls)
            else:
                self.showError("No valid public URLs were found in that file.")

    def showError(self, message: str) -> None:
        self.errorLabel.setText(message)
        self.errorLabel.show()
