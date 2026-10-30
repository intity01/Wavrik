"""Semantic theme tokens (Wavrik Key Colors: light ink default, graphite dark)."""

from __future__ import annotations

ACCENT = "#0E1116"

LIGHT = {
    "bg": "#F6F7F9",
    "panel": "#FFFFFF",
    "surface": "#FFFFFF",
    "surface_hover": "#F1F3F6",
    "border": "#E4E7EC",
    "border_strong": "#CDD2DA",
    "text": "#0E1116",
    "text_muted": "#3D4552",
    "text_subtle": "#5B6472",
    "accent": ACCENT,
    "accent_text": "#FFFFFF",
    "accent_surface": "#F1F3F6",
    "accent_border": "#0E1116",
    "success": "#15803D",
    "warning": "#B45309",
    "danger": "#B42318",
}

DARK = {
    "bg": "#0F1113",
    "panel": "#14171A",
    "surface": "#191D21",
    "surface_hover": "#1F252B",
    "border": "#262C33",
    "border_strong": "#36404A",
    "text": "#F1F5F9",
    "text_muted": "#B4BFCC",
    "text_subtle": "#8A94A2",
    "accent": "#F1F5F9",
    "accent_text": "#0E1116",
    "accent_surface": "#1F252B",
    "accent_border": "#F1F5F9",
    "success": "#22C55E",
    "warning": "#F59E0B",
    "danger": "#EF4444",
}

# Camelot wheel position 1..12 -> hue. The same hue marks the minor (A) and major (B) key at that position.
KEY_HUES = (
    "#2BB3A3", "#3BAA5C", "#7DB63A", "#C9B227", "#E39A2A", "#E5713A",
    "#E0554F", "#D9497F", "#B04FBF", "#7D5CD6", "#4C72DB", "#2F9BD6",
)

THEMES = ("light", "dark")


def palette(theme: str = "light") -> dict[str, str]:
    return DARK if theme == "dark" else LIGHT


def key_tint(hex_color: str, theme: str = "light") -> str:
    """Blend a key hue toward the theme surface so text on it stays readable."""
    base = 0x14171A if theme == "dark" else 0xFFFFFF
    weight = 0.22 if theme == "dark" else 0.16
    value = int(hex_color.lstrip("#"), 16)
    channels = []
    for shift in (16, 8, 0):
        c, b = (value >> shift) & 255, (base >> shift) & 255
        channels.append(round(c * weight + b * (1 - weight)))
    return "#{:02X}{:02X}{:02X}".format(*channels)
