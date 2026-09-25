"""Application shell and page navigation."""

from __future__ import annotations

from typing import Any

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QMainWindow,
    QStackedWidget,
    QWidget,
)

from src.ui.components.navigation import (
    FluentIcon,
    NavigationItemPosition,
    NavigationPanel,
)
from src.ui.pages.history_page import HistoryInterface
from src.ui.pages.settings_page import SettingsInterface
from src.ui.pages.workspace_page import WorkspaceInterface
from src.ui.theme.styles import applyTheme

from .window_lifecycle import WindowLifecycleMixin
from .window_setup import WindowDependencies, initialize


class MediaDownloaderUI(WindowLifecycleMixin, QMainWindow):
    def __init__(
        self, deps_or_settings: WindowDependencies | Any = None, *args: Any, **kwargs: Any,
    ) -> None:
        super().__init__()
        deps = (
            deps_or_settings
            if isinstance(deps_or_settings, WindowDependencies)
            else self._unpack_legacy_deps(deps_or_settings, args, kwargs)
        )
        initialize(self, deps)

    @staticmethod
    def _unpack_legacy_deps(
        first: Any, args: tuple[Any, ...], kwargs: dict[str, Any],
    ) -> WindowDependencies:
        k = kwargs.get
        config = first if first is not None else k("config", k("settings"))
        logger = args[0] if len(args) > 0 else k("logger")
        downloader = (
            args[1] if len(args) > 1
            else k("downloader", k("downloads", k("engine")))
        )
        updater = args[2] if len(args) > 2 else k("updater")
        tray = args[3] if len(args) > 3 else k("tray", k("trayIcon"))
        history = (
            args[4] if len(args) > 4
            else k("history", k("historyManager"))
        )
        return WindowDependencies(
            config=config,
            logger=logger,
            downloader=downloader,
            updater=updater,
            tray=tray,
            history=history,
        )

    def _build_shell(self) -> None:
        root = QWidget()
        root.setObjectName("AppRoot")
        self.setCentralWidget(root)
        layout = QHBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.navigationPanel = NavigationPanel()
        self.stackedWidget = QStackedWidget()
        layout.addWidget(self.navigationPanel)
        layout.addWidget(self.stackedWidget, 1)

    def _build_pages(self) -> None:
        self.pageWorkspace = WorkspaceInterface(self._dl, self._hist, self._cfg)
        self.pageHistory = HistoryInterface(self._hist)
        self.pageSettings = SettingsInterface(self._cfg, self._updater)
        for name, page in (("WorkspaceInterface", self.pageWorkspace), ("HistoryInterface", self.pageHistory), ("SettingsInterface", self.pageSettings)):
            page.setObjectName(name)
            self.stackedWidget.addWidget(page)
        self.pageHistory.redownloadRequested.connect(self._redownload)
        self.pageSettings.themeChanged.connect(self._refresh_theme)
        self.pageSettings.concurrencyChanged.connect(self.pageWorkspace.setMaxConcurrency)
        self.pageSettings.updateAvailable.connect(self._update_available)

    def _build_navigation(self) -> None:
        self._add_page(self.pageWorkspace, FluentIcon.HOME, "Downloads")
        self._add_page(self.pageHistory, FluentIcon.HISTORY, "History")
        self._add_page(self.pageSettings, FluentIcon.SETTING, "Settings", NavigationItemPosition.BOTTOM)
        self.navigationPanel.setCurrentItem(self.pageWorkspace.objectName())
        self.stackedWidget.currentChanged.connect(self._page_changed)

    def _add_page(self, page, icon, text: str, position=NavigationItemPosition.TOP) -> None:
        self.navigationPanel.addItem(
            page.objectName(), icon, text,
            lambda checked=False, selected=page: self.switchTo(selected), position,
        )

    def switchTo(self, page) -> None:
        self.stackedWidget.setCurrentWidget(page)
        self.navigationPanel.setCurrentItem(page.objectName())

    def _page_changed(self, _index: int) -> None:
        if self.stackedWidget.currentWidget() is self.pageHistory:
            self.pageHistory.refresh()

    def _redownload(self, url: str) -> None:
        self.switchTo(self.pageWorkspace)
        self.pageWorkspace.addUrl(url)

    def _refresh_theme(self) -> None:
        applyTheme(self, self._cfg)

    def _schedule_update_check(self) -> None:
        if self._updater.isConfigured and self._cfg.get("checkUpdatesOnStartup", True):
            QTimer.singleShot(1200, lambda: self.pageSettings.updateCard.check(silent=True))

    def _update_available(self, info) -> None:
        self.pageWorkspace.showUpdateBanner(info, lambda: self.switchTo(self.pageSettings))

    def _setup_clipboard(self) -> None:
        self._clipboard = QApplication.clipboard()
        if self._clipboard:
            self._clipboard.dataChanged.connect(self._clipboard_changed)

    def _clipboard_changed(self) -> None:
        if not self._cfg.get("clipboardMonitoring", True) or not self._clipboard:
            return
        text = self._clipboard.text().strip()
        if text and text != self._lastClip and self._dl.validateUrl(text):
            self._lastClip = text
            self.pageWorkspace.showClipboardBanner(text)
