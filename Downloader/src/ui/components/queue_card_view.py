"""Build the visual structure for a queue item card."""

from __future__ import annotations

from PyQt6.QtCore import QSize, Qt
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout

from .controls import PrimaryPushButton, ProgressBar, ToolButton


def build(card) -> None:
    outer = QHBoxLayout(card)
    outer.setContentsMargins(0, 0, 0, 0)
    container = QFrame()
    container.setObjectName("QueueCard")
    outer.addWidget(container)
    root = QHBoxLayout(container)
    root.setContentsMargins(12, 12, 12, 12)
    root.setSpacing(12)
    card._thumb = QLabel("Preview")
    card._thumb.setObjectName("Thumbnail")
    card._thumb.setFixedSize(QSize(96, 54))
    card._thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
    root.addWidget(card._thumb)
    content = QVBoxLayout()
    content.setSpacing(7)
    content.addLayout(_title_row(card))
    card._lblMeta = QLabel("Waiting for metadata")
    card._lblMeta.setObjectName("MutedText")
    content.addWidget(card._lblMeta)
    card._progress = ProgressBar()
    card._progress.setRange(0, 100)
    card._progress.hide()
    content.addWidget(card._progress)
    card._progressText = QLabel()
    card._progressText.setObjectName("MutedText")
    card._progressText.hide()
    content.addWidget(card._progressText)
    content.addLayout(_action_row(card))
    root.addLayout(content, 1)


def _title_row(card) -> QHBoxLayout:
    row = QHBoxLayout()
    card._title = QLabel(card._videoTitle)
    card._title.setObjectName("SectionTitle")
    card._title.setWordWrap(True)
    card._lblStatus = QLabel()
    card._lblStatus.setProperty("status", "fetching")
    card._btnDel = ToolButton("Remove")
    card._btnDel.setAccessibleName("Remove this item from the queue")
    card._btnDel.clicked.connect(lambda: card.removeRequested.emit(card._url))
    row.addWidget(card._title, 1)
    row.addWidget(card._lblStatus)
    row.addWidget(card._btnDel)
    return row


def _action_row(card) -> QHBoxLayout:
    row = QHBoxLayout()
    details = QVBoxLayout()
    details.setSpacing(1)
    card._presetLabel = QLabel()
    card._presetLabel.setObjectName("PresetLabel")
    card._engineLabel = QLabel()
    card._engineLabel.setObjectName("MutedText")
    details.addWidget(card._presetLabel)
    details.addWidget(card._engineLabel)
    card._btnDl = PrimaryPushButton("Download")
    card._btnDl.setAccessibleName("Download this item")
    card._btnDl.clicked.connect(card._handle_action)
    row.addLayout(details, 1)
    row.addWidget(card._btnDl)
    return row
