"""DJ deck transport controls (CUE, Hot Cues, Pitch Nudge, and Sync)."""

from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from src.ui.components.controls import PushButton, ToolButton


class DJDeckControls(QWidget):
    cuePressed = pyqtSignal(str)
    cueReleased = pyqtSignal(str)
    hotCueClicked = pyqtSignal(str, int)
    nudgePressed = pyqtSignal(str, str)
    nudgeReleased = pyqtSignal(str)
    syncClicked = pyqtSignal(str)

    def __init__(self, deck: str = "A", parent=None):
        super().__init__(parent)
        self._deck = (deck or "A").strip().upper()
        self.deckLabel = QLabel(f"DECK {self._deck}", objectName="FieldLabel")
        self.cueBtn = ToolButton("CUE")
        self.hotCueBtns = [ToolButton(f"H{i + 1}") for i in range(3)]
        self.h1Btn, self.h2Btn, self.h3Btn = self.hotCueBtns
        self.nudgeBackBtn = ToolButton("- Nudge")
        self.nudgeFwdBtn = ToolButton("+ Nudge")
        self.syncBtn = PushButton("SYNC")
        self._init_layout()
        self._wire_signals()

    def _init_layout(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(4)
        top = QHBoxLayout()
        top.addWidget(self.deckLabel)
        top.addStretch(1)
        top.addWidget(self.syncBtn)
        cues = QHBoxLayout()
        cues.setSpacing(4)
        cues.addWidget(self.cueBtn)
        for w in self.hotCueBtns:
            cues.addWidget(w)
        nudges = QHBoxLayout()
        nudges.setSpacing(4)
        nudges.addWidget(self.nudgeBackBtn)
        nudges.addWidget(self.nudgeFwdBtn)
        root.addLayout(top)
        root.addLayout(cues)
        root.addLayout(nudges)

    def _wire_signals(self) -> None:
        self.cueBtn.pressed.connect(lambda: self.cuePressed.emit(self._deck))
        self.cueBtn.released.connect(lambda: self.cueReleased.emit(self._deck))
        for idx, btn in enumerate(self.hotCueBtns):
            btn.clicked.connect(lambda _c=False, i=idx: self.hotCueClicked.emit(self._deck, i))
        self.nudgeBackBtn.pressed.connect(lambda: self.nudgePressed.emit(self._deck, "backward"))
        self.nudgeBackBtn.released.connect(lambda: self.nudgeReleased.emit(self._deck))
        self.nudgeFwdBtn.pressed.connect(lambda: self.nudgePressed.emit(self._deck, "forward"))
        self.nudgeFwdBtn.released.connect(lambda: self.nudgeReleased.emit(self._deck))
        self.syncBtn.clicked.connect(lambda: self.syncClicked.emit(self._deck))

    @property
    def deck(self) -> str:
        return self._deck
