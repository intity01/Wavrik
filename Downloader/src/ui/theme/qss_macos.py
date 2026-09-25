"""macOS-specific QSS overrides for native appearance."""

from __future__ import annotations

from .qss_macos_base import BASE_QSS
from .qss_macos_components import COMPONENT_QSS


def build(tokens: dict[str, str], accent: str) -> str:
    base = BASE_QSS.format(accent=accent, text=tokens["text"])
    components = COMPONENT_QSS.format(accent=accent)
    return base + components
