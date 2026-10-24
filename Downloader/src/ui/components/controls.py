"""Small named Qt controls styled by global QSS."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFontMetrics
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
)


class PushButton(QPushButton):
    def __init__(self, text: str = "", parent=None):
        super().__init__(text, parent)
        self.setObjectName("SecondaryButton")


class PrimaryPushButton(QPushButton):
    def __init__(self, text: str = "", parent=None):
        super().__init__(text, parent)
        self.setObjectName("PrimaryButton")


class ToolButton(QPushButton):
    def __init__(self, text: str = "", parent=None):
        super().__init__(text, parent)
        self.setObjectName("ToolButton")


class DangerPushButton(QPushButton):
    def __init__(self, text: str = "", parent=None):
        super().__init__(text, parent)
        self.setObjectName("DangerButton")


TransparentToolButton = ToolButton


class LineEdit(QLineEdit):
    pass


class ComboBox(QComboBox):
    pass


class ProgressBar(QProgressBar):
    pass


class SmoothScrollArea(QScrollArea):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)


class ElidedLabel(QLabel):
    """Single-line label that elides long filenames without expanding parent layouts."""

    def __init__(
        self,
        text: str = "",
        parent=None,
        mode: Qt.TextElideMode = Qt.TextElideMode.ElideMiddle,
        **kwargs,
    ):
        super().__init__(text, parent, **kwargs)
        self._full_text = text
        self._mode = mode
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.setMinimumWidth(60)
        self._update_elided()

    def text(self) -> str:
        return self._full_text

    def setText(self, text: str) -> None:
        self._full_text = text
        self.setToolTip(text if len(text) > 48 else "")
        self._update_elided()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._update_elided()

    def _update_elided(self) -> None:
        w = self.width()
        if w <= 20:
            super().setText(self._full_text)
            return
        metrics = QFontMetrics(self.font())
        super().setText(metrics.elidedText(self._full_text, self._mode, max(20, w - 4)))


class ToggleButton(QPushButton):
    """Text-labelled toggle that remains clear without color cues."""

    def __init__(self, accessible_name: str = "", parent=None):
        super().__init__(parent)
        self._accessible_name = accessible_name
        self.setObjectName("StateToggle")
        self.setAccessibleName(accessible_name)
        self.setCheckable(True)
        self.setFixedWidth(72)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.toggled.connect(self._sync_state_text)
        self._sync_state_text(False)

    def _sync_state_text(self, checked: bool) -> None:
        state = "On" if checked else "Off"
        self.setText(state)
        self.setAccessibleDescription(f"{self._accessible_name}: {state.lower()}")


class MessageBox(QDialog):
    def __init__(self, title: str, content: str, parent=None, confirm_text: str = "Confirm"):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(360)
        layout = QVBoxLayout(self)
        heading = QLabel(title, objectName="SectionTitle")
        message = QLabel(content, wordWrap=True)
        row = QHBoxLayout()
        row.addStretch(1)
        cancel, confirm = PushButton("Cancel"), PrimaryPushButton(confirm_text)
        cancel.clicked.connect(self.reject)
        confirm.clicked.connect(self.accept)
        row.addWidget(cancel)
        row.addWidget(confirm)
        layout.addWidget(heading)
        layout.addWidget(message)
        layout.addLayout(row)
