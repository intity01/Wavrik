"""Non-worker interactions for the workspace page."""

from __future__ import annotations

from src.core.parser import normalizeUrl, parseImportFile, parseImportText
from src.ui.components.banners import ClipboardBanner, PlaylistBanner, UpdateBanner


class WorkspaceInteractionMixin:
    def _onPlaylistDetected(self, url: str, title: str, count: int, entries: list) -> None:
        self._removeCard(url)
        banner = PlaylistBanner(title, count)
        urls = [item.get("url", "") for item in entries]
        banner.addAllRequested.connect(lambda: self.addUrls(urls))
        banner.dismissed.connect(banner.deleteLater)
        self.bannerArea.addWidget(banner)

    def showClipboardBanner(self, url: str) -> None:
        if normalizeUrl(url) in self._cards:
            return
        banner = ClipboardBanner(url)
        banner.addRequested.connect(self.addUrl)
        banner.dismissed.connect(banner.deleteLater)
        self.bannerArea.addWidget(banner)


    def showUpdateBanner(self, info, view_callback) -> None:
        current = getattr(self, "_updateBanner", None)
        if current:
            current.deleteLater()
        banner = UpdateBanner(info)
        banner.viewRequested.connect(view_callback)
        banner.dismissed.connect(banner.deleteLater)
        self.bannerArea.addWidget(banner)
        self._updateBanner = banner

    def _onDownloadAll(self) -> None:
        self._downloadAllPending = True
        for card in list(self._cards.values()):
            if card.isDownloadable():
                card.beginDownload()

    def _applyPresetToQueued(self, preset_key: str) -> None:
        for card in self._cards.values():
            card.setPreset(preset_key)

    def _applyEngineToQueued(self, engine: str) -> None:
        for card in self._cards.values():
            card.setEngine(engine)

    def _updateEmptyState(self) -> None:
        has_items = bool(self._cards)
        self.queueContainer.setVisible(has_items)
        self.emptyState.setVisible(not has_items)
        suffix = "" if len(self._cards) == 1 else "s"
        self.queueCount.setText(f"{len(self._cards)} item{suffix}")
        can_download = any(card.canQueueDownload() for card in self._cards.values())
        self.downloadOptions.setQueueState(len(self._cards), can_download)

    def dragEnterEvent(self, event) -> None:
        mime = event.mimeData()
        if mime.hasUrls() or mime.hasText():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event) -> None:
        mime = event.mimeData()
        if mime.hasUrls():
            for item in mime.urls():
                path = item.toLocalFile()
                if item.isLocalFile() and path.lower().endswith(".txt"):
                    self.addUrls(parseImportFile(path))
        elif mime.hasText():
            self.addUrls(parseImportText(mime.text()))

    def _cleanup(self) -> None:
        workers = [*self._metaWorkers.values(), *self._downloadWorkers.values()]
        for worker in workers:
            worker.cancel()
