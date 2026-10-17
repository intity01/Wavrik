"""CPU key and BPM estimation with harmonic chroma, spectral flux tempo, and enharmonic aliases."""

from __future__ import annotations

from array import array
from pathlib import Path
import subprocess
import sys
import wave

from src.core.runtime import find_ffmpeg
from src.services.audio_dsp import compute_chroma as _compute_chroma, estimate_bpm as _estimate_bpm

NOTES = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")
ALL_KEYS = tuple([*(f"{n} major" for n in NOTES), *(f"{n} minor" for n in NOTES)])
_FLAT_TO_SHARP = {"Db": "C#", "Eb": "D#", "Gb": "F#", "Ab": "G#", "Bb": "A#", "D♭": "C#", "E♭": "D#", "G♭": "F#", "A♭": "G#", "B♭": "A#"}
_SHARP_TO_FLAT = {"C#": "Db", "D#": "Eb", "F#": "Gb", "G#": "Ab", "A#": "Bb"}
_PROFILES = {
    "major": (1.20, 0.00, 0.45, 0.05, 0.65, 0.45, 0.00, 0.80, 0.05, 0.40, 0.10, 0.35),
    "minor": (1.15, 0.00, 0.40, 0.65, 0.05, 0.45, 0.00, 0.80, 0.45, 0.05, 0.35, 0.10),
}
_CAMELOT_MAJOR = {"B": "1B", "F#": "2B", "C#": "3B", "G#": "4B", "D#": "5B", "A#": "6B", "F": "7B", "C": "8B", "G": "9B", "D": "10B", "A": "11B", "E": "12B"}
_CAMELOT_MINOR = {"G#": "1A", "D#": "2A", "A#": "3A", "F": "4A", "C": "5A", "G": "6A", "D": "7A", "A": "8A", "E": "9A", "B": "10A", "F#": "11A", "C#": "12A"}


def _norm_note(note: str) -> str:
    return _FLAT_TO_SHARP.get(note, note)


def enharmonic_key(key_name: str) -> str:
    parts = key_name.strip().split()
    if len(parts) != 2:
        return key_name
    note = _norm_note(parts[0])
    flat = _SHARP_TO_FLAT.get(note)
    return f"{flat} {parts[1]}" if flat else f"{note} {parts[1]}"


def camelot_code(key_name: str) -> str:
    parts = key_name.strip().split()
    if len(parts) != 2:
        return "--"
    note = _norm_note(parts[0])
    if note not in NOTES:
        return "--"
    return (_CAMELOT_MINOR if parts[1] == "minor" else _CAMELOT_MAJOR).get(note, "--")


def transpose_key(key_name: str, semitones: int) -> str:
    parts = key_name.strip().split()
    if len(parts) != 2:
        return key_name
    note = _norm_note(parts[0])
    if note not in NOTES:
        return key_name
    return f"{NOTES[(NOTES.index(note) + int(semitones)) % 12]} {parts[1]}"


def analyze_audio_file(path: str | Path, max_seconds: int = 160) -> dict:
    samples, sr = _decode_mono_samples(Path(path), max_seconds)
    if len(samples) < sr // 2 or max((abs(x) for x in samples), default=0.0) < 1e-5:
        return {"key": "C major", "camelot": "8B", "bpm": 120.0, "status": "unavailable", "key_candidates": []}
    key_slice = samples[15 * sr : 135 * sr] if len(samples) > 45 * sr else samples
    bpm_slice = samples[10 * sr :] if len(samples) > 40 * sr else samples
    candidates = _rank_keys(_compute_chroma(key_slice, sr))
    top_key = candidates[0]["key"]
    return {
        "key": top_key,
        "enharmonic": enharmonic_key(top_key),
        "camelot": camelot_code(top_key),
        "bpm": _estimate_bpm(bpm_slice, sr),
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


def _rank_keys(chroma: list[float]) -> list[dict]:
    ranked: list[dict] = []
    for mode, profile in _PROFILES.items():
        for tonic in range(12):
            rot = profile[-tonic:] + profile[:-tonic] if tonic else profile
            ranked.append({"key": f"{NOTES[tonic]} {mode}", "correlation": round(sum(chroma[i] * rot[i] for i in range(12)), 4)})
    ranked.sort(key=lambda item: item["correlation"], reverse=True)
    return ranked
