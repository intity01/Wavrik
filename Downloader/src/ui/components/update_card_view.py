"""Build the software update settings card."""

from __future__ import annotations

from PyQt6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout

from .controls import PrimaryPushButton, ProgressBar, PushButton, ToggleButton


def build(card) -> None:
    layout = QVBoxLayout(card)
    layout.setContentsMargins(16, 14, 16, 14)
    layout.setSpacing(10)
    title = QLabel("Software updates")
    title.setObjectName("SectionTitle")
    current = QLabel(f"Installed version: {card._manager.getCurrentVersion()}")
    current.setObjectName("MutedText")
    configured = card._manager.isConfigured
    message = "Updates are checked through GitHub Releases." if configured else "Updates are not configured for this build."
    card.statusLabel = QLabel(message)
    card.statusLabel.setWordWrap(True)
    card.statusLabel.setObjectName("MutedText")
    card.startupCheck = ToggleButton("Check for updates at startup")
    card.startupCheck.setChecked(card._cfg.get("checkUpdatesOnStartup", True))
    card.startupCheck.toggled.connect(card._save_startup_preference)
    card.startupCheck.setEnabled(configured)
    card.progressBar = ProgressBar()
    card.progressBar.hide()
    layout.addWidget(title)
    layout.addWidget(current)
    layout.addWidget(card.statusLabel)
    layout.addLayout(_preference_row("Check for updates at startup", card.startupCheck))
    layout.addWidget(card.progressBar)
    layout.addLayout(_buttons(card))


def _buttons(card) -> QVBoxLayout:
    rows = QVBoxLayout()
    primary = QHBoxLayout()
    secondary = QHBoxLayout()
    card.checkButton = PrimaryPushButton("Check now")
    card.checkButton.setEnabled(card._manager.isConfigured)
    card.releaseButton = PushButton("Open release")
    card.downloadButton = PushButton("Download verified package")
    card.folderButton = PushButton("Open download folder")
    card.releaseButton.hide()
    card.downloadButton.hide()
    card.folderButton.hide()
    card.checkButton.clicked.connect(card.check)
    card.releaseButton.clicked.connect(card._open_release)
    card.downloadButton.clicked.connect(card._confirm_download)
    card.folderButton.clicked.connect(card._open_folder)
    primary.addWidget(card.checkButton)
    primary.addWidget(card.releaseButton)
    primary.addStretch(1)
    secondary.addWidget(card.downloadButton)
    secondary.addWidget(card.folderButton)
    secondary.addStretch(1)
    rows.addLayout(primary)
    rows.addLayout(secondary)
    return rows


def _preference_row(label: str, control) -> QHBoxLayout:
    row = QHBoxLayout()
    text = QLabel(label)
    row.addWidget(text, 1)
    row.addWidget(control)
    return row
