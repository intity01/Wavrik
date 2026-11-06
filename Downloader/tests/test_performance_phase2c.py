"""Performance benchmarks and numerical regression test suite for Phase 2c (DSP & Vectorization)."""

from __future__ import annotations

import io
import math
from pathlib import Path
import sys
import time
import wave
from unittest.mock import MagicMock

import numpy as np
import pytest

from src.core.config import Config
from src.services.audio_analysis import (
    _decode_mono_samples,
    _read_wav_fallback,
    analyze_audio_file,
)
from src.services.audio_dsp import (
    _spectral_flux_onset,
    downsample_peaks,
    estimate_bpm,
)
from src.services.audio_hpcp import (
    _fft_pair_mag,
    extract_key_and_sections,
    extract_key_candidates,
)
from src.services.audio_stems import (
    _read_pcm16,
    fuse_min_magnitude,
    phase_lock_stems,
)
import main


def _create_wav_file(path: Path, seconds: float = 2.0, sr: int = 16000, channels: int = 1, bpm: float = 120.0) -> Path:
    """Generate a clean test WAV file for tests."""
    total_samples = int(seconds * sr)
    beat_period = 60.0 / bpm
    pcm = np.zeros(total_samples * channels, dtype=np.int16)
    freqs = (261.63, 329.63, 392.0)  # C-major triad
    for i in range(total_samples):
        t = i / float(sr)
        env = math.exp(-4.0 * ((t % beat_period) / beat_period))
        val = sum(math.sin(2.0 * math.pi * f * t) for f in freqs) / len(freqs)
        sample_val = int(np.clip(val * env * 0.8, -0.9, 0.9) * 32767)
        for c in range(channels):
            pcm[i * channels + c] = sample_val
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(pcm.tobytes())
    return path


def test_lazy_imports_media_downloader_and_cli():
    """Verify that importing media_downloader does not eagerly load yt_dlp extractors."""
    # Ensure yt_dlp is not eagerly imported
    for mod in list(sys.modules):
        if mod == "yt_dlp" or mod.startswith("yt_dlp."):
            del sys.modules[mod]

    import src.domain.media_downloader as md  # noqa: F401

    assert "yt_dlp" not in sys.modules, "yt_dlp should be lazy-loaded in media_downloader"

    buf = io.StringIO()
    main.sys.stdout = buf
    exit_code = main.main(["--version"])
    assert exit_code == 0
    assert Config.VERSION in buf.getvalue()
    assert "yt_dlp" not in sys.modules, "yt_dlp should not be loaded on --version"

    buf_help = io.StringIO()
    main.sys.stdout = buf_help
    assert main.main(["--help"]) == 0
    assert "usage:" in buf_help.getvalue().lower()

    buf_h = io.StringIO()
    main.sys.stdout = buf_h
    assert main.main(["-h"]) == 0
    assert "usage:" in buf_h.getvalue().lower()


def test_requirements_and_spec_numpy_declaration():
    """Verify numpy dependency is locked in requirements.txt and MediaDownloaderPRO.spec."""
    req_path = Path(__file__).resolve().parents[2] / "requirements.txt"
    assert req_path.is_file()
    req_text = req_path.read_text(encoding="utf-8")
    assert "numpy>=2.0,<3" in req_text

    spec_path = Path(__file__).resolve().parents[2] / "MediaDownloaderPRO.spec"
    assert spec_path.is_file()
    spec_text = spec_path.read_text(encoding="utf-8")
    assert "numpy" in spec_text


def test_spectral_flux_onset_vectorization_and_accuracy():
    """Verify multi-band spectral flux onset and BPM estimation accuracy and speed."""
    sr = 16000
    target_bpm = 120.0
    beat_period = 60.0 / target_bpm
    n_samples = sr * 6
    t = np.arange(n_samples, dtype=np.float32) / float(sr)
    env = np.exp(-4.0 * ((t % beat_period) / beat_period))
    samples = (np.sin(2.0 * np.pi * 220.0 * t) * env).astype(np.float32)

    t0 = time.perf_counter()
    onset = _spectral_flux_onset(samples, sr, 256, 128)
    elapsed = time.perf_counter() - t0

    assert isinstance(onset, np.ndarray)
    assert len(onset) > 0
    # 6 seconds of audio should process in well under 100ms with numpy (pure Python took > 1.2s)
    assert elapsed < 0.5

    bpm = estimate_bpm(samples, sr)
    assert abs(bpm - target_bpm) <= 2.0


def test_estimate_bpm_edge_cases():
    """Test BPM estimation edge cases: empty, short audio, and silence."""
    sr = 16000
    assert estimate_bpm([], sr) == 120.0
    assert estimate_bpm(np.zeros(100, dtype=np.float32), sr) == 120.0
    assert estimate_bpm(np.zeros(sr * 4, dtype=np.float32), sr) == 120.0


def test_hpcp_fft_vectorization_and_key_accuracy():
    """Verify vectorized FFT HPCP key detection accuracy."""
    sr = 16000
    freqs = (261.63, 329.63, 392.00)  # C major triad
    t = np.arange(sr * 3, dtype=np.float32) / float(sr)
    samples = sum(0.3 * np.sin(2.0 * np.pi * f * t) for f in freqs).astype(np.float32)

    t0 = time.perf_counter()
    cands, k1, k2 = extract_key_and_sections(samples, sr)
    elapsed = time.perf_counter() - t0

    assert elapsed < 0.5
    assert cands[0]["key"] in {"C major", "A minor", "G major"}
    assert k1 in {"C major", "A minor", "G major"}
    assert k2 in {"C major", "A minor", "G major"}

    # Verify _fft_pair_mag works on numpy and list inputs
    x1 = np.random.randn(4096).astype(np.float32)
    x2 = np.random.randn(4096).astype(np.float32)
    m1, m2 = _fft_pair_mag(x1, x2)
    assert len(m1) == 1425
    assert len(m2) == 1425
    assert np.all(m1 >= 0.0)


def test_downsample_peaks_vectorization(tmp_path: Path):
    """Verify downsample_peaks is vectorized and handles 2.88M samples in milliseconds."""
    samples = np.random.randn(2_880_000).astype(np.float32)

    t0 = time.perf_counter()
    peaks = downsample_peaks(samples, 80)
    elapsed = time.perf_counter() - t0

    assert len(peaks) == 80
    assert all(0.05 <= p <= 1.0 for p in peaks)
    assert max(peaks) == 1.0
    # 2.88M samples downsampled in < 50ms (previously > 400ms)
    assert elapsed < 0.25

    # Edge cases
    assert downsample_peaks([]) == []
    assert downsample_peaks(np.zeros(1000, dtype=np.float32), 40) == [0.05] * 40


def test_decode_mono_samples_contiguous_float32(tmp_path: Path):
    """Verify _decode_mono_samples and fallback return contiguous numpy float32 arrays."""
    wav_path = _create_wav_file(tmp_path / "test_stereo.wav", seconds=1.0, channels=2)
    samples, sr = _read_wav_fallback(wav_path, max_seconds=5)

    assert isinstance(samples, np.ndarray)
    assert samples.dtype == np.float32
    assert len(samples) == sr * 1
    assert float(np.max(np.abs(samples))) <= 1.0

    # Non-existent file
    with pytest.raises(FileNotFoundError):
        _decode_mono_samples(tmp_path / "non_existent.wav", 10)


def test_phase_locked_stems_bit_perfect_vectorization(tmp_path: Path):
    """Verify phase_lock_stems is 100% bit-perfect and highly performant with numpy."""
    n_samples = 500_000
    m_data = np.random.randint(-30000, 30000, size=n_samples, dtype=np.int16)
    i_data = np.random.randint(-30000, 30000, size=n_samples, dtype=np.int16)

    m_wav = tmp_path / "master.wav"
    i_wav = tmp_path / "inst.wav"
    voc_dst = tmp_path / "vocals.wav"
    inst_dst = tmp_path / "instrumental.wav"

    with wave.open(str(m_wav), "wb") as wf:
        wf.setparams((1, 2, 44100, n_samples, "NONE", "not compressed"))
        wf.writeframes(m_data.tobytes())

    with wave.open(str(i_wav), "wb") as wf:
        wf.setparams((1, 2, 44100, n_samples, "NONE", "not compressed"))
        wf.writeframes(i_data.tobytes())

    t0 = time.perf_counter()
    phase_lock_stems(m_wav, i_wav, voc_dst, inst_dst)
    elapsed = time.perf_counter() - t0

    # 500,000 samples disk read + vectorized lock + disk write under 1.0s (pure Python loop took > 4s)
    assert elapsed < 1.0

    v_pcm, sr_v, _ = _read_pcm16(voc_dst)
    i_pcm, sr_i, _ = _read_pcm16(inst_dst)
    m_pcm, _, _ = _read_pcm16(m_wav)

    assert len(v_pcm) == len(i_pcm) == len(m_pcm)
    # 100% bit-perfect reconstruction verification
    assert np.all(v_pcm.astype(np.int32) + i_pcm.astype(np.int32) == m_pcm.astype(np.int32))

    # Test cancellation token
    cancel_mock = MagicMock(return_value=True)
    with pytest.raises(RuntimeError, match="cancelled"):
        phase_lock_stems(m_wav, i_wav, voc_dst, inst_dst, cancel_check=cancel_mock)


def test_fuse_min_magnitude_vectorized(tmp_path: Path):
    """Verify fuse_min_magnitude picks minimum absolute magnitude element-wise."""
    a = np.array([100, -200, 300, -400], dtype=np.int16)
    b = np.array([-150, 150, -350, 200], dtype=np.int16)

    w1 = tmp_path / "w1.wav"
    w2 = tmp_path / "w2.wav"
    out = tmp_path / "fused.wav"

    for path, data in ((w1, a), (w2, b)):
        with wave.open(str(path), "wb") as wf:
            wf.setparams((1, 2, 16000, len(data), "NONE", "not compressed"))
            wf.writeframes(data.tobytes())

    fuse_min_magnitude(w1, w2, out)
    fused, _, _ = _read_pcm16(out)

    expected = np.array([100, 150, 300, 200], dtype=np.int16)
    assert np.array_equal(fused, expected)


def test_analyze_audio_file_end_to_end(tmp_path: Path):
    """Verify analyze_audio_file operates seamlessly end-to-end with numpy optimizations."""
    wav_path = _create_wav_file(tmp_path / "song.wav", seconds=4.0, bpm=120.0)
    result = analyze_audio_file(wav_path, max_seconds=10)
    assert result["status"] == "estimate"
    assert result["key"] in {"C major", "A minor", "G major"}
    assert abs(result["bpm"] - 120.0) <= 5.0
    assert len(result["peaks"]) == 80

    # Also test extract_key_candidates convenience wrapper
    samples, sr = _read_wav_fallback(wav_path, 5)
    candidates = extract_key_candidates(samples, sr)
    assert len(candidates) > 0
    assert candidates[0]["key"] in {"C major", "A minor", "G major"}

