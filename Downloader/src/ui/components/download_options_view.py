"""Compact utility toolbar for output format, save location, and engine."""

from __future__ import annotations

from PyQt6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from src.ui.i18n import tr

from .controls import ComboBox, LineEdit, PrimaryPushButton, PushButton, ToolButton


def build(options) -> None:
    root = QVBoxLayout(options)
    root.setContentsMargins(10, 8, 10, 8)
    root.setSpacing(6)
    options.mediaCombo = combo("Media type", ["Audio", "Video"])
    options.mediaCombo.setFixedWidth(96)
    options.presetCombo = ComboBox()
    options.presetCombo.setAccessibleName("Format and quality")
    options.presetCombo.setMinimumWidth(160)
    options.engineCombo = engine_combo()
    options.pathInput = LineEdit(options._cfg.get("downloadPath", ""))
    options.pathInput.setReadOnly(True)
    options.pathInput.setCursorPosition(0)
    options.pathInput.setAccessibleName("Download folder")
    options.browseButton = PushButton("Change folder")
    options.browseButton.clicked.connect(options._browse)
    options.advancedButton = ToolButton("Advanced options")
    options.advancedButton.setCheckable(True)
    options.advancedButton.setAccessibleDescription("Show download compatibility options")
    options.downloadAllButton = PrimaryPushButton("Download all")
    options.downloadAllButton.setEnabled(False)
    options.downloadAllButton.clicked.connect(options.downloadAllRequested.emit)
    root.addLayout(_toolbar_row(options))
    options.advancedPanel = advanced_panel(options.engineCombo)
    options.advancedButton.toggled.connect(options.advancedPanel.setVisible)
    root.addWidget(options.advancedPanel)
    options.mediaCombo.currentTextChanged.connect(options._media_changed)
    options.presetCombo.currentIndexChanged.connect(options._preset_changed)
    options.engineCombo.currentIndexChanged.connect(options._engine_changed)


def _toolbar_row(options) -> QHBoxLayout:
    row = QHBoxLayout()
    row.setSpacing(8)
    options.lblType = field_label("TYPE")
    options.lblFormat = field_label("FORMAT")
    options.lblFolder = field_label("FOLDER")
    for w, stretch in (
        (options.lblType, 0),
        (options.mediaCombo, 0),
        (options.lblFormat, 0),
        (options.presetCombo, 0),
        (options.lblFolder, 0),
        (options.pathInput, 1),
        (options.browseButton, 0),
        (options.advancedButton, 0),
        (options.downloadAllButton, 0),
    ):
        row.addWidget(w, stretch)
    return row


def combo(name: str, items: list[str]) -> ComboBox:
    control = ComboBox()
    control.addItems(items)
    control.setAccessibleName(name)
    return control


def engine_combo() -> ComboBox:
    control = combo("Download compatibility", [])
    for label, key in (
        ("Auto — recommended", "auto"),
        ("Built-in downloader", "native"),
        ("Compatibility downloader", "yt-dlp"),
    ):
        control.addItem(label, key)
    return control


def advanced_panel(engine_combo_control: ComboBox) -> QWidget:
    panel = QWidget()
    layout = QHBoxLayout(panel)
    layout.setContentsMargins(0, 2, 0, 0)
    layout.setSpacing(8)
    layout.addWidget(field_label("COMPATIBILITY ENGINE"))
    layout.addWidget(engine_combo_control)
    detail = QLabel("Leave on Auto unless a source requires specific extraction.")
    detail.setObjectName("MutedText")
    layout.addWidget(detail, 1)
    panel.setVisible(False)
    return panel


def field_label(text: str) -> QLabel:
    label = QLabel(text)
    label.setObjectName("FieldLabel")
    return label


def set_language(options, lang: str) -> None:
    options.lblType.setText(tr("dl.type_label", lang).upper())
    options.lblFormat.setText(tr("dl.format_label", lang).upper())
    options.lblFolder.setText(tr("dl.folder_label", lang).upper())


def short_label(label: str) -> str:
    parts = [part.strip() for part in label.split("·")]
    return " · ".join(parts[1:]) if len(parts) > 1 else label
