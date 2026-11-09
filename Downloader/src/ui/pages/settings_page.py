"""Scrollable application settings with single-locale support."""

from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget

from src.services.platform_actions import open_path
from src.ui.components.controls import SmoothScrollArea
from src.ui.components.update_card import UpdateCard
from src.ui.i18n import tr

from .settings_view import (
    build_appearance_card,
    build_behavior_card,
    build_cobalt_card,
    build_queue_card,
    build_turbo_card,
)


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
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)
        self.titleLabel = QLabel(tr("set.title", "en"), objectName="PageTitle")
        self.subtitleLabel = QLabel(tr("set.subtitle", "en"), objectName="PageSubtitle")
        layout.addWidget(self.titleLabel)
        layout.addWidget(self.subtitleLabel)
        self.turboCard = build_turbo_card(self)
        for card in (
            build_appearance_card(self),
            build_queue_card(self),
            self.turboCard,
            build_cobalt_card(self),
            build_behavior_card(self),
        ):
            layout.addWidget(card)
        self.updateCard = UpdateCard(self._updater, self._cfg)
        self.updateCard.updateAvailable.connect(self.updateAvailable.emit)
        layout.addWidget(self.updateCard)
        layout.addStretch(1)
        scroll.setWidget(content)
        root.addWidget(scroll)
        self._wire_tab_order()

    def _wire_tab_order(self) -> None:
        self.setTabOrder(self.languageCombo, self.themeCombo)
        self.setTabOrder(self.themeCombo, self.concurrentSpin)
        self.setTabOrder(self.concurrentSpin, self.turboToggle)
        self.setTabOrder(self.turboToggle, self.turboThreadsCombo)
        self.setTabOrder(self.turboThreadsCombo, self.cobaltCheck)
        self.setTabOrder(self.cobaltCheck, self.cobaltUrlInput)
        self.setTabOrder(self.cobaltUrlInput, self.clipboardCheck)
        self.setTabOrder(self.clipboardCheck, self.trayCheck)
        self.setTabOrder(self.trayCheck, self.openLogsBtn)
        if hasattr(self.updateCard, "checkButton"):
            self.setTabOrder(self.openLogsBtn, self.updateCard.checkButton)

    def _open_logs(self) -> None:
        log_dir = self._cfg.appDataDir / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        open_path(log_dir)

    def setLanguage(self, lang: str) -> None:
        self.titleLabel.setText(tr("set.title", lang))
        self.subtitleLabel.setText(tr("set.subtitle", lang))
        self.appHeading.setText(tr("set.appearance", lang))
        self.lblLang.setText(tr("set.lang_label", lang))
        self.lblTheme.setText(tr("set.theme_label", lang))
        for i in range(self.themeCombo.count()):
            self.themeCombo.setItemText(i, tr(f"set.theme_{self.themeCombo.itemData(i)}", lang))
        self.queueHeading.setText(tr("set.queue", lang))
        self.queueHint.setText(tr("set.queue_hint", lang))
        self.lblConcurrent.setText(tr("set.concurrent_label", lang))
        if hasattr(self, "turboHeading"):
            self.turboHeading.setText(tr("set.turbo_heading", lang))
            self.lblTurboEn.setText(tr("set.turbo_enable", lang))
            self.lblTurboThreads.setText(tr("set.turbo_threads", lang))
        if hasattr(self, "cobaltHeading"):
            self.cobaltHeading.setText(tr("set.cobalt_heading", lang))
            self.lblCobaltEn.setText(tr("set.cobalt_enable", lang))
            self.lblCobaltUrl.setText(tr("set.cobalt_url", lang))
        self.behHeading.setText(tr("set.behavior", lang))
        self.lblClipboard.setText(tr("set.clipboard_label", lang))
        self.lblTray.setText(tr("set.tray_label", lang))
        self.lblLogs.setText(tr("set.logs_label", lang))
        self.openLogsBtn.setText(tr("set.open_logs", lang))
        if hasattr(self.updateCard, "setLanguage"):
            self.updateCard.setLanguage(lang)

    def _save_language(self) -> None:
        lang = str(self.languageCombo.currentData() or "th")
        self._save("language", lang)
        self.languageChanged.emit(lang)

    def _save_theme(self) -> None:
        self._save("theme", str(self.themeCombo.currentData() or "light"))
        self.themeChanged.emit()

    def _save_concurrency(self, value: int) -> None:
        self._save("maxConcurrentDownloads", value)
        self.concurrencyChanged.emit(value)

    def _save(self, key: str, value) -> None:
        self._cfg.set(key, value)
        self._cfg.saveSettings()
