"""Offline unit and integration tests for waveform spectrogram, beat grid, and transport."""

from __future__ import annotations

import numpy as np
from PyQt6.QtCore import QPoint, Qt
import pytest

from src.services.audio_beat_grid import (
    compute_beat_grid,
    detect_beat_phase_offset,
    get_adaptive_grid_markers,
)
from src.services.audio_spectrogram import (
    _aggregate_bands,
    _normalize_spectrogram,
    compute_spectrogram,
    downsample_spectrogram_columns,
)
from src.ui.components.audio_transport import AudioTransportController
from src.ui.components.waveform_widget import WaveformWidget


def test_compute_spectrogram_shape_and_bounds():
    sr = 16000
    t = np.linspace(0.0, 1.0, sr, endpoint=False, dtype=np.float32)
    sine_wave = np.sin(2.0 * np.pi * 440.0 * t).astype(np.float32)

    spec = compute_spectrogram(sine_wave, sr=sr, n_fft=512, hop=256, n_bands=40)

    expected_frames = (len(sine_wave) - 512) // 256 + 1
    assert spec.shape == (expected_frames, 40)
    assert spec.dtype == np.float32
    assert np.all(spec >= 0.0)
    assert np.all(spec <= 1.0)
    assert float(np.max(spec)) > 0.0

    stereo = np.column_stack([sine_wave, sine_wave * 0.8])
    spec_stereo = compute_spectrogram(stereo, sr=sr, n_fft=512, hop=256, n_bands=40)
    assert spec_stereo.shape == (expected_frames, 40)
    assert spec_stereo.dtype == np.float32


def test_compute_spectrogram_empty_or_silence():
    empty = np.zeros(0, dtype=np.float32)
    spec_empty = compute_spectrogram(empty, sr=16000, n_fft=512, hop=256, n_bands=40)
    assert spec_empty.shape == (0, 40)
    assert spec_empty.dtype == np.float32

    short = np.ones(200, dtype=np.float32)
    spec_short = compute_spectrogram(short, sr=16000, n_fft=512, hop=256, n_bands=40)
    assert spec_short.shape == (0, 40)

    assert compute_spectrogram(short, n_bands=0).shape == (0, 0)
    assert compute_spectrogram(short, hop=0).shape == (0, 40)

    silence = np.zeros(16000, dtype=np.float32)
    spec_silence = compute_spectrogram(silence, sr=16000, n_fft=512, hop=256, n_bands=40)
    assert spec_silence.shape == (61, 40)
    assert np.allclose(spec_silence, 0.0)


def test_downsample_spectrogram_columns():
    sr = 16000
    t = np.linspace(0.0, 1.0, sr, endpoint=False, dtype=np.float32)
    sine_wave = np.sin(2.0 * np.pi * 440.0 * t).astype(np.float32)
    spec = compute_spectrogram(sine_wave, sr=sr, n_fft=512, hop=256, n_bands=40)

    target_cols = 50
    down = downsample_spectrogram_columns(spec, target_cols)
    assert down.shape == (target_cols, 40)
    assert down.dtype == np.float32
    assert np.all(down >= 0.0)
    assert np.all(down <= 1.0)

    down_same = downsample_spectrogram_columns(spec, spec.shape[0])
    assert down_same.shape == spec.shape
    assert np.allclose(down_same, spec)

    empty_spec = np.zeros((0, 40), dtype=np.float32)
    down_empty = downsample_spectrogram_columns(empty_spec, target_cols)
    assert down_empty.shape == (target_cols, 40)

    down_zero = downsample_spectrogram_columns(spec, 0)
    assert down_zero.shape == (0, 40)


def test_spectrogram_internal_helpers():
    empty_bands = _aggregate_bands(np.zeros((0, 100), dtype=np.float32), 40)
    assert empty_bands.shape == (0, 40)

    zero_bands = _aggregate_bands(np.ones((10, 100), dtype=np.float32), 0)
    assert zero_bands.shape == (10, 0)

    uniform_matrix = np.full((10, 40), 5.0, dtype=np.float32)
    norm_uniform = _normalize_spectrogram(uniform_matrix)
    assert np.allclose(norm_uniform, 0.0)

    empty_norm = _normalize_spectrogram(np.zeros((0, 0), dtype=np.float32))
    assert empty_norm.size == 0


