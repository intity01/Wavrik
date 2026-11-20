"""Localised display strings for library rows."""

from __future__ import annotations

from src.ui.i18n import tr


def harmony_text(analysis: dict, is_audio: bool, lang: str = "en") -> str:
    if analysis.get("key"):
        return f"{analysis['key']} ({analysis.get('camelot', '--')}) · {float(analysis.get('bpm', 0.0)):.1f} BPM"
    return tr("lib.filter_audio" if is_audio else "lib.filter_video", lang)


def metadata_text(entry: dict, analysis: dict, lang: str = "en") -> str:
    ts = entry.get("timestamp", "").replace("T", " ")[:16]
    m_raw = entry.get("mediaType", "audio")
    m_lbl = tr("lib.filter_audio" if m_raw == "audio" else "lib.filter_video", lang)
    base = f"{ts} · {m_lbl} · {format_size(int(entry.get('fileSize', 0) or 0), lang)}"
    if analysis.get("key"):
        conf = f" [{analysis['confidence']}%]" if analysis.get("confidence") else ""
        return f"{base} · {analysis['key']} ({analysis.get('camelot', '--')}) · {float(analysis.get('bpm', 0.0)):.1f} BPM{conf}"
    return base


def status_text(entry: dict, lang: str = "en") -> str:
    raw = entry.get("status", "failed")
    key = f"lib.filter_{raw}" if f"lib.filter_{raw}" in ("lib.filter_completed", "lib.filter_failed", "lib.filter_cancelled") else None
    st = tr(key, lang) if key else raw.title()
    err = entry.get("error", "")
    return f"{st}: {err}" if err else st


def format_size(size: int, lang: str = "en") -> str:
    if size <= 0:
        return tr("lib.size_unavailable", lang)
    val = float(size)
    for unit in ("B", "KB", "MB", "GB"):
        if val < 1024 or unit == "GB":
            return f"{val:.1f} {unit}"
        val /= 1024
    return tr("lib.size_unavailable", lang)
