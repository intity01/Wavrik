"""Pure NumPy Chromaprint-compatible audio fingerprinting service."""

from __future__ import annotations

import base64
from pathlib import Path
import struct
import zlib
from typing import Sequence

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view

_N_FFT = 2048
_HOP = 1024
_NUM_BANDS = 33
_MIN_FREQ = 300.0
_MAX_FREQ = 2000.0


def _prepare_mono(samples: Sequence[float] | np.ndarray, sr: int, max_sec: int = 120) -> np.ndarray:
    arr = np.asarray(samples, dtype=np.float32)
    if arr.ndim > 1:
        axis = 1 if arr.shape[0] > arr.shape[1] else 0
        arr = np.mean(arr, axis=axis)
    max_len = sr * max_sec
    return arr[:max_len] if len(arr) > max_len else arr


def _compute_subbands(frames: np.ndarray, sr: int, n_fft: int) -> np.ndarray:
    win = np.hanning(n_fft).astype(np.float32)
    spec = np.fft.rfft(frames * win, axis=-1)
    power = np.abs(spec) ** 2
    edges = np.geomspace(_MIN_FREQ, _MAX_FREQ, _NUM_BANDS + 1)
    bins = [int(round(e * n_fft / sr)) for e in edges]
    energies = [np.sum(power[:, bins[k] : max(bins[k + 1], bins[k] + 1)], axis=-1) for k in range(_NUM_BANDS)]
    return np.log1p(np.column_stack(energies) * 1000.0)


def generate_chromaprint (samples: Sequence[float] | np.ndarray, sr: int = 16000) -> list[int]:
    mono = _prepare_mono(samples, sr)
    if len(mono) < _N_FFT + _HOP:
        return []
    n_frames = (len(mono) - _N_FFT) // _HOP + 1
    frames = sliding_window_view(mono, window_shape=_N_FFT)[::_HOP][:n_frames]
    log_energy = _compute_subbands(frames, sr, _N_FFT)
    if len(log_energy) < 2:
        return []
    diff_freq = log_energy[:, :-1] - log_energy[:, 1:]
    diff_2d = diff_freq[1:, :] - diff_freq[:-1, :]
    bits = (diff_2d > 0).astype(np.uint32)
    powers = np.uint32(1) << np.arange(32, dtype=np.uint32)
    packed = np.dot(bits, powers)
    return [int(x) for x in packed]


def encode_fingerprint_base64 (subfingerprints: list[int]) -> str:
    if not subfingerprints:
        return ""
    header = struct.pack("<B", 1)
    body = struct.pack(f"<{len(subfingerprints)}I", *subfingerprints)
    compressed = zlib.compress(header + body)
    return base64.urlsafe_b64encode(compressed).decode("ascii")


def decode_fingerprint_base64 (encoded: str) -> list[int]:
    if not encoded:
        return []
    decomp = zlib.decompress(base64.urlsafe_b64decode(encoded))
    count = (len(decomp) - 1) // 4
    return list(struct.unpack(f"<{count}I", decomp[1 : 1 + count * 4]))


def fingerprint_similarity (fp1: list[int], fp2: list[int]) -> float:
    if not fp1 or not fp2:
        return 0.0
    max_shift = min(20, max(len(fp1), len(fp2)) // 4)
    best_sim = 0.0
    for shift in range(-max_shift, max_shift + 1):
        s1 = fp1[max(0, shift) : min(len(fp1), len(fp2) + shift)]
        s2 = fp2[max(0, -shift) : min(len(fp2), len(fp1) - shift)]
        if not s1 or not s2:
            continue
        matches = sum(32 - (a ^ b).bit_count() for a, b in zip(s1, s2))
        sim = matches / (len(s1) * 32)
        if sim > best_sim:
            best_sim = sim
            if best_sim >= 0.9999:
                return 1.0
    return round(float(best_sim), 4)


def fingerprint_audio_file (file_path: str | Path, max_sec: int = 120) -> tuple[int, str]:
    from src.services.audio_analysis import _decode_mono_samples
    samples, sr = _decode_mono_samples(Path(file_path), max_sec)
    if len(samples) == 0:
        return 0, ""
    dur = int(round(len(samples) / float(sr)))
    fp = generate_chromaprint (samples, sr)
    return dur, encode_fingerprint_base64 (fp)
