"""Widget construction helpers for the download options panel."""

from __future__ import annotations

from PyQt6.QtWidgets import QGridLayout, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from .controls import ComboBox, LineEdit, PrimaryPushButton, PushButton, ToolButton


def build(options) -> None:
    root = QVBoxLayout(options)
    root.setContentsMargins(16, 14, 16, 14)
    root.setSpacing(12)
    root.addLayout(header(options))
    controls = controls_grid()
    options.mediaCombo = combo("Media type", ["Audio", "Video"])
    options.presetCombo = ComboBox()
    options.presetCombo.setAccessibleName("Format and quality")
    options.engineCombo = engine_combo()
    options.pathInput = LineEdit(options._cfg.get("downloadPath", ""))
    options.pathInput.setReadOnly(True)
    options.pathInput.setCursorPosition(0)
    options.pathInput.setAccessibleName("Download folder")
    options.browseButton = PushButton("Change folder")
    options.browseButton.setMaximumWidth(160)
    options.browseButton.clicked.connect(options._browse)
    add_main_fields(controls, options)
    root.addLayout(controls)
    options.advancedButton = ToolButton("Advanced options")
    options.advancedButton.setCheckable(True)
    options.advancedButton.setAccessibleDescription("Show download compatibility options")
    options.advancedPanel = advanced_panel(options.engineCombo)
    options.advancedButton.toggled.connect(options.advancedPanel.setVisible)
    root.addWidget(options.advancedButton)
    root.addWidget(options.advancedPanel)
    options.mediaCombo.currentTextChanged.connect(options._media_changed)
    options.presetCombo.currentIndexChanged.connect(options._preset_changed)
    options.engineCombo.currentIndexChanged.connect(options._engine_changed)


def header(options) -> QHBoxLayout:
    row = QHBoxLayout()
    text = QVBoxLayout()
    title = QLabel("Download options")
    title.setObjectName("SectionTitle")
    detail = QLabel("Used for new downloads. Active jobs keep their current settings.")
    detail.setObjectName("MutedText")
    detail.setWordWrap(True)
    text.addWidget(title)
    text.addWidget(detail)
    options.downloadAllButton = PrimaryPushButton("Download all")
    options.downloadAllButton.setEnabled(False)
    options.downloadAllButton.clicked.connect(options.downloadAllRequested.emit)
    row.addLayout(text, 1)
    row.addWidget(options.downloadAllButton)
    return row


def controls_grid() -> QGridLayout:
    controls = QGridLayout()
    controls.setHorizontalSpacing(10)
    controls.setVerticalSpacing(6)
    controls.setColumnStretch(0, 2)
    controls.setColumnStretch(1, 3)
    return controls


def combo(name: str, items: list[str]) -> ComboBox:
    control = ComboBox()
    control.addItems(items)
    control.setAccessibleName(name)
    return control


def engine_combo() -> ComboBox:
    control = combo("Download compatibility", [])
    control.addItem("Auto — recommended", "auto")
    control.addItem("Built-in downloader", "native")
    control.addItem("Compatibility downloader", "yt-dlp")
    return control


def add_main_fields(controls: QGridLayout, options) -> None:
    controls.addWidget(field_label("Media type"), 0, 0)
    controls.addWidget(field_label("Format and quality"), 0, 1)
    controls.addWidget(options.mediaCombo, 1, 0)
    controls.addWidget(options.presetCombo, 1, 1)
    controls.addWidget(field_label("Save location"), 2, 0, 1, 2)
    controls.addWidget(path_control(options.pathInput, options.browseButton), 3, 0, 1, 2)


def advanced_panel(engine_combo_control: ComboBox) -> QWidget:
    panel = QWidget()
    layout = QVBoxLayout(panel)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.addWidget(field_label("Download compatibility"))
    detail = QLabel("Leave this on Auto unless a download needs help.")
    detail.setObjectName("MutedText")
    layout.addWidget(detail)
    layout.addWidget(engine_combo_control)
    panel.setVisible(False)
    return panel


def path_control(path_input: LineEdit, button: PushButton) -> QWidget:
    row = QHBoxLayout()
    row.setContentsMargins(0, 0, 0, 0)
    row.addWidget(path_input, 1)
    row.addWidget(button)
    wrapper = QWidget()
    wrapper.setLayout(row)
    return wrapper


def field_label(text: str) -> QLabel:
    label = QLabel(text)
    label.setObjectName("FieldLabel")
    return label


def short_label(label: str) -> str:
    parts = [part.strip() for part in label.split("·")]
    return " · ".join(parts[1:]) if len(parts) > 1 else label
