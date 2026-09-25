"""Batch audio-format downloads for the explicit all-formats preset."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from .models import DownloadResult, JobState
from .native_downloader import NativeDownloader
from .presets import PRESETS


def download_all(owner, url: str, output_dir: Path, progress_callback: Callable | None, engine: str) -> DownloadResult:
    formats = _audio_formats()
    files: list[Path] = []
    errors: list[str] = []
    for index, format_name in enumerate(formats):
        if owner._cancel.is_set():
            return DownloadResult(False, JobState.CANCELLED)
        preset = _preset_for(format_name)
        if not preset:
            errors.append(f"{format_name}: preset unavailable")
            continue
        _cleanup_partials(output_dir, format_name)
        callback = _progress_callback(progress_callback, index, len(formats))
        result = _download_one(owner, url, output_dir, preset, callback, engine)
        if result.success and result.file_path:
            files.append(result.file_path)
        elif result.error:
            errors.append(f"{format_name}: {result.error}")
    if progress_callback:
        progress_callback({"status": "processing", "percent": 100.0, "speed": "", "eta": ""})
    return _batch_result(files, errors, engine)


def _audio_formats() -> list[str]:
    return list(dict.fromkeys(
        preset.container for preset in PRESETS
        if preset.media_type.value == "audio" and preset.container not in {"best", "all"}
    ))


def _preset_for(container: str):
    return next((preset for preset in PRESETS if preset.container == container and preset.media_type.value == "audio"), None)


def _cleanup_partials(folder: Path, container: str) -> None:
    for suffix in ("part", "temp", "ytdl"):
        for path in folder.glob(f"*.{container}.{suffix}"):
            path.unlink(missing_ok=True)


def _progress_callback(callback: Callable | None, index: int, total: int) -> Callable | None:
    if not callback:
        return None

    def report(info: dict) -> None:
        progress = index + info.get("percent", 0) / 100
        callback({
            "status": info.get("status", "downloading"),
            "percent": progress / total * 100,
            "speed": info.get("speed", ""),
            "eta": info.get("eta", ""),
        })

    return report


def _download_one(owner, url, output_dir, preset, callback, engine):
    if engine == "native" or (engine == "auto" and owner._native_kind(url)):
        owner._native = NativeDownloader(owner._cancel, owner.logger)
        return owner._native.download(url, output_dir, preset, callback)
    return owner._download_ytdlp(url, output_dir, preset, callback)


def _batch_result(files: list[Path], errors: list[str], engine: str) -> DownloadResult:
    if files:
        message = f"Some formats failed: {'; '.join(errors)}" if errors else ""
        return DownloadResult(
            True, JobState.COMPLETED, file_path=files[0],
            additional_files=files[1:] or None, error=message, engine=engine,
        )
    details = "; ".join(errors) or "No audio format was downloaded."
    return DownloadResult(False, JobState.FAILED, error=f"Failed to download audio formats. {details}", engine=engine)
