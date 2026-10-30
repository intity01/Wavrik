"""Compact Precision Sidebar with single-locale section labels."""

from __future__ import annotations

from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from src.ui.i18n import tr


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
        self.setFixedWidth(184)
        root = QVBoxLayout(self)
        root.setContentsMargins(10, 12, 10, 12)
        root.setSpacing(4)
        self._brand_sub = QLabel(objectName="BrandSubtitle")
        root.addWidget(_brand_header(self._brand_sub))
        self._top = QVBoxLayout()
        self._top.setSpacing(2)
        self._bottom = QVBoxLayout()
        self._bottom.setSpacing(2)
        root.addLayout(self._top)
        root.addStretch(1)
        root.addLayout(self._bottom)
        self.buttons: dict[str, QPushButton] = {}
        self._sections: list[tuple[QLabel, str]] = []

    def addSection(self, title_key: str, position=None) -> None:
        lbl = QLabel(objectName="NavCategoryLabel")
        self._sections.append((lbl, title_key))
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

    def setLanguage(self, lang: str) -> None:
        self._brand_sub.setText(tr("brand.subtitle", lang))
        for lbl, key in self._sections:
            lbl.setText(tr(key, lang))

    def updateStyles(self) -> None:
        self.update()


def _brand_header(sub_label: QLabel) -> QFrame:
    card = QFrame(objectName="BrandHeader")
    lay = QVBoxLayout(card)
    lay.setContentsMargins(8, 2, 8, 10)
    lay.setSpacing(1)
    top = QHBoxLayout()
    top.setContentsMargins(0, 0, 0, 0)
    top.setSpacing(8)
    logo = QLabel(objectName="BrandLogo")
    logo.setPixmap(QIcon(str(Path(__file__).parents[2] / "core" / "app.ico")).pixmap(24, 24))
    logo.setAccessibleName("Wavrik")
    top.addWidget(logo)
    top.addWidget(QLabel("Wavrik", objectName="BrandTitle"))
    top.addStretch(1)
    lay.addLayout(top)
    sub_label.setText(tr("brand.subtitle", "en"))
    sub_label.setWordWrap(True)
    lay.addWidget(sub_label)
    return card
