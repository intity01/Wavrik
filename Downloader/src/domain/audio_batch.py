"""Batch audio-format downloads for the explicit all-formats preset."""

from __future__ import annotations

import time
from collections.abc import Callable
from pathlib import Path

from .models import DownloadResult, JobState
from .presets import PRESETS

STALE_PARTIAL_SECONDS = 60


def download_all(owner, url: str, output_dir: Path, progress_callback: Callable | None, engine: str) -> DownloadResult:
    formats = _audio_formats()
    if _uses_native(owner, url, engine):
        formats = formats[:1]  # The native route copies the source bytes; repeating it only duplicates the file.
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
    """Remove abandoned partial files; recently touched ones may belong to a running job."""
    cutoff = time.time() - STALE_PARTIAL_SECONDS
    for suffix in ("part", "temp", "ytdl"):
        for path in folder.glob(f"*.{container}.{suffix}"):
            try:
                if path.stat().st_mtime < cutoff:
                    path.unlink(missing_ok=True)
            except OSError:
                continue


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


def _uses_native(owner, url: str, engine: str) -> bool:
    return engine == "native" or (engine == "auto" and bool(owner._native_kind(url)))


def _download_one(owner, url, output_dir, preset, callback, engine):
    if _uses_native(owner, url, engine):
        owner._native = owner._new_native()
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
