"""Unit tests for DJ console UI widgets and mixing rack integration."""

from __future__ import annotations

from unittest.mock import MagicMock

from PyQt6.QtWidgets import QApplication, QWidget
import pytest

from src.core.config import Config
from src.ui.components.crossfader_widget import CrossfaderWidget
from src.ui.components.dj_deck_controls import DJDeckControls
from src.ui.pages.audio_tools_dj import build_dj_rack, handle_dj_sync, wire_dj_events
from src.ui.pages.audio_tools_page import AudioToolsInterface
from src.ui.pages.audio_tools_presenter import set_controls_enabled


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_crossfader_widget_defaults_and_position(qapp):
    cf = CrossfaderWidget()
    assert cf.slider.value() == 500
    assert cf.position() == pytest.approx(0.5, abs=0.001)
    assert cf.curve() == "equal_power"

    cf.setCrossfadePosition(0.25)
    assert cf.slider.value() == 250
    assert cf.position() == pytest.approx(0.25, abs=0.001)

    cf.setCrossfadePosition(-0.5)
    assert cf.slider.value() == 0
    assert cf.position() == 0.0

    cf.setCrossfadePosition(1.5)
    assert cf.slider.value() == 1000
    assert cf.position() == 1.0

    cf.center()
    assert cf.position() == pytest.approx(0.5, abs=0.001)


def test_crossfader_widget_signals_and_curve(qapp):
    cf = CrossfaderWidget()
    emitted = []
    cf.crossfadeChanged.connect(lambda pos, curve: emitted.append((pos, curve)))

    cf.setCurve("scratch")
    assert cf.curve() == "scratch"
    assert len(emitted) == 1
    assert emitted[-1][1] == "scratch"

    cf.slider.setValue(800)
    assert len(emitted) == 2
    assert emitted[-1][0] == pytest.approx(0.8, abs=0.001)

    cf.setCurve("invalid_curve")
    assert cf.curve() == "scratch"


def test_dj_deck_controls_signals(qapp):
    deck_a = DJDeckControls("A")
    assert deck_a.deck == "A"
    assert "DECK A" in deck_a.deckLabel.text()

    events = []
    deck_a.cuePressed.connect(lambda d: events.append(("cue_press", d)))
    deck_a.cueReleased.connect(lambda d: events.append(("cue_release", d)))
    deck_a.hotCueClicked.connect(lambda d, i: events.append(("hot_cue", d, i)))
    deck_a.nudgePressed.connect(lambda d, dir: events.append(("nudge_press", d, dir)))
    deck_a.nudgeReleased.connect(lambda d: events.append(("nudge_release", d)))
    deck_a.syncClicked.connect(lambda d: events.append(("sync", d)))

    deck_a.cueBtn.pressed.emit()
    deck_a.cueBtn.released.emit()
    assert events[:2] == [("cue_press", "A"), ("cue_release", "A")]

    deck_a.h1Btn.clicked.emit()
    deck_a.h2Btn.clicked.emit()
    deck_a.h3Btn.clicked.emit()
    assert events[2:5] == [("hot_cue", "A", 0), ("hot_cue", "A", 1), ("hot_cue", "A", 2)]

    deck_a.nudgeBackBtn.pressed.emit()
    deck_a.nudgeBackBtn.released.emit()
    deck_a.nudgeFwdBtn.pressed.emit()
    deck_a.nudgeFwdBtn.released.emit()
    assert events[5:9] == [
        ("nudge_press", "A", "backward"),
        ("nudge_release", "A"),
        ("nudge_press", "A", "forward"),
        ("nudge_release", "A"),
    ]

    deck_a.syncBtn.clicked.emit()
    assert events[9] == ("sync", "A")


def test_audio_tools_dj_wiring_and_events(qapp):
    class MockPage(QWidget):
        def __init__(self):
            super().__init__()
            self.transport = MagicMock()
            self.transport.deckPositionSec.return_value = 14.5
            self.statusLabel = MagicMock()
            self.bpmSpin = MagicMock()
            self.bpmSpin.value.return_value = 126.0
            self.targetBpmSpin = MagicMock()
            self.targetBpmSpin.value.return_value = 120.0
            self.detectedKeyCombo = MagicMock()
            self.detectedKeyCombo.currentText.return_value = "8B"
            self.semitoneSpin = MagicMock()

    page = MockPage()
    build_dj_rack(page)
    wire_dj_events(page)

    assert hasattr(page, "djDeckA")
    assert hasattr(page, "djDeckB")
    assert hasattr(page, "djCrossfader")
    assert hasattr(page, "djRack")

    page.djCrossfader.slider.setValue(700)
    page.transport.setCrossfade.assert_called_with(pytest.approx(0.7, abs=0.001), "equal_power")

    page.djDeckA.cueBtn.pressed.emit()
    page.transport.seekDeck.assert_called_with("A", 0.0)

    page.djDeckA.h1Btn.clicked.emit()
    assert page._hot_cues["A"][0] == 14.5
    page.transport.seekDeck.reset_mock()
    page.djDeckA.h1Btn.clicked.emit()
    page.transport.seekDeck.assert_called_with("A", 14.5)

    page.djDeckB.nudgeFwdBtn.pressed.emit()
    page.transport.setPlaybackRate.assert_called_with("B", pytest.approx(1.03, abs=0.005))
    page.djDeckB.nudgeFwdBtn.released.emit()
    page.transport.setPlaybackRate.assert_called_with("B", 1.0)

    page.djDeckB.syncBtn.clicked.emit()
    page.transport.setPlaybackRate.assert_called()


def test_audio_tools_page_integration(qapp, tmp_path):
    cfg = Config(tmp_path / "cfg.json")
    page = AudioToolsInterface(cfg)

    assert hasattr(page, "djDeckA")
    assert hasattr(page, "djDeckB")
    assert hasattr(page, "djCrossfader")
    assert hasattr(page, "djRack")

    assert not page.djDeckA.isEnabled()
    assert not page.djCrossfader.isEnabled()

    set_controls_enabled(page, True)
    assert page.djDeckA.isEnabled()
    assert page.djCrossfader.isEnabled()
    assert page.djDeckB.isEnabled()
