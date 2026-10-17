"""CPU key and BPM estimation with Hann-windowed harmonic chroma and comb tempo."""

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
    "major": (1.20, 0.00, 0.45, 0.05, 0.65, 0.45, 0.00, 0.80, 0.05, 0.40, 0.10, 0.35),
    "minor": (1.15, 0.00, 0.40, 0.65, 0.05, 0.45, 0.00, 0.80, 0.45, 0.05, 0.35, 0.10),
}
_CAMELOT_MAJOR = {"B": "1B", "F#": "2B", "C#": "3B", "G#": "4B", "D#": "5B", "A#": "6B", "F": "7B", "C": "8B", "G": "9B", "D": "10B", "A": "11B", "E": "12B"}
_CAMELOT_MINOR = {"G#": "1A", "D#": "2A", "A#": "3A", "F": "4A", "C": "5A", "G": "6A", "D": "7A", "A": "8A", "E": "9A", "B": "10A", "F#": "11A", "C#": "12A"}


def camelot_code(key_name: str) -> str:
    parts = key_name.strip().split()
    if len(parts) != 2 or parts[0] not in NOTES:
        return "--"
    return (_CAMELOT_MINOR if parts[1] == "minor" else _CAMELOT_MAJOR).get(parts[0], "--")


def transpose_key(key_name: str, semitones: int) -> str:
    parts = key_name.strip().split()
    if len(parts) != 2 or parts[0] not in NOTES:
        return key_name
    return f"{NOTES[(NOTES.index(parts[0]) + int(semitones)) % 12]} {parts[1]}"


def analyze_audio_file(path: str | Path, max_seconds: int = 135) -> dict:
    samples, sr = _decode_mono_samples(Path(path), max_seconds)
    if len(samples) < sr // 2 or max((abs(x) for x in samples), default=0.0) < 1e-5:
        return {"key": "C major", "camelot": "8B", "bpm": 120.0, "status": "unavailable", "key_candidates": []}
    body = samples[15 * sr :] if len(samples) > 45 * sr else samples
    candidates = _rank_keys(_compute_chroma(body, sr))
    top_key = candidates[0]["key"]
    return {
        "key": top_key,
        "camelot": camelot_code(top_key),
        "bpm": _estimate_bpm(body, sr),
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
        proc = subprocess.run(cmd, capture_output=True, timeout=45, check=False, creationflags=flags)
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
    return [pcm[i] / 32768.0 for i in range(0, len(pcm), max(1, ch))], sr


def _compute_chroma(samples: list[float], sr: int) -> list[float]:
    win = min(4096, len(samples))
    hann = [0.5 - 0.5 * math.cos(2.0 * math.pi * i / max(1, win - 1)) for i in range(win)]
    stride = max(win, len(samples) // 60)
    coeffs = [(m % 12, 2.0 * math.cos(2.0 * math.pi * (440.0 * (2.0 ** ((m - 69) / 12.0))) / sr)) for m in range(53, 89)]
    chroma = [0.0] * 12
    for start in range(0, len(samples) - win + 1, stride):
        f_ch = _frame_pitch_energy([samples[start + i] * hann[i] for i in range(win)], coeffs)
        mean_e = sum(f_ch) / 12.0
        whitened = [max(0.0, v - 0.9 * mean_e) for v in f_ch]
        peak = max(whitened, default=0.0)
        if peak > 1e-6:
            for pc in range(12):
                chroma[pc] += whitened[pc] / peak
    mx = max(chroma, default=1.0) or 1.0
    return [v / mx for v in chroma]


def _frame_pitch_energy(frame: list[float], coeffs: list[tuple[int, float]]) -> list[float]:
    f_ch = [0.0] * 12
    for pc, coeff in coeffs:
        s1, s2 = 0.0, 0.0
        for x in frame:
            s0 = x + coeff * s1 - s2
            s2, s1 = s1, s0
        f_ch[pc] += math.log1p(20.0 * math.sqrt(max(0.0, s1 * s1 + s2 * s2 - coeff * s1 * s2)))
    return f_ch


def _rank_keys(chroma: list[float]) -> list[dict]:
    ranked: list[dict] = []
    for mode, profile in _PROFILES.items():
        for tonic in range(12):
            rot = profile[-tonic:] + profile[:-tonic] if tonic else profile
            ranked.append({"key": f"{NOTES[tonic]} {mode}", "correlation": round(sum(chroma[i] * rot[i] for i in range(12)), 4)})
    ranked.sort(key=lambda item: item["correlation"], reverse=True)
    return ranked


def _estimate_bpm(samples: list[float], sr: int) -> float:
    hop = max(32, sr // 172)
    env = [sum(abs(x) for x in samples[i : i + hop]) for i in range(0, len(samples) - hop, hop)]
    onset = [max(0.0, env[i + 1] - env[i]) for i in range(len(env) - 1)]
    if len(onset) < 80:
        return 120.0
    fps = sr / float(hop)
    best_bpm, best_score = 120.0, -1.0
    for bpm_x2 in range(140, 350):
        bpm = bpm_x2 / 2.0
        prior = math.exp(-0.5 * ((math.log2(bpm / 120.0)) / 0.45) ** 2)
        weighted = _comb_score(onset, fps, bpm) * (0.85 + 0.15 * prior)
        if weighted > best_score:
            best_score, best_bpm = weighted, round(fps * 60.0 / max(1, int(round(fps * 60.0 / bpm))))
    return float(best_bpm)


def _comb_score(onset: list[float], fps: float, bpm: float) -> float:
    total = 0.0
    for mult, weight in ((1, 1.0), (2, 0.5), (4, 0.25)):
        lag = int(round(fps * 60.0 * mult / bpm))
        if 0 < lag < len(onset):
            total += weight * (sum(onset[i] * onset[i - lag] for i in range(lag, len(onset), 2)) / ((len(onset) - lag) // 2 + 1))
    return total
