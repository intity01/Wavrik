"""Open local files and folders with the operating system."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


BLOCKED_EXTENSIONS = frozenset({
    ".bat", ".cmd", ".exe", ".ps1", ".vbs", ".vbe", ".js", ".jse",
    ".wsf", ".wsh", ".scr", ".msi", ".com", ".pif", ".application",
    ".gadget", ".msp", ".hta", ".cpl", ".msc", ".jar", ".lnk",
    ".inf", ".reg", ".sh", ".command", ".app", ".bin", ".desktop",
    ".run", ".url", ".py", ".pyw", ".appx", ".msix", ".chm", ".ws",
    ".wsc", ".scf", ".docm",
})

SAFE_OPEN_EXTENSIONS = frozenset({
    ".mp3", ".m4a", ".aac", ".ogg", ".oga", ".opus", ".wav", ".flac", ".wma", ".aiff", ".aif", ".mka",
    ".mp4", ".m4v", ".webm", ".mkv", ".mov", ".avi", ".flv", ".ts", ".mpg", ".mpeg", ".3gp", ".wmv",
    ".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp",
    ".lrc", ".srt", ".vtt", ".ass", ".ssa", ".txt",
})


def is_safe_to_open(target: Path) -> bool:
    """Directories are always openable; files only when on the media/document allow-list."""
    if target.is_dir():
        return True
    suffix = target.suffix.lower()
    return suffix in SAFE_OPEN_EXTENSIONS and suffix not in BLOCKED_EXTENSIONS


def open_path(path: str | Path) -> bool:
    target = Path(path)
    if not target.exists() or not is_safe_to_open(target):
        return False
    try:
        if sys.platform == "win32":
            os.startfile(str(target))
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(target)])
        else:
            subprocess.Popen(["xdg-open", str(target)])
        return True
    except OSError:
        return False


def open_parent(path: str | Path) -> bool:
    target = Path(path)
    folder = target if target.is_dir() else target.parent
    return open_path(folder)
