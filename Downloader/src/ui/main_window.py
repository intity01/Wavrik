"""Application shell and page navigation."""

from __future__ import annotations

from typing import Any

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
from src.ui.pages.audio_tools_page import AudioToolsInterface
from src.ui.pages.library_page import LibraryInterface
from src.ui.pages.settings_page import SettingsInterface
from src.ui.pages.workspace_page import WorkspaceInterface
from src.ui.theme.styles import applyTheme

from .window_lifecycle import WindowLifecycleMixin
from .window_setup import WindowDependencies, initialize, resolve_dependencies


class MediaDownloaderUI(WindowLifecycleMixin, QMainWindow):
    def __init__(
        self, deps_or_settings: WindowDependencies | Any = None, *args: Any, **kwargs: Any,
    ) -> None:
        super().__init__()
        initialize(self, resolve_dependencies(deps_or_settings, args, kwargs))

    def _build_shell(self) -> None:
        root = QWidget(objectName="AppRoot")
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
        self.pageAudioTools = AudioToolsInterface(self._cfg, self._hist)
        self.pageLibrary = LibraryInterface(self._hist)
        self.pageHistory = self.pageLibrary
        self.pageSettings = SettingsInterface(self._cfg, self._updater)
        pages = (
            ("WorkspaceInterface", self.pageWorkspace),
            ("AudioToolsInterface", self.pageAudioTools),
            ("LibraryInterface", self.pageLibrary),
            ("SettingsInterface", self.pageSettings),
        )
        for name, page in pages:
            page.setObjectName(name)
            self.stackedWidget.addWidget(page)
        self.pageWorkspace.fileDownloaded.connect(self.pageLibrary.enqueueAutoAnalyze)
        self.pageAudioTools.analysisCompleted.connect(self.pageLibrary.storeAnalysisResult)
        self.pageAudioTools.fileExported.connect(self.pageLibrary.enqueueAutoAnalyze)
        self.pageLibrary.redownloadRequested.connect(self._redownload)
        self.pageLibrary.openInAudioToolsRequested.connect(self._open_in_audio_tools)
        self.pageSettings.themeChanged.connect(self._refresh_theme)
        self.pageSettings.concurrencyChanged.connect(self.pageWorkspace.setMaxConcurrency)
        self.pageSettings.updateAvailable.connect(self._update_available)

    def _build_navigation(self) -> None:
        self._add_page(self.pageWorkspace, FluentIcon.HOME, "Downloads")
        self._add_page(self.pageAudioTools, FluentIcon.AUDIO, "Audio Tools")
        self._add_page(self.pageLibrary, FluentIcon.HISTORY, "Library")
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
        if self.stackedWidget.currentWidget() is self.pageLibrary:
            self.pageLibrary.refresh()

    def _redownload(self, url: str) -> None:
        self.switchTo(self.pageWorkspace)
        self.pageWorkspace.addUrl(url)

    def _open_in_audio_tools(self, file_path: str) -> None:
        self.switchTo(self.pageAudioTools)
        self.pageAudioTools.loadFile(file_path, self.pageLibrary.getCachedAnalysis(file_path))

    def _refresh_theme(self) -> None:
        applyTheme(self, self._cfg)

    def _schedule_update_check(self) -> None:
        return

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
