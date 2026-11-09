"""Pure NumPy audio beat grid computation, phase detection, and adaptive markers."""

from __future__ import annotations

from typing import Sequence

import numpy as np

from src.services.audio_dsp import _spectral_flux_onset


def compute_beat_grid(bpm: float, duration: float, first_beat_sec: float = 0.0) -> dict:
    """Generate 4/4 meter beat, downbeat, and phrase marker timestamps."""
    safe_bpm = max(1.0, float(bpm)) if bpm and bpm > 0 else 120.0
    safe_dur = max(0.0, float(duration))
    beat_interval = 60.0 / safe_bpm
    safe_t0 = max(0.0, float(first_beat_sec))
    if safe_t0 >= beat_interval:
        safe_t0 = safe_t0 % beat_interval
    beats: list[float] = []
    downbeats: list[float] = []
    phrase_markers: list[float] = []
    if safe_dur > 0.0:
        idx = 0
        t = safe_t0
        while t <= safe_dur + 1e-4:
            t_round = round(t, 4)
            beats.append(t_round)
            if idx % 4 == 0:
                downbeats.append(t_round)
            if idx % 16 == 0:
                phrase_markers.append(t_round)
            idx += 1
            t = safe_t0 + idx * beat_interval
    return {
        "bpm": safe_bpm, "duration": safe_dur, "beat_interval": round(beat_interval, 6),
        "first_beat_sec": round(safe_t0, 4), "beats": beats, "downbeats": downbeats,
        "phrase_markers": phrase_markers,
    }


def detect_beat_phase_offset(samples: np.ndarray | Sequence[float], sr: int, bpm: float) -> float:
    """Estimate first beat phase offset t0 in [0.0, beat_interval] via onset comb filter."""
    if bpm <= 0.0 or sr <= 0:
        return 0.0
    beat_interval = 60.0 / float(bpm)
    fps = sr / 128.0
    onset = _spectral_flux_onset(samples, sr, 256, 128)
    if len(onset) == 0:
        return 0.0
    lag = fps * beat_interval
    max_p = max(1, int(round(lag)))
    sub = onset[: min(len(onset), int(round(15.0 * fps)))]
    if len(sub) == 0 or float(np.max(sub)) <= 1e-6:
        return 0.0
    scores = np.zeros(max_p, dtype=np.float32)
    for p in range(max_p):
        pulses = np.arange(p, len(sub), lag).astype(int)
        pulses = pulses[pulses < len(sub)]
        if len(pulses) > 0:
            scores[p] = np.sum(sub[pulses])
    best_p = int(np.argmax(scores))
    t0 = best_p / fps
    if t0 >= beat_interval:
        t0 = 0.0
    return round(float(np.clip(t0, 0.0, beat_interval)), 4)


def get_adaptive_grid_markers(grid: dict, width_px: int, duration: float) -> list[tuple[float, str]]:
    """Return adaptive beat grid markers based on horizontal pixel density."""
    if width_px <= 0 or duration <= 0.0:
        return []
    beat_interval = float(grid.get("beat_interval", 0.0))
    if beat_interval <= 0.0:
        bpm = float(grid.get("bpm", 0.0))
        beat_interval = (60.0 / bpm) if bpm > 0.0 else 0.5
    px_per_beat = (float(width_px) / float(duration)) * beat_interval
    if px_per_beat >= 6.0:
        downbeat_set = {round(t, 4) for t in grid.get("downbeats", [])}
        return [(t, "downbeat" if round(t, 4) in downbeat_set else "beat") for t in grid.get("beats", [])]
    if px_per_beat >= 2.5:
        return [(t, "downbeat") for t in grid.get("downbeats", [])]
    return [(t, "phrase") for t in grid.get("phrase_markers", [])]
