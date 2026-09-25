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
    return [
        {"title": item.get("title", "Untitled"), "url": item.get("webpage_url") or item.get("url", "")}
        for item in entries
    ]


def resolve_output(folder: Path, info: dict, preset: DownloadPreset, started: float) -> Path | None:
    requested = info.get("requested_downloads") or []
    candidates = [Path(item["filepath"]) for item in requested if item.get("filepath")]
    filename = info.get("_filename") or info.get("filepath")
    if filename:
        candidates.append(Path(filename))
    if preset.media_type == "audio":
        candidates.extend(path.with_suffix(f".{preset.container}") for path in candidates[:])
    for path in candidates:
        if path.is_file():
            return path
    recent = [path for path in folder.glob("*") if path.is_file() and path.stat().st_mtime >= started - 2]
    return max(recent, key=lambda path: path.stat().st_mtime, default=None)


def resolve_thumbnail(folder: Path, started: float) -> Path | None:
    thumbnail_dir = folder / "thumbnails"
    if not thumbnail_dir.exists():
        return None
    recent = [
        path for path in thumbnail_dir.glob("*")
        if path.is_file() and path.stat().st_mtime >= started - 2
    ]
    return max(recent, key=lambda path: path.stat().st_mtime, default=None)
