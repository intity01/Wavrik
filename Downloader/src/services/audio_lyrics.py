"""LRC and SRT lyrics serialization, parsing, and FFmpeg metadata embedding."""

from __future__ import annotations

from bisect import bisect_right
from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

from src.core.runtime import find_ffmpeg

_LRC_TS_RE = re.compile(r"\[(\d{1,2}):(\d{2}(?:\.\d{1,3})?)\]")


@dataclass(frozen=True, slots=True)
class LyricLine:
    timestamp: float
    text: str


def format_lrc_timestamp(seconds: float) -> str:
    s = max(0.0, float(seconds))
    mins, secs = int(s // 60), s % 60.0
    return f"[{mins:02d}:{secs:05.2f}]"


def format_srt_timestamp(seconds: float) -> str:
    s = max(0.0, float(seconds))
    hrs, rem = int(s // 3600), s % 3600.0
    mins, secs = int(rem // 60), rem % 60.0
    return f"{hrs:02d}:{mins:02d}:{int(secs):02d},{int((secs % 1.0) * 1000):03d}"


def export_lrc(lines: list[LyricLine], title: str = "", artist: str = "") -> str:
    out: list[str] = []
    title and out.append(f"[ti:{title}]")
    artist and out.append(f"[ar:{artist}]")
    for item in sorted(lines, key=lambda x: x.timestamp):
        out.append(f"{format_lrc_timestamp(item.timestamp)} {item.text}")
    return "\n".join(out)


def export_srt(lines: list[LyricLine], default_dur: float = 3.0) -> str:
    sorted_lines = sorted(lines, key=lambda x: x.timestamp)
    blocks: list[str] = []
    for idx, item in enumerate(sorted_lines):
        next_ts = sorted_lines[idx + 1].timestamp if idx + 1 < len(sorted_lines) else item.timestamp + default_dur
        end_ts = max(item.timestamp + 0.5, min(item.timestamp + default_dur, next_ts))
        ts_line = f"{format_srt_timestamp(item.timestamp)} --> {format_srt_timestamp(end_ts)}"
        blocks.append(f"{idx + 1}\n{ts_line}\n{item.text}\n")
    return "\n".join(blocks)


def parse_lrc(content: str) -> list[LyricLine]:
    lines: list[LyricLine] = []
    for raw in content.splitlines():
        st = raw.strip()
        if not st or st.startswith(("[ti:", "[ar:", "[al:", "[by:", "[offset:")):
            continue
        matches = list(_LRC_TS_RE.finditer(st))
        if not matches:
            continue
        text = _LRC_TS_RE.sub("", st).strip()
        for m in matches:
            lines.append(LyricLine(round(float(m.group(1)) * 60.0 + float(m.group(2)), 3), text))
    lines.sort(key=lambda item: item.timestamp)
    return lines


def find_active_line_index(timestamps: list[float], current_sec: float) -> int:
    if not timestamps or current_sec < timestamps[0]:
        return -1
    return max(0, min(len(timestamps) - 1, bisect_right(timestamps, current_sec) - 1))


def find_lyrics_for_audio(audio_path: str | Path | None) -> Path | None:
    if not audio_path:
        return None
    p = Path(audio_path).resolve()
    return cand if (cand := p.with_suffix(".lrc")).is_file() else None


def load_lrc_file(path: str | Path) -> list[LyricLine]:
    p = Path(path).resolve()
    return parse_lrc(p.read_text(encoding="utf-8", errors="replace")) if p.is_file() else []


def _ffmpeg_path() -> str:
    folder = find_ffmpeg()
    exe = "ffmpeg.exe" if sys.platform == "win32" else "ffmpeg"
    if folder and (p := Path(folder) / exe).is_file():
        return str(p)
    return "ffmpeg"


def embed_lyrics_to_audio(source: str | Path, lyrics_text: str, target: str | Path | None = None) -> Path:
    src = Path(source).resolve()
    if not src.is_file():
        raise FileNotFoundError(f"Source audio not found: {src}")
    dst = Path(target).resolve() if target is not None else src
    dst.parent.mkdir(parents=True, exist_ok=True)
    ext = dst.suffix.lower()
    with tempfile.TemporaryDirectory(prefix="lyr-", dir=dst.parent) as tmp:
        staged = Path(tmp) / f"staged{ext}"
        cmd = [_ffmpeg_path(), "-y", "-hide_banner", "-loglevel", "error", "-nostdin", "-i", str(src), "-c", "copy"]
        for key in ("lyrics", "lyrics-eng", "LYRICS", "unsyncedlyrics"):
            cmd.extend(["-metadata", f"{key}={lyrics_text}"])
        cmd.append(str(staged))
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if sys.platform == "win32" else 0
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False, creationflags=flags)
        if proc.returncode != 0 or not staged.is_file() or staged.stat().st_size <= 44:
            raise RuntimeError(f"FFmpeg lyric embedding failed: {proc.stderr.strip()}")
        os.replace(staged, dst)
    return dst


def read_embedded_lyrics(audio_path: str | Path) -> str:
    folder = find_ffmpeg()
    exe = "ffprobe.exe" if sys.platform == "win32" else "ffprobe"
    probe = str(Path(folder) / exe) if folder and (Path(folder) / exe).is_file() else "ffprobe"
    cmd = [probe, "-hide_banner", "-loglevel", "error", "-show_entries", "format_tags:stream_tags", "-of", "json", str(Path(audio_path).resolve())]
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if sys.platform == "win32" else 0
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=False, creationflags=flags)
        if proc.returncode != 0 or not proc.stdout:
            return ""
        data = json.loads(proc.stdout)
        tags = dict(data.get("streams", [{}])[0].get("tags", {}))
        tags.update(data.get("format", {}).get("tags", {}))
        lower_map = {str(k).lower(): str(v) for k, v in tags.items()}
        for k in ("lyrics", "lyrics-eng", "unsyncedlyrics", "lyrics-und"):
            if val := lower_map.get(k):
                return val
        return ""
    except Exception:
        return ""
