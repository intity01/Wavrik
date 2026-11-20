"""Safe filenames for native downloads."""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import unquote, urlsplit


MAX_STEM_LENGTH = 150

_DOS_NAMES = frozenset(
    {"CON", "PRN", "AUX", "NUL", "CONIN$", "CONOUT$"}
    | {f"COM{i}" for i in range(10)}
    | {f"LPT{i}" for i in range(10)}
)


MEDIA_EXTENSIONS = frozenset({
    "mp3", "m4a", "aac", "ogg", "opus", "wav", "flac", "alac", "mka",
    "mp4", "m4v", "webm", "mkv", "mov",
})
_CONTENT_TYPE_EXTENSIONS = {
    "audio/mpeg": "mp3", "audio/mp4": "m4a", "audio/aac": "aac", "audio/ogg": "ogg",
    "audio/wav": "wav", "audio/x-wav": "wav", "audio/flac": "flac",
    "video/mp4": "mp4", "video/webm": "webm", "video/x-matroska": "mkv", "video/quicktime": "mov",
}
_ABSTRACT_CONTAINERS = frozenset({"best", "all"})


def native_extension(url: str, content_disposition: str, content_type: str, container: str) -> str:
    """Name a direct download after the bytes it really contains; the native route never transcodes."""
    raw = filename_from_header(content_disposition) or Path(unquote(urlsplit(url).path)).name
    suffix = Path(raw).suffix.lower().lstrip(".")
    if suffix in MEDIA_EXTENSIONS:
        return suffix
    mime = content_type.split(";")[0].strip().lower()
    if mime in _CONTENT_TYPE_EXTENSIONS:
        return _CONTENT_TYPE_EXTENSIONS[mime]
    return "bin" if container in _ABSTRACT_CONTAINERS else container


def manifest_extension(preset) -> str:
    """Container for stream copies; abstract presets use Matroska, which accepts any codec."""
    if preset.container not in _ABSTRACT_CONTAINERS:
        return preset.container
    return "mka" if getattr(preset.media_type, "value", preset.media_type) == "audio" else "mkv"


def reserve_target(
    folder: Path, url: str, content_disposition: str, extension: str, *, reserve_final: bool = False,
) -> Path:
    """Pick a free target and claim it atomically so concurrent jobs never share a file name."""
    for _ in range(10_000):
        candidate = target_path(folder, url, content_disposition, extension)
        marker = candidate if reserve_final else candidate.with_suffix(candidate.suffix + ".part")
        try:
            with marker.open("xb"):
                return candidate
        except FileExistsError:
            continue
    raise OSError("Could not reserve a unique file name.")


def target_path(folder: Path, url: str, content_disposition: str, fallback_extension: str) -> Path:
    raw = filename_from_header(content_disposition) or Path(unquote(urlsplit(url).path)).name
    clean = re.sub(r"[<>:\\/*?|\x00-\x1f]", "_", Path(raw).name).strip(". ")
    stem = Path(clean).stem.strip(". ") if clean else ""
    stem = stem[:MAX_STEM_LENGTH].rstrip(". ")
    if not stem:
        stem = "download"
    if _is_dos_device(stem):
        stem = f"_{stem}"
    clean_ext = re.sub(r"[<>:\\/*?|\x00-\x1f]", "_", fallback_extension).strip(". ")
    ext = clean_ext or "download"
    filename = f"{stem}.{ext}"
    candidate = folder / filename
    count = 2
    while candidate.exists() or candidate.with_suffix(candidate.suffix + ".part").exists():
        candidate = folder / f"{stem} ({count}).{ext}"
        count += 1
    if not candidate.resolve().is_relative_to(folder.resolve()):
        raise ValueError(f"Path traversal detected in destination: {filename}")
    return candidate


def _is_dos_device(stem: str) -> bool:
    upper = stem.upper()
    return upper in _DOS_NAMES or upper.split(".")[0] in _DOS_NAMES


def filename_from_header(value: str) -> str:
    match = re.search(r"filename\*?=(?:UTF-8''|\")?([^;\"]+)", value, re.IGNORECASE)
    return unquote(match.group(1)) if match else ""
