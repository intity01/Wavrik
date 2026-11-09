"""Pure NumPy STFT power spectrogram computation and column downsampling."""

from __future__ import annotations

from typing import Sequence

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view


def compute_spectrogram(
    samples: np.ndarray | Sequence[float],
    sr: int = 16000,
    n_fft: int = 512,
    hop: int = 256,
    n_bands: int = 40,
) -> np.ndarray:
    """Compute normalized STFT power spectrogram binned into frequency bands."""
    arr = np.asarray(samples, dtype=np.float32)
    if arr.ndim > 1:
        arr = np.mean(arr, axis=1 if arr.shape[0] > arr.shape[1] else 0)
    if len(arr) < n_fft or n_bands <= 0 or hop <= 0:
        return np.zeros((0, max(0, n_bands)), dtype=np.float32)
    num_frames = (len(arr) - n_fft) // hop + 1
    if num_frames <= 0:
        return np.zeros((0, n_bands), dtype=np.float32)

    frames = sliding_window_view(arr, window_shape=n_fft)[::hop][:num_frames]
    window = np.hanning(n_fft).astype(np.float32)
    spec = np.fft.rfft(frames * window, n=n_fft)
    power = np.abs(spec) ** 2
    log_power = np.log1p(power * 10.0)
    bands = _aggregate_bands(log_power, n_bands)
    return _normalize_spectrogram(bands)


def downsample_spectrogram_columns(spec: np.ndarray, target_cols: int) -> np.ndarray:
    """Downsample time frames into target_cols columns for fast UI rendering."""
    if spec.size == 0 or target_cols <= 0:
        n_bands = spec.shape[1] if spec.ndim == 2 else 0
        return np.zeros((max(0, target_cols), n_bands), dtype=np.float32)
    num_frames, n_bands = spec.shape
    if num_frames == target_cols:
        return spec.astype(np.float32)
    edges = np.linspace(0, num_frames, target_cols + 1, dtype=int)
    out = np.zeros((target_cols, n_bands), dtype=np.float32)
    for i in range(target_cols):
        lo = min(edges[i], num_frames - 1)
        hi = min(num_frames, max(lo + 1, edges[i + 1]))
        out[i] = np.max(spec[lo:hi], axis=0)
    return out


def _aggregate_bands(log_power: np.ndarray, n_bands: int) -> np.ndarray:
    num_frames, num_bins = log_power.shape
    if num_frames == 0 or n_bands <= 0:
        return np.zeros((num_frames, max(0, n_bands)), dtype=np.float32)
    edges = np.linspace(0, num_bins, n_bands + 1, dtype=int)
    bands = np.zeros((num_frames, n_bands), dtype=np.float32)
    for i in range(n_bands):
        lo = min(edges[i], num_bins - 1)
        hi = min(num_bins, max(lo + 1, edges[i + 1]))
        bands[:, i] = np.mean(log_power[:, lo:hi], axis=1)
    return bands


def _normalize_spectrogram(mat: np.ndarray) -> np.ndarray:
    if mat.size == 0:
        return mat.astype(np.float32)
    p_min = float(np.min(mat))
    p_max = float(np.max(mat))
    if p_max - p_min < 1e-7:
        return np.zeros_like(mat, dtype=np.float32)
    norm = (mat - p_min) / (p_max - p_min)
    return np.clip(norm, 0.0, 1.0).astype(np.float32)
