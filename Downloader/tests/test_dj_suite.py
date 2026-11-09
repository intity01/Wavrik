"""Comprehensive offline test suite for DJ Suite Phase 4.

Covers:
- Pure DSP crossfader gain calculations and volume staging (audio_crossfader.py)
- Harmonic tempo sync, extended Camelot wheel, phase error, and nudging (audio_dj_sync.py)
- Dual-deck transport controller methods and backward compatibility (audio_transport.py)
- DJ console UI rack layout, wiring, hot-cues, and sync execution (audio_tools_dj.py)
"""

from __future__ import annotations

from array import array
import math
from pathlib import Path
from unittest.mock import MagicMock
import wave

from PyQt6.QtMultimedia import QMediaPlayer
from PyQt6.QtWidgets import QSpinBox, QWidget
import pytest

from src.services.audio_crossfader import (
    CURVE_EQUAL_POWER,
    CURVE_LINEAR,
    CURVE_SCRATCH,
    bipolar_to_normalized,
    calculate_effective_volume,
    crossfader_gains,
    normalized_to_bipolar,
    step_crossfader,
)
from src.services.audio_dj_sync import (
    calculate_beat_phase_error,
    calculate_harmonic_tempo_ratio,
    calculate_momentary_nudge_rate,
    get_extended_camelot_transitions,
    recommend_harmonic_shifts,
)
from src.ui.components.audio_transport import AudioTransportController
from src.ui.pages.audio_tools_dj import (
    build_dj_rack,
    handle_dj_sync,
    wire_dj_events,
)


def _create_wav(path: Path, seconds: float = 0.5, sr: int = 8000) -> Path:
    total = int(seconds * sr)
    samples = array(
        "h",
        [int(0.3 * 32767 * math.sin(2 * math.pi * 440 * i / sr)) for i in range(total)],
    )
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(samples.tobytes())
    return path


# ==============================================================================
# 1. Pure DSP Crossfader Tests (audio_crossfader.py)
# ==============================================================================


def test_crossfader_equal_power_power_invariant():
    """Verify equal power curve preserves acoustic power g_a^2 + g_b^2 == 1.0 (0 dB dip)."""
    test_points = [0.0, 0.1, 0.25, 0.5, 0.75, 0.9, 1.0]
    for pos in test_points:
        ga, gb = crossfader_gains(pos, CURVE_EQUAL_POWER)
        power = ga**2 + gb**2
        assert power == pytest.approx(1.0, abs=1e-5), f"Power invariant failed at pos={pos}"
        assert 0.0 <= ga <= 1.0
        assert 0.0 <= gb <= 1.0

    # Specifically at center (0.5), both gains should be cos(pi/4) = sqrt(2)/2 ~= 0.7071
    ga_center, gb_center = crossfader_gains(0.5, CURVE_EQUAL_POWER)
    expected_center = math.sqrt(2.0) / 2.0
    assert ga_center == pytest.approx(expected_center, abs=1e-4)
    assert gb_center == pytest.approx(expected_center, abs=1e-4)

    # Extreme boundary positions and clamping
    assert crossfader_gains(0.0) == (1.0, 0.0)
    assert crossfader_gains(1.0) == (0.0, 1.0)
    assert crossfader_gains(-0.5) == (1.0, 0.0)
    assert crossfader_gains(1.5) == (0.0, 1.0)


def test_crossfader_linear_curve():
    """Verify linear curve preserves linear sum g_a + g_b == 1.0."""
    test_points = [0.0, 0.2, 0.5, 0.8, 1.0]
    for pos in test_points:
        ga, gb = crossfader_gains(pos, CURVE_LINEAR)
        assert ga + gb == pytest.approx(1.0, abs=1e-6)
        assert ga == pytest.approx(1.0 - pos, abs=1e-6)
        assert gb == pytest.approx(pos, abs=1e-6)

    # Case-insensitive curve name
    ga_upper, gb_upper = crossfader_gains(0.3, "  LINEAR  ")
    assert ga_upper == pytest.approx(0.7, abs=1e-6)
    assert gb_upper == pytest.approx(0.3, abs=1e-6)


