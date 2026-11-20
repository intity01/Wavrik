"""Record normalisation helpers for the history store."""

from __future__ import annotations

import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.domain.models import HistoryRecord

_LEGACY_KEYS = (("media_type", "mediaType"), ("file_path", "filePath"), ("file_size", "fileSize"))


def migrate_entry(entry: dict[str, Any]) -> dict[str, Any]:
    migrated = dict(entry)
    for old, new in _LEGACY_KEYS:
        if old in migrated and new not in migrated:
            migrated[new] = migrated.pop(old)
    migrated.setdefault("status", "completed" if migrated.get("success") else "failed")
    migrated.setdefault("error", "")
    return migrated


def unpack_legacy_record(record_or_url: str, args: tuple[Any, ...], kwargs: dict[str, Any]) -> HistoryRecord:
    k = kwargs.get
    return HistoryRecord(
        url=record_or_url or k("url", ""), title=args[0] if len(args) > 0 else k("title", "Untitled"),
        media_type=args[1] if len(args) > 1 else k("mediaType", k("media_type", "")),
        format=args[2] if len(args) > 2 else k("format", ""), file_path=args[3] if len(args) > 3 else k("filePath", k("file_path", "")),
        is_success=args[4] if len(args) > 4 else k("isSuccess", k("is_success", True)),
        file_size=args[5] if len(args) > 5 else k("fileSize", k("file_size", 0)), status=args[6] if len(args) > 6 else k("status"),
        error=args[7] if len(args) > 7 else k("error", ""), thumbnail_path=args[8] if len(args) > 8 else k("thumbnailPath", k("thumbnail_path", "")),
    )


def normalise_path(path: Any) -> str:
    return os.path.normcase(os.path.abspath(str(path)))


def same_file(entry: dict[str, Any], target_norm: str) -> bool:
    raw_path = entry.get("filePath")
    return bool(raw_path) and normalise_path(raw_path) == target_norm


def local_audio_entry(file_path: str | Path, analysis: dict[str, Any]) -> dict[str, Any]:
    """Build a history row for a local file analysed outside the download flow."""
    p = Path(file_path)
    return {
        "timestamp": datetime.now(UTC).isoformat(timespec="seconds"), "url": "", "title": p.stem or "Local Audio",
        "mediaType": "audio", "format": p.suffix.lstrip(".").upper() or "AUDIO", "filePath": str(p),
        "success": True, "status": "completed", "fileSize": p.stat().st_size if p.is_file() else 0,
        "error": "", "thumbnailPath": "", "analysis": analysis,
    }
