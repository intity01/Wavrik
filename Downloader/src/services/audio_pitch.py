"""Safe non-destructive pitch shifting with Rubber Band R3 and FFmpeg fallback."""

from __future__ import annotations

import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from src.core.runtime import find_ffmpeg, find_rubberband

_FORMATS = {
    "wav": (".wav", ["-c:a", "pcm_s24le"]),
    "flac": (".flac", ["-c:a", "flac"]),
    "mp3": (".mp3", ["-c:a", "libmp3lame", "-b:a", "320k"]),
}


def build_export_filename(
    source: str | Path, semitones: int, target_key: str = "", fmt: str = "wav",
) -> str:
    stem = Path(source).stem or "track"
    ext = _FORMATS.get(fmt, _FORMATS["wav"])[0]
    sign = f"+{semitones}" if semitones > 0 else str(semitones)
    key_tag = _compact_key(target_key)
    suffix = f"_[Key_{key_tag}_{sign}st]" if key_tag else f"_[{sign}st]"
    return f"{stem}{suffix}{ext}"


def unique_export_path(directory: Path, filename: str) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    candidate = directory / filename
    if not candidate.exists():
        return candidate
    stem, suffix = candidate.stem, candidate.suffix
    index = 1
    while (directory / f"{stem}_{index}{suffix}").exists():
        index += 1
    return directory / f"{stem}_{index}{suffix}"


def render_pitch_shift(
    source: str | Path,
    target: str | Path,
    semitones: int,
    engine: str = "r3_finer",
    fmt: str = "wav",
) -> Path:
    src, dst = _validate_paths(source, target, semitones)
    ffmpeg_exe = _require_ffmpeg()
    rb_exe = find_rubberband() if engine == "r3_finer" else None
    dst.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="wavrik-pitch-", dir=dst.parent) as stage_dir:
        staged = Path(stage_dir) / f"output{_FORMATS.get(fmt, _FORMATS['wav'])[0]}"
        if semitones == 0:
            _encode_direct(ffmpeg_exe, src, staged, fmt)
        elif rb_exe:
            _render_with_r3(ffmpeg_exe, rb_exe, src, staged, semitones, fmt)
        else:
            _render_with_ffmpeg(ffmpeg_exe, src, staged, semitones, fmt)
        if not staged.is_file() or staged.stat().st_size <= 44:
            raise RuntimeError("Rendered output file was empty or invalid.")
        os.replace(staged, dst)
    return dst


def _validate_paths(source: str | Path, target: str | Path, semitones: int) -> tuple[Path, Path]:
    src, dst = Path(source).resolve(), Path(target).resolve()
    if isinstance(semitones, bool) or not math.isfinite(semitones) or abs(semitones) > 12:
        raise ValueError("Pitch shift must be within -12 to +12 semitones.")
    if not src.is_file():
        raise FileNotFoundError(f"Source file not found: {src}")
    if src == dst:
        raise ValueError("Output path must differ from original source file.")
    return src, dst


def _require_ffmpeg() -> str:
    folder = find_ffmpeg()
    exe_name = "ffmpeg.exe" if sys.platform == "win32" else "ffmpeg"
    if folder and (Path(folder) / exe_name).is_file():
        return str(Path(folder) / exe_name)
    found = shutil.which("ffmpeg")
    if not found:
        raise RuntimeError("FFmpeg executable is required for audio rendering.")
    return found


def _encode_direct(ffmpeg_exe: str, src: Path, dst: Path, fmt: str) -> None:
    codec = _FORMATS.get(fmt, _FORMATS["wav"])[1]
    cmd = [ffmpeg_exe, "-hide_banner", "-loglevel", "error", "-nostdin", "-y", "-i", str(src), "-vn", *codec, str(dst)]
    _run_cmd(cmd)


def _render_with_r3(ffmpeg_exe: str, rb_exe: str, src: Path, dst: Path, semitones: int, fmt: str) -> None:
    quiet = dst.parent / "headroom_in.wav"
    shifted = dst.parent / "r3_shifted.wav"
    codec = _FORMATS.get(fmt, _FORMATS["wav"])[1]
    _run_cmd([ffmpeg_exe, "-hide_banner", "-loglevel", "error", "-nostdin", "-y", "-i", str(src), "-vn", "-af", "volume=0.25", "-c:a", "pcm_f32le", str(quiet)])
    _run_cmd([rb_exe, "-3", "-F", "--centre-focus", "-t", "1", "-p", str(semitones), str(quiet), str(shifted)])
    _run_cmd([ffmpeg_exe, "-hide_banner", "-loglevel", "error", "-nostdin", "-y", "-i", str(shifted), "-vn", "-af", "volume=4.0,alimiter=limit=0.891:level=disabled", *codec, str(dst)])


def _render_with_ffmpeg(ffmpeg_exe: str, src: Path, dst: Path, semitones: int, fmt: str) -> None:
    ratio = 2.0 ** (semitones / 12.0)
    filt = f"rubberband=tempo=1:pitch={ratio:.8f}:pitchq=quality:channels=together:formant=preserved"
    codec = _FORMATS.get(fmt, _FORMATS["wav"])[1]
    _run_cmd([ffmpeg_exe, "-hide_banner", "-loglevel", "error", "-nostdin", "-y", "-i", str(src), "-vn", "-af", filt, *codec, str(dst)])


def _run_cmd(cmd: list[str]) -> None:
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if sys.platform == "win32" else 0
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300, check=False, creationflags=flags)
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "Audio processing failed").strip().splitlines()[-1]
        raise RuntimeError(detail)


def _compact_key(key_name: str) -> str:
    parts = key_name.strip().split()
    if len(parts) != 2:
        return ""
    return f"{parts[0]}m" if parts[1].lower() == "minor" else parts[0]
