"""CPU key and BPM estimation with Krumhansl-Schmuckler pitch profiles."""

from __future__ import annotations

from array import array
import math
from pathlib import Path
import subprocess
import sys
import wave

from src.core.runtime import find_ffmpeg

NOTES = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")
ALL_KEYS = tuple([*(f"{n} major" for n in NOTES), *(f"{n} minor" for n in NOTES)])
_PROFILES = {
    "major": (6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88),
    "minor": (6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17),
}
_CAMELOT_MAJOR = {
    "B": "1B", "F#": "2B", "C#": "3B", "G#": "4B", "D#": "5B", "A#": "6B",
    "F": "7B", "C": "8B", "G": "9B", "D": "10B", "A": "11B", "E": "12B",
}
_CAMELOT_MINOR = {
    "G#": "1A", "D#": "2A", "A#": "3A", "F": "4A", "C": "5A", "G": "6A",
    "D": "7A", "A": "8A", "E": "9A", "B": "10A", "F#": "11A", "C#": "12A",
}


def camelot_code(key_name: str) -> str:
    parts = key_name.strip().split()
    if len(parts) != 2 or parts[0] not in NOTES:
        return "--"
    return (_CAMELOT_MINOR if parts[1] == "minor" else _CAMELOT_MAJOR).get(parts[0], "--")


def transpose_key(key_name: str, semitones: int) -> str:
    parts = key_name.strip().split()
    if len(parts) != 2 or parts[0] not in NOTES:
        return key_name
    idx = (NOTES.index(parts[0]) + int(semitones)) % 12
    return f"{NOTES[idx]} {parts[1]}"


def analyze_audio_file(path: str | Path, max_seconds: int = 35) -> dict:
    samples, sr = _decode_mono_samples(Path(path), max_seconds)
    if len(samples) < sr // 2 or max((abs(x) for x in samples), default=0.0) < 1e-5:
        return {"key": "C major", "camelot": "8B", "bpm": 120.0, "status": "unavailable", "key_candidates": []}
    chroma = _compute_chroma(samples, sr)
    candidates = _rank_keys(chroma)
    top_key = candidates[0]["key"]
    bpm = _estimate_bpm(samples, sr)
    return {
        "key": top_key,
        "camelot": camelot_code(top_key),
        "bpm": bpm,
        "status": "estimate",
        "badge": "Experimental / Estimate · ทดลอง / ค่าประมาณ",
        "key_candidates": candidates[:3],
    }


def _decode_mono_samples(path: Path, max_seconds: int) -> tuple[list[float], int]:
    if not path.is_file():
        raise FileNotFoundError(path)
    ffmpeg_dir = find_ffmpeg()
    exe = str(Path(ffmpeg_dir) / ("ffmpeg.exe" if sys.platform == "win32" else "ffmpeg")) if ffmpeg_dir else None
    if exe and Path(exe).is_file():
        cmd = [exe, "-hide_banner", "-loglevel", "error", "-nostdin", "-i", str(path), "-t", str(max_seconds), "-vn", "-ac", "1", "-ar", "11025", "-f", "s16le", "pipe:1"]
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if sys.platform == "win32" else 0
        proc = subprocess.run(cmd, capture_output=True, timeout=30, check=False, creationflags=flags)
        if proc.returncode == 0 and proc.stdout:
            pcm = array("h")
            pcm.frombytes(proc.stdout[: (len(proc.stdout) // 2) * 2])
            return [s / 32768.0 for s in pcm], 11025
    return _read_wav_fallback(path, max_seconds)


def _read_wav_fallback(path: Path, max_seconds: int) -> tuple[list[float], int]:
    with wave.open(str(path), "rb") as wf:
        sr, ch, width = wf.getframerate(), wf.getnchannels(), wf.getsampwidth()
        raw = wf.readframes(min(wf.getnframes(), sr * max_seconds))
    if width != 2 or not raw:
        return [], 11025
    pcm = array("h")
    pcm.frombytes(raw[: (len(raw) // 2) * 2])
    step = max(1, ch)
    return [pcm[i] / 32768.0 for i in range(0, len(pcm), step)], sr


def _compute_chroma(samples: list[float], sr: int) -> list[float]:
    chroma = [0.0] * 12
    win = min(2048, len(samples))
    stride = max(win, len(samples) // 20)
    for midi in range(36, 84):
        freq = 440.0 * (2.0 ** ((midi - 69) / 12.0))
        coeff = 2.0 * math.cos(2.0 * math.pi * freq / sr)
        energy = 0.0
        for start in range(0, len(samples) - win + 1, stride):
            s1, s2 = 0.0, 0.0
            for x in samples[start : start + win]:
                s0 = x + coeff * s1 - s2
                s2, s1 = s1, s0
            energy += s1 * s1 + s2 * s2 - coeff * s1 * s2
        chroma[midi % 12] += max(0.0, energy)
    return chroma


def _rank_keys(chroma: list[float]) -> list[dict]:
    ranked: list[dict] = []
    for mode, profile in _PROFILES.items():
        for tonic in range(12):
            rotated = profile[-tonic:] + profile[:-tonic] if tonic else profile
            score = _pearson(chroma, rotated)
            ranked.append({"key": f"{NOTES[tonic]} {mode}", "correlation": round(score, 4)})
    ranked.sort(key=lambda item: item["correlation"], reverse=True)
    return ranked


def _pearson(xs: list[float], ys: tuple[float, ...]) -> float:
    mx, my = sum(xs) / 12.0, sum(ys) / 12.0
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    den = math.sqrt(sum((x - mx) ** 2 for x in xs) * sum((y - my) ** 2 for y in ys))
    return num / den if den > 1e-12 else 0.0


def _estimate_bpm(samples: list[float], sr: int) -> float:
    hop = max(64, sr // 86)
    env = [sum(abs(x) for x in samples[i : i + hop]) for i in range(0, len(samples) - hop, hop)]
    onset = [max(0.0, env[i + 1] - env[i]) for i in range(len(env) - 1)]
    if len(onset) < 60:
        return 120.0
    fps = sr / float(hop)
    min_lag, max_lag = max(1, int(fps * 60.0 / 175.0)), min(len(onset) // 2, int(fps * 60.0 / 68.0))
    best_lag, best_score = min_lag, -1.0
    for lag in range(min_lag, max(min_lag + 1, max_lag + 1)):
        score = sum(onset[i] * onset[i - lag] for i in range(lag, len(onset)))
        if score > best_score:
            best_lag, best_score = lag, score
    return round(60.0 * fps / best_lag, 1) if best_lag > 0 else 120.0
