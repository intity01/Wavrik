"""Compact utility toolbar for output format, save location, and engine."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from src.ui.i18n import tr

from .controls import ComboBox, LineEdit, PushButton, ToolButton


def build(options) -> None:
    root = QVBoxLayout(options)
    root.setContentsMargins(10, 8, 10, 8)
    root.setSpacing(6)
    _create_controls(options)
    root.addLayout(_row_one(options))
    root.addLayout(_row_two(options))
    options.advancedPanel, options.advancedLabel, options.advancedDetail = advanced_panel(options.engineCombo)
    options.advancedButton.toggled.connect(options.advancedPanel.setVisible)
    root.addWidget(options.advancedPanel)
    _connect_signals(options)
    _wire_tab_order(options)


def _create_controls(options) -> None:
    options.mediaCombo = ComboBox()
    options.mediaCombo.addItem("Audio", "audio")
    options.mediaCombo.addItem("Video", "video")
    options.mediaCombo.setFixedWidth(96)
    options.presetCombo = ComboBox()
    options.presetCombo.setAccessibleName("Format and quality")
    options.presetCombo.setMinimumWidth(160)
    options.engineCombo = engine_combo()
    options.pathInput = LineEdit(options._cfg.get("downloadPath", ""))
    options.pathInput.setReadOnly(True)
    options.pathInput.setFocusPolicy(Qt.FocusPolicy.NoFocus)
    options.pathInput.setCursorPosition(0)
    options.pathInput.setAccessibleName("Download folder")
    options.browseButton = PushButton("Change folder")
    options.browseButton.clicked.connect(options._browse)
    options.advancedButton = ToolButton("Advanced options")
    options.advancedButton.setCheckable(True)
    options.advancedButton.setAccessibleDescription("Show download compatibility options")
    options.downloadAllButton = PushButton("Download all")
    options.downloadAllButton.setEnabled(False)
    options.downloadAllButton.clicked.connect(options.downloadAllRequested.emit)
    options.lblType, options.lblFormat, options.lblFolder = field_label("TYPE"), field_label("FORMAT"), field_label("FOLDER")


def _connect_signals(options) -> None:
    options.mediaCombo.currentIndexChanged.connect(options._media_changed)
    options.presetCombo.currentIndexChanged.connect(options._preset_changed)
    options.engineCombo.currentIndexChanged.connect(options._engine_changed)


def _row_one(options) -> QHBoxLayout:
    row = QHBoxLayout()
    row.setSpacing(8)
    row.addWidget(options.lblType)
    row.addWidget(options.mediaCombo)
    row.addWidget(options.lblFormat)
    row.addWidget(options.presetCombo)
    row.addStretch(1)
    return row


def _row_two(options) -> QHBoxLayout:
    row = QHBoxLayout()
    row.setSpacing(8)
    row.addWidget(options.lblFolder)
    row.addWidget(options.pathInput, 1)
    row.addWidget(options.browseButton)
    row.addWidget(options.advancedButton)
    row.addWidget(options.downloadAllButton)
    return row


def _wire_tab_order(options) -> None:
    options.setTabOrder(options.mediaCombo, options.presetCombo)
    options.setTabOrder(options.presetCombo, options.browseButton)
    options.setTabOrder(options.browseButton, options.advancedButton)
    options.setTabOrder(options.advancedButton, options.downloadAllButton)


def engine_combo() -> ComboBox:
    control = ComboBox()
    control.setAccessibleName("Download compatibility")
    for label, key in (
        ("Auto — recommended", "auto"),
        ("Cobalt stream engine", "cobalt"),
        ("Built-in downloader", "native"),
        ("Compatibility downloader", "yt-dlp"),
    ):
        control.addItem(label, key)
    return control


def advanced_panel(engine_combo_control: ComboBox) -> tuple[QWidget, QLabel, QLabel]:
    panel = QWidget()
    layout = QHBoxLayout(panel)
    layout.setContentsMargins(0, 2, 0, 0)
    layout.setSpacing(8)
    lbl = field_label("COMPATIBILITY ENGINE")
    layout.addWidget(lbl)
    layout.addWidget(engine_combo_control)
    detail = QLabel("Leave on Auto unless a source requires specific extraction.", objectName="MutedText")
    layout.addWidget(detail, 1)
    panel.setVisible(False)
    return panel, lbl, detail


def field_label(text: str) -> QLabel:
    label = QLabel(text)
    label.setObjectName("FieldLabel")
    return label


def set_language(options, lang: str) -> None:
    options.lblType.setText(tr("dl.type_label", lang).upper())
    options.lblFormat.setText(tr("dl.format_label", lang).upper())
    options.lblFolder.setText(tr("dl.folder_label", lang).upper())
    options.browseButton.setText(tr("dl.change_folder", lang))
    options.advancedButton.setText(tr("dl.advanced_options", lang))
    options.downloadAllButton.setText(tr("dl.download_all", lang))
    for i in range(options.mediaCombo.count()):
        k = options.mediaCombo.itemData(i)
        options.mediaCombo.setItemText(i, tr(f"dl.media_{k}", lang))
    for i in range(options.engineCombo.count()):
        k = options.engineCombo.itemData(i)
        options.engineCombo.setItemText(i, tr(f"dl.engine_{k}", lang))
    if hasattr(options, "advancedLabel"):
        options.advancedLabel.setText(tr("dl.compat_engine", lang))
    if hasattr(options, "advancedDetail"):
        options.advancedDetail.setText(tr("dl.compat_engine_hint", lang))


def short_label(label: str) -> str:
    parts = [part.strip() for part in label.split("·")]
    return " · ".join(parts[1:]) if len(parts) > 1 else label
