"""Text-first application navigation."""

from __future__ import annotations

import sys

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QPushButton, QVBoxLayout, QWidget


class NavigationItemPosition:
    TOP = 0
    BOTTOM = 1


class FluentIcon:
    HOME = "home"
    HISTORY = "history"
    SETTING = "settings"


class NavigationPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("NavigationPanel")
        self.setFixedWidth(176)
        root = QVBoxLayout(self)
        root.setContentsMargins(10, 20, 10, 14)
        root.setSpacing(6)
        self._top = QVBoxLayout()
        self._bottom = QVBoxLayout()
        root.addLayout(self._top)
        root.addStretch(1)
        root.addLayout(self._bottom)
        self.buttons: dict[str, QPushButton] = {}
        
        # macOS-specific: set sidebar appearance
        if sys.platform == "darwin":
            self.setProperty("macosSidebar", True)

    def addItem(self, routeKey, icon, text, onClick, position=None) -> None:
        button = QPushButton(text, self)
        button.setObjectName("NavigationButton")
        button.setAccessibleName(f"Go to {text}")
        button.setCheckable(True)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.clicked.connect(onClick)
        self.buttons[routeKey] = button
        target = self._bottom if position == NavigationItemPosition.BOTTOM else self._top
        target.addWidget(button)

    def setCurrentItem(self, routeKey: str) -> None:
        for key, button in self.buttons.items():
            button.setChecked(key == routeKey)

    def updateStyles(self) -> None:
        self.update()
