"""Offline speech-to-text transcription engine adapter and discovery."""

from __future__ import annotations

import importlib.util
import json
import math
from dataclasses import dataclass
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from typing import Any

from src.services.audio_vad import AudioChunk, segment_speech_chunks

_WHISPER_TIMEOUT_SEC = 180


@dataclass(frozen=True, slots=True)
class LyricSegment:
    start_sec: float
    end_sec: float
    text: str
    confidence: float = 1.0


@dataclass(frozen=True, slots=True)
class TranscriptionResult:
    segments: list[LyricSegment]
    engine_name: str
    status: str
    language: str = "en"


def discover_speech_engines() -> dict[str, bool]:
    has_faster = importlib.util.find_spec("faster_whisper") is not None
    has_cli = shutil.which("whisper") is not None or shutil.which("whisper.exe") is not None
    has_cpp = shutil.which("whisper-cli") is not None or shutil.which("whisper-cli.exe") is not None
    has_vosk = importlib.util.find_spec("vosk") is not None
    return {
        "faster_whisper": has_faster,
        "whisper_cli": has_cli,
        "whisper_cpp": has_cpp,
        "vosk": has_vosk,
        "heuristic_vad": True,
    }


def _transcribe_heuristic(chunks: list[AudioChunk]) -> list[LyricSegment]:
    return [
        LyricSegment(
            start_sec=c.start_sec,
            end_sec=c.end_sec,
            text=f"[Vocal Phrase {c.index + 1}]",
            confidence=0.85,
        )
        for c in chunks
    ]


def _segment_confidence(raw: dict[str, Any]) -> float:
    logprob = raw.get("avg_logprob")
    if not isinstance(logprob, (int, float)):
        return 1.0
    return max(0.0, min(1.0, math.exp(float(logprob))))


def _parse_whisper_json(json_path: Path) -> list[LyricSegment]:
    try:
        data = json.loads(json_path.read_text(encoding="utf-8", errors="replace"))
        raw_segments = data["segments"]
        return [
            LyricSegment(float(s["start"]), float(s["end"]), str(s["text"]).strip(), _segment_confidence(s))
            for s in raw_segments
            if str(s["text"]).strip()
        ]
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise RuntimeError("whisper CLI output unsupported") from exc


def _run_whisper_cli(exe: str, audio_path: Path, cancel_check: Any) -> list[LyricSegment]:
    """Run openai-whisper CLI and parse the ``<stem>.json`` it writes to --output_dir.

    Returns [] only when cancelled. Raises RuntimeError on failure or unsupported output.
    """
    if cancel_check and cancel_check():
        return []
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if sys.platform == "win32" else 0
    with tempfile.TemporaryDirectory(prefix="wavrik_whisper_") as out_dir:
        cmd = [exe, str(audio_path), "--output_format", "json", "--output_dir", out_dir, "--model", "tiny"]
        try:
            proc = subprocess.run(
                cmd, capture_output=True, text=True, encoding="utf-8", errors="replace",
                timeout=_WHISPER_TIMEOUT_SEC, check=False, creationflags=flags,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            raise RuntimeError("whisper CLI could not run") from exc
        if proc.returncode != 0:
            raise RuntimeError("whisper CLI failed")
        return _parse_whisper_json(Path(out_dir) / f"{audio_path.stem}.json")


def transcribe_audio(
    path: str | Path,
    preferred_engine: str = "auto",
    cancel_check: Any = None,
    max_seconds: int = 600,
) -> TranscriptionResult:
    from src.services.audio_analysis import _decode_mono_samples
    file_path = Path(path).resolve()
    if not file_path.is_file():
        return TranscriptionResult([], "none", "file_not_found")
    samples, sr = _decode_mono_samples(file_path, max_seconds)
    if len(samples) == 0:
        return TranscriptionResult([], "none", "empty_audio")
    chunks = segment_speech_chunks(samples, sr)
    if not chunks:
        return TranscriptionResult([], "vad", "no_speech_detected")
    engines = discover_speech_engines()
    if preferred_engine == "whisper_cli" or (preferred_engine == "auto" and engines["whisper_cli"]):
        exe = shutil.which("whisper") or shutil.which("whisper.exe")
        if exe:
            try:
                segs = _run_whisper_cli(exe, file_path, cancel_check)
            except RuntimeError:
                segs = []
            if segs:
                return TranscriptionResult(segs, "whisper_cli", "success")
    segs = _transcribe_heuristic(chunks)
    return TranscriptionResult(segs, "heuristic_vad", "fallback")
