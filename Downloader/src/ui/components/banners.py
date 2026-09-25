"""Clear, non-blocking clipboard and playlist prompts."""

from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout

from .controls import PrimaryPushButton, ToolButton


class ClipboardBanner(QFrame):
    addRequested = pyqtSignal(str)
    add_requested = addRequested
    dismissed = pyqtSignal()

    def __init__(self, url: str, parent=None):
        super().__init__(parent)
        self.url = url
        self.setObjectName("InfoBanner")
        row = QHBoxLayout(self)
        text = QVBoxLayout()
        heading = QLabel("Link detected in clipboard")
        heading.setObjectName("SectionTitle")
        detail = QLabel(url)
        detail.setObjectName("MutedText")
        detail.setTextInteractionFlags(detail.textInteractionFlags())
        text.addWidget(heading)
        text.addWidget(detail)
        add = PrimaryPushButton("Add")
        close = ToolButton("Dismiss")
        add.clicked.connect(lambda: self.addRequested.emit(url))
        close.clicked.connect(self.dismissed.emit)
        row.addLayout(text, 1)
        row.addWidget(add)
        row.addWidget(close)


class PlaylistBanner(QFrame):
    addAllRequested = pyqtSignal()
    add_all_requested = addAllRequested
    dismissed = pyqtSignal()

    def __init__(self, title: str, count: int, parent=None):
        super().__init__(parent)
        self.setObjectName("InfoBanner")
        row = QHBoxLayout(self)
        text = QVBoxLayout()
        heading = QLabel(f"Playlist found: {title}")
        heading.setObjectName("SectionTitle")
        detail = QLabel(f"{count} items can be added to the queue.")
        detail.setObjectName("MutedText")
        text.addWidget(heading)
        text.addWidget(detail)
        add = PrimaryPushButton("Add all")
        close = ToolButton("Dismiss")
        add.clicked.connect(self.addAllRequested.emit)
        close.clicked.connect(self.dismissed.emit)
        row.addLayout(text, 1)
        row.addWidget(add)
        row.addWidget(close)


class UpdateBanner(QFrame):
    viewRequested = pyqtSignal()
    dismissed = pyqtSignal()

    def __init__(self, info, parent=None):
        super().__init__(parent)
        self.setObjectName("InfoBanner")
        row = QHBoxLayout(self)
        text = QVBoxLayout()
        heading = QLabel(f"Version {info.version} is available")
        heading.setObjectName("SectionTitle")
        if info.can_download_safely:
            message = "A verified package can be downloaded from Settings."
        else:
            message = "Open the GitHub release to review the package and release notes."
        detail = QLabel(message)
        detail.setObjectName("MutedText")
        detail.setWordWrap(True)
        text.addWidget(heading)
        text.addWidget(detail)
        view = PrimaryPushButton("View update")
        close = ToolButton("Dismiss")
        view.clicked.connect(self.viewRequested.emit)
        close.clicked.connect(self.dismissed.emit)
        row.addLayout(text, 1)
        row.addWidget(view)
        row.addWidget(close)
