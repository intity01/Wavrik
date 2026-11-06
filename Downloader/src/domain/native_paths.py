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
    return candidate


def _is_dos_device(stem: str) -> bool:
    upper = stem.upper()
    return upper in _DOS_NAMES or upper.split(".")[0] in _DOS_NAMES


def filename_from_header(value: str) -> str:
    match = re.search(r"filename\*?=(?:UTF-8''|\")?([^;\"]+)", value, re.IGNORECASE)
    return unquote(match.group(1)) if match else ""
