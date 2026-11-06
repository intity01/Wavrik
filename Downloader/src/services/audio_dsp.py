"""DSP routines for multi-band spectral flux BPM estimation and peak envelope downsampling."""

from __future__ import annotations

import math
from typing import Sequence

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view

_FLUX_FREQS = (75.0, 130.0, 220.0, 380.0, 660.0, 1150.0, 2000.0, 3400.0)


def estimate_bpm(samples: Sequence[float] | np.ndarray, sr: int) -> float:
    win, hop = 256, 128
    fps = sr / float(hop)
    onset = _spectral_flux_onset(samples, sr, win, hop)
    n_frames = len(onset)
    if n_frames < 80:
        return 120.0
    win_len = min(n_frames, int(round(12.0 * fps)))
    win_hop = max(1, int(round(4.0 * fps)))
    windows = [onset[s : s + win_len] for s in range(0, max(1, n_frames - win_len + 1), win_hop)]
    scores: dict[int, float] = {b: 0.0 for b in range(66, 180)}
    for w in windows:
        _accumulate_window_bpm(w, fps, scores)
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    best_bpm, top_sc = ranked[0]
    if top_sc <= 1e-6:
        return 120.0
    half_b = int(round(best_bpm / 2.0))
    if 72 <= half_b <= 95 and scores.get(half_b, 0.0) >= top_sc * 0.88:
        return float(half_b)
    t_cands = [b for b in (int(best_bpm * 0.75), int(best_bpm * 0.75) + 1) if 75 <= b <= 92]
    if t_cands:
        sub_b = max(t_cands, key=lambda b: scores.get(b, 0.0))
        if scores.get(sub_b, 0.0) >= top_sc * 0.91:
            best_bpm = sub_b
    return _parabolic_bpm_refine(best_bpm, scores)


def _parabolic_bpm_refine(bpm: int, scores: dict[int, float]) -> float:
    ym1, y0, yp1 = scores.get(bpm - 1, 0.0), scores.get(bpm, 0.0), scores.get(bpm + 1, 0.0)
    den = ym1 - 2.0 * y0 + yp1
    delta = max(-0.4, min(0.4, 0.5 * (ym1 - yp1) / den)) if abs(den) > 1e-9 and ym1 > 0 and yp1 > 0 else 0.0
    return round(float(bpm) + delta, 1)


def _spectral_flux_onset(samples: Sequence[float] | np.ndarray, sr: int, win: int, hop: int) -> np.ndarray:
    arr = np.asarray(samples, dtype=np.float32)
    n_frames = (len(arr) - win) // hop
    if n_frames <= 0:
        return np.array([], dtype=np.float32)
    frames = sliding_window_view(arr, window_shape=win)[::hop][:n_frames]
    omegas = 2.0 * np.pi * np.array(_FLUX_FREQS, dtype=np.float32) / sr
    n = np.arange(win, dtype=np.float32)
    basis = np.exp(-1j * (n[:, None] * omegas[None, :])).astype(np.complex64)
    x_spec = frames @ basis
    mag = np.abs(x_spec) * (1.0 / math.sqrt(win))
    lp = np.log1p(100.0 * mag)
    diff = np.diff(lp, axis=0, prepend=0.0)
    flux = np.sum(np.maximum(0.0, diff), axis=1)
    return _sharpen_onset(flux, max(3, int(round(0.15 * sr / hop))))


def _sharpen_onset(flux: np.ndarray, hw: int) -> np.ndarray:
    n = len(flux)
    if n == 0:
        return np.array([], dtype=np.float32)
    ps = np.pad(np.cumsum(flux, dtype=np.float64), (1, 0))
    idx = np.arange(n)
    hi = np.minimum(n, idx + hw + 1)
    lo = np.maximum(0, idx - hw)
    avg = (ps[hi] - ps[lo]) / np.maximum(1, hi - lo)
    return np.maximum(0.0, flux - avg).astype(np.float32)


def _accumulate_window_bpm(w: Sequence[float] | np.ndarray, fps: float, scores: dict[int, float]) -> None:
    arr = np.asarray(w, dtype=np.float64)
    wn = len(arr)
    norm = math.sqrt(float(np.sum(arr * arr)) / max(1, wn))
    if norm < 1e-4:
        return
    wnorm = arr / norm
    max_lag = min(wn - 2, int(fps * 60.0 * 4.0 / 65.0) + 4)
    corr = np.correlate(wnorm, wnorm, mode="full")[wn - 1 : wn + max_lag]
    lags = np.arange(max_lag + 1)
    acf = corr / (wn - lags)
    bpms = np.arange(66, 180, dtype=np.float64)
    base_lags = fps * 60.0 / bpms
    sc = (
        1.0 * _vec_interp(acf, base_lags, max_lag)
        + 0.55 * _vec_interp(acf, base_lags * 2.0, max_lag)
        + 0.35 * _vec_interp(acf, base_lags * 4.0, max_lag)
        + 0.20 * _vec_interp(acf, base_lags * 3.0, max_lag)
    )
    priors = np.exp(-0.5 * ((np.log2(bpms / 102.0)) / 0.50) ** 2)
    weighted = sc * (0.80 + 0.20 * priors)
    for idx_b, bpm in enumerate(range(66, 180)):
        scores[bpm] += float(weighted[idx_b])


def _vec_interp(acf: np.ndarray, lags: np.ndarray, max_lag: int) -> np.ndarray:
    idx = lags.astype(np.int32)
    valid = (idx >= 15) & (idx < max_lag)
    idx_c = np.clip(idx, 0, max_lag - 1)
    frac = lags - idx
    val = acf[idx_c] * (1.0 - frac) + acf[idx_c + 1] * frac
    return np.where(valid, val, 0.0)


def _interp(acf: list[float] | np.ndarray, lag_f: float, max_lag: int) -> float:
    idx = int(lag_f)
    if idx < 15 or idx >= max_lag:
        return 0.0
    frac = lag_f - idx
    return float(acf[idx] * (1.0 - frac) + acf[idx + 1] * frac)


def downsample_peaks(samples: Sequence[float] | np.ndarray, count: int = 80) -> list[float]:
    arr = np.abs(np.asarray(samples, dtype=np.float32))
    n = len(arr)
    if n == 0:
        return []
    step = max(1, n // count)
    raw = [float(np.max(arr[i : i + step])) for i in range(0, min(n, count * step), step)]
    top = max(raw, default=0.0)
    if top <= 1e-6:
        return [0.05] * len(raw)
    return [round(max(0.05, min(1.0, (p / top) ** 0.75)), 3) for p in raw]
