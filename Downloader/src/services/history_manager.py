"""Thread-safe download history repository."""

from __future__ import annotations

import threading
from datetime import UTC, datetime
from typing import Any

from src.core.json_store import JsonStore
from src.domain.models import HistoryItem, HistoryRecord


class HistoryManager:
    """Persist successful, failed, and cancelled jobs."""

    SCHEMA_VERSION = 2

    def __init__(self, config, logger=None):
        self.config = config
        self.logger = logger
        self.historyFile = config.historyFile
        self._store = JsonStore(self.historyFile)
        self._lock = threading.RLock()
        self.history = self._load_history()

    def _load_history(self) -> list[dict[str, Any]]:
        payload = self._store.read({"schemaVersion": self.SCHEMA_VERSION, "entries": []})
        if isinstance(payload, list):
            entries = payload
        elif isinstance(payload, dict) and self._supported_schema(payload.get("schemaVersion", 1)):
            entries = payload.get("entries", [])
        else:
            self._store.backup()
            return []
        if not isinstance(entries, list):
            self._store.backup()
            return []
        return [self._migrate(entry) for entry in entries if isinstance(entry, dict)]

    def _supported_schema(self, value: Any) -> bool:
        return isinstance(value, int) and not isinstance(value, bool) and 1 <= value <= self.SCHEMA_VERSION

    def _migrate(self, entry: dict[str, Any]) -> dict[str, Any]:
        migrated = dict(entry)
        aliases = {"media_type": "mediaType", "file_path": "filePath", "file_size": "fileSize"}
        for old, new in aliases.items():
            if old in migrated and new not in migrated:
                migrated[new] = migrated.pop(old)
        migrated.setdefault("status", "completed" if migrated.get("success") else "failed")
        migrated.setdefault("error", "")
        return migrated

    def _save(self) -> None:
        self._store.write({"schemaVersion": self.SCHEMA_VERSION, "entries": self.history})

    def _unpack_legacy_add_entry(
        self, record_or_url: str, args: tuple[Any, ...], kwargs: dict[str, Any],
    ) -> HistoryRecord:
        k = kwargs.get
        return HistoryRecord(
            url=record_or_url or k("url", ""),
            title=args[0] if len(args) > 0 else k("title", "Untitled"),
            media_type=args[1] if len(args) > 1 else k("mediaType", k("media_type", "")),
            format=args[2] if len(args) > 2 else k("format", ""),
            file_path=args[3] if len(args) > 3 else k("filePath", k("file_path", "")),
            is_success=args[4] if len(args) > 4 else k("isSuccess", k("is_success", True)),
            file_size=args[5] if len(args) > 5 else k("fileSize", k("file_size", 0)),
            status=args[6] if len(args) > 6 else k("status"),
            error=args[7] if len(args) > 7 else k("error", ""),
            thumbnail_path=args[8] if len(args) > 8 else k("thumbnailPath", k("thumbnail_path", "")),
        )

    def addEntry(
        self, record_or_url: HistoryRecord | str | None = None, *args: Any, **kwargs: Any,
    ) -> HistoryItem:
        if isinstance(record_or_url, HistoryRecord):
            rec = record_or_url
        else:
            rec = self._unpack_legacy_add_entry(record_or_url or "", args, kwargs)
        entry: HistoryItem = {
            "timestamp": datetime.now(UTC).isoformat(timespec="seconds"),
            "url": rec.url,
            "title": rec.title or "Untitled",
            "mediaType": rec.media_type,
            "format": rec.format,
            "filePath": rec.file_path,
            "success": rec.is_success,
            "status": rec.status or ("completed" if rec.is_success else "failed"),
            "fileSize": rec.file_size,
            "error": rec.error,
            "thumbnailPath": rec.thumbnail_path,
        }
        with self._lock:
            self.history.insert(0, entry)
            self.history = self.history[:1000]
            self._save()
        return entry

    def getHistory(self, limit: int = 100) -> list[dict[str, Any]]:
        with self._lock:
            return [dict(entry) for entry in self.history[:limit]]

    def search(self, query: str) -> list[dict[str, Any]]:
        needle = query.casefold()
        return [entry for entry in self.getHistory(1000) if needle in entry.get("title", "").casefold() or needle in entry.get("url", "").casefold()]

    def filterByType(self, mediaType: str) -> list[dict[str, Any]]:
        return [entry for entry in self.getHistory(1000) if entry.get("mediaType") == mediaType]

    def clearHistory(self) -> None:
        with self._lock:
            self.history.clear()
            self._save()
        if self.logger:
            self.logger.info("History cleared")

    def getStats(self) -> dict[str, float | int]:
        entries = self.getHistory(1000)
        return {
            "totalDownloads": len(entries),
            "successful": sum(entry.get("status") == "completed" for entry in entries),
            "failed": sum(entry.get("status") == "failed" for entry in entries),
            "audios": sum(entry.get("mediaType") == "audio" for entry in entries),
            "videos": sum(entry.get("mediaType") == "video" for entry in entries),
            "totalSizeMb": sum(int(entry.get("fileSize", 0)) for entry in entries) / 1048576,
        }

    def getStatistics(self) -> dict[str, int]:
        stats = self.getStats()
        return {"total": int(stats["totalDownloads"])}
