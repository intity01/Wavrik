"""Cross-platform dialog compatibility re-exports."""

from .dialogs import get_open_file_path, get_save_directory, get_save_file_path

__all__ = [
    "get_open_file_path",
    "get_save_directory",
    "get_save_file_path",
]
