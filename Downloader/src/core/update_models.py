"""Typed update metadata shared across core and UI."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ReleaseAsset:
    name: str
    url: str
    size: int
    sha256: str


@dataclass(frozen=True)
class UpdateInfo:
    version: str
    notes: str
    release_url: str
    immutable: bool
    asset: ReleaseAsset | None = None

    @property
    def can_download_safely(self) -> bool:
        return bool(self.immutable and self.asset and self.asset.sha256)
