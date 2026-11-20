"""Form fields and detection-result mapping for the audio tag dialog."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from PyQt6.QtWidgets import QFormLayout, QHBoxLayout, QLabel

from src.services.audio_acoustid import parse_filename_heuristic
from src.ui.components.controls import LineEdit, ToolButton

TAG_KEYS = ("title", "artist", "album", "date", "track", "genre")


def build_tag_form(owner: Any, on_browse: Callable[[], None]) -> QFormLayout:
    """Create the tag editors as attributes of ``owner`` and return their layout."""
    form = QFormLayout()
    owner.titleEdit, owner.artistEdit = LineEdit(), LineEdit()
    owner.albumEdit, owner.dateEdit = LineEdit(), LineEdit()
    owner.trackEdit, owner.genreEdit = LineEdit(), LineEdit()
    owner.coverEdit = LineEdit()
    owner.browseCoverBtn = ToolButton("Browse...")
    owner.browseCoverBtn.clicked.connect(on_browse)
    cov_row = QHBoxLayout()
    cov_row.addWidget(owner.coverEdit, 1)
    cov_row.addWidget(owner.browseCoverBtn)
    for lbl, w in (
        ("Title:", owner.titleEdit), ("Artist:", owner.artistEdit),
        ("Album:", owner.albumEdit), ("Year/Date:", owner.dateEdit),
        ("Track #:", owner.trackEdit), ("Genre:", owner.genreEdit),
    ):
        form.addRow(QLabel(lbl), w)
    form.addRow(QLabel("Cover Art:"), cov_row)
    return form


def resolve_detection(res: dict[str, Any], filename: str) -> tuple[dict[str, str], str]:
    """Return (tag values, status text); fall back to the filename when no match."""
    if res.get("title") or res.get("artist"):
        values = {k: str(res.get(k, "")) for k in TAG_KEYS}
        return values, f"matched via AcoustID (score {float(res.get('score', 0.0)):.2f})"
    values = parse_filename_heuristic(filename)
    status = res.get("status")
    if status == "unavailable":
        reason = f"{res.get('error', 'online lookup unavailable')}; parsed from filename"
    elif status == "not_found":
        reason = "no online match; parsed from filename"
    elif status == "error":
        reason = "online lookup failed; parsed from filename"
    else:
        reason = "parsed from filename"
    return {k: str(values.get(k, "")) for k in TAG_KEYS}, reason
