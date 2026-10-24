"""Semantic theme tokens (Precision Graphite Studio + Teal)."""

from __future__ import annotations

ACCENT = "#2BC3B0"

DARK = {
    "bg": "#0F1113",
    "panel": "#14171A",
    "surface": "#191D21",
    "surface_hover": "#1F252B",
    "border": "#262C33",
    "border_strong": "#36404A",
    "text": "#F1F5F9",
    "text_muted": "#94A3B8",
    "text_subtle": "#64748B",
    "accent": ACCENT,
    "accent_text": "#061815",
    "accent_surface": "#112926",
    "accent_border": "#1F4F48",
    "success": "#22C55E",
    "warning": "#F59E0B",
    "danger": "#EF4444",
}

LIGHT = DARK


def palette(_theme: str = "dark") -> dict[str, str]:
    return DARK