def test_crossfader_scratch_curve_and_cut():
    """Verify scratch / cut curve provides rapid cut-in and full amplitude across center."""
    # Under 0.05: Deck A is full, Deck B ramps up
    ga, gb = crossfader_gains(0.025, CURVE_SCRATCH)
    assert ga == 1.0
    assert gb == pytest.approx(0.5, abs=1e-3)

    # Center zone [0.05, 0.95]: both decks are at 100% volume
    for pos in [0.06, 0.5, 0.94]:
        ga, gb = crossfader_gains(pos, CURVE_SCRATCH)
        assert ga == 1.0
        assert gb == 1.0

    # Above 0.95: Deck B is full, Deck A ramps down
    ga, gb = crossfader_gains(0.975, CURVE_SCRATCH)
    assert ga == pytest.approx(0.5, abs=1e-3)
    assert gb == 1.0

    # Alias 'cut'
    assert crossfader_gains(0.5, "cut") == (1.0, 1.0)


def test_calculate_effective_volume():
    """Verify staged volume calculation and clamping."""
    # Normal stage
    vol = calculate_effective_volume(master=0.8, channel=0.9, gain=1.0, crossfade=0.5)
    assert vol == pytest.approx(0.8 * 0.9 * 1.0 * 0.5, abs=1e-5)

    # Muted stage returns 0.0 immediately
    assert calculate_effective_volume(1.0, 1.0, 1.0, 1.0, muted=True) == 0.0

    # Upper clamp to 1.0
    assert calculate_effective_volume(master=1.0, channel=1.0, gain=2.0, crossfade=1.0) == 1.0

    # Lower clamp to 0.0
    assert calculate_effective_volume(master=-0.5, channel=1.0, gain=1.0, crossfade=1.0) == 0.0


def test_step_crossfader():
    """Verify incremental crossfader step towards target position."""
    # Stepping forward
    assert step_crossfader(0.2, 0.5, step=0.1) == pytest.approx(0.3, abs=1e-5)
    # Reaching target without overshoot
    assert step_crossfader(0.45, 0.5, step=0.1) == pytest.approx(0.5, abs=1e-5)

    # Stepping backward
    assert step_crossfader(0.8, 0.5, step=0.1) == pytest.approx(0.7, abs=1e-5)
    # Reaching target backward without undershoot
    assert step_crossfader(0.55, 0.5, step=0.1) == pytest.approx(0.5, abs=1e-5)

    # Already at target or zero step
    assert step_crossfader(0.5, 0.5, step=0.05) == 0.5
    assert step_crossfader(0.3, 0.8, step=0.0) == 0.8


def test_bipolar_normalized_conversions():
    """Verify bidirectional conversion between [-1.0, 1.0] and [0.0, 1.0]."""
    assert bipolar_to_normalized(-1.0) == 0.0
    assert bipolar_to_normalized(0.0) == 0.5
    assert bipolar_to_normalized(1.0) == 1.0

    assert normalized_to_bipolar(0.0) == -1.0
    assert normalized_to_bipolar(0.5) == 0.0
    assert normalized_to_bipolar(1.0) == 1.0

    # Roundtrip test across values
    for x in [-1.0, -0.75, -0.2, 0.0, 0.33, 0.8, 1.0]:
        assert normalized_to_bipolar(bipolar_to_normalized(x)) == pytest.approx(x, abs=1e-5)


# ==============================================================================
# 2. Harmonic & Tempo Sync Tests (audio_dj_sync.py)
# ==============================================================================


