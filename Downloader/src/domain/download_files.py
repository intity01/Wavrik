"""Resolve output artifacts and normalize extracted media metadata."""

from __future__ import annotations

from pathlib import Path

from .models import DownloadPreset


def metadata(info: dict) -> dict:
    return {
        "title": info.get("title", "Unknown title"),
        "duration": int(info.get("duration") or 0),
        "thumbnail": info.get("thumbnail", ""),
        "uploader": info.get("uploader", "Unknown creator"),
    }


def map_entries(entries: list[dict]) -> list[dict]:
    results = []
    for item in entries:
        url = item.get("webpage_url") or item.get("url", "")
        if url and not url.startswith(("http://", "https://")):
            url = f"https://www.youtube.com/watch?v={url}"
        results.append({"title": item.get("title", "Untitled"), "url": url})
    return results


_IGNORE_EXTS = frozenset({".part", ".ytdl", ".tmp", ".temp"})


def _is_valid_output(path: Path) -> bool:
    try:
        name = path.name.lower()
        return path.is_file() and not any(name.endswith(ext) for ext in _IGNORE_EXTS)
    except OSError:
        return False


def _safe_mtime(path: Path) -> float:
    try:
        return path.stat().st_mtime
    except OSError:
        return -1.0


def resolve_output(folder: Path, info: dict, preset: DownloadPreset, started: float) -> Path | None:
    requested = info.get("requested_downloads") or []
    candidates = [Path(item["filepath"]) for item in requested if item.get("filepath")]
    filename = info.get("_filename") or info.get("filepath")
    if filename:
        candidates.append(Path(filename))
    if preset.media_type == "audio":
        candidates.extend(path.with_suffix(f".{preset.container}") for path in candidates[:])
    for path in candidates:
        if _is_valid_output(path):
            return path
    recent = [
        (mtime, path) for path in folder.glob("*")
        if _is_valid_output(path) and (mtime := _safe_mtime(path)) >= started - 2
    ]
    return max(recent, key=lambda item: item[0])[1] if recent else None


def _is_safe_file(path: Path) -> bool:
    try:
        return path.is_file()
    except OSError:
        return False


def resolve_thumbnail(folder: Path, started: float) -> Path | None:
    thumbnail_dir = folder / "thumbnails"
    if not thumbnail_dir.exists():
        return None
    recent = [
        (mtime, path) for path in thumbnail_dir.glob("*")
        if _is_safe_file(path) and (mtime := _safe_mtime(path)) >= started - 2
    ]
    return max(recent, key=lambda item: item[0])[1] if recent else None
