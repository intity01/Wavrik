"""DSP routines for multi-band spectral flux BPM estimation and peak envelope downsampling."""

from __future__ import annotations

import math

_FLUX_FREQS = (75.0, 130.0, 220.0, 380.0, 660.0, 1150.0, 2000.0, 3400.0)


def estimate_bpm(samples: list[float], sr: int) -> float:
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


def _spectral_flux_onset(samples: list[float], sr: int, win: int, hop: int) -> list[float]:
    n_frames = (len(samples) - win) // hop
    if n_frames <= 0:
        return []
    coeffs = [2.0 * math.cos(2.0 * math.pi * f / sr) for f in _FLUX_FREQS]
    prev_lp = [0.0] * len(coeffs)
    flux = [0.0] * n_frames
    for f_idx in range(n_frames):
        frame = samples[f_idx * hop : f_idx * hop + win]
        total = 0.0
        for b_idx, c in enumerate(coeffs):
            s1, s2 = 0.0, 0.0
            for x in frame:
                s0 = x + c * s1 - s2
                s2, s1 = s1, s0
            lp = math.log1p(100.0 * math.sqrt(max(0.0, s1 * s1 + s2 * s2 - c * s1 * s2) / win))
            if lp > prev_lp[b_idx]:
                total += lp - prev_lp[b_idx]
            prev_lp[b_idx] = lp
        flux[f_idx] = total
    return _sharpen_onset(flux, max(3, int(round(0.15 * sr / hop))))


def _sharpen_onset(flux: list[float], hw: int) -> list[float]:
    n = len(flux)
    ps = [0.0] * (n + 1)
    for i in range(n):
        ps[i + 1] = ps[i] + flux[i]
    return [
        max(0.0, flux[i] - (ps[min(n, i + hw + 1)] - ps[max(0, i - hw)]) / max(1, min(n, i + hw + 1) - max(0, i - hw)))
        for i in range(n)
    ]


def _accumulate_window_bpm(w: list[float], fps: float, scores: dict[int, float]) -> None:
    wn = len(w)
    norm = math.sqrt(sum(x * x for x in w) / max(1, wn))
    if norm < 1e-4:
        return
    wnorm = [x / norm for x in w]
    max_lag = min(wn - 2, int(fps * 60.0 * 4.0 / 65.0) + 4)
    needed: set[int] = set()
    for bpm in range(66, 180):
        base = fps * 60.0 / bpm
        for mult in (1.0, 2.0, 3.0, 4.0):
            idx = int(base * mult)
            if 15 <= idx < max_lag:
                needed.add(idx)
                needed.add(idx + 1)
    acf = [0.0] * (max_lag + 1)
    for lag in needed:
        acf[lag] = sum(wnorm[i] * wnorm[i - lag] for i in range(lag, wn)) / (wn - lag)
    for bpm in range(66, 180):
        lag = fps * 60.0 / bpm
        sc = (
            1.0 * _interp(acf, lag, max_lag)
            + 0.55 * _interp(acf, lag * 2.0, max_lag)
            + 0.35 * _interp(acf, lag * 4.0, max_lag)
            + 0.20 * _interp(acf, lag * 3.0, max_lag)
        )
        prior = math.exp(-0.5 * ((math.log2(bpm / 102.0)) / 0.50) ** 2)
        scores[bpm] += sc * (0.80 + 0.20 * prior)


def _interp(acf: list[float], lag_f: float, max_lag: int) -> float:
    idx = int(lag_f)
    if idx < 15 or idx >= max_lag:
        return 0.0
    frac = lag_f - idx
    return acf[idx] * (1.0 - frac) + acf[idx + 1] * frac


def downsample_peaks(samples: list[float], count: int = 80) -> list[float]:
    if not samples:
        return []
    step = max(1, len(samples) // count)
    raw = [max((abs(s) for s in samples[i : i + step]), default=0.0) for i in range(0, len(samples), step)][:count]
    top = max(raw, default=0.0)
    if top <= 1e-6:
        return [0.05] * len(raw)
    return [round(max(0.05, min(1.0, (p / top) ** 0.75)), 3) for p in raw]
