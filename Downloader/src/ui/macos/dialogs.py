"""Compatibility re-exports for cross-platform file dialog helpers."""

from __future__ import annotations

from src.ui.dialogs import (
    get_open_file_path,
    get_save_directory,
    get_save_file_path,
)

__all__ = [
    "get_open_file_path",
    "get_save_directory",
    "get_save_file_path",
]

