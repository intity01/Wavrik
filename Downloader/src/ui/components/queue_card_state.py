"""Presentation labels for queue item states."""

from __future__ import annotations

from src.ui.i18n import tr

ACTIVE_STATES = {"queued", "downloading", "processing"}


def action_text(state: str, lang: str = "en") -> str:
    if state in ACTIVE_STATES:
        return tr("queue.action_cancel", lang)
    if state == "completed":
        return tr("queue.action_open_folder", lang)
    if state in {"failed", "cancelled"}:
        return tr("queue.action_retry", lang)
    return tr("queue.action_download", lang)


def action_description(state: str) -> str:
    messages = {
        "fetching": "Waiting for the link check to finish",
        "queued": "Cancel this queued download",
        "downloading": "Cancel this download",
        "processing": "Cancel file processing",
        "completed": "Open the folder that contains this download",
        "failed": "Try this download again",
        "cancelled": "Try this download again",
    }
    return messages.get(state, "Start this download")


def format_duration(seconds) -> str:
    total = int(seconds or 0)
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours}:{minutes:02d}:{secs:02d}" if hours else f"{minutes}:{secs:02d}"


def engine_label(engine: str) -> str:
    return {"auto": "Auto", "native": "Native", "yt-dlp": "yt-dlp"}[engine]
