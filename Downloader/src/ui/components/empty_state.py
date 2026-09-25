"""Compact first-use guidance for the download workspace."""

from __future__ import annotations

from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from src.ui.theme.styles import getFont

_STEPS = (
    ("1", "Add a link", "Paste a public video or playlist URL."),
    ("2", "Choose output", "Select media type, quality, and save location above."),
    ("3", "Download", "Start the queue, track progress, then open the saved folder."),
)


class EmptyState(QWidget):
    def __init__(self, config=None, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 14, 10, 14)
        layout.setSpacing(8)
        is_first_run = bool(config and config.get("firstRun", True))
        title = QLabel("Start with one link" if is_first_run else "Your queue is empty")
        self.title = title
        title.setObjectName("PageTitle")
        title.setFont(getFont(17, True))
        subtitle = QLabel(
            "Set the output above, then add a public URL."
            if is_first_run else "Paste a public video or playlist URL above to add another download."
        )
        subtitle.setObjectName("PageSubtitle")
        layout.addWidget(title)
        layout.addWidget(subtitle)
        if is_first_run:
            for number, heading, body in _STEPS:
                layout.addWidget(_step_row(number, heading, body))
            tip = QLabel("Batch tip: Import a .txt file with one URL per line.")
            tip.setObjectName("MutedText")
            tip.setWordWrap(True)
            layout.addWidget(tip)
        layout.addStretch(1)


def _step_row(number: str, heading: str, body: str) -> QFrame:
    card = QFrame()
    card.setObjectName("Card")
    card.setMinimumHeight(42)
    row = QHBoxLayout(card)
    row.setContentsMargins(12, 7, 12, 7)
    row.setSpacing(10)
    badge = QLabel(number)
    badge.setFixedWidth(24)
    badge.setFont(getFont(11, True))
    badge.setObjectName("StepBadge")
    title = QLabel(heading)
    title.setObjectName("SectionTitle")
    title.setMinimumWidth(108)
    description = QLabel(body)
    description.setObjectName("MutedText")
    description.setWordWrap(True)
    row.addWidget(badge)
    row.addWidget(title)
    row.addWidget(description, 1)
    return card
