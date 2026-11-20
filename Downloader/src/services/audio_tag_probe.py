"""Read container tags with ffprobe, or with the bundled ffmpeg when ffprobe is absent."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

from src.core.runtime import find_ffmpeg

_PROBE_TIMEOUT_SEC = 30
_ESCAPED = {"=", ";", "#", "\\", "\n"}


def _bin(name: str) -> str | None:
    folder = find_ffmpeg()
    exe = f"{name}.exe" if sys.platform == "win32" else name
    if folder and (p := Path(folder) / exe).is_file():
        return str(p)
    return shutil.which(name)


def _run(cmd: list[str]) -> str:
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if sys.platform == "win32" else 0
    proc = subprocess.run(
        cmd, capture_output=True, text=True, encoding="utf-8", errors="replace",
        check=False, creationflags=flags, timeout=_PROBE_TIMEOUT_SEC,
    )
    return proc.stdout if proc.returncode == 0 else ""


def _lower(tags: dict) -> dict[str, str]:
    return {str(k).lower(): str(v) for k, v in tags.items()}


def _probe_json(probe: str, path: Path) -> dict[str, str]:
    out = _run([probe, "-hide_banner", "-loglevel", "error", "-show_entries", "format_tags:stream_tags", "-of", "json", str(path)])
    if not out:
        return {}
    data = json.loads(out)
    tags = dict((data.get("streams") or [{}])[0].get("tags", {}))
    tags.update(data.get("format", {}).get("tags", {}))
    return _lower(tags)


def _split_entries(text: str) -> list[tuple[str, str | None]]:
    """Split FFMETADATA1 text into (key, value) pairs; a backslash escapes the next character."""
    entries: list[tuple[str, str | None]] = []
    key, value, escaped = "", None, False
    for ch in text.replace("\r\n", "\n") + "\n":
        if escaped:
            escaped = False
        elif ch == "\\":
            escaped = True
            continue
        elif ch == "\n":
            entries.append((key, value))
            key, value = "", None
            continue
        elif ch == "=" and value is None:
            value = ""
            continue
        if value is None:
            key += ch
        else:
            value += ch
    return entries


def parse_ffmetadata(text: str) -> dict[str, str]:
    """Return the global tags of an FFMETADATA1 document (stops at the first [SECTION])."""
    tags: dict[str, str] = {}
    for key, value in _split_entries(text):
        if key.startswith("["):
            break
        if value is not None and key and key[0] not in ";#":
            tags[key.lower()] = value
    return tags


def _ffmetadata(ffmpeg: str, path: Path) -> dict[str, str]:
    base = [ffmpeg, "-hide_banner", "-loglevel", "error", "-nostdin", "-i", str(path)]
    tags = parse_ffmetadata(_run([*base, "-f", "ffmetadata", "-"]))
    if not tags:  # Ogg/Opus keep Vorbis comments on the audio stream, not the container.
        tags = parse_ffmetadata(_run([*base, "-map_metadata", "0:s:a:0", "-f", "ffmetadata", "-"]))
    tags.pop("encoder", None)
    return tags


def probe_tags(path: Path) -> dict[str, str]:
    try:
        if probe := _bin("ffprobe"):
            return _probe_json(probe, path)
        if ffmpeg := _bin("ffmpeg"):
            return _ffmetadata(ffmpeg, path)
    except Exception:
        return {}
    return {}
