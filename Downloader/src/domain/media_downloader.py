"""Independent cancellable download session per job."""

from __future__ import annotations

import threading
from collections.abc import Callable
from pathlib import Path

import yt_dlp

from src.core.parser import validateUrl

from .audio_batch import download_all
from .download_files import map_entries, metadata, resolve_output, resolve_thumbnail
from .download_support import DownloadCancelled
from .models import DownloadPreset, DownloadResult, JobState
from .native_downloader import NativeDownloader, native_kind
from .utils import percent
from .yt_download import download as download_ytdlp
from .yt_options import YtDownloadSettings, metadataOptions


class MediaDownloader:
    def __init__(self, logger=None, config=None):
        self.logger = logger
        self.config = config
        self._cancel = threading.Event()
        self.lastDownloadedFile: Path | None = None
        self._native: NativeDownloader | None = None

    def newSession(self) -> MediaDownloader:
        return MediaDownloader(self.logger, self.config)

    def validateUrl(self, url: str) -> bool:
        return validateUrl(url)

    def cancelDownload(self) -> None:
        self._cancel.set()
        if self._native:
            self._native.cancel()

    def inspect(self, url: str, cookie_file: str | None = None) -> dict:
        settings = YtDownloadSettings.from_config(self.config)
        cookie = settings.cookie_file if cookie_file is None else cookie_file
        options = metadataOptions(cookie, socket_timeout=settings.socket_timeout)
        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=False)
        entries = list(info.get("entries") or []) if info else []
        if entries:
            return {
                "type": "playlist", "title": info.get("title", "Playlist"),
                "count": len(entries), "entries": map_entries(entries),
            }
        return {"type": "video", "metadata": metadata(info or {})}

    def getVideoInfo(self, url: str, cookieFile: str | None = None) -> dict | None:
        try:
            result = self.inspect(url, cookieFile)
            return result.get("metadata") if result.get("type") == "video" else None
        except Exception:  # noqa: BLE001 - provider failures become a safe UI result.
            return None

    def detectContentType(self, url: str) -> dict:
        try:
            result = self.inspect(url)
            return result if result["type"] == "playlist" else {"type": "video"}
        except Exception:  # noqa: BLE001 - provider failures become a safe UI result.
            return {"type": "video"}

    def download(
        self, url: str, output_dir: Path, preset: DownloadPreset,
        progress_callback: Callable | None = None, engine: str = "auto",
    ) -> DownloadResult:
        selected = engine if engine in {"auto", "native", "yt-dlp"} else "auto"
        if preset.media_type.value == "audio" and preset.container == "all":
            return self._download_all_audio_formats(url, output_dir, preset, progress_callback, selected)
        if selected == "native" or (selected == "auto" and native_kind(url)):
            self._native = NativeDownloader(self._cancel, self.logger)
            result = self._native.download(url, output_dir, preset, progress_callback)
            if result.success:
                self.lastDownloadedFile = result.file_path
            if selected == "native" or result.success or result.state == JobState.CANCELLED:
                return result
        return self._download_ytdlp(url, output_dir, preset, progress_callback)

    def _download_ytdlp(self, url, output_dir, preset, progress_callback=None) -> DownloadResult:
        return download_ytdlp(self, url, output_dir, preset, progress_callback)

    def _download_all_audio_formats(
        self, url, output_dir, preset, progress_callback=None, engine="auto",
    ) -> DownloadResult:
        return download_all(self, url, output_dir, progress_callback, engine)

    def _progress_hook(self, callback: Callable | None) -> Callable:
        def hook(data: dict) -> None:
            if self._cancel.is_set():
                raise DownloadCancelled()
            if callback:
                self._report_progress(callback, data)

        return hook

    @staticmethod
    def _report_progress(callback: Callable, data: dict) -> None:
        status = data.get("status")
        if status == "downloading":
            callback({
                "status": "downloading", "percent": percent(data),
                "speed": data.get("_speed_str") or "—", "eta": data.get("_eta_str") or "—",
            })
        elif status == "finished":
            callback({"status": "processing", "percent": 100.0, "speed": "", "eta": ""})

    def _resolve_output(self, folder, info, preset, started):
        return resolve_output(folder, info, preset, started)

    def _resolve_thumbnail(self, folder, started):
        return resolve_thumbnail(folder, started)

    def _native_kind(self, url: str):
        return native_kind(url)
