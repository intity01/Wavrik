"""Direct streaming downloader utilizing Cobalt API backend."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import requests

from src.core.config import Config
from .cobalt_client import CobaltClient, CobaltError, preset_to_cobalt_request
from .cobalt_models import CobaltResponse, CobaltStatus
from .cobalt_security import is_loopback_url, safe_media_filename, validate_media_url
from .cobalt_stream import MAX_STREAM_BYTES, CancelledDownload, open_media_stream, report, write_stream
from .models import DownloadPreset, DownloadResult, JobState, MediaType
from .native_paths import target_path
from .utils import friendly_error


def _fallback_extension(preset: DownloadPreset) -> str:
    if preset.container not in {"best", "all"}:
        return preset.container
    return "mp3" if preset.media_type == MediaType.AUDIO else "mp4"


def _content_length(value: str | None) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


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
        except CancelledDownload:
            return DownloadResult(False, JobState.CANCELLED, engine="cobalt")
        except Exception as exc:  # noqa: BLE001
            return DownloadResult(False, JobState.FAILED, error=friendly_error(str(exc)), engine="cobalt")

    def _allow_private(self) -> bool:
        base = getattr(self._client, "base_url", "")
        return isinstance(base, str) and is_loopback_url(base)

    def _validate_response(self, resp: CobaltResponse) -> str | None:
        if resp.status == CobaltStatus.ERROR:
            msg = resp.error_code or "Cobalt stream resolution failed."
            return f"Cobalt error: {msg}"
        if resp.status == CobaltStatus.PICKER:
            return "Cobalt returned multiple picker items. Single-stream download required."
        if resp.status not in (CobaltStatus.REDIRECT, CobaltStatus.TUNNEL) or not resp.url:
            return "Cobalt returned no downloadable stream URL."
        if not validate_media_url(resp.url, self._allow_private()):
            return "Cobalt returned an unsafe media URL."
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
            with open_media_stream(resp.url, self._allow_private(), headers) as stream_resp:
                stream_resp.raise_for_status()
                target = self._target(resp, stream_resp, target_dir, preset)
                temporary = target.with_suffix(target.suffix + ".part")
                total = _content_length(stream_resp.headers.get("content-length"))
                report(progress, "downloading", 0.0, "—", "—")
                self._write_stream(stream_resp, temporary, total, progress)
                temporary.replace(target)
                report(progress, "processing", 100.0, "", "")
                return DownloadResult(True, JobState.COMPLETED, file_path=target, engine="cobalt")
        finally:
            if temporary:
                temporary.unlink(missing_ok=True)

    @staticmethod
    def _target(resp: CobaltResponse, stream_resp, folder: Path, preset: DownloadPreset) -> Path:
        name = safe_media_filename(resp.filename, _fallback_extension(preset))
        ext = name.rsplit(".", 1)[-1]
        if not resp.filename:
            return target_path(folder, resp.url, stream_resp.headers.get("content-disposition", ""), ext)
        return target_path(folder, resp.url, f'filename="{name}"', ext)

    def _write_stream(
        self, resp: requests.Response, temporary: Path, total: int,
        progress: Callable | None, max_bytes: int = MAX_STREAM_BYTES,
    ) -> None:
        write_stream(self._cancel, resp, temporary, total, progress, max_bytes)
