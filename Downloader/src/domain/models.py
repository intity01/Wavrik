"""Typed download domain models."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any


class MediaType(str, Enum):
    AUDIO = "audio"
    VIDEO = "video"


class JobState(str, Enum):
    QUEUED = "Queued"
    FETCHING = "Fetching"
    DOWNLOADING = "Downloading"
    PROCESSING = "Processing"
    COMPLETED = "Completed"
    FAILED = "Failed"
    CANCELLED = "Cancelled"


@dataclass(frozen=True)
class DownloadPreset:
    key: str
    label: str
    media_type: MediaType
    container: str
    video_height: int | None = None
    audio_bitrate: str | None = None


@dataclass(frozen=True)
class DownloadResult:
    success: bool
    state: JobState
    file_path: Path | None = None
    thumbnail_path: Path | None = None
    error: str = ""
    engine: str = "yt-dlp"
    additional_files: list[Path] | None = None  # For batch downloads


@dataclass(frozen=True)
class MediaMetadata:
    title: str
    duration: int
    uploader: str
    thumbnail: str
    media_type: MediaType = MediaType.VIDEO


HistoryItem = dict[str, Any]


@dataclass(frozen=True)
class HistoryRecord:
    url: str
    title: str = "Untitled"
    media_type: str = ""
    format: str = ""
    file_path: str = ""
    is_success: bool = True
    file_size: int = 0
    status: str | None = None
    error: str = ""
    thumbnail_path: str = ""


@dataclass(frozen=True)
class DownloadJobConfig:
    url: str
    downloader: Any
    preset: DownloadPreset
    output_dir: Path
    signals: Any
    history: Any = None
    title: str = ""
    engine: str = "auto"


@dataclass(frozen=True)
class AttemptContext:
    output_dir: Path
    preset: DownloadPreset
    options: dict[str, Any]
    started: float
    settings: Any

