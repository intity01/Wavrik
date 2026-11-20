"""URL validation and import parsing."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import parse_qsl, unquote_plus, urlsplit, urlunsplit

_TRACKING_KEYS = {"fbclid", "gclid", "utm_source", "utm_medium", "utm_campaign"}
_YT_TRACKING_KEYS = {"si", "feature", "pp"}
_YT_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com", "youtu.be"}
_YT_MIX_KEYS = {"list", "start_radio", "index"}


def _drop_params(query: str, names: set[str]) -> str:
    """Remove named parameters while leaving every other byte of the raw query untouched."""
    kept = [part for part in query.split("&") if unquote_plus(part.split("=", 1)[0]) not in names]
    return "&".join(kept)


def _is_youtube(host: str) -> bool:
    return any(host == yt or host.endswith("." + yt) for yt in _YT_HOSTS)


def _is_youtube_mix(host: str, path: str, query: str) -> bool:
    params = dict(parse_qsl(query, keep_blank_values=True))
    is_video = bool(params.get("v")) or path.startswith(("/watch", "/shorts/")) or host == "youtu.be"
    is_mix = params.get("list", "").startswith(("RD", "UL")) or "start_radio" in params
    return is_video and is_mix


def _clean_query(host: str, path: str, query: str) -> str:
    names = set(_TRACKING_KEYS)
    if _is_youtube(host):
        names |= _YT_TRACKING_KEYS
    cleaned = _drop_params(query, names)
    if _is_youtube(host) and _is_youtube_mix(host, path, cleaned):
        cleaned = _drop_params(cleaned, _YT_MIX_KEYS)
    return cleaned


def normalizeUrl(url: str) -> str:
    """Return a normalized public HTTP(S) URL or an empty string."""
    value = url.strip()
    try:
        parts = urlsplit(value)
        port = parts.port
    except ValueError:
        return ""
    if parts.scheme.lower() not in {"http", "https"} or not parts.hostname:
        return ""
    if parts.username or parts.password:
        return ""
    host = parts.hostname.lower()
    netloc = f"[{host}]" if ":" in host else host
    if port:
        netloc = f"{netloc}:{port}"
    query = _clean_query(host, parts.path, parts.query)
    return urlunsplit((parts.scheme.lower(), netloc, parts.path or "/", query, ""))


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