def test_harmonic_tempo_ratio_direct():
    """Verify tempo ratio calculation for direct tempo matching."""
    # Same tempo
    ratio, mode = calculate_harmonic_tempo_ratio(128.0, 128.0)
    assert ratio == 1.0
    assert mode == "direct"

    # Direct ratio
    ratio, mode = calculate_harmonic_tempo_ratio(126.0, 120.0)
    assert ratio == pytest.approx(126.0 / 120.0, abs=1e-4)
    assert mode == "direct"

    # Clamping between 0.5 and 2.0
    ratio_high, _ = calculate_harmonic_tempo_ratio(250.0, 100.0)
    assert ratio_high == 2.0

    ratio_low, _ = calculate_harmonic_tempo_ratio(60.0, 150.0)
    assert ratio_low == 0.5

    # Invalid or zero BPM
    assert calculate_harmonic_tempo_ratio(0.0, 120.0) == (1.0, "direct")
    assert calculate_harmonic_tempo_ratio(120.0, -10.0) == (1.0, "direct")


def test_harmonic_tempo_ratio_half_and_double_time():
    """Verify half-time and double-time ratio detection."""
    # Deck A is 140 BPM, Deck B is 70 BPM -> half-time match (ratio ~ 1.0)
    ratio, mode = calculate_harmonic_tempo_ratio(140.0, 70.0, allow_half_double=True)
    assert ratio == pytest.approx(1.0, abs=1e-4)
    assert mode == "half_time"

    # Deck A is 144 BPM, Deck B is 70 BPM
    ratio, mode = calculate_harmonic_tempo_ratio(144.0, 70.0, allow_half_double=True)
    assert ratio == pytest.approx(144.0 / 140.0, abs=1e-4)
    assert mode == "half_time"

    # Deck A is 70 BPM, Deck B is 140 BPM -> double-time match (ratio ~ 1.0)
    ratio, mode = calculate_harmonic_tempo_ratio(70.0, 140.0, allow_half_double=True)
    assert ratio == pytest.approx(1.0, abs=1e-4)
    assert mode == "double_time"

    # If allow_half_double is False, returns direct clamped ratio
    ratio_direct, mode_direct = calculate_harmonic_tempo_ratio(140.0, 70.0, allow_half_double=False)
    assert ratio_direct == 2.0
    assert mode_direct == "direct"


def test_extended_camelot_transitions():
    """Verify 6 extended Camelot transitions (Match, Relative, +/-1, +/-2)."""
    transitions = get_extended_camelot_transitions("8B")
    assert len(transitions) == 6

    labels = {t["label"]: t for t in transitions}
    assert labels["Match"]["code"] == "8B"
    assert labels["Match"]["key"] == "C major"
    assert labels["Match"]["compatibility"] == 1.0

    assert labels["Relative"]["code"] == "8A"
    assert labels["Relative"]["key"] == "A minor"
    assert labels["Relative"]["compatibility"] == 1.0

    assert labels["+1 Boost"]["code"] == "9B"
    assert labels["-1 Drop"]["code"] == "7B"
    assert labels["+2 Energy Boost"]["code"] == "10B"
    assert labels["-2 Energy Drop"]["code"] == "6B"

    # Test clock boundary wrap: 12B wraps to 1B and 2B
    trans_12b = {t["label"]: t["code"] for t in get_extended_camelot_transitions("12B")}
    assert trans_12b["+1 Boost"] == "1B"
    assert trans_12b["+2 Energy Boost"] == "2B"
    assert trans_12b["-1 Drop"] == "11B"
    assert trans_12b["-2 Energy Drop"] == "10B"

    # Test clock boundary wrap: 1A wraps backwards to 12A and 11A
    trans_1a = {t["label"]: t["code"] for t in get_extended_camelot_transitions("1A")}
    assert trans_1a["-1 Drop"] == "12A"
    assert trans_1a["-2 Energy Drop"] == "11A"
    assert trans_1a["+1 Boost"] == "2A"
    assert trans_1a["+2 Energy Boost"] == "3A"

    # Input by musical key name
    trans_key = get_extended_camelot_transitions("A minor")
    assert len(trans_key) == 6
    assert trans_key[0]["code"] == "8A"

    # Invalid input
    assert get_extended_camelot_transitions("") == []
    assert get_extended_camelot_transitions("InvalidKey") == []


