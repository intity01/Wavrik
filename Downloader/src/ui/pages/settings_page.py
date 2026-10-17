"""Scrollable application settings."""

from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QSpinBox, QVBoxLayout, QWidget

from src.ui.components.controls import ComboBox, SmoothScrollArea, ToggleButton
from src.ui.components.update_card import UpdateCard
from src.ui.pages.settings import build_thumbnail_card


class SettingsInterface(QWidget):
    themeChanged = pyqtSignal()
    languageChanged = pyqtSignal(str)
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
        title = QLabel("Settings · ตั้งค่าระบบ", objectName="PageTitle")
        subtitle = QLabel("ตั้งค่าภาษา คิวงานดาวน์โหลด ระบบคลิปบอร์ด และการอัปเดต", objectName="PageSubtitle")
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
        card, layout = _settings_card("Language & Appearance")
        self.languageCombo = ComboBox()
        self.languageCombo.setMaximumWidth(260)
        self.languageCombo.addItem("ไทย (Thai)", "th")
        self.languageCombo.addItem("English", "en")
        current = self._cfg.get("language", "th")
        index = next((i for i in range(self.languageCombo.count()) if self.languageCombo.itemData(i) == current), 0)
        self.languageCombo.setCurrentIndex(index)
        self.languageCombo.currentIndexChanged.connect(self._save_language)
        theme_label = QLabel("Dark Studio · Teal")
        theme_label.setObjectName("MutedText")
        layout.addLayout(_row("Interface language", self.languageCombo))
        layout.addLayout(_row("Theme", theme_label))
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

    def _save_language(self) -> None:
        lang = str(self.languageCombo.currentData() or "th")
        self._save("language", lang)
        self.languageChanged.emit(lang)

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
