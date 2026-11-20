"""Thread-safe download history repository."""

from __future__ import annotations

import threading
from pathlib import Path
from datetime import UTC, datetime
from typing import Any

from src.core.json_store import JsonStore
from src.domain.models import HistoryItem, HistoryRecord

from .history_records import local_audio_entry, migrate_entry, normalise_path, same_file, unpack_legacy_record

_ANALYSIS_KEYS = ("key", "enharmonic", "camelot", "bpm", "confidence", "section_summary", "badge", "key_candidates", "peaks", "duration_sec")


class HistoryManager:
    """Persist successful, failed, and cancelled jobs."""

    SCHEMA_VERSION = 2

    def __init__(self, config, logger=None):
        self.config, self.logger = config, logger
        self.historyFile = config.historyFile
        self._store = JsonStore(self.historyFile)
        self._lock = threading.RLock()
        self.history = self._load_history()

    def _load_history(self) -> list[dict[str, Any]]:
        payload = self._store.read({"schemaVersion": self.SCHEMA_VERSION, "entries": []})
        valid = isinstance(payload, dict) and self._supported_schema(payload.get("schemaVersion", 1))
        entries = payload.get("entries", []) if valid else (payload if isinstance(payload, list) else None)
        if not isinstance(entries, list):
            self._store.backup()
            return []
        return [migrate_entry(entry) for entry in entries if isinstance(entry, dict)]

    def _supported_schema(self, value: Any) -> bool:
        return isinstance(value, int) and not isinstance(value, bool) and 1 <= value <= self.SCHEMA_VERSION

    def _save(self) -> None:
        if self._store.unreadable and not self._merge_unreadable_file():
            return
        self._store.write({"schemaVersion": self.SCHEMA_VERSION, "entries": self.history})

    def _merge_unreadable_file(self) -> bool:
        """Retry a file that could not be read at start-up; never overwrite it while it is unreadable."""
        stored = self._load_history()
        if self._store.unreadable:
            if self.logger:
                self.logger.warning("History file is unreadable; keeping new entries in memory only.")
            return False
        self.history = [*self.history, *stored][:1000]
        return True

    def addEntry(
        self, record_or_url: HistoryRecord | str | None = None, *args: Any, **kwargs: Any,
    ) -> HistoryItem:
        rec = record_or_url if isinstance(record_or_url, HistoryRecord) else unpack_legacy_record(record_or_url or "", args, kwargs)
        entry: HistoryItem = {
            "timestamp": datetime.now(UTC).isoformat(timespec="seconds"), "url": rec.url, "title": rec.title or "Untitled",
            "mediaType": rec.media_type, "format": rec.format, "filePath": rec.file_path, "success": rec.is_success,
            "status": rec.status or ("completed" if rec.is_success else "failed"), "fileSize": rec.file_size,
            "error": rec.error, "thumbnailPath": rec.thumbnail_path, "analysis": rec.analysis or {},
        }
        with self._lock:
            self.history.insert(0, entry)
            self.history = self.history[:1000]
            self._save()
        return entry

    def updateAnalysis(self, file_path: str | Path, analysis: dict[str, Any]) -> None:
        if not file_path or not isinstance(analysis, dict):
            return
        compact = {k: analysis[k] for k in _ANALYSIS_KEYS if k in analysis}
        if not compact or analysis.get("status") == "unavailable":
            return  # A failed decode yields placeholder values that must not be cached.
        target_norm = normalise_path(file_path)
        with self._lock:
            matches = [e for e in self.history if same_file(e, target_norm)]
            for e in matches:
                e["analysis"] = compact
            if not matches:
                self.history.insert(0, local_audio_entry(file_path, compact))
                self.history = self.history[:1000]
            self._save()

    def getCachedAnalysis(self, file_path: str | Path | None) -> dict[str, Any] | None:
        if not file_path:
            return None
        target_norm = normalise_path(file_path)
        with self._lock:
            for e in self.history:
                analysis = e.get("analysis") if same_file(e, target_norm) else None
                if isinstance(analysis, dict) and analysis.get("key"):
                    return dict(analysis)
        return None

    def getHistory(self, limit: int = 100) -> list[dict[str, Any]]:
        with self._lock:
            return [dict(entry) for entry in self.history[:limit]]

    def search(self, query: str) -> list[dict[str, Any]]:
        needle = query.casefold()
        return [e for e in self.getHistory(1000) if needle in e.get("title", "").casefold() or needle in e.get("url", "").casefold()]

    def filterByType(self, mediaType: str) -> list[dict[str, Any]]:
        return [e for e in self.getHistory(1000) if e.get("mediaType") == mediaType]

    def clearHistory(self) -> None:
        with self._lock:
            self.history.clear()
            self._save()
        if self.logger:
            self.logger.info("History cleared")

    def getStats(self) -> dict[str, float | int]:
        e = self.getHistory(1000)
        return {
            "totalDownloads": len(e), "successful": sum(x.get("status") == "completed" for x in e),
            "failed": sum(x.get("status") == "failed" for x in e), "audios": sum(x.get("mediaType") == "audio" for x in e),
            "videos": sum(x.get("mediaType") == "video" for x in e), "totalSizeMb": sum(int(x.get("fileSize") or 0) for x in e) / 1048576,
        }

    def getStatistics(self) -> dict[str, int]:
        return {"total": int(self.getStats()["totalDownloads"])}

