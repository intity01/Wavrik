"""Thumbnail download settings card."""

from __future__ import annotations

from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from src.ui.components.controls import ComboBox, ToggleButton


def build_thumbnail_card(config, save_callback) -> QFrame:
    """Build and return the thumbnail settings card."""
    card = QFrame()
    card.setObjectName("SettingsCard")
    layout = QVBoxLayout(card)
    layout.setContentsMargins(16, 14, 16, 14)
    
    _create_header(layout)
    check, details = _create_controls(config, save_callback)
    card.thumbnailToggle = check
    card.thumbnailDetails = details
    layout.addLayout(_row("Download thumbnails", check))
    layout.addWidget(details)
    return card


def _create_header(layout: QVBoxLayout) -> None:
    heading = QLabel("Thumbnails")
    heading.setObjectName("SectionTitle")
    layout.addWidget(heading)
    
    detail = QLabel("Thumbnails are saved in a thumbnails subfolder.")
    detail.setObjectName("MutedText")
    detail.setWordWrap(True)
    layout.addWidget(detail)


def _create_controls(config, save_callback):
    thumb_check = ToggleButton("Download thumbnails")
    thumb_check.setChecked(config.get("downloadThumbnail", False))
    thumb_format_combo = ComboBox()
    thumb_format_combo.addItems(["JPG", "PNG", "WEBP"])
    thumb_format_combo.setMaximumWidth(120)
    thumb_format_combo.setCurrentText(config.get("thumbnailFormat", "jpg").upper())
    thumb_format_combo.currentTextChanged.connect(lambda value: save_callback("thumbnailFormat", value.lower()))
    thumb_quality_combo = ComboBox()
    thumb_quality_combo.addItems(["Original", "High"])
    thumb_quality_combo.setMaximumWidth(120)
    thumb_quality_combo.setCurrentText(config.get("thumbnailQuality", "original").title())
    thumb_quality_combo.currentTextChanged.connect(lambda value: save_callback("thumbnailQuality", value.lower()))
    details = QWidget()
    detail_layout = QVBoxLayout(details)
    detail_layout.setContentsMargins(0, 0, 0, 0)
    detail_layout.addLayout(_row("Thumbnail format", thumb_format_combo))
    detail_layout.addLayout(_row("Thumbnail quality", thumb_quality_combo))
    details.setVisible(thumb_check.isChecked())
    thumb_check.toggled.connect(lambda value: _save_and_toggle(save_callback, value, details))
    return thumb_check, details


def _save_and_toggle(save_callback, value, details: QWidget) -> None:
    """Save the preference and reveal its dependent choices."""
    save_callback("downloadThumbnail", value)
    details.setVisible(value)


def _row(label: str, control: QWidget) -> QHBoxLayout:
    row = QHBoxLayout()
    text = QLabel(label)
    text.setMinimumWidth(170)
    row.addWidget(text)
    row.addWidget(control, 1)
    return row
