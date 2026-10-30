"""Apply the global solid-surface theme."""

from __future__ import annotations

import sys
from pathlib import Path

from PyQt6.QtGui import QFont, QFontDatabase
from PyQt6.QtWidgets import QApplication

from . import key_colors, qss_base, qss_controls, qss_layout
from .tokens import THEMES, palette

_FONT_LOADED = False


def applyTheme(window, config=None) -> None:
    theme = _theme_name(config)
    tokens = palette(theme)
    accent = tokens["accent"]
    app = QApplication.instance()
    if app:
        app.setProperty("appTheme", theme)
        app.setProperty("accentColor", accent)

    styles = (
        qss_base.build(tokens, accent)
        + qss_controls.build(tokens, accent)
        + qss_layout.build(tokens, accent)
        + key_colors.build_qss(theme)
    )

    window.setStyleSheet(styles)
    window.style().unpolish(window)
    window.style().polish(window)


def _theme_name(config) -> str:
    theme = config.get("theme", "light") if config is not None else "light"
    return theme if theme in THEMES else "light"


def isDarkTheme() -> bool:
    app = QApplication.instance()
    return bool(app) and app.property("appTheme") == "dark"


def getFont(size: int = 10, isBold: bool = False) -> QFont:
    _load_font()
    if "Inter" in QFontDatabase.families():
        family = "Inter"
    elif sys.platform == "win32":
        family = "Segoe UI"
    else:
        family = "Sans Serif"
    font = QFont(family, size)
    font.setBold(isBold)
    return font


def _load_font() -> None:
    global _FONT_LOADED
    if _FONT_LOADED:
        return
    font_path = Path(__file__).parent / "fonts" / "Inter.ttf"
    if font_path.exists():
        QFontDatabase.addApplicationFont(str(font_path))
    _FONT_LOADED = True
