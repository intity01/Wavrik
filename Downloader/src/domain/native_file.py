"""Streaming implementation for direct native media files."""

from __future__ import annotations

import time
from collections.abc import Callable
from pathlib import Path

from .models import DownloadPreset, DownloadResult, JobState
from .native_paths import target_path
from .utils import friendly_error


class NativeDownloadError(RuntimeError):
    """An actionable failure from a native download route."""


def download_file(cancel, request_get, url: str, output_dir: Path, preset: DownloadPreset, progress: Callable | None) -> DownloadResult:
    output_dir.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with request_get(url, stream=True, timeout=(10, 60), headers={"User-Agent": "MediaDownloaderPRO/2.1"}) as response:
            _validate_response(response)
            target = target_path(output_dir, url, response.headers.get("content-disposition", ""), preset.container)
            temporary = target.with_suffix(target.suffix + ".part")
            total = int(response.headers.get("content-length") or 0)
            _report(progress, "downloading", 0.0, "—", "—")
            _stream(cancel, response, temporary, total, progress)
            temporary.replace(target)
            _report(progress, "processing", 100.0, "", "")
            return DownloadResult(True, JobState.COMPLETED, file_path=target, engine="native")
    except (OSError, NativeDownloadError) as exc:
        return DownloadResult(False, JobState.FAILED, error=_safe_error(exc), engine="native")
    except _CancelledDownload:
        return DownloadResult(False, JobState.CANCELLED, engine="native")
    except Exception as exc:  # noqa: BLE001 - request adapters expose provider-specific exceptions.
        return DownloadResult(False, JobState.FAILED, error=friendly_error(str(exc)), engine="native")
    finally:
        if temporary:
            temporary.unlink(missing_ok=True)


def _validate_response(response) -> None:
    if response.status_code in {401, 403}:
        raise NativeDownloadError("This file is not available to this app. Check access permission or use a fresh public link.")
    response.raise_for_status()
    if "text/html" in response.headers.get("content-type", "").lower():
        raise NativeDownloadError("This URL returned a web page, not a direct media file. Select Auto or yt-dlp for supported website URLs.")


def _safe_error(exc: Exception) -> str:
    return str(exc) if isinstance(exc, NativeDownloadError) else friendly_error(str(exc))


def _stream(cancel, response, temporary: Path, total: int, progress: Callable | None) -> None:
    written = 0
    started = time.monotonic()
    with temporary.open("wb") as handle:
        for chunk in response.iter_content(256 * 1024):
            if cancel.is_set():
                raise _CancelledDownload()
            if not chunk:
                continue
            handle.write(chunk)
            written += len(chunk)
            if progress:
                elapsed = max(time.monotonic() - started, 0.01)
                speed = written / elapsed
                percent = written * 100 / total if total else 0.0
                eta = max(total - written, 0) / speed if speed else 0
                _report(progress, "downloading", percent, _rate(speed), _time(eta) if total else "—")


class _CancelledDownload(Exception):
    """Internal control flow for a user cancellation."""


def _report(progress, status: str, percent: float, speed: str, eta: str) -> None:
    if progress:
        progress({"status": status, "percent": percent, "speed": speed, "eta": eta})


def _rate(bytes_per_second: float) -> str:
    if bytes_per_second >= 1024 * 1024:
        return f"{bytes_per_second / 1024 / 1024:.1f} MB/s"
    return f"{bytes_per_second / 1024:.0f} KB/s"


def _time(seconds: float) -> str:
    total = max(0, int(seconds))
    return f"{total // 60:02d}:{total % 60:02d}"
