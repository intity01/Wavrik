import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

from src.core.config import Config
from src.core.logger import Logger
from src.domain.models import DownloadResult, JobState
from src.services.history_manager import HistoryManager


class FakeDownloader:
    def __init__(self):
        self.cancelled = False

    def newSession(self):
        return FakeDownloader()

    def validateUrl(self, url: str) -> bool:
        return url.startswith(("http://", "https://"))

    def cancelDownload(self) -> None:
        self.cancelled = True

    def inspect(self, url: str) -> dict:
        if "playlist" in url:
            return {
                "type": "playlist",
                "title": "Example playlist",
                "count": 2,
                "entries": [
                    {"title": "One", "url": "https://example.com/one"},
                    {"title": "Two", "url": "https://example.com/two"},
                ],
            }
        return {
            "type": "video",
            "metadata": {
                "title": "Example media",
                "duration": 125,
                "uploader": "Example creator",
                "thumbnail": "",
            },
        }

    def download(self, url, output_dir, preset, progress_callback=None, engine="auto"):
        if progress_callback:
            progress_callback({"status": "downloading", "percent": 50, "speed": "1 MB/s", "eta": "00:02"})
            progress_callback({"status": "processing", "percent": 100, "speed": "", "eta": ""})
        output_dir.mkdir(parents=True, exist_ok=True)
        path = output_dir / f"example.{preset.container}"
        path.write_bytes(b"test")
        return DownloadResult(True, JobState.COMPLETED, path)


@pytest.fixture
def config(tmp_path: Path):
    cfg = Config(tmp_path / "appdata")
    cfg.update(
        downloadPath=str(tmp_path / "downloads"),
        minimizeToTray=False,
        checkUpdatesOnStartup=False,
    )
    return cfg


@pytest.fixture
def logger(tmp_path: Path):
    return Logger(tmp_path / "logs", "DEBUG")


@pytest.fixture
def history(config, logger):
    return HistoryManager(config, logger)


@pytest.fixture
def fake_downloader():
    return FakeDownloader()
