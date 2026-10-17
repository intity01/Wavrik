"""Native download paths for direct files and unprotected media manifests."""

from __future__ import annotations

import shutil
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from urllib.parse import unquote, urlsplit

import requests

from src.core.runtime import find_ffmpeg

from .models import DownloadPreset, DownloadResult, JobState
from .native_file import NativeDownloadError, download_file
from .native_paths import target_path

__all__ = ["NativeDownloadError", "NativeDownloader", "native_kind"]


def native_kind(url: str) -> str | None:
    """Return the native route implied by a public URL, without fetching it."""
    path = urlsplit(url).path.lower()
    if path.endswith(".m3u8"):
        return "hls"
    if path.endswith(".mpd"):
        return "dash"
    if path.endswith((".mp4", ".m4v", ".webm", ".mkv", ".mov", ".mp3", ".m4a", ".aac", ".ogg", ".wav", ".flac")):
        return "file"
    return None


class NativeDownloader:
    """Download permitted direct files and FFmpeg-readable HLS/DASH manifests."""

    def __init__(self, cancel, logger=None):
        self._cancel = cancel
        self._logger = logger
        self._process: subprocess.Popen | None = None

    def cancel(self) -> None:
        if self._process and self._process.poll() is None:
            try:
                self._process.terminate()
            except OSError:
                pass

    def download(
        self,
        url: str,
        output_dir: Path,
        preset: DownloadPreset,
        progress: Callable[[dict], None] | None = None,
    ) -> DownloadResult:
        kind = native_kind(url)
        if kind in {"hls", "dash"}:
            return self._download_manifest(url, output_dir, preset, progress)
        return self._download_file(url, output_dir, preset, progress)

    def _download_file(self, url, output_dir, preset, progress) -> DownloadResult:
        return download_file(self._cancel, requests.get, url, output_dir, preset, progress)

    def _download_manifest(self, url, output_dir, preset, progress) -> DownloadResult:
        if self._cancel.is_set():
            return DownloadResult(False, JobState.CANCELLED, engine="native")
        executable = _ffmpeg_executable()
        if not executable:
            return DownloadResult(False, JobState.FAILED, error="FFmpeg is required for HLS or DASH downloads. Add ffmpeg.exe beside RunApp.bat.", engine="native")
        output_dir.mkdir(parents=True, exist_ok=True)
        stem = Path(unquote(urlsplit(url).path)).stem or "stream"
        target = target_path(output_dir, f"{stem}.{preset.container}", "", preset.container)
        command = [executable, "-y", "-nostdin", "-rw_timeout", "15000000", "-i", url, "-map", "0", "-c", "copy", str(target)]
        try:
            if progress:
                progress({"status": "downloading", "percent": 0.0, "speed": "FFmpeg", "eta": "—"})
            popen_kwargs = {"creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0)} if sys.platform == "win32" else {}
            self._process = subprocess.Popen(
                command, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE, text=True, **popen_kwargs,
            )
            _, stderr = self._process.communicate(timeout=300)
            return self._handle_manifest_result(target, stderr, progress)
        except subprocess.TimeoutExpired:
            if self._process:
                self._process.kill()
                try:
                    self._process.communicate()
                except Exception:
                    pass
            target.unlink(missing_ok=True)
            return DownloadResult(False, JobState.FAILED, error="FFmpeg timed out after 300 seconds.", engine="native")
        except OSError:
            return DownloadResult(False, JobState.FAILED, error="Could not start FFmpeg. Check that ffmpeg.exe is available.", engine="native")
        finally:
            self._process = None

    def _handle_manifest_result(self, target: Path, stderr: str | None, progress) -> DownloadResult:
        if self._cancel.is_set():
            target.unlink(missing_ok=True)
            return DownloadResult(False, JobState.CANCELLED, engine="native")
        if self._process and self._process.returncode != 0:
            return DownloadResult(False, JobState.FAILED, error=_manifest_error(stderr), engine="native")
        if not target.is_file() or target.stat().st_size == 0:
            return DownloadResult(False, JobState.FAILED, error="FFmpeg finished without producing a media file.", engine="native")
        if progress:
            progress({"status": "processing", "percent": 100.0, "speed": "", "eta": ""})
        return DownloadResult(True, JobState.COMPLETED, file_path=target, engine="native")


def _ffmpeg_executable() -> str | None:
    ffmpeg_dir = find_ffmpeg()
    if not ffmpeg_dir:
        return shutil.which("ffmpeg")
    exe_name = "ffmpeg.exe" if sys.platform == "win32" else "ffmpeg"
    executable = Path(ffmpeg_dir) / exe_name
    if executable.is_file():
        return str(executable)
    return shutil.which("ffmpeg")


def _manifest_error(stderr: str | None) -> str:
    if "403 Forbidden" in (stderr or ""):
        return "The media server rejected this stream (403). Try a fresh public manifest URL."
    return "This HLS/DASH stream could not be downloaded. It may be protected, expired, or require access permission."
