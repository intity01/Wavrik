"""yt-dlp download operation used by one cancellable session."""

from __future__ import annotations

import time
from collections.abc import Callable
from pathlib import Path

import yt_dlp

from .download_support import DownloadCancelled, log_error
from .models import AttemptContext, DownloadPreset, DownloadResult, JobState
from .utils import friendly_error
from .yt_options import YtDownloadSettings, buildOptions


def download(
    owner, url: str, output_dir: Path, preset: DownloadPreset,
    progress_callback: Callable | None,
) -> DownloadResult:
    started = time.time()
    hook = owner._progress_hook(progress_callback)
    settings = YtDownloadSettings.from_config(owner.config)
    options = buildOptions(output_dir, preset, hook, settings)
    ctx = AttemptContext(output_dir, preset, options, started, settings)
    for attempt in range(3):
        result = _attempt(owner, url, attempt, 3, ctx)
        if result is not None:
            return result
        if owner._cancel.is_set():
            return DownloadResult(False, JobState.CANCELLED)
        if attempt < 2:
            delay = min(settings.sleep_interval * (2 ** (attempt + 1)), settings.max_sleep_interval)
            if owner._cancel.wait(timeout=delay):
                return DownloadResult(False, JobState.CANCELLED)
    return DownloadResult(False, JobState.FAILED, error="The download could not be completed.", engine="yt-dlp")


def _attempt(
    self, url: str, attempt: int, max_attempts: int, ctx: AttemptContext,
) -> DownloadResult | None:
    try:
        with yt_dlp.YoutubeDL(ctx.options) as ydl:
            info = ydl.extract_info(url, download=True)
        file_path = self._resolve_output(ctx.output_dir, info or {}, ctx.preset, ctx.started)
        thumbnail = self._resolve_thumbnail(ctx.output_dir, ctx.started) if ctx.settings.download_thumbnail else None
        self.lastDownloadedFile = file_path
        if not file_path:
            return DownloadResult(False, JobState.FAILED, error="The output file could not be found.")
        return DownloadResult(
            True, JobState.COMPLETED, file_path=file_path,
            thumbnail_path=thumbnail, engine="yt-dlp",
        )
    except DownloadCancelled:
        return DownloadResult(False, JobState.CANCELLED)
    except Exception as exc:  # noqa: BLE001 - yt-dlp exposes provider-specific exceptions.
        if self._cancel.is_set():
            return DownloadResult(False, JobState.CANCELLED)
        message = str(exc).lower()
        limited = any(token in message for token in ("403", "forbidden", "rate limit", "unavailable", "try again later"))
        if limited:
            log_error(self.logger, f"Download retryable failure: {exc}")
            return None
        log_error(self.logger, f"Download failed: {exc}")
        return DownloadResult(False, JobState.FAILED, error=friendly_error(str(exc)), engine="yt-dlp")
