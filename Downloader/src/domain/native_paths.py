"""Safe filenames for native downloads."""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import unquote, urlsplit


_DOS_NAMES = frozenset(
    {"CON", "PRN", "AUX", "NUL"}
    | {f"COM{i}" for i in range(10)}
    | {f"LPT{i}" for i in range(10)}
)


def target_path(folder: Path, url: str, content_disposition: str, fallback_extension: str) -> Path:
    raw = filename_from_header(content_disposition) or Path(unquote(urlsplit(url).path)).name
    clean = re.sub(r"[<>:\\/*?|\x00-\x1f]", "_", Path(raw).name).strip(". ")
    stem = Path(clean).stem.strip(". ") if clean else ""
    if not stem:
        stem = "download"
    if stem.upper() in _DOS_NAMES:
        stem = f"_{stem}"
    ext = fallback_extension.lstrip(".") or "download"
    filename = f"{stem}.{ext}"
    candidate = folder / filename
    count = 2
    while candidate.exists() or candidate.with_suffix(candidate.suffix + ".part").exists():
        candidate = folder / f"{stem} ({count}).{ext}"
        count += 1
    return candidate


def filename_from_header(value: str) -> str:
    match = re.search(r"filename\*?=(?:UTF-8''|\")?([^;\"]+)", value, re.IGNORECASE)
    return unquote(match.group(1)) if match else ""
