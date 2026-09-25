"""Bounded thumbnail loader."""

from __future__ import annotations

import requests
from PyQt6.QtCore import QRunnable, pyqtSlot
from PyQt6.QtGui import QImage

_MAX_BYTES = 5 * 1024 * 1024


class ThumbnailWorker(QRunnable):
    def __init__(self, url: str, image_url: str, signals):
        super().__init__()
        self.url = url
        self.image_url = image_url
        self.signals = signals
        self.setAutoDelete(True)

    @pyqtSlot()
    def run(self) -> None:
        try:
            response = requests.get(self.image_url, timeout=(5, 10), stream=True)
            response.raise_for_status()
            content_type = response.headers.get("content-type", "")
            if content_type and not content_type.startswith("image/"):
                return
            chunks: list[bytes] = []
            size = 0
            for chunk in response.iter_content(32768):
                size += len(chunk)
                if size > _MAX_BYTES:
                    return
                chunks.append(chunk)
            image = QImage()
            if image.loadFromData(b"".join(chunks)):
                self.signals.thumbnailReady.emit(self.url, image)
        except requests.RequestException:
            return
