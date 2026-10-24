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
from src.services.audio_analysis import (
    analyze_audio_file,
    camelot_code,
    enharmonic_key,
    mirex_bpm_score,
    mirex_key_score,
    transpose_key,
)
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
    assert mirex_key_score("Eb minor", "D# minor") == (1.0, "exact")
    assert mirex_key_score("G major", "C major") == (0.5, "fifth")
    assert mirex_key_score("A minor", "C major") == (0.3, "relative")
    assert mirex_key_score("F minor", "F major") == (0.2, "parallel")
    assert mirex_bpm_score(80.0, 80.0) == (1.0, "acc1_exact")
    assert mirex_bpm_score(160.0, 80.0) == (0.5, "acc2_harmonic")


def test_analyze_audio_file_estimates_key_and_bpm(tmp_path: Path):
    wav_path = _write_test_wav(tmp_path / "c_major_120bpm.wav", seconds=6.0, bpm=120.0)
    result = analyze_audio_file(wav_path, max_seconds=6)
    assert result["status"] == "estimate"
    assert "Experimental / Estimate" in result["badge"]
    assert 50 <= int(result["confidence"]) <= 99
    assert result["first_half_key"] in {"C major", "A minor", "G major", "F major", "E minor"}
    assert "section_summary" in result
    assert result["key"] in {"C major", "A minor", "G major", "F major", "E minor"}
    assert 110.0 <= float(result["bpm"]) <= 130.0
    assert len(result["key_candidates"]) == 3


def test_build_export_filename_and_unique_export_path(tmp_path: Path):
    name = build_export_filename("C:/music/vocal_track.mp3", -2, "D# minor", "wav")
    assert name == "vocal_track_[Key_D#m_-2st].wav"
    stretched = build_export_filename("C:/music/vocal_track.mp3", -2, "D# minor", "wav", 132.0)
    assert stretched == "vocal_track_[Key_D#m_132BPM_-2st].wav"

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

    with pytest.raises(ValueError, match="0.5x to 2.0x"):
        render_pitch_shift(source, tmp_path / "bad_tempo.wav", 0, tempo_ratio=3.0)

    out_r3 = render_pitch_shift(source, tmp_path / "out_r3.wav", -2, engine="r3_finer", fmt="wav", tempo_ratio=1.1)
    assert out_r3.is_file() and out_r3.stat().st_size > 1000
    assert source.read_bytes() == orig_bytes

    out_ff = render_pitch_shift(source, tmp_path / "out_ff.wav", 2, engine="ffmpeg_formant", fmt="wav", tempo_ratio=0.9)
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

    window.pageLibrary.storeAnalysisResult({
        "filePath": str(wav_path),
        "key": "F# minor",
        "camelot": "11A",
        "bpm": 88.0,
        "confidence": 90,
        "section_summary": "Stable: F# minor (11A) throughout",
        "key_candidates": [{"key": "F# minor", "correlation": 0.85}, {"key": "A major", "correlation": 0.72}],
    })
    card = window.pageLibrary.listLay.itemAt(0).widget()
    assert "F# minor (11A)" in card.metadata.text()
    card._open_audio_tools()

    assert window.stackedWidget.currentWidget() is window.pageAudioTools
    assert window.pageAudioTools._source == wav_path

    tools = window.pageAudioTools
    assert tools.detectedKeyCombo.currentText() == "F# minor"
    tools.candButtons[1].click()
    assert tools.detectedKeyCombo.currentText() == "A major"
    tools.detectedKeyCombo.setCurrentText("F minor")
    tools.semitoneSpin.setValue(-2)
    assert "D# minor (2A)" in tools.resultingKeyLabel.text()
    assert "Key_D#m_-2st" in tools.outputPreviewLabel.text()

    tools.bpmSpin.setValue(140.0)
    tools.halfBpmBtn.click()
    assert tools.bpmSpin.value() == 70.0
    tools.doubleBpmBtn.click()
    assert tools.bpmSpin.value() == 140.0
    tools.targetBpmSpin.setValue(154.0)
    assert "1.10x" in tools.tempoRatioLabel.text()
    assert "154BPM" in tools.outputPreviewLabel.text()

    # Camelot harmonic mix button check
    assert len(tools.camelotButtons) == 4
    # F# minor harmonic neighbors: 11A Match (0st), 11B Rel (+3st)
    assert "11A" in tools.camelotButtons[0].text()
    assert "11B" in tools.camelotButtons[1].text()
    tools.camelotButtons[1].click()
    assert tools.semitoneSpin.value() == 3
    assert hasattr(tools, "waveformWidget")


