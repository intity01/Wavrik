"""Precision download queue workspace."""

from __future__ import annotations

from PyQt6.QtCore import QThreadPool, pyqtSignal
from PyQt6.QtWidgets import QWidget

from src.core.parser import normalizeUrl
from src.ui.components.queue_card import QueueItemCard

from . import workspace_jobs, workspace_view
from .workspace_interactions import WorkspaceInteractionMixin


class WorkspaceInterface(WorkspaceInteractionMixin, QWidget):
    historyRequested = pyqtSignal()
    fileDownloaded = pyqtSignal(str)

    def __init__(self, downloader, historyManager, config, parent=None):
        super().__init__(parent)
        self._dl = downloader
        self._hist = historyManager
        self._cfg = config
        self._cards: dict[str, QueueItemCard] = {}
        self._metaWorkers: dict[str, object] = {}
        self._downloadWorkers: dict[str, object] = {}
        self._downloadAllPending = False
        self._metaPool = QThreadPool(self)
        self._metaPool.setMaxThreadCount(4)
        self._downloadPool = QThreadPool(self)
        self._downloadPool.setMaxThreadCount(config.get("maxConcurrentDownloads", 2))
        self.setAcceptDrops(True)
        workspace_view.build(self)
        self.destroyed.connect(self._cleanup)

    def setLanguage(self, lang: str) -> None:
        workspace_view.set_language(self, lang)

    def setMaxConcurrency(self, count: int) -> None:
        self._downloadPool.setMaxThreadCount(count)

    def addUrl(self, raw_url: str) -> None:
        url = normalizeUrl(raw_url)
        if not url:
            self.inputBar.showError("Enter a valid public http or https URL.")
            return
        if url in self._cards:
            self.inputBar.showError("This URL is already in the queue.")
            return
        card = QueueItemCard(url, self._cfg, self.downloadOptions.currentPresetKey(), self.downloadOptions.currentEngine())
        card.removeRequested.connect(self._removeCard)
        card.downloadRequested.connect(self._startDownload)
        card.cancelRequested.connect(self._cancelDownload)
        self._cards[url] = card
        self.listLay.insertWidget(self.listLay.count() - 1, card)
        self._cfg.update(firstRun=False)
        self._updateEmptyState()
        workspace_jobs.startMetadata(self, url)

    def addUrls(self, urls: list[str]) -> None:
        for url in urls[:100]:
            self.addUrl(url)

    def _removeCard(self, url: str) -> None:
        self._cancelDownload(url)
        worker = self._metaWorkers.pop(url, None)
        if worker:
            worker.cancel()
        card = self._cards.pop(url, None)
        if card:
            self.listLay.removeWidget(card)
            card.deleteLater()
        self._updateEmptyState()

    def _startDownload(self, url: str, preset_key: str, engine: str = "auto") -> None:
        if url in self._downloadWorkers:
            return
        workspace_jobs.startDownload(self, url, preset_key, engine)

    def _cancelDownload(self, url: str) -> None:
        worker = self._downloadWorkers.get(url)
        if worker:
            worker.cancel()
            card = self._cards.get(url)
            if card:
                card.setStatus("cancelled", "Cancelling")
                card.setActionEnabled(False)
        self._updateEmptyState()

    def _onMetaReady(self, url: str, metadata: dict) -> None:
        card = self._cards.get(url)
        if card:
            card.setMeta(url, metadata)
        self._metaWorkers.pop(url, None)

    def _onThumbnailReady(self, url: str, pixmap) -> None:
        card = self._cards.get(url)
        if card:
            card.setThumbnail(pixmap)

    def _onStatus(self, url: str, state: str, message: str) -> None:
        if state in {"fetching", "ready"} and url in self._downloadWorkers:
            return
        card = self._cards.get(url)
        if card:
            card.setStatus(state, message)
            if state == "ready" and self._downloadAllPending:
                card.beginDownload()
        self._updateEmptyState()

    def _onProgress(self, url: str, percent: float, speed: str, eta: str) -> None:
        card = self._cards.get(url)
        if card:
            card.updateProgress(percent, speed, eta)

    def _onError(self, url: str, message: str) -> None:
        card = self._cards.get(url)
        if card:
            card.setStatus("failed", message)
        self._metaWorkers.pop(url, None)
        self._updateEmptyState()

    def _onFinished(self, url: str, result) -> None:
        self._downloadWorkers.pop(url, None)
        card = self._cards.get(url)
        if card:
            card.finish(result)
        fp = getattr(result, "file_path", None) or (result.get("file_path") if isinstance(result, dict) else None)
        if fp:
            self.fileDownloaded.emit(str(fp))
        self._updateEmptyState()