def test_compute_beat_grid_values():
    bpm = 120.0
    duration = 60.0
    grid = compute_beat_grid(bpm, duration)

    assert grid["bpm"] == 120.0
    assert grid["duration"] == 60.0
    assert pytest.approx(grid["beat_interval"], 1e-4) == 0.5
    assert grid["first_beat_sec"] == 0.0
    assert len(grid["beats"]) == 121
    assert len(grid["downbeats"]) == 31
    assert len(grid["phrase_markers"]) == 8
    assert grid["phrase_markers"][0] == 0.0
    assert grid["phrase_markers"][1] == 8.0

    grid_offset = compute_beat_grid(120.0, 10.0, first_beat_sec=0.2)
    assert grid_offset["first_beat_sec"] == 0.2
    assert grid_offset["beats"][0] == 0.2
    assert grid_offset["beats"][1] == 0.7

    grid_zero = compute_beat_grid(120.0, 0.0)
    assert grid_zero["beats"] == []
    assert grid_zero["downbeats"] == []
    assert grid_zero["phrase_markers"] == []


def test_detect_beat_phase_offset():
    sr = 16000
    bpm = 120.0
    beat_interval = 60.0 / bpm
    duration = 4.0
    total_samples = int(duration * sr)
    pulse_audio = np.zeros(total_samples, dtype=np.float32)

    t0_target = 0.15
    for beat_idx in range(int(duration / beat_interval)):
        onset_sample = int((t0_target + beat_idx * beat_interval) * sr)
        if onset_sample + 64 < total_samples:
            pulse_audio[onset_sample : onset_sample + 64] = 0.9

    detected_offset = detect_beat_phase_offset(pulse_audio, sr=sr, bpm=bpm)
    assert isinstance(detected_offset, float)
    assert 0.0 <= detected_offset <= beat_interval

    silence = np.zeros(total_samples, dtype=np.float32)
    assert detect_beat_phase_offset(silence, sr=sr, bpm=bpm) == 0.0

    assert detect_beat_phase_offset(pulse_audio, sr=0, bpm=bpm) == 0.0
    assert detect_beat_phase_offset(pulse_audio, sr=sr, bpm=0.0) == 0.0


def test_get_adaptive_grid_markers():
    grid = compute_beat_grid(120.0, 60.0)

    markers_large = get_adaptive_grid_markers(grid, width_px=800, duration=60.0)
    kinds_large = {kind for _, kind in markers_large}
    assert "beat" in kinds_large
    assert "downbeat" in kinds_large
    assert len(markers_large) == len(grid["beats"])

    markers_medium = get_adaptive_grid_markers(grid, width_px=400, duration=60.0)
    kinds_medium = {kind for _, kind in markers_medium}
    assert kinds_medium == {"downbeat"}
    assert len(markers_medium) == len(grid["downbeats"])

    markers_small = get_adaptive_grid_markers(grid, width_px=150, duration=60.0)
    kinds_small = {kind for _, kind in markers_small}
    assert kinds_small == {"phrase"}
    assert len(markers_small) == len(grid["phrase_markers"])

    assert get_adaptive_grid_markers(grid, width_px=0, duration=60.0) == []
    assert get_adaptive_grid_markers(grid, width_px=800, duration=0.0) == []


def test_waveform_widget_spectrogram_and_beat_grid(qtbot):
    widget = WaveformWidget()
    qtbot.addWidget(widget)
    widget.resize(400, 78)
    widget.show()

    widget.setPeaks([0.2, 0.8, 0.5], 10.0, section_text="Intro | Verse")
    assert len(widget._peaks) == 3

    spec_matrix = np.full((50, 40), 0.6, dtype=np.float32)
    widget.setSpectrogram(spec_matrix)
    assert widget._spectrogram is not None
    assert widget._spectrogram.shape == (50, 40)

    widget.setBpm(120.0)
    grid = widget.beatGrid()
    assert grid is not None
    assert grid["bpm"] == 120.0
    assert len(grid["beats"]) > 0

    widget.setKeyCamelot("8B")
    widget.repaint()

    received_seeks: list[float] = []
    widget.seekRequested.connect(received_seeks.append)
    qtbot.mouseClick(widget, Qt.MouseButton.LeftButton, pos=QPoint(200, 39))
    assert len(received_seeks) == 1
    assert 0.0 <= received_seeks[0] <= 10.0

    widget.setSeekPosition(3.0)
    assert widget.seekPosition() == 3.0

    widget.clear()
    assert widget.seekPosition() == 0.0
    assert widget.beatGrid() is None
    assert widget._spectrogram is None

    # Empty repaint test
    widget.repaint()


def test_audio_transport_position_signal(qtbot):
    controller = AudioTransportController(None)

    received_positions: list[float] = []
    controller.positionChanged.connect(received_positions.append)

    controller._on_position_changed(2500)
    assert len(received_positions) == 1
    assert pytest.approx(received_positions[0], 1e-3) == 2.5

    controller._on_position_changed(0)
    assert len(received_positions) == 2
    assert received_positions[1] == 0.0

    controller._on_position_changed(12345)
    assert len(received_positions) == 3
    assert pytest.approx(received_positions[2], 1e-3) == 12.345