def test_recommend_harmonic_shifts():
    """Verify minimal semitone shift recommendations between Deck A and Deck B."""
    # Same key (8B to 8B): top recommendation is exact Match with 0 semitone shift
    recs = recommend_harmonic_shifts("8B", "8B")
    assert len(recs) == 6
    assert recs[0]["semitones"] == 0
    assert recs[0]["label"] == "Match"
    assert recs[0]["compatibility"] == 1.0

    # All semitone shifts must fall within [-6, +6]
    for r in recs:
        assert -6 <= r["semitones"] <= 6

    # Verify sorted order by absolute semitone distance
    abs_distances = [abs(r["semitones"]) for r in recs]
    assert abs_distances == sorted(abs_distances)

    # Invalid keys
    assert recommend_harmonic_shifts("", "8B") == []
    assert recommend_harmonic_shifts("8B", "") == []


def test_calculate_beat_phase_error():
    """Verify beat phase error calculation and symmetric wrapping in [-T/2, +T/2]."""
    # Exactly in-phase at 120 BPM (period T = 0.5s)
    err = calculate_beat_phase_error(
        pos_a=10.0, bpm_a=120.0, t0_a=0.0,
        pos_b=5.0, bpm_b=120.0, t0_b=0.0,
    )
    assert err == pytest.approx(0.0, abs=1e-5)

    # Deck A ahead by 0.1s: phi_a = 0.1, phi_b = 0.0 -> err = +0.1
    err_ahead = calculate_beat_phase_error(
        pos_a=0.1, bpm_a=120.0, t0_a=0.0,
        pos_b=0.0, bpm_b=120.0, t0_b=0.0,
    )
    assert err_ahead == pytest.approx(0.1, abs=1e-5)

    # Deck B ahead by 0.1s: phi_a = 0.0, phi_b = 0.1 -> err = -0.1
    err_behind = calculate_beat_phase_error(
        pos_a=0.0, bpm_a=120.0, t0_a=0.0,
        pos_b=0.1, bpm_b=120.0, t0_b=0.0,
    )
    assert err_behind == pytest.approx(-0.1, abs=1e-5)

    # Wrap test: phi_a = 0.4, phi_b = 0.0 -> diff is 0.4s, which is > T/2 (0.25s), wraps to -0.1s
    err_wrap = calculate_beat_phase_error(
        pos_a=0.4, bpm_a=120.0, t0_a=0.0,
        pos_b=0.0, bpm_b=120.0, t0_b=0.0,
    )
    assert err_wrap == pytest.approx(-0.1, abs=1e-5)

    # Zero or negative BPM
    assert calculate_beat_phase_error(1.0, 0.0, 0.0, 1.0, 120.0, 0.0) == 0.0


def test_calculate_momentary_nudge_rate():
    """Verify momentary pitch-bend playback rate calculation for nudges."""
    # Forward (+2%)
    assert calculate_momentary_nudge_rate(1.0, "forward", 0.02) == pytest.approx(1.02, abs=1e-5)
    assert calculate_momentary_nudge_rate(1.0, "fwd", 0.03) == pytest.approx(1.03, abs=1e-5)
    assert calculate_momentary_nudge_rate(1.0, "+", 0.02) == pytest.approx(1.02, abs=1e-5)

    # Backward (-2%)
    assert calculate_momentary_nudge_rate(1.0, "backward", 0.02) == pytest.approx(0.98, abs=1e-5)
    assert calculate_momentary_nudge_rate(1.0, "bwd", 0.04) == pytest.approx(0.96, abs=1e-5)
    assert calculate_momentary_nudge_rate(1.0, "-", 0.02) == pytest.approx(0.98, abs=1e-5)

    # Unknown direction returns base rate unchanged
    assert calculate_momentary_nudge_rate(1.05, "unknown") == 1.05

    # Boundary clamping
    assert calculate_momentary_nudge_rate(1.99, "+", 0.1) == 2.0
    assert calculate_momentary_nudge_rate(0.51, "-", 0.1) == 0.5


# ==============================================================================
# 3. Dual-Deck Transport Controller Tests (audio_transport.py)
# ==============================================================================


