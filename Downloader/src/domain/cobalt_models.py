"""Domain models and data schemas for Cobalt API."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class CobaltStatus(str, Enum):
    """Cobalt v10 API status outcomes."""

    REDIRECT = "redirect"
    TUNNEL = "tunnel"
    PICKER = "picker"
    ERROR = "error"


@dataclass
class CobaltRequest:
    """Request payload parameters for Cobalt processing."""

    url: str
    videoQuality: str = "1080"
    audioFormat: str = "mp3"
    audioBitrate: str = "128"
    downloadMode: str = "auto"
    youtubeVideoCodec: str = "h264"
    alwaysProxy: bool = False
    filenameStyle: str = "classic"

    def to_dict(self) -> dict[str, Any]:
        return {
            "url": self.url,
            "videoQuality": self.videoQuality,
            "audioFormat": self.audioFormat,
            "audioBitrate": self.audioBitrate,
            "downloadMode": self.downloadMode,
            "youtubeVideoCodec": self.youtubeVideoCodec,
            "alwaysProxy": self.alwaysProxy,
            "filenameStyle": self.filenameStyle,
        }


@dataclass
class CobaltPickerItem:
    """Media item inside a picker response."""

    type: str
    url: str
    thumb: str = ""


@dataclass
class CobaltResponse:
    """Parsed response from Cobalt v10 API."""

    status: CobaltStatus
    url: str = ""
    filename: str = ""
    picker: list[CobaltPickerItem] = field(default_factory=list)
    error_code: str = ""
    error_context: dict[str, Any] = field(default_factory=dict)
    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CobaltResponse:
        if not isinstance(data, dict):
            return cls(status=CobaltStatus.ERROR, error_code="error.invalid_payload")
        raw_status = str(data.get("status") or "")
        try:
            status = CobaltStatus(raw_status)
        except ValueError:
            status = CobaltStatus.ERROR
        picker_items = [
            CobaltPickerItem(
                type=str(item.get("type") or ""),
                url=str(item.get("url") or ""),
                thumb=str(item.get("thumb") or ""),
            )
            for item in data.get("picker", [])
            if isinstance(item, dict)
        ]
        err = data.get("error")
        if isinstance(err, dict):
            code = str(err.get("code") or "")
            ctx = err.get("context") if isinstance(err.get("context"), dict) else {}
        elif isinstance(err, str):
            code, ctx = err, {}
        else:
            code = str(data.get("text") or ("error.unknown" if status == CobaltStatus.ERROR else ""))
            ctx = {}
        return cls(
            status=status,
            url=str(data.get("url") or ""),
            filename=str(data.get("filename") or ""),
            picker=picker_items,
            error_code=code,
            error_context=ctx,
            raw=data,
        )

    @property
    def is_success(self) -> bool:
        return self.status in (CobaltStatus.REDIRECT, CobaltStatus.TUNNEL)
