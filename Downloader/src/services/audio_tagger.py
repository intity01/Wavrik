"""Multi-format lossless FFmpeg audio metadata tagging service."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

from src.core.runtime import find_ffmpeg
from src.services.audio_acoustid import parse_filename_heuristic

COVER_EXTS = {".mp3", ".flac", ".m4a", ".mp4"}
TAG_FIELDS = ("title", "artist", "album", "date", "track", "genre", "comment")


@dataclass(frozen=True, slots=True)
class AudioMetadata:
    title: str = ""
    artist: str = ""
    album: str = ""
    date: str = ""
    track: str = ""
    genre: str = ""
    comment: str = ""
    cover_path: str = ""


def _ffmpeg_bin() -> str:
    folder = find_ffmpeg()
    exe = "ffmpeg.exe" if sys.platform == "win32" else "ffmpeg"
    if folder and (p := Path(folder) / exe).is_file():
        return str(p)
    if found := shutil.which("ffmpeg"):
        return found
    raise FileNotFoundError("FFmpeg executable not found")


def _ffprobe_bin() -> str | None:
    folder = find_ffmpeg()
    exe = "ffprobe.exe" if sys.platform == "win32" else "ffprobe"
    if folder and (p := Path(folder) / exe).is_file():
        return str(p)
    return shutil.which("ffprobe")


def _build_tag_cmd(src: Path, staged: Path, meta: AudioMetadata, has_cover: bool) -> list[str]:
    cmd = [_ffmpeg_bin(), "-y", "-hide_banner", "-loglevel", "error", "-nostdin", "-i", str(src)]
    if has_cover:
        cmd.extend(["-i", str(Path(meta.cover_path).resolve()), "-map", "0:a", "-map", "1:0", "-disposition:v:0", "attached_pic"])
    cmd.extend(["-c", "copy"])
    if staged.suffix.lower() == ".mp3":
        cmd.extend(["-id3v2_version", "3"])
    for key in TAG_FIELDS:
        if val := getattr(meta, key, ""):
            cmd.extend(["-metadata", f"{key}={val}"])
    cmd.append(str(staged))
    return cmd


def apply_audio_metadata(
    source: str | Path,
    metadata: AudioMetadata,
    target: str | Path | None = None,
) -> Path:
    src = Path(source).resolve()
    if not src.is_file():
        raise FileNotFoundError(f"Source file not found: {src}")
    dst = Path(target).resolve() if target is not None else src
    dst.parent.mkdir(parents=True, exist_ok=True)
    ext = dst.suffix.lower()
    has_cov = ext in COVER_EXTS and bool(metadata.cover_path) and Path(metadata.cover_path).is_file()
    with tempfile.TemporaryDirectory(prefix="tag-", dir=dst.parent) as tmp_dir:
        staged = Path(tmp_dir) / f"staged{ext}"
        cmd = _build_tag_cmd(src, staged, metadata, has_cov)
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if sys.platform == "win32" else 0
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False, creationflags=flags)
        if proc.returncode != 0:
            raise RuntimeError(f"FFmpeg tagging failed: {proc.stderr.strip()}")
        if not staged.is_file() or staged.stat().st_size <= 44:
            raise RuntimeError(f"Staged file invalid: {staged}")
        os.replace(staged, dst)
    return dst


def _probe_tags(path: Path) -> dict[str, str]:
    probe = _ffprobe_bin()
    if not probe:
        return {}
    cmd = [probe, "-hide_banner", "-loglevel", "error", "-show_entries", "format_tags:stream_tags", "-of", "json", str(path)]
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if sys.platform == "win32" else 0
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False, creationflags=flags)
        if proc.returncode != 0 or not proc.stdout:
            return {}
        data = json.loads(proc.stdout)
        tags = dict(data.get("streams", [{}])[0].get("tags", {}))
        tags.update(data.get("format", {}).get("tags", {}))
        return {str(k).lower(): str(v) for k, v in tags.items()}
    except Exception:
        return {}


def read_audio_metadata(file_path: str | Path) -> AudioMetadata:
    path = Path(file_path).resolve()
    if not path.is_file():
        return AudioMetadata()
    tags = _probe_tags(path)
    title = tags.get("title", "")
    artist = tags.get("artist", "") or tags.get("author", "")
    album = tags.get("album", "")
    date = tags.get("date", "") or tags.get("year", "")
    track = tags.get("track", "") or tags.get("tracknumber", "")
    genre = tags.get("genre", "")
    comment = tags.get("comment", "") or tags.get("description", "")
    if not (title or artist):
        heur = parse_filename_heuristic(path.name)
        title, artist = heur.get("title", ""), heur.get("artist", "")
        album = album or heur.get("album", "")
        track = track or heur.get("track", "")
    return AudioMetadata(title=title, artist=artist, album=album, date=date, track=track, genre=genre, comment=comment)
