"""Clear, non-blocking clipboard and playlist prompts."""

from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout

from src.ui.i18n import tr

from .controls import PushButton, ToolButton


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
        self._heading = QLabel(tr("banner.clip_title", "en"), objectName="SectionTitle")
        detail = QLabel(url, objectName="MutedText")
        detail.setTextInteractionFlags(detail.textInteractionFlags())
        text.addWidget(self._heading)
        text.addWidget(detail)
        self._addBtn = PushButton(tr("banner.clip_add", "en"))
        self._closeBtn = ToolButton(tr("banner.dismiss", "en"))

        def _on_add() -> None:
            self.addRequested.emit(url)
            self.dismissed.emit()
            self.deleteLater()

        self._addBtn.clicked.connect(_on_add)
        self._closeBtn.clicked.connect(lambda: (self.dismissed.emit(), self.deleteLater()))
        row.addLayout(text, 1)
        row.addWidget(self._addBtn)
        row.addWidget(self._closeBtn)

    def setLanguage(self, lang: str) -> None:
        self._heading.setText(tr("banner.clip_title", lang))
        self._addBtn.setText(tr("banner.clip_add", lang))
        self._closeBtn.setText(tr("banner.dismiss", lang))


class PlaylistBanner(QFrame):
    addAllRequested = pyqtSignal()
    add_all_requested = addAllRequested
    dismissed = pyqtSignal()

    def __init__(self, title: str, count: int, parent=None):
        super().__init__(parent)
        self.setObjectName("InfoBanner")
        self._title = title
        self._count = count
        row = QHBoxLayout(self)
        text = QVBoxLayout()
        self._heading = QLabel(tr("banner.playlist_title", "en").replace("{title}", title), objectName="SectionTitle")
        self._detail = QLabel(tr("banner.playlist_count", "en").replace("{count}", str(count)), objectName="MutedText")
        text.addWidget(self._heading)
        text.addWidget(self._detail)
        self._addBtn = PushButton(tr("banner.playlist_add_all", "en"))
        self._closeBtn = ToolButton(tr("banner.dismiss", "en"))

        def _on_add_all() -> None:
            self.addAllRequested.emit()
            self.dismissed.emit()
            self.deleteLater()

        self._addBtn.clicked.connect(_on_add_all)
        self._closeBtn.clicked.connect(lambda: (self.dismissed.emit(), self.deleteLater()))
        row.addLayout(text, 1)
        row.addWidget(self._addBtn)
        row.addWidget(self._closeBtn)

    def setLanguage(self, lang: str) -> None:
        self._heading.setText(tr("banner.playlist_title", lang).replace("{title}", self._title))
        self._detail.setText(tr("banner.playlist_count", lang).replace("{count}", str(self._count)))
        self._addBtn.setText(tr("banner.playlist_add_all", lang))
        self._closeBtn.setText(tr("banner.dismiss", lang))


class UpdateBanner(QFrame):
    viewRequested = pyqtSignal()
    dismissed = pyqtSignal()

    def __init__(self, info, parent=None):
        super().__init__(parent)
        self.setObjectName("InfoBanner")
        self._info = info
        row = QHBoxLayout(self)
        text = QVBoxLayout()
        self._heading = QLabel(tr("banner.update_title", "en").replace("{version}", str(info.version)), objectName="SectionTitle")
        msg_key = "banner.update_safe" if info.can_download_safely else "banner.update_github"
        self._detail = QLabel(tr(msg_key, "en"), objectName="MutedText", wordWrap=True)
        text.addWidget(self._heading)
        text.addWidget(self._detail)
        self._viewBtn = PushButton(tr("banner.update_view", "en"))
        self._closeBtn = ToolButton(tr("banner.dismiss", "en"))
        self._viewBtn.clicked.connect(self.viewRequested.emit)
        self._closeBtn.clicked.connect(self.dismissed.emit)
        row.addLayout(text, 1)
        row.addWidget(self._viewBtn)
        row.addWidget(self._closeBtn)

    def setLanguage(self, lang: str) -> None:
        self._heading.setText(tr("banner.update_title", lang).replace("{version}", str(self._info.version)))
        msg_key = "banner.update_safe" if self._info.can_download_safely else "banner.update_github"
        self._detail.setText(tr(msg_key, lang))
        self._viewBtn.setText(tr("banner.update_view", lang))
        self._closeBtn.setText(tr("banner.dismiss", lang))