def test_transport_initialization_and_volume_attenuation():
    """Verify dual QAudioOutput volume calculations upon crossfader repositioning."""
    ctrl = AudioTransportController(None)
    assert ctrl._player_a is not None
    assert ctrl._player_b is not None
    assert ctrl._output_a is not None
    assert ctrl._output_b is not None
    assert ctrl.activeSlot() == "A"
    assert not ctrl.isPlaying()

    # Default crossfade is 0.5 equal_power
    vol_a = ctrl._output_a.volume()
    vol_b = ctrl._output_b.volume()
    expected_vol = 0.9 * (math.sqrt(2.0) / 2.0)
    assert vol_a == pytest.approx(expected_vol, abs=1e-3)
    assert vol_b == pytest.approx(expected_vol, abs=1e-3)

    # Crossfade full left (0.0): Deck A = 0.9, Deck B = 0.0
    ctrl.setCrossfade(0.0)
    assert ctrl._output_a.volume() == pytest.approx(0.9, abs=1e-3)
    assert ctrl._output_b.volume() == pytest.approx(0.0, abs=1e-3)

    # Crossfade full right (1.0): Deck A = 0.0, Deck B = 0.9
    ctrl.setCrossfade(1.0)
    assert ctrl._output_a.volume() == pytest.approx(0.0, abs=1e-3)
    assert ctrl._output_b.volume() == pytest.approx(0.9, abs=1e-3)

    # Linear crossfade at 0.5: Deck A = 0.45, Deck B = 0.45
    ctrl.setCrossfade(0.5, curve="linear")
    assert ctrl._output_a.volume() == pytest.approx(0.45, abs=1e-3)
    assert ctrl._output_b.volume() == pytest.approx(0.45, abs=1e-3)


def test_transport_playback_rate():
    """Verify dynamic playback rate routing to independent decks."""
    ctrl = AudioTransportController(None)
    mock_pa = MagicMock()
    mock_pb = MagicMock()
    ctrl._player_a = mock_pa
    ctrl._player = mock_pa
    ctrl._player_b = mock_pb

    ctrl.setPlaybackRate("A", 1.05)
    mock_pa.setPlaybackRate.assert_called_with(1.05)

    ctrl.setPlaybackRate("B", 0.94)
    mock_pb.setPlaybackRate.assert_called_with(0.94)

    # Clamping
    ctrl.setPlaybackRate("A", 3.0)
    mock_pa.setPlaybackRate.assert_called_with(2.0)

    ctrl.setPlaybackRate("B", 0.1)
    mock_pb.setPlaybackRate.assert_called_with(0.5)


def test_transport_play_and_stop_dual_decks(tmp_path: Path):
    """Verify independent playDeck and stopDeck operations on Deck A and Deck B."""
    ctrl = AudioTransportController(None)
    wav_a = _create_wav(tmp_path / "deck_a.wav")
    wav_b = _create_wav(tmp_path / "deck_b.wav")
    ctrl.setSlotA(wav_a)
    ctrl.setSlotB(wav_b)

    mock_pa = MagicMock()
    mock_pb = MagicMock()
    mock_pa.playbackState.return_value = QMediaPlayer.PlaybackState.PlayingState
    mock_pb.playbackState.return_value = QMediaPlayer.PlaybackState.PlayingState
    mock_pa.mediaStatus.return_value = QMediaPlayer.MediaStatus.LoadedMedia
    mock_pb.mediaStatus.return_value = QMediaPlayer.MediaStatus.LoadedMedia
    mock_pa.position.return_value = 1500
    mock_pb.position.return_value = 3500

    ctrl._player_a = mock_pa
    ctrl._player = mock_pa
    ctrl._player_b = mock_pb

    # Play Deck A
    assert ctrl.playDeck("A", 1.5)
    assert ctrl._current_source == wav_a
    mock_pa.play.assert_called()

    # Play Deck B
    assert ctrl.playDeck("B", 3.5)
    assert ctrl._source_b == wav_b
    mock_pb.play.assert_called()

    assert ctrl.isDeckPlaying("A")
    assert ctrl.isDeckPlaying("B")
    assert ctrl.deckPositionSec("A") == pytest.approx(1.5, abs=1e-3)
    assert ctrl.deckPositionSec("B") == pytest.approx(3.5, abs=1e-3)

    # Stop Deck A only -> Deck B is still playing so ctrl.isPlaying() remains True
    mock_pa.playbackState.return_value = QMediaPlayer.PlaybackState.StoppedState
    ctrl.stopDeck("A")
    mock_pa.stop.assert_called()
    assert ctrl.isPlaying()

    # Stop Deck B -> neither deck playing so ctrl.isPlaying() becomes False
    mock_pb.playbackState.return_value = QMediaPlayer.PlaybackState.StoppedState
    ctrl.stopDeck("B")
    mock_pb.stop.assert_called()
    assert not ctrl.isPlaying()


