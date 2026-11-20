"""Validated, size-capped streaming of media resolved by Cobalt."""

from __future__ import annotations

import time
from collections.abc import Callable
from pathlib import Path
from urllib.parse import urljoin

import requests

from .cobalt_client import CobaltError
from .cobalt_security import validate_media_url

MAX_STREAM_BYTES = 10 * 1024 * 1024 * 1024
MAX_REDIRECTS = 5
_REDIRECT_CODES = frozenset({301, 302, 303, 307, 308})
_SIZE_ERROR = "Download size exceeds maximum permitted limit (10 GB)."


class CancelledDownload(Exception):
    """Internal signal for cooperative cancellation."""


def _rate(bytes_per_sec: float) -> str:
    if bytes_per_sec >= 1024 * 1024:
        return f"{bytes_per_sec / (1024 * 1024):.1f} MB/s"
    return f"{bytes_per_sec / 1024:.0f} KB/s"


def _time(seconds: float) -> str:
    total = max(0, int(seconds))
    return f"{total // 60:02d}:{total % 60:02d}"


def report(progress: Callable | None, status: str, percent: float, speed: str, eta: str) -> None:
    if progress:
        progress({"status": status, "percent": percent, "speed": speed, "eta": eta})


def open_media_stream(url: str, allow_private: bool, headers: dict[str, str]) -> requests.Response:
    """GET a media URL, validating the URL and every redirect hop."""
    current = url
    for _ in range(MAX_REDIRECTS + 1):
        safe = validate_media_url(current, allow_private)
        if not safe:
            raise CobaltError("Cobalt returned an unsafe media URL.")
        resp = requests.get(safe, stream=True, timeout=(10, 60), headers=headers, allow_redirects=False)
        if resp.status_code not in _REDIRECT_CODES:
            return resp
        location = str(resp.headers.get("location", ""))
        resp.close()
        current = urljoin(safe, location)
    raise CobaltError("Cobalt media URL redirected too many times.")


def _progress_tick(progress: Callable, written: int, total: int, started: float) -> None:
    speed = written / max(time.monotonic() - started, 0.01)
    pct = (written * 100.0 / total) if total > 0 else 0.0
    eta = max(total - written, 0) / speed if (speed > 0 and total > 0) else 0.0
    report(progress, "downloading", pct, _rate(speed), _time(eta) if total > 0 else "—")


def write_stream(
    cancel, resp: requests.Response, temporary: Path, total: int,
    progress: Callable | None, max_bytes: int = MAX_STREAM_BYTES,
) -> None:
    if total > max_bytes:
        raise CobaltError(_SIZE_ERROR)
    written, started, last_rep = 0, time.monotonic(), 0.0
    with temporary.open("wb") as handle:
        for chunk in resp.iter_content(256 * 1024):
            if cancel.is_set():
                raise CancelledDownload()
            if not chunk:
                continue
            written += len(chunk)
            if written > max_bytes:
                raise CobaltError(_SIZE_ERROR)
            handle.write(chunk)
            now = time.monotonic()
            if progress and (now - last_rep >= 0.05 or written == total):
                last_rep = now
                _progress_tick(progress, written, total, started)
