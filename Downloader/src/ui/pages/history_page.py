"""Compatibility re-export for LibraryInterface."""

from __future__ import annotations

from .library_page import LibraryInterface

HistoryInterface = LibraryInterface

__all__ = ["HistoryInterface", "LibraryInterface"]

