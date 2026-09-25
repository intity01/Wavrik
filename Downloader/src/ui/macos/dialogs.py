"""macOS-specific file dialog helpers."""

from __future__ import annotations

import sys
from pathlib import Path

from PyQt6.QtWidgets import QFileDialog


def get_save_directory(parent=None, caption: str = "Select Directory", start_dir: str | Path = "") -> Path | None:
    if sys.platform == "darwin":
        return _native_directory(parent, caption, start_dir)
    selected = QFileDialog.getExistingDirectory(parent, caption, _start_path(start_dir))
    return Path(selected) if selected else None


def get_save_file_path(
    parent=None, caption: str = "Save File", default_name: str = "",
    filters: str = "All Files (*.*)", start_dir: str | Path = "",
) -> Path | None:
    if sys.platform == "darwin":
        return _native_save(parent, caption, default_name, filters, start_dir)
    selected, _ = QFileDialog.getSaveFileName(parent, caption, _save_path(start_dir, default_name), filters)
    return Path(selected) if selected else None


def get_open_file_path(
    parent=None, caption: str = "Open File",
    filters: str = "All Files (*.*)", start_dir: str | Path = "",
) -> Path | None:
    if sys.platform == "darwin":
        return _native_open(parent, caption, filters, start_dir)
    selected, _ = QFileDialog.getOpenFileName(parent, caption, _start_path(start_dir) or str(Path.home()), filters)
    return Path(selected) if selected else None


def _native_directory(parent, caption: str, start_dir: str | Path) -> Path | None:
    dialog = QFileDialog(parent, caption)
    dialog.setFileMode(QFileDialog.FileMode.Directory)
    dialog.setOption(QFileDialog.Option.ShowDirsOnly, True)
    dialog.setOption(QFileDialog.Option.DontUseNativeDialog, False)
    if start_dir:
        dialog.setDirectory(str(start_dir))
    if dialog.exec() and dialog.selectedFiles():
        return Path(dialog.selectedFiles()[0])
    return None


def _native_save(parent, caption: str, default_name: str, filters: str, start_dir: str | Path) -> Path | None:
    dialog = QFileDialog(parent, caption)
    dialog.setAcceptMode(QFileDialog.AcceptMode.AcceptSave)
    dialog.setFileMode(QFileDialog.FileMode.AnyFile)
    dialog.setOption(QFileDialog.Option.DontUseNativeDialog, False)
    if default_name:
        dialog.selectFile(default_name)
    if filters:
        dialog.setNameFilter(filters)
    if start_dir:
        dialog.setDirectory(str(start_dir))
    if dialog.exec() and dialog.selectedFiles():
        return Path(dialog.selectedFiles()[0])
    return None


def _native_open(parent, caption: str, filters: str, start_dir: str | Path) -> Path | None:
    dialog = QFileDialog(parent, caption)
    dialog.setAcceptMode(QFileDialog.AcceptMode.AcceptOpen)
    dialog.setFileMode(QFileDialog.FileMode.ExistingFile)
    dialog.setOption(QFileDialog.Option.DontUseNativeDialog, False)
    if filters:
        dialog.setNameFilter(filters)
    if start_dir:
        dialog.setDirectory(str(start_dir))
    if dialog.exec() and dialog.selectedFiles():
        return Path(dialog.selectedFiles()[0])
    return None


def _start_path(start_dir: str | Path) -> str:
    return str(start_dir) if start_dir else str(Path.home() / "Downloads")


def _save_path(start_dir: str | Path, default_name: str) -> str:
    base = Path(start_dir) if start_dir else Path.home() / "Downloads"
    return str(base / default_name)
