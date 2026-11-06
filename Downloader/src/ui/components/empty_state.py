"""Compact first-use guidance for the download workspace."""

from __future__ import annotations

from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from src.ui.i18n import tr
from src.ui.theme.styles import getFont

_STEPS = (
    ("1", "empty.step1_title", "empty.step1_desc"),
    ("2", "empty.step2_title", "empty.step2_desc"),
    ("3", "empty.step3_title", "empty.step3_desc"),
)


class EmptyState(QWidget):
    def __init__(self, config=None, parent=None):
        super().__init__(parent)
        self._cfg = config
        self._is_first_run = bool(config and config.get("firstRun", True))
        self._step_labels: list[tuple[QLabel, QLabel, str]] = []
        self._cards: list[QFrame] = []
        self._tip: QLabel | None = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 14, 10, 14)
        layout.setSpacing(8)
        self.title = QLabel(objectName="PageTitle")
        self.title.setFont(getFont(17, True))
        self.subtitle = QLabel(objectName="PageSubtitle")
        layout.addWidget(self.title)
        layout.addWidget(self.subtitle)
        for number, h_key, b_key in _STEPS:
            card, title_lbl, desc_lbl = _step_row(number, h_key, b_key)
            self._step_labels.append((title_lbl, desc_lbl, number))
            self._cards.append(card)
            layout.addWidget(card)
        self._tip = QLabel(objectName="MutedText", wordWrap=True)
        layout.addWidget(self._tip)
        layout.addStretch(1)
        self.setLanguage("en")

    def setLanguage(self, lang: str) -> None:
        self._is_first_run = bool(self._cfg and self._cfg.get("firstRun", True))
        for card in self._cards:
            card.setVisible(self._is_first_run)
        if self._tip:
            self._tip.setVisible(self._is_first_run)
        if self._is_first_run:
            self.title.setText(tr("empty.first_run_title", lang))
            self.subtitle.setText(tr("empty.first_run_subtitle", lang))
            for title_lbl, desc_lbl, num in self._step_labels:
                title_lbl.setText(tr(f"empty.step{num}_title", lang))
                desc_lbl.setText(tr(f"empty.step{num}_desc", lang))
            if self._tip:
                self._tip.setText(tr("empty.batch_tip", lang))
        else:
            self.title.setText(tr("empty.queue_title", lang))
            self.subtitle.setText(tr("empty.queue_subtitle", lang))


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
    return card, title, description
