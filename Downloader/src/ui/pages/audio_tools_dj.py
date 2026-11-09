"""DJ Mixing Console layout, transport wiring, and harmonic tempo sync."""

from __future__ import annotations

from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout

from src.services.audio_dj_sync import (
    calculate_harmonic_tempo_ratio,
    calculate_momentary_nudge_rate,
    recommend_harmonic_shifts,
)
from src.ui.components.crossfader_widget import CrossfaderWidget
from src.ui.components.dj_deck_controls import DJDeckControls


def build_dj_rack(page) -> QFrame:
    card = QFrame(objectName="AudioToolsCard")
    layout = QVBoxLayout(card)
    layout.setContentsMargins(12, 10, 12, 10)
    layout.setSpacing(10)
    page.djDeckA = DJDeckControls("A")
    page.djCrossfader = CrossfaderWidget()
    page.djDeckB = DJDeckControls("B")
    page.djRack = card
    lbl = QLabel("DJ MIXING CONSOLE", objectName="FieldLabel")
    row = QHBoxLayout()
    row.setSpacing(16)
    for w, st in ((page.djDeckA, 1), (page.djCrossfader, 1), (page.djDeckB, 1)):
        row.addWidget(w, st)
    layout.addWidget(lbl)
    layout.addLayout(row)
    return card


def wire_dj_events(page) -> None:
    page._hot_cues = getattr(page, "_hot_cues", {"A": {}, "B": {}})
    page._rate_a, page._rate_b = getattr(page, "_rate_a", 1.0), getattr(page, "_rate_b", 1.0)
    page.djCrossfader.crossfadeChanged.connect(page.transport.setCrossfade)
    for deck, ctrl in (("A", page.djDeckA), ("B", page.djDeckB)):
        ctrl.cuePressed.connect(lambda d: _on_cue_pressed(page, d))
        ctrl.hotCueClicked.connect(lambda d, idx: _on_hot_cue_clicked(page, d, idx))
        ctrl.nudgePressed.connect(lambda d, dir: _on_nudge_pressed(page, d, dir))
        ctrl.nudgeReleased.connect(lambda d: _on_nudge_released(page, d))
        ctrl.syncClicked.connect(lambda d: handle_dj_sync(page, d))


def _on_cue_pressed(page, deck: str) -> None:
    cue_pos = page._hot_cues.get(deck, {}).get("cue", 0.0)
    page.transport.seekDeck(deck, cue_pos)


def _on_hot_cue_clicked(page, deck: str, idx: int) -> None:
    deck_cues = page._hot_cues.setdefault(deck, {})
    if idx in deck_cues:
        page.transport.seekDeck(deck, deck_cues[idx])
    else:
        deck_cues[idx] = page.transport.deckPositionSec(deck)


def _on_nudge_pressed(page, deck: str, direction: str) -> None:
    base = getattr(page, f"_rate_{deck.lower()}", 1.0)
    rate = calculate_momentary_nudge_rate(base, direction, intensity=0.03)
    page.transport.setPlaybackRate(deck, rate)


def _on_nudge_released(page, deck: str) -> None:
    base = getattr(page, f"_rate_{deck.lower()}", 1.0)
    page.transport.setPlaybackRate(deck, base)


def handle_dj_sync(page, deck: str) -> None:
    is_b = (deck.strip().upper() == "B")
    bpm_m = page.bpmSpin.value() if (is_b and hasattr(page, "bpmSpin")) else getattr(page, "_bpm_b", 120.0)
    bpm_s = getattr(page, "_bpm_b", page.targetBpmSpin.value() if hasattr(page, "targetBpmSpin") else 120.0) if is_b else (page.bpmSpin.value() if hasattr(page, "bpmSpin") else 120.0)
    ratio, mode = calculate_harmonic_tempo_ratio(bpm_m, bpm_s, allow_half_double=True)
    page.transport.setPlaybackRate(deck, ratio)
    setattr(page, f"_rate_{deck.lower()}", ratio)
    key_a = page.detectedKeyCombo.currentText() if hasattr(page, "detectedKeyCombo") else "C major"
    key_b = getattr(page, "_deck_b_key", "") or getattr(page, "_key_b", "") or key_a
    shifts = recommend_harmonic_shifts(key_a, key_b) if is_b else recommend_harmonic_shifts(key_b, key_a)
    if shifts and is_b and hasattr(page, "semitoneSpin"):
        page.semitoneSpin.setValue(shifts[0]["semitones"])
    msg = f"Deck {deck} synced: {ratio:.2f}x ({mode})"
    if shifts:
        msg += f" · Key shift {shifts[0]['semitones']:+d} st ({shifts[0]['target_code']})"
    hasattr(page, "statusLabel") and page.statusLabel.setText(msg)
