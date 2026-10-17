"""CPU key and BPM estimation with harmonic chroma, spectral flux tempo, and enharmonic aliases."""

from __future__ import annotations

from array import array
from pathlib import Path
import subprocess
import sys
import wave

from src.core.runtime import find_ffmpeg
from src.services.audio_dsp import estimate_bpm as _estimate_bpm
from src.services.audio_hpcp import extract_key_candidates as _extract_key_candidates

NOTES = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")
ALL_KEYS = tuple([*(f"{n} major" for n in NOTES), *(f"{n} minor" for n in NOTES)])
_FLAT_TO_SHARP = {"Db": "C#", "Eb": "D#", "Gb": "F#", "Ab": "G#", "Bb": "A#", "D♭": "C#", "E♭": "D#", "G♭": "F#", "A♭": "G#", "B♭": "A#"}
_SHARP_TO_FLAT = {"C#": "Db", "D#": "Eb", "F#": "Gb", "G#": "Ab", "A#": "Bb"}
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


def mirex_key_score(predicted: str, reference: str) -> tuple[float, str]:
    p_parts, r_parts = predicted.strip().split(), reference.strip().split()
    if len(p_parts) != 2 or len(r_parts) != 2:
        return 0.0, "unrelated"
    p_note, p_mode = _norm_note(p_parts[0]), p_parts[1].lower()
    r_note, r_mode = _norm_note(r_parts[0]), r_parts[1].lower()
    if p_note not in NOTES or r_note not in NOTES:
        return 0.0, "unrelated"
    if p_note == r_note and p_mode == r_mode:
        return 1.0, "exact"
    diff = (NOTES.index(p_note) - NOTES.index(r_note)) % 12
    if p_mode == r_mode and diff in (5, 7):
        return 0.5, "fifth"
    if p_mode != r_mode and ((r_mode == "major" and diff == 9) or (r_mode == "minor" and diff == 3)):
        return 0.3, "relative"
    if p_note == r_note and p_mode != r_mode:
        return 0.2, "parallel"
    return 0.0, "unrelated"


def mirex_bpm_score(predicted: float, reference: float) -> tuple[float, str]:
    if reference <= 0:
        return 0.0, "miss"
    if abs(predicted - reference) <= max(1.5, reference * 0.04):
        return 1.0, "acc1_exact"
    for mult in (0.5, 2.0, 2.0 / 3.0, 1.5, 0.75, 4.0 / 3.0):
        target = reference * mult
        if abs(predicted - target) <= max(1.5, target * 0.04):
            return 0.5, "acc2_harmonic"
    return 0.0, "miss"


def analyze_audio_file(path: str | Path, max_seconds: int = 250) -> dict:
    samples, sr = _decode_mono_samples(Path(path), max_seconds)
    if len(samples) < sr // 2 or max((abs(x) for x in samples), default=0.0) < 1e-5:
        return {"key": "C major", "camelot": "8B", "bpm": 120.0, "confidence": 0, "status": "unavailable", "key_candidates": []}
    bpm_slice = samples[10 * sr : 160 * sr] if len(samples) > 40 * sr else samples
    candidates = _extract_key_candidates(samples, sr)
    top_key, r1 = candidates[0]["key"], float(candidates[0]["correlation"])
    sec_key, r2 = candidates[1]["key"], float(candidates[1]["correlation"])
    _sc, rel = mirex_key_score(top_key, sec_key)
    conf = min(99, max(50, int(round(r1 * 88.0 + min(0.15, max(0.0, r1 - r2)) * 90.0))))
    return {
        "key": top_key,
        "enharmonic": enharmonic_key(top_key),
        "camelot": camelot_code(top_key),
        "bpm": _estimate_bpm(bpm_slice, sr),
        "confidence": conf,
        "relation": rel,
        "status": "estimate",
        "badge": f"Experimental / Estimate · ความเชื่อมั่น {conf}% (2nd: {sec_key} · {rel})",
        "key_candidates": candidates[:3],
    }


def _decode_mono_samples(path: Path, max_seconds: int) -> tuple[list[float], int]:
    if not path.is_file():
        raise FileNotFoundError(path)
    ffmpeg_dir = find_ffmpeg()
    exe = str(Path(ffmpeg_dir) / ("ffmpeg.exe" if sys.platform == "win32" else "ffmpeg")) if ffmpeg_dir else None
    if exe and Path(exe).is_file():
        cmd = [exe, "-hide_banner", "-loglevel", "error", "-nostdin", "-i", str(path), "-t", str(max_seconds), "-vn", "-ac", "1", "-ar", "16000", "-f", "s16le", "pipe:1"]
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if sys.platform == "win32" else 0
        proc = subprocess.run(cmd, capture_output=True, timeout=45, check=False, creationflags=flags)
        if proc.returncode == 0 and proc.stdout:
            pcm = array("h")
            pcm.frombytes(proc.stdout[: (len(proc.stdout) // 2) * 2])
            return [s / 32768.0 for s in pcm], 16000
    return _read_wav_fallback(path, max_seconds)


def _read_wav_fallback(path: Path, max_seconds: int) -> tuple[list[float], int]:
    with wave.open(str(path), "rb") as wf:
        sr, ch, width = wf.getframerate(), wf.getnchannels(), wf.getsampwidth()
        raw = wf.readframes(min(wf.getnframes(), sr * max_seconds))
    if width != 2 or not raw:
        return [], 16000
    pcm = array("h")
    pcm.frombytes(raw[: (len(raw) // 2) * 2])
    return [pcm[i] / 32768.0 for i in range(0, len(pcm), max(1, ch))], sr
