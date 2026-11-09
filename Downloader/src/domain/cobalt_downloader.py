"""Direct streaming downloader utilizing Cobalt API backend."""

from __future__ import annotations

import time
from collections.abc import Callable
from pathlib import Path

import requests

from src.core.config import Config
from .cobalt_client import CobaltClient, CobaltError, preset_to_cobalt_request
from .cobalt_models import CobaltResponse, CobaltStatus
from .models import DownloadPreset, DownloadResult, JobState, MediaType
from .native_paths import target_path
from .utils import friendly_error


class _CancelledDownload(Exception):
    """Internal signal for cooperative cancellation."""


def _rate(bytes_per_sec: float) -> str:
    if bytes_per_sec >= 1024 * 1024:
        return f"{bytes_per_sec / (1024 * 1024):.1f} MB/s"
    return f"{bytes_per_sec / 1024:.0f} KB/s"


def _time(seconds: float) -> str:
    total = max(0, int(seconds))
    return f"{total // 60:02d}:{total % 60:02d}"


def _report(progress: Callable | None, status: str, percent: float, speed: str, eta: str) -> None:
    if progress:
        progress({"status": status, "percent": percent, "speed": speed, "eta": eta})


def _target_extension(preset: DownloadPreset, cobalt_filename: str) -> str:
    if cobalt_filename and "." in cobalt_filename:
        return cobalt_filename.rsplit(".", 1)[-1]
    if preset.container not in {"best", "all"}:
        return preset.container
    return "mp3" if preset.media_type == MediaType.AUDIO else "mp4"


class CobaltDownloader:
    """Streams resolved media from Cobalt direct or tunnel URLs."""

    def __init__(self, cancel, client: CobaltClient | None = None, logger=None) -> None:
        self._cancel = cancel
        self._client = client or CobaltClient()
        self._logger = logger

    def cancel(self) -> None:
        if hasattr(self._cancel, "set"):
            self._cancel.set()

    def download(
        self,
        url: str,
        output_dir: Path,
        preset: DownloadPreset,
        progress: Callable | None = None,
    ) -> DownloadResult:
        """Download media via Cobalt API resolution and direct streaming."""
        if self._cancel.is_set():
            return DownloadResult(False, JobState.CANCELLED, engine="cobalt")
        try:
            req = preset_to_cobalt_request(url, preset)
            resp = self._client.resolve_stream(req)
            val_err = self._validate_response(resp)
            if val_err:
                return DownloadResult(False, JobState.FAILED, error=val_err, engine="cobalt")
            return self._stream_download(resp, output_dir, preset, progress)
        except (CobaltError, OSError) as exc:
            return DownloadResult(False, JobState.FAILED, error=str(exc), engine="cobalt")
        except _CancelledDownload:
            return DownloadResult(False, JobState.CANCELLED, engine="cobalt")
        except Exception as exc:  # noqa: BLE001
            return DownloadResult(False, JobState.FAILED, error=friendly_error(str(exc)), engine="cobalt")

    def _validate_response(self, resp: CobaltResponse) -> str | None:
        if resp.status == CobaltStatus.ERROR:
            msg = resp.error_code or "Cobalt stream resolution failed."
            return f"Cobalt error: {msg}"
        if resp.status == CobaltStatus.PICKER:
            return "Cobalt returned multiple picker items. Single-stream download required."
        if resp.status not in (CobaltStatus.REDIRECT, CobaltStatus.TUNNEL) or not resp.url:
            return "Cobalt returned no downloadable stream URL."
        return None

    def _stream_download(
        self,
        resp: CobaltResponse,
        output_dir: Path,
        preset: DownloadPreset,
        progress: Callable | None,
    ) -> DownloadResult:
        target_dir = Path(output_dir)
        target_dir.mkdir(parents=True, exist_ok=True)
        temporary: Path | None = None
        headers = {"User-Agent": f"WavrikMediaEngine/{Config.VERSION}"}
        try:
            with requests.get(resp.url, stream=True, timeout=(10, 60), headers=headers) as stream_resp:
                stream_resp.raise_for_status()
                ext = _target_extension(preset, resp.filename)
                disp = f'filename="{resp.filename}"' if resp.filename else stream_resp.headers.get("content-disposition", "")
                target = target_path(target_dir, resp.url, disp, ext)
                temporary = target.with_suffix(target.suffix + ".part")
                total = max(0, int(stream_resp.headers.get("content-length") or 0))
                _report(progress, "downloading", 0.0, "—", "—")
                self._write_stream(stream_resp, temporary, total, progress)
                temporary.replace(target)
                _report(progress, "processing", 100.0, "", "")
                return DownloadResult(True, JobState.COMPLETED, file_path=target, engine="cobalt")
        finally:
            if temporary:
                temporary.unlink(missing_ok=True)

    def _write_stream(
        self, resp: requests.Response, temporary: Path, total: int, progress: Callable | None
    ) -> None:
        written, started = 0, time.monotonic()
        with temporary.open("wb") as handle:
            for chunk in resp.iter_content(256 * 1024):
                if self._cancel.is_set():
                    raise _CancelledDownload()
                if not chunk:
                    continue
                written += len(chunk)
                handle.write(chunk)
                if progress:
                    elapsed = max(time.monotonic() - started, 0.01)
                    speed = written / elapsed
                    pct = (written * 100.0 / total) if total > 0 else 0.0
                    eta = max(total - written, 0) / speed if (speed > 0 and total > 0) else 0.0
                    _report(progress, "downloading", pct, _rate(speed), _time(eta) if total > 0 else "—")
