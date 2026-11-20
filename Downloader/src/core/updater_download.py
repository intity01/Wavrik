"""Hardened asset download helpers for the updater."""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urljoin, urlsplit

import requests

ALLOWED_HOSTS = frozenset({"github.com", "objects.githubusercontent.com", "release-assets.githubusercontent.com"})
MAX_PACKAGE_BYTES = 600_000_000
MAX_REDIRECTS = 5
FALLBACK_ASSET_NAME = "update-package.bin"
_REDIRECT_CODES = frozenset({301, 302, 303, 307, 308})
_UNSAFE_CHARS = re.compile(r"[<>:\"|?*\x00-\x1f]")
_RESERVED = frozenset({"CON", "PRN", "AUX", "NUL"} | {f"COM{i}" for i in range(10)} | {f"LPT{i}" for i in range(10)})


class UpdateError(RuntimeError):
    """Safe, user-facing update error."""


def parse_size(value, label: str) -> int:
    """Parse a non-negative integer; null/empty means unknown (0)."""
    if value is None or value == "":
        return 0
    try:
        return max(0, int(value))
    except (TypeError, ValueError) as exc:
        raise UpdateError(f"GitHub reported an invalid {label}.") from exc


def safe_asset_name(name) -> str:
    """Reduce an untrusted asset name to a plain, non-reserved filename."""
    base = re.split(r"[\\/]", str(name))[-1]
    clean = _UNSAFE_CHARS.sub("_", base).strip(". ")
    if not clean or clean.split(".")[0].upper() in _RESERVED:
        return FALLBACK_ASSET_NAME
    return clean[:120]


def is_allowed_url(url: str) -> bool:
    try:
        parts = urlsplit(url)
        hostname = parts.hostname
    except ValueError:
        return False
    return parts.scheme == "https" and hostname in ALLOWED_HOSTS and "@" not in parts.netloc


def open_asset(session, url: str):
    """GET an asset, validating https and the allowed host before every hop."""
    current = url
    for _ in range(MAX_REDIRECTS + 1):
        if not is_allowed_url(current):
            raise UpdateError("GitHub redirected the download to an unexpected host.")
        response = session.get(current, stream=True, timeout=(5, 60), allow_redirects=False)
        if response.status_code not in _REDIRECT_CODES:
            return response
        location = str(response.headers.get("location", ""))
        close = getattr(response, "close", None)
        if close:
            close()
        current = urljoin(current, location)
    raise UpdateError("The update download was redirected too many times.")


def _write_chunks(response, path: Path, digest, progress, total: int) -> None:
    written = 0
    with path.open("wb") as handle:
        for chunk in response.iter_content(1024 * 256):
            if not chunk:
                continue
            written += len(chunk)
            if written > MAX_PACKAGE_BYTES:
                raise UpdateError("The update package is larger than the safety limit.")
            handle.write(chunk)
            digest.update(chunk)
            if progress and total:
                progress(min(100, int(written * 100 / total)))


def stream_asset(session, asset, path: Path, digest, progress) -> None:
    try:
        with open_asset(session, asset.url) as response:
            response.raise_for_status()
            if getattr(response, "status_code", 200) >= 300:
                raise UpdateError("GitHub did not return the update package.")
            header = response.headers.get("content-length")
            declared = parse_size(header if header is not None else asset.size, "package size")
            if declared > MAX_PACKAGE_BYTES:
                raise UpdateError("The update package is larger than the safety limit.")
            _write_chunks(response, path, digest, progress, declared)
    except requests.RequestException as exc:
        raise UpdateError("The update package could not be downloaded from GitHub.") from exc