def test_long_filename_elision_and_persisted_analysis(
    qtbot, config, logger, fake_downloader, history, tmp_path: Path,
):
    tray = MagicMock()
    tray.isAvailable.return_value = False
    window = MediaDownloaderUI(
        config, logger, fake_downloader,
        UpdateManager("2.1.0", "owner/repo", logger), tray, history,
    )
    qtbot.addWidget(window)
    window.resize(1120, 760)
    window.show()

    long_name = (
        "Dua Lipa - Training Season (Live from the Royal Albert Hall) "
        "[Official Performance Video] (Instrumental) (Mel-RoFormer by Gabox Fv7).wav"
    )
    wav_path = _write_test_wav(tmp_path / long_name, seconds=2.0)
    with patch("src.ui.pages.library_page.get_open_file_path", return_value=wav_path):
        window.pageLibrary._add_local()

    analysis_payload = {
        "filePath": str(wav_path),
        "key": "F minor",
        "camelot": "4A",
        "bpm": 123.0,
        "confidence": 92,
        "section_summary": "Stable: F minor (4A) throughout",
        "key_candidates": [{"key": "F minor", "correlation": 0.89}],
        "peaks": [0.05, 0.2, 0.15, 0.25],
        "duration_sec": 210.0,
    }
    window.pageLibrary.storeAnalysisResult(analysis_payload)

    # Verify analysis is persisted to history.json across reloads
    saved_entries = history.getHistory()
    assert saved_entries[0]["analysis"]["key"] == "F minor"
    assert saved_entries[0]["analysis"]["camelot"] == "4A"

    # Load into Audio Tools and ensure long filename never blows out scroll content width
    window.pageAudioTools.loadFile(wav_path, analysis_payload)
    qtbot.wait(20)
    viewport_w = window.pageAudioTools.findChild(object, "AudioToolsCard").width()
    assert viewport_w <= window.width()
    assert long_name in window.pageAudioTools.fileLabel.text()
    assert max(window.pageAudioTools.waveformWidget._peaks) == 1.0


def test_camelot_wheel_harmonic_neighbors():
    from src.services.audio_camelot import get_harmonic_neighbors, key_from_camelot, semitone_distance

    assert key_from_camelot("11A") == "F# minor"
    assert key_from_camelot("8B") == "C major"
    assert semitone_distance("F# minor", "A major") == 3
    neighbors = get_harmonic_neighbors("F# minor")
    assert len(neighbors) == 4
    codes = [n["code"] for n in neighbors]
    assert codes == ["11A", "11B", "12A", "10A"]
    assert neighbors[0]["semitones"] == 0
    assert neighbors[1]["semitones"] == 3


def test_waveform_widget_rendering(qtbot):
    from src.ui.components.waveform_widget import WaveformWidget

    widget = WaveformWidget()
    qtbot.addWidget(widget)
    widget.show()
    widget.setPeaks([0.1, 0.4, 0.8, 0.9, 0.3], duration_sec=120.0, section_text="1st Half C | 2nd Half G")
    assert len(widget._peaks) == 5
    widget.clear()
    assert len(widget._peaks) == 0


