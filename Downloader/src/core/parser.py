"""URL validation and import parsing."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

_TRACKING_KEYS = {"fbclid", "gclid", "si", "feature", "utm_source", "utm_medium", "utm_campaign"}


def normalizeUrl(url: str) -> str:
    """Return a normalized public HTTP(S) URL or an empty string."""
    value = url.strip()
    try:
        parts = urlsplit(value)
    except ValueError:
        return ""
    if parts.scheme.lower() not in {"http", "https"} or not parts.hostname:
        return ""
    if parts.username or parts.password:
        return ""
    query = [(key, val) for key, val in parse_qsl(parts.query, keep_blank_values=True) if key not in _TRACKING_KEYS]
    host = parts.hostname.lower()
    try:
        port = parts.port
    except ValueError:
        return ""
    if port:
        host = f"{host}:{port}"
    return urlunsplit((parts.scheme.lower(), host, parts.path or "/", urlencode(query), ""))


def validateUrl(url: str) -> bool:
    return bool(normalizeUrl(url))


def parseImportText(text: str) -> list[str]:
    seen: set[str] = set()
    urls: list[str] = []
    for line in text.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        normalized = normalizeUrl(line)
        if normalized and normalized not in seen:
            seen.add(normalized)
            urls.append(normalized)
    return urls


def parseImportFile(filePath: str) -> list[str]:
    try:
        return parseImportText(Path(filePath).read_text(encoding="utf-8"))
    except OSError:
        return []
