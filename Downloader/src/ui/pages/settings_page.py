"""Scrollable application settings."""

from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QSpinBox, QVBoxLayout, QWidget

from src.ui.components.controls import ComboBox, SmoothScrollArea, ToggleButton
from src.ui.components.update_card import UpdateCard
from src.ui.pages.settings import build_thumbnail_card


class SettingsInterface(QWidget):
    themeChanged = pyqtSignal()
    concurrencyChanged = pyqtSignal(int)
    updateAvailable = pyqtSignal(object)

    def __init__(self, config, updater, parent=None):
        super().__init__(parent)
        self._cfg = config
        self._updater = updater
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        scroll = SmoothScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(14)
        title = QLabel("Settings")
        title.setObjectName("PageTitle")
        subtitle = QLabel("Set appearance, queue behavior, and update preferences.")
        subtitle.setObjectName("PageSubtitle")
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addWidget(self._appearance_card())
        layout.addWidget(self._queue_card())
        layout.addWidget(self._behavior_card())
        layout.addWidget(build_thumbnail_card(self._cfg, self._save))
        self.updateCard = UpdateCard(self._updater, self._cfg)
        self.updateCard.updateAvailable.connect(self.updateAvailable.emit)
        layout.addWidget(self.updateCard)
        layout.addStretch(1)
        scroll.setWidget(content)
        root.addWidget(scroll)

    def _appearance_card(self) -> QFrame:
        card, layout = _settings_card("Appearance")
        self.themeCombo = ComboBox()
        self.themeCombo.addItems(["Dark", "Light"])
        self.themeCombo.setMaximumWidth(260)
        self.themeCombo.setCurrentText(self._cfg.get("theme", "dark").title())
        self.themeCombo.currentTextChanged.connect(self._save_theme)
        self.accentCombo = ComboBox()
        self.accentCombo.setMaximumWidth(260)
        accents = [("Blue", "#2563EB"), ("Teal", "#0F766E"), ("Violet", "#7C3AED"), ("Rose", "#BE123C")]
        for name, color in accents:
            self.accentCombo.addItem(name, color)
        current = self._cfg.get("accentColor", "#2563EB")
        index = next((i for i in range(self.accentCombo.count()) if self.accentCombo.itemData(i) == current), 0)
        self.accentCombo.setCurrentIndex(index)
        self.accentCombo.currentIndexChanged.connect(self._save_accent)
        layout.addLayout(_row("Theme", self.themeCombo))
        layout.addLayout(_row("Accent color", self.accentCombo))
        return card

    def _queue_card(self) -> QFrame:
        card, layout = _settings_card("Queue")
        detail = QLabel("Format, quality, and save location are selected on the Downloads page.")
        detail.setObjectName("MutedText")
        detail.setWordWrap(True)
        self.concurrentSpin = QSpinBox()
        self.concurrentSpin.setRange(1, 5)
        self.concurrentSpin.setMaximumWidth(120)
        self.concurrentSpin.setValue(self._cfg.get("maxConcurrentDownloads", 2))
        self.concurrentSpin.valueChanged.connect(self._save_concurrency)
        layout.addWidget(detail)
        layout.addLayout(_row("Simultaneous downloads", self.concurrentSpin))
        return card

    def _behavior_card(self) -> QFrame:
        card, layout = _settings_card("Behavior")
        self.clipboardCheck = ToggleButton("Clipboard link suggestions")
        self.clipboardCheck.setChecked(self._cfg.get("clipboardMonitoring", True))
        self.clipboardCheck.toggled.connect(lambda value: self._save("clipboardMonitoring", value))
        self.trayCheck = ToggleButton("Continue in system tray")
        self.trayCheck.setChecked(self._cfg.get("minimizeToTray", False))
        self.trayCheck.toggled.connect(lambda value: self._save("minimizeToTray", value))
        layout.addLayout(_row("Clipboard link suggestions", self.clipboardCheck))
        layout.addLayout(_row("Continue in system tray", self.trayCheck))
        return card

    def _save_theme(self, value: str) -> None:
        self._save("theme", value.lower())
        self.themeChanged.emit()

    def _save_accent(self) -> None:
        self._save("accentColor", self.accentCombo.currentData())
        self.themeChanged.emit()

    def _save_concurrency(self, value: int) -> None:
        self._save("maxConcurrentDownloads", value)
        self.concurrencyChanged.emit(value)

    def _save(self, key: str, value) -> None:
        self._cfg.set(key, value)
        self._cfg.saveSettings()


def _settings_card(title: str) -> tuple[QFrame, QVBoxLayout]:
    card = QFrame()
    card.setObjectName("SettingsCard")
    layout = QVBoxLayout(card)
    layout.setContentsMargins(16, 14, 16, 14)
    heading = QLabel(title)
    heading.setObjectName("SectionTitle")
    layout.addWidget(heading)
    return card, layout


def _row(label: str, control: QWidget) -> QHBoxLayout:
    row = QHBoxLayout()
    text = QLabel(label)
    text.setMinimumWidth(170)
    row.addWidget(text)
    row.addWidget(control, 1)
    return row