def test_transport_seeking_and_status_events():
    """Verify seeking on dual decks with loaded vs pending media status."""
    ctrl = AudioTransportController(None)
    mock_pa = MagicMock()
    mock_pb = MagicMock()
    ctrl._player_a = mock_pa
    ctrl._player = mock_pa
    ctrl._player_b = mock_pb

    # Unloaded state: sets pending seek ms
    mock_pa.mediaStatus.return_value = QMediaPlayer.MediaStatus.LoadingMedia
    mock_pb.mediaStatus.return_value = QMediaPlayer.MediaStatus.LoadingMedia
    ctrl.seekDeck("A", 5.0)
    assert ctrl._pending_seek_ms == 5000

    ctrl.seekDeck("B", 8.0)
    assert ctrl._pending_seek_b_ms == 8000

    # Media status becomes LoadedMedia -> pending seek is executed
    ctrl._on_media_status(QMediaPlayer.MediaStatus.LoadedMedia)
    mock_pa.setPosition.assert_called_with(5000)
    assert ctrl._pending_seek_ms is None

    ctrl._on_media_b_status(QMediaPlayer.MediaStatus.LoadedMedia)
    mock_pb.setPosition.assert_called_with(8000)
    assert ctrl._pending_seek_b_ms is None


def test_transport_legacy_compatibility(tmp_path: Path):
    """Verify complete backward compatibility for legacy callers and tests."""
    ctrl = AudioTransportController(None)
    wav_a = _create_wav(tmp_path / "track_a.wav")
    wav_b = _create_wav(tmp_path / "track_b.wav")

    ctrl.setSlotA(wav_a)
    assert ctrl._slot_a == wav_a
    assert ctrl.activeSlot() == "A"

    ctrl.setSlotB(wav_b)
    assert ctrl._slot_b == wav_b

    # Stem preview setup
    ctrl.setStemPreview(wav_b, stem_name="vocals", auto_play=False)
    assert ctrl.activeStem() == "vocals"
    assert "Auditioning vocals" in ctrl.auditionLabel()

    # Position signal emission
    pos_emitted = []
    ctrl.positionChanged.connect(pos_emitted.append)
    ctrl._on_position_changed(4500)
    assert pos_emitted == [pytest.approx(4.5, abs=1e-3)]

    # Stop resets playing state
    ctrl.stop()
    assert not ctrl.isPlaying()


# ==============================================================================
# 4. DJ Rack & Sync Execution Tests (audio_tools_dj.py)
# ==============================================================================


def test_dj_rack_build_and_components(qtbot):
    """Verify build_dj_rack creates Deck A, Crossfader, and Deck B components."""
    page = QWidget()
    qtbot.addWidget(page)
    rack = build_dj_rack(page)
    assert rack is not None
    assert hasattr(page, "djDeckA")
    assert hasattr(page, "djDeckB")
    assert hasattr(page, "djCrossfader")
    assert hasattr(page, "djRack")
    assert page.djDeckA.deck == "A"
    assert page.djDeckB.deck == "B"


