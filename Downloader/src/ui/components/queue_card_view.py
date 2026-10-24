"""Build a compact, table-aligned horizontal row for a queue item."""

from __future__ import annotations

from PyQt6.QtCore import QSize, Qt
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from .controls import ElidedLabel, PrimaryPushButton, ProgressBar, ToolButton


def build(card) -> None:
    outer = QHBoxLayout(card)
    outer.setContentsMargins(0, 0, 0, 0)
    container = QFrame()
    container.setObjectName("QueueCard")
    outer.addWidget(container)
    root = QHBoxLayout(container)
    root.setContentsMargins(10, 8, 10, 8)
    root.setSpacing(12)
    card._thumb = QLabel("Media")
    card._thumb.setObjectName("Thumbnail")
    card._thumb.setFixedSize(QSize(72, 40))
    card._thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
    root.addWidget(card._thumb)
    root.addLayout(_media_column(card), 4)
    root.addWidget(_spec_column(card))
    root.addLayout(_status_column(card), 3)
    root.addLayout(_action_column(card))


def _media_column(card) -> QVBoxLayout:
    col = QVBoxLayout()
    col.setSpacing(2)
    card._title = ElidedLabel(card._videoTitle)
    card._title.setObjectName("SectionTitle")
    card._lblMeta = ElidedLabel("Waiting for metadata")
    card._lblMeta.setObjectName("MutedText")
    col.addWidget(card._title)
    col.addWidget(card._lblMeta)
    return col


def _spec_column(card) -> QWidget:
    wrap = QWidget()
    wrap.setFixedWidth(156)
    col = QVBoxLayout(wrap)
    col.setContentsMargins(0, 0, 0, 0)
    col.setSpacing(2)
    card._presetLabel = QLabel()
    card._presetLabel.setObjectName("PresetLabel")
    card._engineLabel = QLabel()
    card._engineLabel.setObjectName("MutedText")
    col.addWidget(card._presetLabel)
    col.addWidget(card._engineLabel)
    return wrap


def _status_column(card) -> QVBoxLayout:
    col = QVBoxLayout()
    col.setSpacing(4)
    card._lblStatus = QLabel()
    card._lblStatus.setProperty("status", "fetching")
    card._lblStatus.setWordWrap(True)
    card._progress = ProgressBar()
    card._progress.setRange(0, 100)
    card._progress.hide()
    card._progressText = QLabel()
    card._progressText.setObjectName("MonoValue")
    card._progressText.hide()
    col.addWidget(card._lblStatus)
    col.addWidget(card._progress)
    col.addWidget(card._progressText)
    return col


def _action_column(card) -> QHBoxLayout:
    row = QHBoxLayout()
    row.setSpacing(6)
    card._btnDl = PrimaryPushButton("Download")
    card._btnDl.setAccessibleName("Download this item")
    card._btnDl.clicked.connect(card._handle_action)
    card._btnDel = ToolButton("Remove")
    card._btnDel.setAccessibleName("Remove this item from the queue")
    card._btnDel.clicked.connect(lambda: card.removeRequested.emit(card._url))
    row.addWidget(card._btnDl)
    row.addWidget(card._btnDel)
    return row
