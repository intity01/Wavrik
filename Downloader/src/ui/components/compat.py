"""Compatibility exports for the previous UI API."""

from PyQt6.QtWidgets import QFrame

from src.ui.theme.styles import getFont, isDarkTheme

from .controls import (
    ComboBox,
    DangerPushButton,
    LineEdit,
    MessageBox,
    PrimaryPushButton,
    ProgressBar,
    PushButton,
    SmoothScrollArea,
    ToggleButton,
    ToolButton,
    TransparentToolButton,
)
from .navigation import FluentIcon, NavigationItemPosition, NavigationPanel

SimpleCardWidget = QFrame


class SplashScreen:
    def __init__(self, icon=None, parent=None):
        self.parent = parent

    def setIconSize(self, size) -> None:
        pass

    def show(self) -> None:
        pass

    def finish(self, window=None) -> None:
        pass


__all__ = [
    "ComboBox", "DangerPushButton", "FluentIcon", "LineEdit", "MessageBox", "NavigationItemPosition",
    "NavigationPanel", "PrimaryPushButton", "ProgressBar", "PushButton",
    "SimpleCardWidget", "SmoothScrollArea", "SplashScreen", "ToggleButton",
    "ToolButton", "TransparentToolButton", "getFont", "isDarkTheme",
]
