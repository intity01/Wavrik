"""Map Camelot codes to the per-key color system used across the UI."""

from __future__ import annotations

import re

from .tokens import KEY_HUES, key_tint, palette

_CODE = re.compile(r"\b(1[0-2]|[1-9])[AB]\b")


def key_index(camelot: str) -> str:
    """Return the wheel position "1".."12" found in a Camelot code, or "" when there is none."""
    match = _CODE.search(str(camelot or "").upper())
    return match.group(1) if match else ""


def key_hue(camelot: str, fallback: str = "") -> str:
    index = key_index(camelot)
    return KEY_HUES[int(index) - 1] if index else fallback


def apply_key_property(widget, camelot: str) -> None:
    """Tag a widget with its key position so the theme QSS can color it, then repolish."""
    widget.setProperty("keyIndex", key_index(camelot))
    widget.style().unpolish(widget)
    widget.style().polish(widget)


def build_qss(theme: str) -> str:
    tokens = palette(theme)
    rules = []
    for i, hue in enumerate(KEY_HUES, start=1):
        tint = key_tint(hue, theme)
        rules.append(
            f'QLabel#StepBadge[keyIndex="{i}"] {{ color: {tokens["text"]}; background: {tint}; border: 1px solid {hue}; }}'
        )
    return "\n".join(rules)
