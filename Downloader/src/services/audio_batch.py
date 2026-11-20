"""Batch audio pitch and tempo rendering service."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from src.services.audio_analysis import transpose_key
from src.services.audio_pitch import build_export_filename, render_audio_clip, unique_export_path


@dataclass
class BatchJobConfig:
    semitones: int = 0
    tempo_ratio: float = 1.0
    engine: str = "r3_finer"
    fmt: str = "wav"
    output_dir: Path | None = None


_KEY_PATTERN = re.compile(r"^[A-Ga-g][#b\u266f\u266d]?\s+(major|minor)$", re.IGNORECASE)


def process_batch_file(
    source: Path, cfg: BatchJobConfig, known_key: str = "", cancel_check: Any = None,
    known_bpm: float = 0.0,
) -> Path:
    """Render one file; key/BPM tags appear in the name only when they are actually known."""
    if not source.is_file():
        raise FileNotFoundError(f"Source file not found: {source}")
    out_dir = cfg.output_dir or source.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    key = str(known_key or "").strip()
    key_known = bool(_KEY_PATTERN.match(key))
    target_key = transpose_key(key, cfg.semitones) if key_known else ""
    tempo_changed = abs(cfg.tempo_ratio - 1.0) >= 0.005
    tbpm = known_bpm * cfg.tempo_ratio if key_known and tempo_changed and known_bpm > 0 else 0.0
    filename = build_export_filename(source, cfg.semitones, target_key, cfg.fmt, tbpm)
    dest = unique_export_path(out_dir, filename)
    opts = (cfg.engine, cfg.fmt, cfg.tempo_ratio, 0.0, 0.0)
    render_audio_clip(source, dest, cfg.semitones, opts, cancel_check=cancel_check)
    return dest
