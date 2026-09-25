"""Retry, thumbnail, and rate-limit policy for yt-dlp."""

from __future__ import annotations

import sys
from collections.abc import Callable
from pathlib import Path

from .yt_format import template


def apply_thumbnail_options(options: dict, output_dir: Path, settings) -> None:
    if not settings.download_thumbnail:
        return
    thumbnail_dir = output_dir / "thumbnails"
    thumbnail_dir.mkdir(parents=True, exist_ok=True)
    options["writethumbnail"] = True
    options["convertthumbnails"] = settings.thumbnail_format
    options["thumbnail_template"] = str(thumbnail_dir / (template(settings.rename_pattern) + ".%(ext)s"))


def apply_rate_limit_protection(options: dict, settings) -> None:
    if not settings.rate_limit_protection:
        return
    options.update({
        "sleep_interval": settings.sleep_interval,
        "max_sleep_interval": settings.max_sleep_interval,
        "sleep_interval_subtitles": settings.sleep_interval,
        "sleep_interval_requests": settings.sleep_interval,
        "nocheckcertificate": False,
        "prefer_insecure": False,
        "geo_bypass": True,
        "geo_bypass_country": None,
        "geo_bypass_ip_block": None,
        "extractor_args": {"youtube": {"player_client": ["android", "web", "ios"], "player_skip": ["configs", "webpage"]}},
        "http_headers": _headers(),
    })


def retry_delays(sleep_interval: int = 1, max_sleep_interval: int = 10) -> dict[str, Callable[[int], int]]:
    return {
        kind: lambda attempt: min(sleep_interval * (2 ** attempt), max_sleep_interval)
        for kind in ("http", "fragment", "extractor", "file_access")
    }


def platform_user_agent() -> str:
    if sys.platform == "darwin":
        return "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    if sys.platform == "win32":
        return "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    return "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"


def _headers() -> dict[str, str]:
    return {
        "User-Agent": platform_user_agent(),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }
