"""Comprehensive tests for 4-Stem Separation, Phase Lock, and Stem Auditioning."""

from __future__ import annotations

from array import array
import math
from pathlib import Path
from unittest.mock import MagicMock
import wave

import numpy as np
import pytest

from src.services.audio_stems import _read_pcm16
from src.services.audio_stems_4stem import (
    Stem4Result,
    is_separator_available,
    lock_stem_pair,
    phase_lock_4stems,
    separate_4stems,
    synthesize_instrumental,
)
from src.ui.components.audio_transport import AudioTransportController
from src.ui.pages.audio_tools_stems import (
    STEM_ALL_MODES,
    _stem_dict,
    _update_stem_buttons,
    handle_4stems_ready,
    reset_stem_controls,
)
from src.ui.workers.stem_worker import Stem4SeparationWorker, Stem4Signals


def _make_test_wav(path: Path, seconds: float = 1.0, sr: int = 8000) -> Path:
    """Create a lightweight deterministic test WAV."""
    samples = array("h")
    total = int(seconds * sr)
    for i in range(total):
        val = math.sin(2.0 * math.pi * 440.0 * (i / sr)) * 0.7
        samples.append(int(val * 32767))
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(samples.tobytes())
    return path


def test_stem4_result_dataclass():
    res = Stem4Result(Path("v.wav"), Path("d.wav"), Path("b.wav"), Path("o.wav"), "dsp_4stem")
    assert res.vocals_path == Path("v.wav")
    assert res.drums_path == Path("d.wav")
    assert res.bass_path == Path("b.wav")
    assert res.other_path == Path("o.wav")
    assert res.mode_used == "dsp_4stem"
    with pytest.raises(Exception):
        res.mode_used = "other"  # frozen


def test_is_separator_available():
    # Should return bool without raising
    avail = is_separator_available()
    assert isinstance(avail, bool)


def test_lock_stem_pair():
    master = np.array([1000, -2000, 3000, -4000], dtype=np.int32)
    est = np.array([800, -1800, 2500, -3800], dtype=np.int32)
    locked, rem = lock_stem_pair(master, est)
    assert locked.dtype == np.int16
    assert rem.dtype == np.int16
    # Exact equality: locked + rem == master
    np.testing.assert_array_equal(locked.astype(np.int32) + rem.astype(np.int32), master)


def test_phase_lock_4stems_bit_perfect(tmp_path: Path):
    sr = 8000
    master_wav = tmp_path / "master.wav"
    _make_test_wav(master_wav, seconds=0.2, sr=sr)
    m_pcm, _, _ = _read_pcm16(master_wav)

    # Create dummy raw stems
    raw_stems = []
    for i, factor in enumerate((0.3, 0.25, 0.2, 0.15)):
        p = tmp_path / f"raw_{i}.wav"
        with wave.open(str(p), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sr)
            wf.writeframes((m_pcm.astype(np.float32) * factor).astype(np.int16).tobytes())
        raw_stems.append(p)

    out_stems = [tmp_path / f"out_{i}.wav" for i in range(4)]
    phase_lock_4stems(master_wav, raw_stems, out_stems)

    # Read back locked stems
    locked_pcms = [_read_pcm16(p)[0].astype(np.int32) for p in out_stems]
    summed = sum(locked_pcms)

    # Bit-perfect assertion: sum of all 4 stems == master
    np.testing.assert_array_equal(summed, m_pcm.astype(np.int32))

    # Test cancellation check
    with pytest.raises(RuntimeError, match="Stem separation cancelled"):
        phase_lock_4stems(master_wav, raw_stems, out_stems, cancel_check=lambda: True)


def test_synthesize_instrumental(tmp_path: Path):
    sr = 8000
    master_wav = _make_test_wav(tmp_path / "master.wav", seconds=0.2, sr=sr)
    voc_wav = _make_test_wav(tmp_path / "voc.wav", seconds=0.2, sr=sr)

    inst_wav = synthesize_instrumental(master_wav, voc_wav)
    assert inst_wav is not None and inst_wav.is_file()

    # None on non-existent files
    assert synthesize_instrumental(tmp_path / "nonexistent.wav", voc_wav) is None
    assert synthesize_instrumental(master_wav, tmp_path / "nonexistent.wav") is None


def test_separate_4stems_dsp_offline(tmp_path: Path):
    src = _make_test_wav(tmp_path / "track.wav", seconds=0.3, sr=8000)
    out_dir = tmp_path / "output_stems"

    res = separate_4stems(src, output_dir=out_dir, mode="dsp_4stem")

    assert res.mode_used == "dsp_4stem"
    for path in (res.vocals_path, res.drums_path, res.bass_path, res.other_path):
        assert path.is_file()
        assert path.stat().st_size > 44

    # Verify bit-perfect sum: Vocals + Drums + Bass + Other == Master
    m_pcm, _, _ = _read_pcm16(src)
    v_pcm = _read_pcm16(res.vocals_path)[0].astype(np.int32)
    d_pcm = _read_pcm16(res.drums_path)[0].astype(np.int32)
    b_pcm = _read_pcm16(res.bass_path)[0].astype(np.int32)
    o_pcm = _read_pcm16(res.other_path)[0].astype(np.int32)

    np.testing.assert_array_equal(v_pcm + d_pcm + b_pcm + o_pcm, m_pcm.astype(np.int32))


def test_separate_4stems_errors_and_cancellation(tmp_path: Path):
    # Non-existent source
    with pytest.raises(FileNotFoundError):
        separate_4stems(tmp_path / "does_not_exist.wav")

    # Cancellation requested upfront
    src = _make_test_wav(tmp_path / "src.wav", seconds=0.1, sr=8000)
    with pytest.raises(RuntimeError, match="cancelled"):
        separate_4stems(src, cancel_check=lambda: True)


def test_stem4_signals_and_worker(tmp_path: Path):
    src = _make_test_wav(tmp_path / "song.wav", seconds=0.2, sr=8000)
    signals = Stem4Signals()

    results = []
    errors = []
    signals.separated.connect(lambda v, d, b, o, m: results.append((v, d, b, o, m)))
    signals.error.connect(lambda err: errors.append(err))

    worker = Stem4SeparationWorker(src, tmp_path / "stems_out", "dsp_4stem", signals)
    assert not worker.is_cancelled()
    worker.run()

    assert len(results) == 1
    v, d, b, o, m = results[0]
    assert Path(v).is_file()
    assert Path(d).is_file()
    assert Path(b).is_file()
    assert Path(o).is_file()
    assert m == "dsp_4stem"
    assert len(errors) == 0

    # Worker cancellation test
    cancelled_worker = Stem4SeparationWorker(src, tmp_path / "stems_out", "dsp_4stem", signals)
    cancelled_worker.cancel()
    assert cancelled_worker.is_cancelled()
    cancelled_worker.run()
    assert len(results) == 1  # No additional signal emitted

    # Worker error emission test
    err_signals = Stem4Signals()
    err_list = []
    err_signals.error.connect(lambda err: err_list.append(err))
    failing_worker = Stem4SeparationWorker(tmp_path / "missing.wav", None, "dsp_4stem", err_signals)
    failing_worker.run()
    assert len(err_list) == 1
    assert "4-stem separation failed" in err_list[0]


def test_audio_transport_stem_audition(tmp_path: Path):
    transport = AudioTransportController()
    wav_a = _make_test_wav(tmp_path / "master.wav", seconds=0.2, sr=8000)
    wav_b = _make_test_wav(tmp_path / "vocals.wav", seconds=0.2, sr=8000)

    transport.setSlotA(wav_a)
    assert transport.activeSlot() == "A"
    assert transport.activeStem() == ""
    assert transport.auditionLabel() == ""

    # Set stem preview
    audition_emissions = []
    transport.auditionChanged.connect(lambda s: audition_emissions.append(s))
    transport.setStemPreview(wav_b, stem_name="Vocals")

    assert transport.activeStem() == "Vocals"
    assert "Vocals" in transport.auditionLabel()
    assert "Vocals" in audition_emissions

    # Clear Slot B
    transport.setSlotB(None)
    assert transport.activeStem() == ""
    assert transport.auditionLabel() == ""


def test_audio_tools_stems_rack_helpers(tmp_path: Path):
    # Check mode tuple
    assert any(m[1] == "htdemucs" for m in STEM_ALL_MODES)
    assert any(m[1] == "dsp_4stem" for m in STEM_ALL_MODES)

    # Test dummy page for UI state updates
    class DummyBtn:
        def __init__(self):
            self.enabled = False

        def setEnabled(self, val: bool):
            self.enabled = val

    class DummyPage:
        def __init__(self):
            self.loadVocalsBtn = DummyBtn()
            self.loadInstBtn = DummyBtn()
            self.previewVocalsBtn = DummyBtn()
            self.previewInstBtn = DummyBtn()
            self.loadDrumsBtn = DummyBtn()
            self.loadBassBtn = DummyBtn()
            self.loadOtherBtn = DummyBtn()
            self.previewDrumsBtn = DummyBtn()
            self.previewBassBtn = DummyBtn()
            self.previewOtherBtn = DummyBtn()
            self.separateStemsBtn = DummyBtn()
            self.openFolderBtn = MagicMock()
            self.statusLabel = MagicMock()
            self.fileExported = MagicMock()
            self._hist = MagicMock()
            self._source = tmp_path / "song.wav"
            self._busy = True

    page = DummyPage()
    _update_stem_buttons(page, has_voc_inst=True, has_all_4=False)
    assert page.loadVocalsBtn.enabled is True
    assert page.loadDrumsBtn.enabled is False

    _update_stem_buttons(page, has_voc_inst=True, has_all_4=True)
    assert page.loadDrumsBtn.enabled is True
    assert page.loadBassBtn.enabled is True

    reset_stem_controls(page)
    assert page.loadVocalsBtn.enabled is False
    assert page.loadDrumsBtn.enabled is False

    # Test handle_4stems_ready
    _make_test_wav(page._source, seconds=0.1, sr=8000)
    v_wav = _make_test_wav(tmp_path / "song_[Vocals].wav", seconds=0.1, sr=8000)
    d_wav = _make_test_wav(tmp_path / "song_[Drums].wav", seconds=0.1, sr=8000)
    b_wav = _make_test_wav(tmp_path / "song_[Bass].wav", seconds=0.1, sr=8000)
    o_wav = _make_test_wav(tmp_path / "song_[Other].wav", seconds=0.1, sr=8000)

    handle_4stems_ready(page, str(v_wav), str(d_wav), str(b_wav), str(o_wav), "dsp_4stem")
    assert page._busy is False
    assert page.separateStemsBtn.enabled is True
    assert page._vocalsStem == v_wav
    assert page._drumsStem == d_wav
    assert page._bassStem == b_wav
    assert page._otherStem == o_wav
    assert page.openFolderBtn.show.called
    assert page.statusLabel.setText.called

    stems = _stem_dict(page)
    assert stems["vocals"][0] == v_wav
    assert stems["drums"][0] == d_wav
    assert stems["bass"][0] == b_wav
    assert stems["other"][0] == o_wav