def test_dj_rack_cue_and_hot_cues(qtbot):
    """Verify CUE jump to 0.0s and Hot-Cue 1/2/3 set and recall mechanics."""
    page = QWidget()
    qtbot.addWidget(page)
    build_dj_rack(page)

    mock_transport = MagicMock()
    mock_transport.deckPositionSec.return_value = 12.34
    page.transport = mock_transport

    wire_dj_events(page)

    # Press CUE on Deck A -> seeks to 0.0
    page.djDeckA.cueBtn.pressed.emit()
    mock_transport.seekDeck.assert_called_with("A", 0.0)

    # First click on H1: stores 12.34
    page.djDeckA.h1Btn.clicked.emit()
    assert page._hot_cues["A"][0] == 12.34

    # Change current position to 25.0
    mock_transport.deckPositionSec.return_value = 25.0
    mock_transport.seekDeck.reset_mock()

    # Second click on H1: recalls stored 12.34
    page.djDeckA.h1Btn.clicked.emit()
    mock_transport.seekDeck.assert_called_with("A", 12.34)

    # Click on H2: stores 25.0
    page.djDeckA.h2Btn.clicked.emit()
    assert page._hot_cues["A"][1] == 25.0


def test_dj_rack_nudge_pitch_bend_events(qtbot):
    """Verify momentary pitch-bend rate adjustments upon nudge press and release."""
    page = QWidget()
    qtbot.addWidget(page)
    build_dj_rack(page)

    mock_transport = MagicMock()
    page.transport = mock_transport
    page._rate_b = 1.05

    wire_dj_events(page)

    # Press Deck B forward nudge (+3% on 1.05 base)
    page.djDeckB.nudgeFwdBtn.pressed.emit()
    mock_transport.setPlaybackRate.assert_called_with("B", pytest.approx(1.05 * 1.03, abs=1e-4))

    # Release Deck B forward nudge -> returns to base 1.05
    page.djDeckB.nudgeFwdBtn.released.emit()
    mock_transport.setPlaybackRate.assert_called_with("B", pytest.approx(1.05, abs=1e-4))

    # Press Deck B backward nudge (-3% on 1.05 base)
    page.djDeckB.nudgeBackBtn.pressed.emit()
    mock_transport.setPlaybackRate.assert_called_with("B", pytest.approx(1.05 * 0.97, abs=1e-4))


def test_handle_dj_sync_execution(qtbot):
    """Verify harmonic tempo sync and semitone shift application."""
    page = QWidget()
    qtbot.addWidget(page)
    build_dj_rack(page)

    mock_transport = MagicMock()
    page.transport = mock_transport
    page.bpmSpin = QSpinBox()
    page.bpmSpin.setRange(30, 300)
    page.bpmSpin.setValue(128)
    page._bpm_b = 120.0
    page._deck_b_key = "3B"

    status_mock = MagicMock()
    page.statusLabel = status_mock

    semitone_spin = QSpinBox()
    semitone_spin.setRange(-12, 12)
    page.semitoneSpin = semitone_spin

    # Sync Deck B to Deck A
    handle_dj_sync(page, "B")

    # Ratio: 128 / 120 = 1.0667x
    expected_ratio = 128.0 / 120.0
    mock_transport.setPlaybackRate.assert_called_with("B", pytest.approx(expected_ratio, abs=1e-3))
    assert page._rate_b == pytest.approx(expected_ratio, abs=1e-3)

    # Status label was updated
    status_mock.setText.assert_called()
    status_text = status_mock.setText.call_args[0][0]
    assert "Deck B synced" in status_text
    assert "1.07x (direct)" in status_text
    assert "Key shift -1 st (8B)" in status_text

    # Semitone shift was computed and applied to semitoneSpin
    assert semitone_spin.value() == -1


