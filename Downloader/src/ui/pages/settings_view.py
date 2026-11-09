"""Layout and card construction helpers for the Settings page."""

from __future__ import annotations

from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QSpinBox, QVBoxLayout, QWidget

from src.ui.components.controls import ComboBox, LineEdit, PushButton, ToggleButton
from src.ui.i18n import tr


def settings_card(title: str) -> tuple[QFrame, QVBoxLayout, QLabel]:
    card = QFrame()
    card.setObjectName("SettingsCard")
    layout = QVBoxLayout(card)
    layout.setContentsMargins(14, 12, 14, 12)
    layout.setSpacing(8)
    heading = QLabel(title)
    heading.setObjectName("SectionTitle")
    layout.addWidget(heading)
    return card, layout, heading


def settings_row(label: str, control: QWidget) -> tuple[QHBoxLayout, QLabel]:
    row = QHBoxLayout()
    text = QLabel(label)
    text.setMinimumWidth(190)
    row.addWidget(text)
    row.addWidget(control, 1)
    return row, text


def build_appearance_card(page) -> QFrame:
    card, layout, page.appHeading = settings_card("Language & Appearance")
    page.languageCombo = ComboBox()
    page.languageCombo.setMaximumWidth(240)
    page.languageCombo.addItem("ไทย (Thai)", "th")
    page.languageCombo.addItem("English", "en")
    current = page._cfg.get("language", "th")
    index = next((i for i in range(page.languageCombo.count()) if page.languageCombo.itemData(i) == current), 0)
    page.languageCombo.setCurrentIndex(index)
    page.languageCombo.currentIndexChanged.connect(page._save_language)
    page.themeCombo = ComboBox()
    page.themeCombo.setMaximumWidth(240)
    for data in ("light", "dark"):
        page.themeCombo.addItem(tr(f"set.theme_{data}", current), data)
    page.themeCombo.setCurrentIndex(max(0, page.themeCombo.findData(page._cfg.get("theme", "light"))))
    page.themeCombo.currentIndexChanged.connect(page._save_theme)
    row_lang, page.lblLang = settings_row("Interface language", page.languageCombo)
    row_theme, page.lblTheme = settings_row("Theme", page.themeCombo)
    layout.addLayout(row_lang)
    layout.addLayout(row_theme)
    return card


def build_queue_card(page) -> QFrame:
    card, layout, page.queueHeading = settings_card("Queue Concurrency")
    page.queueHint = QLabel(tr("set.queue_hint", "en"), objectName="MutedText")
    page.queueHint.setWordWrap(True)
    page.concurrentSpin = QSpinBox()
    page.concurrentSpin.setRange(1, 5)
    page.concurrentSpin.setMaximumWidth(120)
    page.concurrentSpin.setValue(page._cfg.get("maxConcurrentDownloads", 2))
    page.concurrentSpin.valueChanged.connect(page._save_concurrency)
    layout.addWidget(page.queueHint)
    row_conc, page.lblConcurrent = settings_row("Simultaneous downloads", page.concurrentSpin)
    layout.addLayout(row_conc)
    return card


def build_cobalt_card(page) -> QFrame:
    card, layout, page.cobaltHeading = settings_card("Cobalt Media Engine")
    page.cobaltCheck = ToggleButton("Enable Cobalt stream extraction")
    page.cobaltCheck.setChecked(page._cfg.get("cobaltEnabled", True))
    page.cobaltCheck.toggled.connect(lambda v: page._save("cobaltEnabled", bool(v)))
    page.cobaltUrlInput = LineEdit(page._cfg.get("cobaltUrl", "https://api.cobalt.tools/"))
    page.cobaltUrlInput.setPlaceholderText("https://api.cobalt.tools/")
    page.cobaltUrlInput.textChanged.connect(lambda v: page._save("cobaltUrl", v.strip()))
    row_en, page.lblCobaltEn = settings_row("Enable Cobalt stream extraction", page.cobaltCheck)
    row_url, page.lblCobaltUrl = settings_row("Instance URL", page.cobaltUrlInput)
    layout.addLayout(row_en)
    layout.addLayout(row_url)
    return card


def build_turbo_card(page) -> QFrame:
    card, layout, page.turboHeading = settings_card("Download Acceleration (Turbo)")
    page.turboToggle = ToggleButton("Multi-segment turbo acceleration")
    page.turboToggle.setChecked(page._cfg.get("turboDownloadEnabled", True))
    page.turboToggle.toggled.connect(lambda v: page._save("turboDownloadEnabled", bool(v)))
    page.turboThreadsCombo = ComboBox()
    page.turboThreadsCombo.setMaximumWidth(120)
    for n in (2, 4, 8):
        page.turboThreadsCombo.addItem(str(n), n)
    cur = page._cfg.get("turboThreadCount", 4)
    page.turboThreadsCombo.setCurrentIndex(max(0, page.turboThreadsCombo.findData(cur)))
    page.turboThreadsCombo.currentIndexChanged.connect(
        lambda: page._save("turboThreadCount", int(page.turboThreadsCombo.currentData() or 4))
    )
    row_en, page.lblTurboEn = settings_row("Multi-segment turbo acceleration", page.turboToggle)
    row_th, page.lblTurboThreads = settings_row("Parallel segments per file", page.turboThreadsCombo)
    layout.addLayout(row_en)
    layout.addLayout(row_th)
    return card


def build_behavior_card(page) -> QFrame:
    card, layout, page.behHeading = settings_card("System Behavior")
    page.clipboardCheck = ToggleButton("Clipboard link suggestions")
    page.clipboardCheck.setChecked(page._cfg.get("clipboardMonitoring", True))
    page.clipboardCheck.toggled.connect(lambda value: page._save("clipboardMonitoring", value))
    page.trayCheck = ToggleButton("Continue in system tray")
    page.trayCheck.setChecked(page._cfg.get("minimizeToTray", False))
    page.trayCheck.toggled.connect(lambda value: page._save("minimizeToTray", value))
    page.openLogsBtn = PushButton("Open Log Folder")
    page.openLogsBtn.clicked.connect(page._open_logs)
    row_clip, page.lblClipboard = settings_row("Clipboard link suggestions", page.clipboardCheck)
    row_tray, page.lblTray = settings_row("Continue in system tray", page.trayCheck)
    row_logs, page.lblLogs = settings_row("Log files", page.openLogsBtn)
    layout.addLayout(row_clip)
    layout.addLayout(row_tray)
    layout.addLayout(row_logs)
    return card
