"""Small named Qt controls styled by global QSS."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
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
    pass


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
        heading = QLabel(title)
        heading.setObjectName("SectionTitle")
        message = QLabel(content)
        message.setWordWrap(True)
        row = QHBoxLayout()
        row.addStretch(1)
        cancel = PushButton("Cancel")
        confirm = PrimaryPushButton(confirm_text)
        cancel.clicked.connect(self.reject)
        confirm.clicked.connect(self.accept)
        row.addWidget(cancel)
        row.addWidget(confirm)
        layout.addWidget(heading)
        layout.addWidget(message)
        layout.addLayout(row)
