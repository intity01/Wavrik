"""Scrollable application settings with single-locale support."""

from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QSpinBox, QVBoxLayout, QWidget

from src.ui.components.controls import ComboBox, SmoothScrollArea, ToggleButton
from src.ui.components.update_card import UpdateCard
from src.ui.i18n import tr


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
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(10)
        self.titleLabel = QLabel("Settings", objectName="PageTitle")
        self.subtitleLabel = QLabel(tr("set.subtitle", "en"), objectName="PageSubtitle")
        layout.addWidget(self.titleLabel)
        layout.addWidget(self.subtitleLabel)
        layout.addWidget(self._appearance_card())
        layout.addWidget(self._queue_card())
        layout.addWidget(self._behavior_card())
        self.updateCard = UpdateCard(self._updater, self._cfg)
        self.updateCard.updateAvailable.connect(self.updateAvailable.emit)
        layout.addWidget(self.updateCard)
        layout.addStretch(1)
        scroll.setWidget(content)
        root.addWidget(scroll)

    def _appearance_card(self) -> QFrame:
        card, layout, self.appHeading = _settings_card("Language & Appearance")
        self.languageCombo = ComboBox()
        self.languageCombo.setMaximumWidth(240)
        self.languageCombo.addItem("ไทย (Thai)", "th")
        self.languageCombo.addItem("English", "en")
        current = self._cfg.get("language", "th")
        index = next((i for i in range(self.languageCombo.count()) if self.languageCombo.itemData(i) == current), 0)
        self.languageCombo.setCurrentIndex(index)
        self.languageCombo.currentIndexChanged.connect(self._save_language)
        self.themeValueLabel = QLabel("Precision Graphite · Teal Accent", objectName="MutedText")
        row_lang, self.lblLang = _row("Interface language", self.languageCombo)
        row_theme, self.lblTheme = _row("Color surface", self.themeValueLabel)
        layout.addLayout(row_lang)
        layout.addLayout(row_theme)
        return card

    def _queue_card(self) -> QFrame:
        card, layout, self.queueHeading = _settings_card("Queue Concurrency")
        self.queueHint = QLabel(tr("set.queue_hint", "en"), objectName="MutedText")
        self.queueHint.setWordWrap(True)
        self.concurrentSpin = QSpinBox()
        self.concurrentSpin.setRange(1, 5)
        self.concurrentSpin.setMaximumWidth(120)
        self.concurrentSpin.setValue(self._cfg.get("maxConcurrentDownloads", 2))
        self.concurrentSpin.valueChanged.connect(self._save_concurrency)
        layout.addWidget(self.queueHint)
        row_conc, self.lblConcurrent = _row("Simultaneous downloads", self.concurrentSpin)
        layout.addLayout(row_conc)
        return card

    def _behavior_card(self) -> QFrame:
        card, layout, self.behHeading = _settings_card("System Behavior")
        self.clipboardCheck = ToggleButton("Clipboard link suggestions")
        self.clipboardCheck.setChecked(self._cfg.get("clipboardMonitoring", True))
        self.clipboardCheck.toggled.connect(lambda value: self._save("clipboardMonitoring", value))
        self.trayCheck = ToggleButton("Continue in system tray")
        self.trayCheck.setChecked(self._cfg.get("minimizeToTray", False))
        self.trayCheck.toggled.connect(lambda value: self._save("minimizeToTray", value))
        row_clip, self.lblClipboard = _row("Clipboard link suggestions", self.clipboardCheck)
        row_tray, self.lblTray = _row("Continue in system tray", self.trayCheck)
        layout.addLayout(row_clip)
        layout.addLayout(row_tray)
        return card

    def setLanguage(self, lang: str) -> None:
        self.titleLabel.setText(tr("set.title", lang))
        self.subtitleLabel.setText(tr("set.subtitle", lang))
        self.appHeading.setText(tr("set.appearance", lang))
        self.lblLang.setText(tr("set.lang_label", lang))
        self.lblTheme.setText(tr("set.theme_label", lang))
        self.queueHeading.setText(tr("set.queue", lang))
        self.queueHint.setText(tr("set.queue_hint", lang))
        self.lblConcurrent.setText(tr("set.concurrent_label", lang))
        self.behHeading.setText(tr("set.behavior", lang))
        self.lblClipboard.setText(tr("set.clipboard_label", lang))
        self.lblTray.setText(tr("set.tray_label", lang))

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


def _settings_card(title: str) -> tuple[QFrame, QVBoxLayout, QLabel]:
    card = QFrame()
    card.setObjectName("SettingsCard")
    layout = QVBoxLayout(card)
    layout.setContentsMargins(14, 12, 14, 12)
    layout.setSpacing(8)
    heading = QLabel(title)
    heading.setObjectName("SectionTitle")
    layout.addWidget(heading)
    return card, layout, heading


def _row(label: str, control: QWidget) -> tuple[QHBoxLayout, QLabel]:
    row = QHBoxLayout()
    text = QLabel(label)
    text.setMinimumWidth(190)
    row.addWidget(text)
    row.addWidget(control, 1)
    return row, text
