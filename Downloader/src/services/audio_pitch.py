"""Safe non-destructive pitch shifting with Rubber Band R3 and FFmpeg fallback."""

from __future__ import annotations

import math
import os
from pathlib import Path
import shutil
import sys
import tempfile
from typing import Any

from src.core.process import is_cancellation_requested, run_cancellable_process
from src.core.runtime import find_ffmpeg, find_rubberband

_FORMATS = {
    "wav": (".wav", ["-c:a", "pcm_s24le"]),
    "flac": (".flac", ["-c:a", "flac"]),
    "mp3": (".mp3", ["-c:a", "libmp3lame", "-b:a", "320k"]),
}


def build_export_filename(
    source: str | Path, semitones: int, target_key: str = "", fmt: str = "wav", target_bpm: float = 0.0,
) -> str:
    stem = Path(Path(source).name).stem or "track"
    ext = _FORMATS.get(fmt, _FORMATS["wav"])[0]
    sign = f"+{semitones}" if semitones > 0 else str(semitones)
    key_tag = _compact_key(target_key)
    bpm_tag = f"_{int(round(target_bpm))}BPM" if target_bpm > 0.0 else ""
    suffix = f"_[Key_{key_tag}{bpm_tag}_{sign}st]" if key_tag else f"_[{sign}st]"
    return f"{stem}{suffix}{ext}"


def unique_export_path(directory: Path, filename: str) -> Path:
    safe_name = Path(filename).name
    if not safe_name:
        raise ValueError(f"Invalid export filename: {filename}")
    resolved_dir = directory.resolve()
    candidate = directory / safe_name
    if not candidate.resolve().is_relative_to(resolved_dir):
        raise ValueError(f"Path traversal detected: {filename}")
    directory.mkdir(parents=True, exist_ok=True)
    if not candidate.exists():
        return candidate
    stem, suffix = candidate.stem, candidate.suffix
    index = 1
    while (directory / f"{stem}_{index}{suffix}").exists():
        index += 1
    result = directory / f"{stem}_{index}{suffix}"
    if not result.resolve().is_relative_to(resolved_dir):
        raise ValueError(f"Path traversal detected: {filename}")
    return result


def render_pitch_shift(
    source: str | Path, target: str | Path, semitones: int,
    engine: str = "r3_finer", fmt: str = "wav", tempo_ratio: float = 1.0,
) -> Path:
    return render_audio_clip(source, target, semitones, (engine, fmt, tempo_ratio, 0.0))


def render_audio_clip(
    source: str | Path, target: str | Path, semitones: int,
    options: tuple = ("r3_finer", "wav", 1.0, 0.0, 0.0),
    cancel_check: Any = None,
) -> Path:
    engine, fmt, tempo_ratio, max_dur = options[:4]
    start_sec = float(options[4]) if len(options) > 4 else 0.0
    src, dst = _validate_paths(source, target, semitones, tempo_ratio)
    ffmpeg_exe = _require_ffmpeg()
    rb_exe = find_rubberband() if engine in {"r3_finer", "r3_percussive"} else None
    dst.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="wavrik-pitch-", dir=dst.parent) as stage_dir:
        staged = Path(stage_dir) / f"output{_FORMATS.get(fmt, _FORMATS['wav'])[0]}"
        opts = (semitones, fmt, tempo_ratio, max_dur, start_sec, engine)
        if semitones == 0 and abs(tempo_ratio - 1.0) < 1e-4:
            _encode_direct(ffmpeg_exe, src, staged, opts, cancel_check)
        elif rb_exe:
            _render_with_r3(ffmpeg_exe, rb_exe, src, staged, opts, cancel_check)
        else:
            _render_with_ffmpeg(ffmpeg_exe, src, staged, opts, cancel_check)
        if is_cancellation_requested(cancel_check):
            raise RuntimeError("Audio rendering cancelled.")
        if not staged.is_file() or staged.stat().st_size <= 44:
            raise RuntimeError("Rendered output file was empty or invalid.")
        os.replace(staged, dst)
    return dst


def _validate_paths(
    source: str | Path, target: str | Path, semitones: int, tempo_ratio: float = 1.0,
) -> tuple[Path, Path]:
    src, dst = Path(source).resolve(), Path(target).resolve()
    if isinstance(semitones, bool) or not math.isfinite(semitones) or abs(semitones) > 12:
        raise ValueError("Pitch shift must be within -12 to +12 semitones.")
    if not math.isfinite(tempo_ratio) or not (0.5 <= tempo_ratio <= 2.0):
        raise ValueError("Tempo ratio must be within 0.5x to 2.0x.")
    if not src.is_file():
        raise FileNotFoundError(f"Source file not found: {src}")
    if src == dst:
        raise ValueError("Output path must differ from original source file.")
    return src, dst


