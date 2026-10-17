"""Categorized application sidebar with Wavrik studio header."""

from __future__ import annotations

import sys

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFrame, QLabel, QPushButton, QVBoxLayout, QWidget


class NavigationItemPosition:
    TOP = 0
    BOTTOM = 1


class FluentIcon:
    HOME = "home"
    AUDIO = "audio"
    HISTORY = "history"
    SETTING = "settings"


class NavigationPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("NavigationPanel")
        self.setFixedWidth(200)
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 16, 12, 14)
        root.setSpacing(6)
        root.addWidget(_brand_header())
        self._top = QVBoxLayout()
        self._bottom = QVBoxLayout()
        root.addLayout(self._top)
        root.addStretch(1)
        root.addLayout(self._bottom)
        self.buttons: dict[str, QPushButton] = {}
        if sys.platform == "darwin":
            self.setProperty("macosSidebar", True)

    def addSection(self, title: str, position=None) -> None:
        lbl = QLabel(title, objectName="NavCategoryLabel")
        target = self._bottom if position == NavigationItemPosition.BOTTOM else self._top
        target.addWidget(lbl)

    def addItem(self, routeKey, icon, text, onClick, position=None, tooltip: str = "") -> None:
        button = QPushButton(text, self)
        button.setObjectName("NavigationButton")
        button.setAccessibleName(f"Go to {text}")
        if tooltip:
            button.setToolTip(tooltip)
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


def _brand_header() -> QFrame:
    card = QFrame(objectName="BrandHeader")
    lay = QVBoxLayout(card)
    lay.setContentsMargins(12, 10, 12, 10)
    lay.setSpacing(2)
    lay.addWidget(QLabel("WAVRIK", objectName="BrandTitle"))
    sub = QLabel("Media & Key/BPM Studio", objectName="BrandSubtitle")
    sub.setWordWrap(True)
    lay.addWidget(sub)
    return card
