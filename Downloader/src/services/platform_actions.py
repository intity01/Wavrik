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
    ".run",
})


def open_path(path: str | Path) -> bool:
    target = Path(path)
    if not target.exists():
        return False
    if target.is_file() and target.suffix.lower() in BLOCKED_EXTENSIONS:
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