def test_handle_dj_sync_half_and_double_time(qtbot):
    """Verify half-time and double-time ratio resolution during sync execution."""
    page = QWidget()
    qtbot.addWidget(page)
    build_dj_rack(page)
    mock_transport = MagicMock()
    page.transport = mock_transport
    page.bpmSpin = QSpinBox()
    page.bpmSpin.setRange(30, 300)

    # Deck A = 140, Deck B = 70 -> half-time match (ratio ~ 1.0)
    page.bpmSpin.setValue(140)
    page._bpm_b = 70.0
    handle_dj_sync(page, "B")
    mock_transport.setPlaybackRate.assert_called_with("B", pytest.approx(1.0, abs=1e-3))
    assert page._rate_b == pytest.approx(1.0, abs=1e-3)

    # Deck A = 70, Deck B = 140 -> double-time match (ratio ~ 1.0)
    page.bpmSpin.setValue(70)
    page._bpm_b = 140.0
    handle_dj_sync(page, "B")
    mock_transport.setPlaybackRate.assert_called_with("B", pytest.approx(1.0, abs=1e-3))


def test_handle_dj_sync_deck_a_slave(qtbot):
    """Verify syncing Deck A (slave) to Deck B (master)."""
    page = QWidget()
    qtbot.addWidget(page)
    build_dj_rack(page)
    mock_transport = MagicMock()
    page.transport = mock_transport

    page.bpmSpin = QSpinBox()
    page.bpmSpin.setRange(30, 300)
    page.bpmSpin.setValue(120)  # Deck A BPM
    page._bpm_b = 126.0         # Deck B BPM (master when syncing A)

    handle_dj_sync(page, "A")
    # Ratio = 126 / 120 = 1.05
    mock_transport.setPlaybackRate.assert_called_with("A", pytest.approx(126.0 / 120.0, abs=1e-3))
    assert page._rate_a == pytest.approx(1.05, abs=1e-3)


def test_handle_dj_sync_minimal_page_robustness(qtbot):
    """Verify handle_dj_sync executes safely even without optional status/key widgets."""
    page = QWidget()
    qtbot.addWidget(page)
    build_dj_rack(page)
    mock_transport = MagicMock()
    page.transport = mock_transport
    # No bpmSpin, no semitoneSpin, no statusLabel
    handle_dj_sync(page, "B")
    mock_transport.setPlaybackRate.assert_called()


def test_transport_invalid_files_and_deck_switching(tmp_path: Path):
    """Verify playDeck handles missing files safely and slot toggling behaves properly."""
    ctrl = AudioTransportController(None)
    assert not ctrl.playDeck("A", 0.0)
    assert not ctrl.playDeck("B", 0.0)

    # Non-existent path
    fake_path = tmp_path / "does_not_exist.wav"
    ctrl.setSlotA(fake_path)
    assert not ctrl.playDeck("A", 0.0)

    # Valid wavs
    wav_a = _create_wav(tmp_path / "track_a.wav")
    wav_b = _create_wav(tmp_path / "track_b.wav")
    ctrl.setSlotA(wav_a)
    ctrl.setSlotB(wav_b)

    # Mock player
    mock_pa = MagicMock()
    mock_pb = MagicMock()
    mock_pa.position.return_value = 0
    mock_pb.position.return_value = 0
    ctrl._player_a = mock_pa
    ctrl._player = mock_pa
    ctrl._player_b = mock_pb

    # Toggle AB when slot B is set
    assert ctrl.toggleAB() == "B"
    assert ctrl.activeSlot() == "B"

    # Toggle back to A
    assert ctrl.toggleAB() == "A"
    assert ctrl.activeSlot() == "A"

    # Clearing slot B stops deck B
    ctrl.setSlotB(None)
    assert ctrl._slot_b is None
    mock_pb.stop.assert_called()


def test_crossfader_unrecognized_curve_and_negative_step():
    """Verify fallback to equal_power and negative step handling in crossfader DSP."""
    # Unrecognized curve defaults to equal_power
    ga, gb = crossfader_gains(0.5, "completely_unknown_curve")
    expected = math.sqrt(2.0) / 2.0
    assert ga == pytest.approx(expected, abs=1e-4)
    assert gb == pytest.approx(expected, abs=1e-4)

    # Negative step magnitude in step_crossfader
    stepped = step_crossfader(0.2, 0.5, step=-0.1)
    assert stepped == pytest.approx(0.3, abs=1e-5)

