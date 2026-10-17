"""Batch audio pitch and tempo rendering service."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from src.services.audio_analysis import transpose_key
from src.services.audio_pitch import build_export_filename, render_pitch_shift, unique_export_path


@dataclass
class BatchJobConfig:
    semitones: int = 0
    tempo_ratio: float = 1.0
    engine: str = "r3_finer"
    fmt: str = "wav"
    output_dir: Path | None = None


def process_batch_file(source: Path, cfg: BatchJobConfig, known_key: str = "C major") -> Path:
    if not source.is_file():
        raise FileNotFoundError(f"Source file not found: {source}")
    out_dir = cfg.output_dir or source.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    target_key = transpose_key(known_key, cfg.semitones)
    tbpm = 120.0 * cfg.tempo_ratio if abs(cfg.tempo_ratio - 1.0) >= 0.005 else 0.0
    filename = build_export_filename(source, cfg.semitones, target_key, cfg.fmt, tbpm)
    dest = unique_export_path(out_dir, filename)
    render_pitch_shift(source, dest, cfg.semitones, cfg.engine, cfg.fmt, cfg.tempo_ratio)
    return dest
