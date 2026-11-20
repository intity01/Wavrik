"""Pure NumPy Voice Activity Detection (VAD) and speech phrase segmenter."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view


@dataclass(frozen=True, slots=True)
class AudioChunk:
    start_sec: float
    end_sec: float
    duration_sec: float
    index: int


def _prepare_mono_vad(samples: Sequence[float] | np.ndarray) -> np.ndarray:
    arr = np.asarray(samples, dtype=np.float32)
    if arr.ndim > 1:
        arr = np.mean(arr, axis=1 if arr.shape[0] > arr.shape[1] else 0)
    peak = float(np.max(np.abs(arr))) if len(arr) > 0 else 0.0
    return (arr / peak) if peak > 1e-6 else arr


def _compute_frame_metrics(frames: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    rms = np.sqrt(np.mean(frames ** 2, axis=1) + 1e-12)
    db = 20.0 * np.log10(rms + 1e-9)
    signs = np.sign(frames)
    zcr = np.mean(signs[:, 1:] != signs[:, :-1], axis=1)
    return db, zcr


def _apply_hangover_filter(raw_active: np.ndarray, attack: int = 2, hangover: int = 30) -> np.ndarray:
    active = np.zeros(len(raw_active), dtype=bool)
    is_on, hang_count, run_count = False, 0, 0
    for i, flag in enumerate(raw_active):
        if flag:
            run_count += 1
            if run_count >= attack:
                is_on, hang_count = True, hangover
        else:
            run_count = 0
            if is_on:
                hang_count -= 1
                if hang_count <= 0:
                    is_on = False
        active[i] = is_on
    return active


def detect_speech_frames(samples: np.ndarray, sr: int = 16000) -> tuple[np.ndarray, np.ndarray]:
    mono = _prepare_mono_vad(samples)
    win, hop = int(0.025 * sr), int(0.010 * sr)
    if len(mono) < win:
        return np.array([], dtype=bool), np.array([], dtype=np.float32)
    n_frames = (len(mono) - win) // hop + 1
    frames = sliding_window_view(mono, window_shape=win)[::hop][:n_frames]
    db, zcr = _compute_frame_metrics(frames)
    p15, p95 = np.percentile(db, 15), np.percentile(db, 95)
    t_energy = float(np.clip(p15 + 0.25 * (p95 - p15), -50.0, -25.0))
    raw_active = (db > t_energy) | ((db > t_energy - 8.0) & (zcr > 0.15))
    return _apply_hangover_filter(raw_active), db


def _split_long_chunk(start: int, end: int, max_frames: int, db: np.ndarray) -> list[tuple[int, int]]:
    if end - start <= max_frames:
        return [(start, end)]
    results: list[tuple[int, int]] = []
    curr = start
    while curr < end:
        if end - curr <= max_frames:
            results.append((curr, end))
            break
        tgt = curr + max_frames
        s_win, e_win = max(curr + 30, tgt - 150), min(end - 30, tgt + 50)
        split_idx = int(s_win + np.argmin(db[s_win:e_win])) if s_win < e_win else tgt
        results.append((curr, split_idx))
        curr = split_idx
    return results


def segment_speech_chunks(
    samples: np.ndarray,
    sr: int = 16000,
    min_speech_sec: float = 0.30,
    max_chunk_sec: float = 15.0,
    pad_sec: float = 0.15,
) -> list[AudioChunk]:
    mask, db = detect_speech_frames(samples, sr)
    if len(mask) == 0 or not np.any(mask):
        return []
    hop_sec = 0.010
    padded = np.concatenate(([False], mask, [False]))
    diffs = np.diff(padded.astype(np.int8))
    starts, ends = np.where(diffs == 1)[0], np.where(diffs == -1)[0]
    min_frames, max_frames = int(min_speech_sec / hop_sec), int(max_chunk_sec / hop_sec)
    total_dur = len(samples) / float(sr)
    chunks: list[AudioChunk] = []
    idx = 0
    for s, e in zip(starts, ends):
        if e - s < min_frames:
            continue
        sub_ranges = _split_long_chunk(s, e, max_frames, db)
        for sub_s, sub_e in sub_ranges:
            st_sec = max(0.0, sub_s * hop_sec - pad_sec)
            en_sec = min(total_dur, sub_e * hop_sec + pad_sec)
            if en_sec - st_sec >= 0.20:
                chunks.append(AudioChunk(round(st_sec, 3), round(en_sec, 3), round(en_sec - st_sec, 3), idx))
                idx += 1
    return chunks
