"""Build yt-dlp options from typed presets."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from src.core.runtime import find_deno, find_ffmpeg

from .models import DownloadPreset
from .yt_format import apply_preset_options, format_selector, template
from .yt_policy import (
    apply_rate_limit_protection,
    apply_thumbnail_options,
    retry_delays,
)


@dataclass(frozen=True)
class YtDownloadSettings:
    rename_pattern: str = "{title}"
    cookie_file: str = ""
    download_thumbnail: bool = False
    thumbnail_format: str = "jpg"
    thumbnail_quality: str = "original"
    socket_timeout: int = 30
    retry_count: int = 5
    sleep_interval: int = 1
    max_sleep_interval: int = 10
    rate_limit_protection: bool = True

    @classmethod
    def from_config(cls, config) -> YtDownloadSettings:
        if not config:
            return cls()
        return cls(
            rename_pattern=config.get("renamePattern", "{title}"),
            cookie_file=config.get("cookieFile", ""),
            download_thumbnail=config.get("downloadThumbnail", False),
            thumbnail_format=config.get("thumbnailFormat", "jpg"),
            thumbnail_quality=config.get("thumbnailQuality", "original"),
            rate_limit_protection=config.get("rateLimitProtection", True),
            sleep_interval=config.get("sleepInterval", 1),
            max_sleep_interval=config.get("maxSleepInterval", 10),
        )


def buildOptions(
    output_dir: Path, preset: DownloadPreset, progress_hook: Callable,
    settings: YtDownloadSettings, postprocessor_hook: Callable | None = None,
) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    options = _base_options(output_dir, preset, progress_hook, settings, postprocessor_hook)
    apply_rate_limit_protection(options, settings)
    apply_thumbnail_options(options, output_dir, settings)
    _apply_runtime_options(options, settings)
    apply_preset_options(options, preset)
    return options


def metadataOptions(cookie_file: str = "", flat: bool = False, socket_timeout: int = 30) -> dict:
    options = {"quiet": True, "no_warnings": True, "extract_flat": flat, "socket_timeout": socket_timeout}
    _apply_js_runtime(options)
    if cookie_file and Path(cookie_file).is_file():
        options["cookiefile"] = cookie_file
    return options


def _base_options(
    output_dir: Path, preset: DownloadPreset, hook: Callable,
    settings: YtDownloadSettings, postprocessor_hook: Callable | None = None,
) -> dict:
    options = {
        "format": format_selector(preset),
        "outtmpl": str(output_dir / (template(settings.rename_pattern) + ".%(ext)s")),
        "progress_hooks": [hook], "quiet": True, "no_warnings": True,
        "continuedl": True, "noplaylist": True, "windowsfilenames": True,
        "socket_timeout": settings.socket_timeout, "retries": settings.retry_count,
        "fragment_retries": settings.retry_count, "extractor_retries": settings.retry_count,
        "file_access_retries": 3,
        "retry_sleep_functions": retry_delays(settings.sleep_interval, settings.max_sleep_interval),
        "skip_unavailable_fragments": False, "ignoreerrors": True,
        "nooverwrites": preset.container != "all",
    }
    if postprocessor_hook:
        options["postprocessor_hooks"] = [postprocessor_hook]
    return options


def _apply_runtime_options(options: dict, settings: YtDownloadSettings) -> None:
    _apply_js_runtime(options)
    ffmpeg_dir = find_ffmpeg()
    if ffmpeg_dir:
        options["ffmpeg_location"] = ffmpeg_dir
    if settings.cookie_file and Path(settings.cookie_file).is_file():
        options["cookiefile"] = settings.cookie_file


def _apply_js_runtime(options: dict) -> None:
    if deno_path := find_deno():
        options["js_runtimes"] = {"deno": {"path": deno_path}}
