"""Runtime paths and bundled tool discovery."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path


def application_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[3]


def resource_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent))
    return Path(__file__).resolve().parents[2]


def find_ffmpeg() -> str | None:
    exe_name = "ffmpeg.exe" if sys.platform == "win32" else "ffmpeg"
    candidates = [
        application_root() / exe_name,
        resource_root() / exe_name,
        application_root() / "_internal" / exe_name,
    ]
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate.parent)
    executable = shutil.which("ffmpeg")
    return str(Path(executable).parent) if executable else None


def find_deno() -> str | None:
    """Find the bundled Deno runtime, or the installed fallback."""
    executable = "deno.exe" if sys.platform == "win32" else "deno"
    candidates = [
        application_root() / executable,
        resource_root() / executable,
        application_root() / "_internal" / executable,
    ]
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)
    try:
        from deno import find_deno_bin
        return find_deno_bin()
    except (FileNotFoundError, ImportError):
        return shutil.which("deno")


def find_rubberband() -> str | None:
    """Find bundled or local Rubber Band R3 CLI executable if available."""
    exe = "rubberband.exe" if sys.platform == "win32" else "rubberband"
    spike_rel = Path("spikes/003-rubberband-finer/tools/rubberband-4.0.0/rubberband-4.0.0-gpl-executable-windows") / exe
    candidates = [
        application_root() / exe,
        resource_root() / exe,
        application_root() / "_internal" / exe,
        application_root() / spike_rel,
    ]
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)
    return shutil.which("rubberband")

