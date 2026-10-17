"""Worker creation and signal wiring for the workspace."""

from __future__ import annotations

import time
from pathlib import Path

from src.domain.models import DownloadJobConfig
from src.domain.presets import getPreset
from src.ui.workers.download_worker import DownloadWorker
from src.ui.workers.meta_worker import MetaWorker
from src.ui.workers.signals import WorkerSignals


def startMetadata(page, url: str) -> None:
    signals = WorkerSignals()
    worker = MetaWorker(url, page._dl, signals, page._metaPool)
    signals.metaReady.connect(page._onMetaReady)
    signals.thumbnailReady.connect(page._onThumbnailReady)
    signals.status.connect(page._onStatus)
    signals.error.connect(page._onError)
    signals.playlistDetected.connect(page._onPlaylistDetected)
    page._metaWorkers[url] = worker
    page._metaPool.start(worker)


def startDownload(page, url: str, preset_key: str, engine: str = "auto") -> None:
    card = page._cards.get(url)
    if not card:
        return
    preset = getPreset(preset_key)

    # Verify the save location before starting a worker.
    try:
        output_dir = page._cfg.getDownloadPath(preset.media_type)
        output_dir_obj = Path(output_dir)
        output_dir_obj.mkdir(parents=True, exist_ok=True)
        test_file = output_dir_obj / f".write_test_{time.monotonic_ns()}"
        test_file.touch()
        test_file.unlink()
    except OSError:
        card.setStatus("failed", "Cannot access save location. Choose another folder.")
        return
    
    signals = WorkerSignals()
    config = DownloadJobConfig(
        url=url, downloader=page._dl, preset=preset,
        output_dir=output_dir_obj, signals=signals,
        history=page._hist, title=card.getVideoTitle(), engine=engine,
    )
    worker = DownloadWorker(config)
    signals.progress.connect(page._onProgress)
    signals.status.connect(page._onStatus)
    signals.error.connect(page._onError)
    signals.finished.connect(page._onFinished)
    page._downloadWorkers[url] = worker
    page._downloadPool.start(worker)
