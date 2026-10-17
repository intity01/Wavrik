"""Semantic theme tokens (Dark Studio + Teal)."""

from __future__ import annotations

ACCENT = "#2BC3B0"

DARK = {
    "bg": "#0F1113",
    "panel": "#15181B",
    "surface": "#1A1E22",
    "surface_hover": "#20262B",
    "border": "#262C33",
    "border_strong": "#343D46",
    "text": "#F1F5F9",
    "text_muted": "#94A3B8",
    "text_subtle": "#64748B",
    "accent": ACCENT,
    "accent_text": "#081C19",
    "success": "#22C55E",
    "warning": "#F59E0B",
    "danger": "#EF4444",
}

LIGHT = DARK


def palette(_theme: str = "dark") -> dict[str, str]:
    return DARK

