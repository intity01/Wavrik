"""Safety checks for Cobalt instance URLs, returned media URLs and filenames."""

from __future__ import annotations

import ipaddress
import re
import socket
from urllib.parse import urlsplit

from src.core.parser import normalizeUrl

LOOPBACK_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})
MEDIA_EXTENSIONS = frozenset({
    "mp3", "m4a", "aac", "ogg", "oga", "opus", "wav", "flac", "wma", "aiff", "aif",
    "mp4", "m4v", "webm", "mkv", "mov", "avi", "flv", "ts", "mpg", "mpeg", "3gp",
    "gif", "jpg", "jpeg", "png", "webp",
})
_RESERVED_NAMES = frozenset(
    {"CON", "PRN", "AUX", "NUL", "CONIN$", "CONOUT$"}
    | {f"COM{i}" for i in range(10)}
    | {f"LPT{i}" for i in range(10)}
)
_UNSAFE_CHARS = re.compile(r"[<>:\"|?*;\x00-\x1f]")
_NUMERIC_HOST = re.compile(r"^[0-9a-fA-FxX.]+$")
_MAX_STEM = 150


def _host_of(url: str) -> str:
    try:
        return (urlsplit(url.strip()).hostname or "").lower()
    except ValueError:
        return ""


def validate_instance_url(url: str) -> str:
    """Return the trimmed Cobalt instance URL, or '' when it is not acceptable.

    https is required; plain http is only allowed for loopback hosts.
    Embedded credentials are always rejected.
    """
    value = str(url).strip()
    try:
        parts = urlsplit(value)
        _ = parts.port
    except ValueError:
        return ""
    host = (parts.hostname or "").lower()
    if not host or "@" in parts.netloc:
        return ""
    scheme = parts.scheme.lower()
    if scheme == "https" or (scheme == "http" and host in LOOPBACK_HOSTS):
        return value
    return ""


def is_loopback_url(url: str) -> bool:
    return _host_of(url) in LOOPBACK_HOSTS


def _legacy_ipv4(name: str) -> ipaddress.IPv4Address | None:
    if not _NUMERIC_HOST.match(name):
        return None
    try:
        return ipaddress.IPv4Address(socket.inet_aton(name))
    except (OSError, ValueError):
        return None


def is_private_host(host: str) -> bool:
    """True for localhost-style names and non-public literal IP addresses."""
    name = host.strip("[]").lower().rstrip(".")
    if name == "localhost" or name.endswith((".localhost", ".local", ".internal")):
        return True
    try:
        addr = ipaddress.ip_address(name)
    except ValueError:
        addr = _legacy_ipv4(name)
    if addr is None:
        return False
    if addr.version == 6 and addr.ipv4_mapped:
        addr = addr.ipv4_mapped
    return not addr.is_global


def validate_media_url(url: str, allow_private: bool = False) -> str:
    """Return the media URL when it is http(s) without credentials and public."""
    value = str(url).strip()
    if not normalizeUrl(value):
        return ""
    if not allow_private and is_private_host(_host_of(value)):
        return ""
    return value


def safe_media_filename(name: str, fallback_ext: str) -> str:
    """Build a bare `stem.ext` filename from untrusted server input."""
    ext = fallback_ext.lower() if fallback_ext.lower() in MEDIA_EXTENSIONS else "mp4"
    base = re.split(r"[\\/]", str(name))[-1].strip()
    stem, dot, tail = base.rpartition(".")
    if dot and tail.lower() in MEDIA_EXTENSIONS:
        ext = tail.lower()
    elif not (dot and re.fullmatch(r"[A-Za-z0-9]{1,5}", tail)):
        stem = base
    stem = _UNSAFE_CHARS.sub("_", stem).strip(". ")[:_MAX_STEM].rstrip(". ")
    if not stem or stem.split(".")[0].upper() in _RESERVED_NAMES:
        stem = "download"
    return f"{stem}.{ext}"
