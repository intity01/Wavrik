"""DJ mixer horizontal crossfader widget with curve selection and center reset."""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QSlider, QVBoxLayout, QWidget

from src.ui.components.controls import ComboBox, ToolButton

CURVE_OPTIONS = ("equal_power", "linear", "scratch")


class CrossfaderWidget(QWidget):
    crossfadeChanged = pyqtSignal(float, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.deckALabel = QLabel("DECK A", objectName="FieldLabel")
        self.deckBLabel = QLabel("DECK B", objectName="FieldLabel")
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(0, 1000)
        self.slider.setValue(500)
        self.centerBtn = ToolButton("Center")
        self.curveCombo = ComboBox()
        self.curveCombo.addItems(list(CURVE_OPTIONS))
        self._init_layout()
        self.slider.valueChanged.connect(self._on_change)
        self.curveCombo.currentTextChanged.connect(self._on_change)
        self.centerBtn.clicked.connect(self.center)

    def _init_layout(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(6)
        top = QHBoxLayout()
        top.addWidget(QLabel("CROSSFADER", objectName="FieldLabel"))
        top.addStretch(1)
        top.addWidget(QLabel("Curve:", objectName="MutedText"))
        top.addWidget(self.curveCombo)
        top.addWidget(self.centerBtn)
        fader = QHBoxLayout()
        fader.addWidget(self.deckALabel)
        fader.addWidget(self.slider, 1)
        fader.addWidget(self.deckBLabel)
        root.addLayout(top)
        root.addLayout(fader)

    def _on_change(self, *_args) -> None:
        self.crossfadeChanged.emit(self.position(), self.curve())

    def position(self) -> float:
        return max(0.0, min(1.0, self.slider.value() / 1000.0))

    def setCrossfadePosition(self, val: float) -> None:
        self.slider.setValue(max(0, min(1000, int(float(val) * 1000.0))))

    def curve(self) -> str:
        return self.curveCombo.currentText() or "equal_power"

    def setCurve(self, curve_name: str) -> None:
        c = (curve_name or "").strip().lower()
        if c in CURVE_OPTIONS:
            self.curveCombo.setCurrentText(c)

    def center(self) -> None:
        self.setCrossfadePosition(0.5)
