"""Semantic theme tokens."""

from __future__ import annotations

DARK = {
    "bg": "#0B0F16",
    "panel": "#101722",
    "surface": "#151E2B",
    "surface_hover": "#1A2636",
    "border": "#263449",
    "border_strong": "#3A4B63",
    "text": "#F3F6FA",
    "text_muted": "#9AA8BA",
    "text_subtle": "#738197",
    "success": "#22C55E",
    "warning": "#F59E0B",
    "danger": "#EF4444",
}

LIGHT = {
    "bg": "#F4F7FB",
    "panel": "#FFFFFF",
    "surface": "#FFFFFF",
    "surface_hover": "#EEF3F9",
    "border": "#D6DFEA",
    "border_strong": "#AAB8C9",
    "text": "#111827",
    "text_muted": "#526173",
    "text_subtle": "#6B7A8D",
    "success": "#15803D",
    "warning": "#B45309",
    "danger": "#B91C1C",
}


def palette(theme: str) -> dict[str, str]:
    return LIGHT if theme == "light" else DARK
