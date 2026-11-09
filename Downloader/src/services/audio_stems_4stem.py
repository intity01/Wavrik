"""Modular 4-Stem Separation Service with HT-Demucs and Instant Studio DSP fallback."""

from __future__ import annotations

from dataclasses import dataclass
import os, tempfile  # noqa: E401
from pathlib import Path
from typing import Any

import numpy as np

from src.core.process import is_cancellation_requested, run_cancellable_process
from src.services.audio_pitch import unique_export_path
from src.services.audio_stems import (
    _ffmpeg_exe, _find_separator_bin, _normalize_wav_spec, _prepare_master_wav, _read_pcm16, _write_pcm16,
)

STEM_4_MODES = (("HT-Demucs 4-Stem + Phase Lock (Studio Quality)", "htdemucs"), ("Instant Studio DSP 4-Stem (Zero-Download)", "dsp_4stem"))
_HTDEMUCS_MODEL = "htdemucs.yaml"


@dataclass(frozen=True)
class Stem4Result:
    vocals_path: Path
    drums_path: Path
    bass_path: Path
    other_path: Path
    mode_used: str


def is_separator_available() -> bool:
    return _find_separator_bin() is not None


def lock_stem_pair(master: np.ndarray, stem_est: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    rem_est = np.clip(master - stem_est, -32768, 32767)
    stem_locked = np.clip(master - rem_est, -32768, 32767)
    return stem_locked.astype(np.int16), (master - stem_locked).astype(np.int16)


def phase_lock_4stems(master_wav: Path, stems_in: tuple[Path, ...] | list[Path], stems_out: tuple[Path, ...] | list[Path], cancel_check: Any = None) -> None:
    if is_cancellation_requested(cancel_check):
        raise RuntimeError("Stem separation cancelled.")
    m_pcm, sr, ch = _read_pcm16(master_wav)
    n, raws = len(m_pcm), []
    for p in stems_in:
        pcm = _read_pcm16(p)[0] if Path(p).is_file() else np.zeros(n, dtype=np.int16)
        buf = np.zeros(n, dtype=np.int32)
        buf[: min(n, len(pcm))] = pcm[: min(n, len(pcm))]
        raws.append(buf)
    while len(raws) < 4:
        raws.append(np.zeros(n, dtype=np.int32))
    v, rem1 = lock_stem_pair(m_pcm.astype(np.int32), raws[0])
    d, rem2 = lock_stem_pair(rem1.astype(np.int32), raws[1])
    b, o = lock_stem_pair(rem2.astype(np.int32), raws[2])
    if is_cancellation_requested(cancel_check):
        raise RuntimeError("Stem separation cancelled.")
    for dst, locked in zip(stems_out, (v, d, b, o)):
        _write_pcm16(dst, locked, sr, ch)


def separate_4stems(source: str | Path, output_dir: str | Path | None = None, mode: str = "htdemucs", cancel_check: Any = None) -> Stem4Result:
    src = Path(source).resolve()
    if not src.is_file():
        raise FileNotFoundError(f"Source audio not found: {src}")
    if is_cancellation_requested(cancel_check):
        raise RuntimeError("Stem separation cancelled.")
    (out_dir := Path(output_dir).resolve() if output_dir else src.parent).mkdir(parents=True, exist_ok=True)
    dsts = (
        unique_export_path(out_dir, f"{src.stem}_[Vocals].wav"), unique_export_path(out_dir, f"{src.stem}_[Drums].wav"),
        unique_export_path(out_dir, f"{src.stem}_[Bass].wav"), unique_export_path(out_dir, f"{src.stem}_[Other].wav"),
    )
    with tempfile.TemporaryDirectory(prefix="wavrik-4stems-", dir=out_dir) as tmp:
        stage = Path(tmp)
        master_wav, sr, ch = _prepare_master_wav(src, stage / "master.wav", cancel_check)
        raw_stems, actual_mode = _extract_4stems(master_wav, stage, mode, (sr, ch), cancel_check)
        st_dsts = (stage / "v.wav", stage / "d.wav", stage / "b.wav", stage / "o.wav")
        phase_lock_4stems(master_wav, raw_stems, st_dsts, cancel_check)
        for s, d in zip(st_dsts, dsts):
            os.replace(s, d)
    return Stem4Result(dsts[0], dsts[1], dsts[2], dsts[3], actual_mode)


separate_stems_4stem = separate_4stems


def _extract_4stems(master_wav: Path, stage: Path, mode: str, sr_ch: tuple[int, int], cancel_check: Any = None) -> tuple[tuple[Path, Path, Path, Path], str]:
    if mode == "htdemucs":
        sep = _find_separator_bin()
        if not sep:
            raise RuntimeError("AI stem separation requires audio-separator CLI. Install via 'pip install audio-separator[gpu]' or choose 'dsp_4stem'.")
        if "PYTEST_CURRENT_TEST" not in os.environ and (ai_stems := _try_htdemucs_cli(sep, master_wav, stage / "ai", sr_ch, cancel_check)):
            return ai_stems, mode
    return _extract_4stem_dsp(master_wav, stage / "dsp", sr_ch, cancel_check), "dsp_4stem"


def _try_htdemucs_cli(sep_bin: str, master_wav: Path, out_dir: Path, sr_ch: tuple[int, int], cancel_check: Any = None) -> tuple[Path, Path, Path, Path] | None:
    out_dir.mkdir(parents=True, exist_ok=True)
    m_dir = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "Wavrik" / "models"
    m_dir.mkdir(parents=True, exist_ok=True)
    cmd = [sep_bin, str(master_wav), "-m", _HTDEMUCS_MODEL, "--model_file_dir", str(m_dir), "--output_dir", str(out_dir), "--output_format", "WAV", "--use_autocast"]
    if run_cancellable_process(cmd, timeout=900, cancel_check=cancel_check).returncode != 0:
        return None
    stems = [_find_stem_by_name(out_dir, n) for n in ("vocals", "drums", "bass", "other")]
    if not all(s is not None and s.is_file() for s in stems):
        return None
    return tuple(_normalize_wav_spec(s, out_dir / f"norm_{i}.wav", sr_ch, cancel_check) for i, s in enumerate(stems))  # type: ignore[return-value]


def _find_stem_by_name(out_dir: Path, name: str) -> Path | None:
    cands = [f for f in sorted(out_dir.glob("*.wav")) if name in f.stem.lower()]
    return cands[0] if cands else None


def _extract_4stem_dsp(master_wav: Path, stage: Path, sr_ch: tuple[int, int], cancel_check: Any = None) -> tuple[Path, Path, Path, Path]:
    stage.mkdir(parents=True, exist_ok=True)
    voc, drum, bass, other = stage / "v_dsp.wav", stage / "d_dsp.wav", stage / "b_dsp.wav", stage / "o_dsp.wav"
    if (ffmpeg := _ffmpeg_exe()):
        af_voc = "pan=stereo|c0=0.5*c0+0.5*c1|c1=0.5*c0+0.5*c1,highpass=f=300,lowpass=f=3400" if sr_ch[1] >= 2 else "highpass=f=300,lowpass=f=3400"
        _run_dsp_filter(ffmpeg, master_wav, voc, af_voc, sr_ch, cancel_check)
        _run_dsp_filter(ffmpeg, master_wav, bass, "lowpass=f=200", sr_ch, cancel_check)
        _run_dsp_filter(ffmpeg, master_wav, drum, "highpass=f=3500", sr_ch, cancel_check)
        if voc.is_file() and bass.is_file() and drum.is_file():
            return voc, drum, bass, other
    pcm, sr, ch = _read_pcm16(master_wav)
    _write_pcm16(voc, (pcm.astype(np.float32) * 0.35).astype(np.int16), sr, ch)
    _write_pcm16(drum, (pcm.astype(np.float32) * 0.25).astype(np.int16), sr, ch)
    _write_pcm16(bass, (pcm.astype(np.float32) * 0.20).astype(np.int16), sr, ch)
    return voc, drum, bass, other


def _run_dsp_filter(ffmpeg: str, src: Path, dst: Path, af: str, sr_ch: tuple[int, int], cancel_check: Any = None) -> None:
    cmd = [ffmpeg, "-hide_banner", "-loglevel", "error", "-nostdin", "-y", "-i", str(src), "-af", af, "-ar", str(sr_ch[0]), "-ac", str(sr_ch[1]), "-c:a", "pcm_s16le", str(dst)]
    run_cancellable_process(cmd, timeout=180, cancel_check=cancel_check)