def _require_ffmpeg() -> str:
    folder = find_ffmpeg()
    exe = "ffmpeg.exe" if sys.platform == "win32" else "ffmpeg"
    found = str(Path(folder) / exe) if (folder and (Path(folder) / exe).is_file()) else shutil.which("ffmpeg")
    if not found:
        raise RuntimeError("FFmpeg executable is required for audio rendering.")
    return found


def _encode_direct(ffmpeg_exe: str, src: Path, dst: Path, opts: tuple, cancel_check: Any = None) -> None:
    _, fmt, _, max_dur, start_sec, _ = opts
    codec = _FORMATS.get(fmt, _FORMATS["wav"])[1]
    seek, limit = (["-ss", f"{start_sec:.2f}"] if start_sec > 0 else []), (["-t", f"{max_dur:.1f}"] if max_dur > 0 else [])
    _run_cmd([ffmpeg_exe, "-hide_banner", "-loglevel", "error", "-nostdin", "-y", *seek, "-i", str(src), *limit, "-vn", *codec, str(dst)], cancel_check)


def _render_with_r3(ffmpeg_exe: str, rb_exe: str, src: Path, dst: Path, opts: tuple, cancel_check: Any = None) -> None:
    semitones, fmt, tempo_ratio, max_dur, start_sec, engine = opts
    quiet, shifted, codec = dst.parent / "headroom_in.wav", dst.parent / "r3_shifted.wav", _FORMATS.get(fmt, _FORMATS["wav"])[1]
    seek, limit = (["-ss", f"{start_sec:.2f}"] if start_sec > 0 else []), (["-t", f"{max_dur:.1f}"] if max_dur > 0 else [])
    dur_ratio = f"{1.0 / max(0.5, min(2.0, tempo_ratio)):.6f}"
    r3_flags = ["-3", "--pitch-hq"] if engine == "r3_percussive" else ["-3", "-F", "--centre-focus"]
    _run_cmd([ffmpeg_exe, "-hide_banner", "-loglevel", "error", "-nostdin", "-y", *seek, "-i", str(src), *limit, "-vn", "-af", "volume=0.5", "-c:a", "pcm_f32le", str(quiet)], cancel_check)
    _run_cmd([rb_exe, *r3_flags, "-t", dur_ratio, "-p", str(semitones), str(quiet), str(shifted)], cancel_check)
    _run_cmd([ffmpeg_exe, "-hide_banner", "-loglevel", "error", "-nostdin", "-y", "-i", str(shifted), "-vn", "-af", "volume=2.0,alimiter=limit=0.95:level=disabled", *codec, str(dst)], cancel_check)


def _render_with_ffmpeg(ffmpeg_exe: str, src: Path, dst: Path, opts: tuple, cancel_check: Any = None) -> None:
    semitones, fmt, tempo_ratio, max_dur, start_sec, _ = opts
    ratio, codec = 2.0 ** (semitones / 12.0), _FORMATS.get(fmt, _FORMATS["wav"])[1]
    seek, limit = (["-ss", f"{start_sec:.2f}"] if start_sec > 0 else []), (["-t", f"{max_dur:.1f}"] if max_dur > 0 else [])
    filt = f"rubberband=tempo={tempo_ratio:.6f}:pitch={ratio:.8f}:pitchq=quality:channels=together:formant=preserved"
    _run_cmd([ffmpeg_exe, "-hide_banner", "-loglevel", "error", "-nostdin", "-y", *seek, "-i", str(src), *limit, "-vn", "-af", filt, *codec, str(dst)], cancel_check)


def _run_cmd(cmd: list[str], cancel_check: Any = None) -> None:
    proc = run_cancellable_process(cmd, timeout=300, cancel_check=cancel_check)
    if proc.returncode != 0:
        lines = ((proc.stderr or "").strip() or (proc.stdout or "").strip() or "Audio processing failed").splitlines()
        raise RuntimeError(lines[-1] if lines else "Audio processing failed")


def _compact_key(key_name: str) -> str:
    parts = key_name.strip().split()
    return (f"{parts[0]}m" if parts[1].lower() == "minor" else parts[0]) if len(parts) == 2 else ""
