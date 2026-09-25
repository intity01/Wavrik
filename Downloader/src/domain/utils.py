"""Helper functions for media downloader."""

from __future__ import annotations


def percent(data: dict) -> float:
    """Extract download percentage from yt-dlp data."""
    raw = str(data.get("_percent_str", "0")).replace("%", "").strip()
    try:
        return float(raw)
    except ValueError:
        total = data.get("total_bytes") or data.get("total_bytes_estimate") or 0
        return (float(data.get("downloaded_bytes", 0)) / total * 100) if total else 0.0


def friendly_error(message: str) -> str:
    """Convert technical error messages to user-friendly ones."""
    lower = message.lower()
    if "drm" in lower or "protected content" in lower:
        return "This item is DRM-protected and cannot be downloaded."
    if "unsupported url" in lower:
        return "This website or URL is not supported."
    if "private" in lower or "login" in lower or "sign in" in lower:
        return "This item may require login or cookies."
    if "429" in lower or "too many requests" in lower or "rate limit" in lower:
        return "This website is limiting requests. Wait a few minutes, then try again."
    if "403" in lower or "access denied" in lower or "forbidden" in lower:
        return "This website denied access. Check that the item is public or add valid cookies."
    if "requested format" in lower or "no video formats" in lower:
        return "The selected format is unavailable. Choose another quality and try again."
    if "no space left" in lower or "disk full" in lower:
        return "There is not enough free disk space in the download folder."
    if "permission denied" in lower or "access is denied" in lower:
        return "The download folder cannot be written to. Choose another folder."
    if "ffmpeg" in lower:
        return "FFmpeg is missing or could not process this file."
    if any(term in lower for term in ("timed out", "timeout", "connection reset", "network is unreachable")):
        return "The network connection was interrupted. The partial download can be resumed by trying again."
    return "Download failed. Check the URL and your internet connection."
