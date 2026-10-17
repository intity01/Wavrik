"""Unit and integration tests for Phase 2 Audio Tools and Wavrik branding."""

from __future__ import annotations

from array import array
import math
from pathlib import Path
from unittest.mock import MagicMock, patch
import wave

import pytest

from src.core.config import Config
from src.core.updater import UpdateManager
from src.services.audio_analysis import analyze_audio_file, camelot_code, enharmonic_key, transpose_key
from src.services.audio_pitch import (
    build_export_filename,
    render_pitch_shift,
    unique_export_path,
)
from src.ui.main_window import MediaDownloaderUI


def _write_test_wav(path: Path, seconds: float = 4.0, sr: int = 11025, bpm: float = 120.0) -> Path:
    """Create a pulsed C-major triad WAV for deterministic analysis and pitch tests."""
    freqs = (261.63, 329.63, 392.00)
    beat_period = 60.0 / bpm
    samples = array("h")
    total = int(seconds * sr)
    for i in range(total):
        t = i / float(sr)
        phase_in_beat = (t % beat_period) / beat_period
        env = math.exp(-4.0 * phase_in_beat)
        val = sum(math.sin(2.0 * math.pi * f * t) for f in freqs) / len(freqs)
        samples.append(int(max(-0.9, min(0.9, val * env * 0.8)) * 32767))
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(samples.tobytes())
    return path


def test_wavrik_branding_in_config_and_window(qtbot, config, logger, fake_downloader, history):
    assert Config.APP_NAME == "Wavrik"
    tray = MagicMock()
    tray.isAvailable.return_value = False
    window = MediaDownloaderUI(
        config, logger, fake_downloader,
        UpdateManager("2.1.0", "owner/repo", logger), tray, history,
    )
    qtbot.addWidget(window)
    assert window.windowTitle() == "Wavrik"
    assert "AudioToolsInterface" in window.navigationPanel.buttons


def test_key_transposition_and_camelot_codes():
    assert camelot_code("C major") == "8B"
    assert camelot_code("A minor") == "8A"
    assert camelot_code("F minor") == "4A"
    assert camelot_code("Eb minor") == "2A"
    assert enharmonic_key("D# minor") == "Eb minor"
    shifted = transpose_key("F minor", -2)
    assert shifted == "D# minor"
    assert camelot_code(shifted) == "2A"


def test_analyze_audio_file_estimates_key_and_bpm(tmp_path: Path):
    wav_path = _write_test_wav(tmp_path / "c_major_120bpm.wav", seconds=6.0, bpm=120.0)
    result = analyze_audio_file(wav_path, max_seconds=6)
    assert result["status"] == "estimate"
    assert "Experimental / Estimate" in result["badge"]
    assert result["key"] in {"C major", "A minor", "G major", "F major", "E minor"}
    assert 110.0 <= float(result["bpm"]) <= 130.0
    assert len(result["key_candidates"]) == 3


def test_build_export_filename_and_unique_export_path(tmp_path: Path):
    name = build_export_filename("C:/music/vocal_track.mp3", -2, "D# minor", "wav")
    assert name == "vocal_track_[Key_D#m_-2st].wav"

    first = unique_export_path(tmp_path, name)
    assert first == tmp_path / name
    first.write_bytes(b"data")

    second = unique_export_path(tmp_path, name)
    assert second == tmp_path / "vocal_track_[Key_D#m_-2st]_1.wav"


def test_render_pitch_shift_safety_guards_and_real_render(tmp_path: Path):
    source = _write_test_wav(tmp_path / "source.wav", seconds=1.5)
    orig_bytes = source.read_bytes()

    with pytest.raises(ValueError, match="differ"):
        render_pitch_shift(source, source, -2)

    with pytest.raises(ValueError, match="-12 to \\+12"):
        render_pitch_shift(source, tmp_path / "bad.wav", -15)

    out_r3 = render_pitch_shift(source, tmp_path / "out_r3.wav", -2, engine="r3_finer", fmt="wav")
    assert out_r3.is_file() and out_r3.stat().st_size > 1000
    assert source.read_bytes() == orig_bytes

    out_ff = render_pitch_shift(source, tmp_path / "out_ff.wav", 2, engine="ffmpeg_formant", fmt="wav")
    assert out_ff.is_file() and out_ff.stat().st_size > 1000


def test_library_to_audio_tools_navigation_and_controls(
    qtbot, config, logger, fake_downloader, history, tmp_path: Path,
):
    tray = MagicMock()
    tray.isAvailable.return_value = False
    window = MediaDownloaderUI(
        config, logger, fake_downloader,
        UpdateManager("2.1.0", "owner/repo", logger), tray, history,
    )
    qtbot.addWidget(window)
    window.show()

    wav_path = _write_test_wav(tmp_path / "song.wav", seconds=2.0)
    with patch("src.ui.pages.library_page.get_open_file_path", return_value=wav_path):
        window.pageLibrary._add_local()

    card = window.pageLibrary.listLay.itemAt(0).widget()
    card._open_audio_tools()

    assert window.stackedWidget.currentWidget() is window.pageAudioTools
    assert window.pageAudioTools._source == wav_path

    tools = window.pageAudioTools
    tools.detectedKeyCombo.setCurrentText("F minor")
    tools.semitoneSpin.setValue(-2)
    assert "D# minor (2A)" in tools.resultingKeyLabel.text()
    assert "Key_D#m_-2st" in tools.outputPreviewLabel.text()

    tools.bpmSpin.setValue(140.0)
    tools.halfBpmBtn.click()
    assert tools.bpmSpin.value() == 70.0
    tools.doubleBpmBtn.click()
    assert tools.bpmSpin.value() == 140.0
