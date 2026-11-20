"""yt-dlp download operation used by one cancellable session."""

from __future__ import annotations

import time
from collections.abc import Callable
from pathlib import Path

from .download_support import DownloadCancelled, log_error
from .models import AttemptContext, DownloadPreset, DownloadResult, JobState
from .utils import friendly_error
from .yt_options import YtDownloadSettings, buildOptions

MAX_ATTEMPTS = 3
_RETRYABLE_TOKENS = ("403", "429", "forbidden", "rate limit", "too many requests", "unavailable", "try again later")


def download(
    owner, url: str, output_dir: Path, preset: DownloadPreset,
    progress_callback: Callable | None,
) -> DownloadResult:
    started = time.time()
    hook = owner._progress_hook(progress_callback)
    post_hook = owner._postprocessor_hook() if hasattr(owner, "_postprocessor_hook") else None
    settings = YtDownloadSettings.from_config(owner.config)
    options = buildOptions(output_dir, preset, hook, settings, post_hook)
    ctx = AttemptContext(output_dir, preset, options, started, settings)
    result = DownloadResult(False, JobState.FAILED, error="The download could not be completed.", engine="yt-dlp")
    for attempt in range(MAX_ATTEMPTS):
        result, retryable = _attempt(owner, url, ctx)
        if not retryable or result.state == JobState.CANCELLED:
            return result
        if attempt < MAX_ATTEMPTS - 1:
            delay = min(settings.sleep_interval * (2 ** (attempt + 1)), settings.max_sleep_interval)
            if owner._cancel.wait(timeout=delay):
                return DownloadResult(False, JobState.CANCELLED)
    return result


def _attempt(owner, url: str, ctx: AttemptContext) -> tuple[DownloadResult, bool]:
    """Run one yt-dlp attempt and return ``(result, retryable)``."""
    import yt_dlp

    try:
        with yt_dlp.YoutubeDL(ctx.options) as ydl:
            info = ydl.extract_info(url, download=True)
        return _finish(owner, ctx, info or {}), False
    except DownloadCancelled:
        return DownloadResult(False, JobState.CANCELLED), False
    except Exception as exc:  # yt-dlp exposes provider-specific exceptions.
        if owner._cancel.is_set():
            return DownloadResult(False, JobState.CANCELLED), False
        message = str(exc)
        retryable = any(token in message.lower() for token in _RETRYABLE_TOKENS)
        log_error(owner.logger, f"Download {'retryable failure' if retryable else 'failed'}: {exc}")
        failure = DownloadResult(False, JobState.FAILED, error=friendly_error(message), engine="yt-dlp")
        return failure, retryable


def _finish(owner, ctx: AttemptContext, info: dict) -> DownloadResult:
    file_path = owner._resolve_output(ctx.output_dir, info, ctx.preset, ctx.started)
    thumbnail = owner._resolve_thumbnail(ctx.output_dir, ctx.started) if ctx.settings.download_thumbnail else None
    owner.lastDownloadedFile = file_path
    if not file_path:
        return DownloadResult(False, JobState.FAILED, error="The output file could not be found.")
    return DownloadResult(
        True, JobState.COMPLETED, file_path=file_path,
        thumbnail_path=thumbnail, engine="yt-dlp",
    )