def test_batch_audio_processing_service_and_worker(tmp_path: Path):
    from src.services.audio_batch import BatchJobConfig, process_batch_file
    from src.ui.workers.batch_worker import BatchAudioSignals, BatchAudioWorker

    wav1 = _write_test_wav(tmp_path / "track1.wav", seconds=1.0)
    wav2 = _write_test_wav(tmp_path / "track2.wav", seconds=1.0)
    out_dir = tmp_path / "batch_out"

    cfg = BatchJobConfig(semitones=-2, tempo_ratio=1.0, engine="r3_finer", fmt="wav", output_dir=out_dir)
    res = process_batch_file(wav1, cfg, known_key="C major")
    assert res.is_file() and res.stat().st_size > 1000

    processed = []
    signals = BatchAudioSignals()
    signals.itemProcessed.connect(lambda cur, tot, name: processed.append(name))
    worker = BatchAudioWorker([wav1, wav2], cfg, signals, {str(wav1): "C major", str(wav2): "A minor"})
    worker.run()
    assert len(processed) == 2


def test_stem_separation_bit_perfect_phase_lock(tmp_path: Path):
    from src.services.audio_stems import _read_pcm16, separate_stems

    src = _write_test_wav(tmp_path / "master_song.wav", seconds=1.5)
    out_dir = tmp_path / "stems"
    res = separate_stems(src, out_dir, mode="dsp_2stem")
    assert res.vocals_path.is_file()
    assert res.instrumental_path.is_file()

    m_pcm, _, _ = _read_pcm16(src)
    v_pcm, _, _ = _read_pcm16(res.vocals_path)
    i_pcm, _, _ = _read_pcm16(res.instrumental_path)
    assert len(m_pcm) == len(v_pcm) == len(i_pcm)
    # Prove 100% bit-perfect phase reconstruction: Master[i] == Vocal[i] + Instrumental[i]
    assert all(v_pcm[idx] + i_pcm[idx] == m_pcm[idx] for idx in range(len(m_pcm)))


def test_detuning_invariant_hpcp_432hz():
    from src.services.audio_hpcp import extract_key_candidates

    sr = 16000
    detune_ratio = 432.0 / 440.0
    # C-major progression notes (C4, E4, G4) detuned to A4=432Hz
    freqs = (261.63 * detune_ratio, 329.63 * detune_ratio, 392.00 * detune_ratio, 130.81 * detune_ratio)
    samples = [
        0.25 * sum(math.sin(2.0 * math.pi * f * (i / sr)) for f in freqs)
        for i in range(sr * 3)
    ]
    cands = extract_key_candidates(samples, sr)
    assert cands[0]["key"] in {"C major", "A minor", "G major"}


def test_interactive_waveform_seek_transport_and_stem_rack(
    qtbot, config, logger, fake_downloader, history, tmp_path: Path,
):
    tray = MagicMock()
    tray.isAvailable.return_value = False
    window = MediaDownloaderUI(
        config, logger, fake_downloader,
        UpdateManager("2.1.0", "owner/repo", logger), tray, history,
    )
    qtbot.addWidget(window)
    tools = window.pageAudioTools
    wav_path = _write_test_wav(tmp_path / "studio_track.wav", seconds=2.0)
    tools.loadFile(wav_path, {
        "filePath": str(wav_path),
        "key": "C major",
        "camelot": "8B",
        "bpm": 120.0,
        "confidence": 94,
        "section_summary": "Stable: C major (8B) throughout",
        "key_candidates": [{"key": "C major", "correlation": 0.91}],
        "peaks": [0.2, 0.5, 0.9, 0.6],
        "duration_sec": 60.0,
    })

    tools.waveformWidget.setSeekPosition(18.5)
    assert tools.waveformWidget.seekPosition() == 18.5
    tools._on_seek_requested(18.5)
    assert "0:18" in tools.statusLabel.text()

    tools._play_original()
    assert tools.transport.isPlaying()
    assert tools.transport.activeSlot() == "A"
    tools._stop_playback()
    assert not tools.transport.isPlaying()

    tools._separate_stems()
    qtbot.waitUntil(lambda: not tools._busy, timeout=8000)
    assert tools.loadVocalsBtn.isEnabled()
    assert tools.loadInstBtn.isEnabled()
    tools.loadInstBtn.click()
    assert "Instrumental" in tools._source.name
