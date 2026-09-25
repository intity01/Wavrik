"""Fetch metadata without blocking the UI thread."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import unquote, urlsplit

from PyQt6.QtCore import QRunnable, pyqtSlot

from src.domain.native_downloader import native_kind
from src.domain.utils import friendly_error

from .thumbnail_worker import ThumbnailWorker


class MetaWorker(QRunnable):
    def __init__(self, url: str, downloader, signals, thumbnail_pool):
        super().__init__()
        self.url = url
        self.downloader = downloader.newSession()
        self.signals = signals
        self.thumbnail_pool = thumbnail_pool
        self.cancelled = False
        self.setAutoDelete(True)

    def cancel(self) -> None:
        self.cancelled = True
        self.downloader.cancelDownload()

    @pyqtSlot()
    def run(self) -> None:
        if self.cancelled:
            return
        self.signals.status.emit(self.url, "fetching", "Reading media information")
        try:
            metadata = _direct_metadata(self.url)
            if metadata:
                self.signals.metaReady.emit(self.url, metadata)
                self.signals.status.emit(self.url, "ready", "Ready to download")
                return
            result = self.downloader.inspect(self.url)
            if self.cancelled:
                return
            if result.get("type") == "playlist":
                self.signals.playlistDetected.emit(
                    self.url, result["title"], result["count"], result["entries"]
                )
                return
            metadata = result.get("metadata", {})
            self.signals.metaReady.emit(self.url, metadata)
            self.signals.status.emit(self.url, "ready", "Ready to download")
            thumbnail = metadata.get("thumbnail", "")
            if thumbnail:
                self.thumbnail_pool.start(ThumbnailWorker(self.url, thumbnail, self.signals))
        except Exception as exc:  # noqa: BLE001 - provider failures become a user-facing status.
            self.signals.error.emit(self.url, f"Could not read this URL. {friendly_error(str(exc))}")


def _direct_metadata(url: str) -> dict | None:
    if native_kind(url) != "file":
        return None
    filename = Path(unquote(urlsplit(url).path)).name or "download"
    return {
        "title": filename, "webpage_url": url, "duration": None,
        "thumbnail": "", "uploader": None,
    }
