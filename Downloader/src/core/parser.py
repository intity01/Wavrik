"""URL validation and import parsing."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

_TRACKING_KEYS = {"fbclid", "gclid", "si", "feature", "utm_source", "utm_medium", "utm_campaign", "pp"}
_YT_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com", "youtu.be"}


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
    host = parts.hostname.lower()
    raw_query = parse_qsl(parts.query, keep_blank_values=True)
    query = [(key, val) for key, val in raw_query if key not in _TRACKING_KEYS]

    # For YouTube video links, strip endless algorithmic mix/radio parameters (list=RD..., start_radio)
    if any(host == yt or host.endswith("." + yt) for yt in _YT_HOSTS):
        query_dict = dict(query)
        is_video = bool(query_dict.get("v")) or parts.path.startswith(("/watch", "/shorts/")) or host == "youtu.be"
        list_id = query_dict.get("list", "")
        is_mix_radio = list_id.startswith(("RD", "UL")) or "start_radio" in query_dict
        if is_video and is_mix_radio:
            query = [(k, v) for k, v in query if k not in {"list", "start_radio", "index"}]

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
