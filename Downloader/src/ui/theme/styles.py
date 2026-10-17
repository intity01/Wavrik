"""Apply the global solid-surface theme."""

from __future__ import annotations

import sys
from pathlib import Path

from PyQt6.QtGui import QFont, QFontDatabase
from PyQt6.QtWidgets import QApplication

from . import qss_base, qss_controls, qss_layout
from .tokens import ACCENT, palette

if sys.platform == "darwin":
    from . import qss_macos

_FONT_LOADED = False


def applyTheme(window, config=None) -> None:
    theme = "dark"
    accent = ACCENT
    tokens = palette(theme)
    app = QApplication.instance()
    if app:
        app.setProperty("appTheme", theme)
        app.setProperty("accentColor", accent)

    styles = (
        qss_base.build(tokens, accent)
        + qss_controls.build(tokens, accent)
        + qss_layout.build(tokens, accent)
    )

    if sys.platform == "darwin":
        styles += qss_macos.build(tokens, accent)

    window.setStyleSheet(styles)
    window.style().unpolish(window)
    window.style().polish(window)


def isDarkTheme() -> bool:
    return True


def getFont(size: int = 10, isBold: bool = False) -> QFont:
    _load_font()
    if "Inter" in QFontDatabase.families():
        family = "Inter"
    elif sys.platform == "darwin":
        # San Francisco - macOS system font with proper weights
        family = ".SF Pro Text"
    elif sys.platform == "win32":
        family = "Segoe UI"
    else:
        family = "Sans Serif"
    font = QFont(family, size)
    font.setBold(isBold)
    
    # macOS-specific font rendering optimizations
    if sys.platform == "darwin":
        # Enable antialiasing for crisp text
        font.setStyleStrategy(QFont.StyleStrategy.PreferAntialias)
        # Use subpixel positioning for better quality
        font.setStyleHint(QFont.StyleHint.SansSerif, QFont.StyleStrategy.PreferQuality)
        # Enable hinting for better readability at small sizes
        font.setHintingPreference(QFont.HintingPreference.PreferFullHinting)
    
    return font


def _load_font() -> None:
    global _FONT_LOADED
    if _FONT_LOADED:
        return
    font_path = Path(__file__).parent / "fonts" / "Inter.ttf"
    if font_path.exists():
        QFontDatabase.addApplicationFont(str(font_path))
    _FONT_LOADED = True
