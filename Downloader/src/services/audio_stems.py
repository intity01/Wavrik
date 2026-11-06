"""Hybrid AI RoFormer Ensemble and Studio Mid-Side DSP stem separation with bit-perfect phase lock."""

from __future__ import annotations

from array import array
from dataclasses import dataclass
import os
from pathlib import Path
import shutil, sys, tempfile, wave  # noqa: E401
from typing import Any

from src.core.process import is_cancellation_requested, run_cancellable_process
from src.core.runtime import find_ffmpeg
from src.services.audio_pitch import unique_export_path

STEM_MODES = (("Ensemble RoFormer + Phase Lock (Best SDR)", "roformer_ensemble"), ("Mel-Band RoFormer Fast + Phase Lock", "roformer_fast"), ("Instant Studio Mid-Side DSP (Zero-Download)", "dsp_2stem"))
_MEL_MODEL, _BS_MODEL = "vocals_mel_band_roformer.ckpt", "model_bs_roformer_ep_317_sdr_12.9755.ckpt"


@dataclass(frozen=True)
class StemResult:
    vocals_path: Path
    instrumental_path: Path
    mode_used: str


def separate_stems(
    source: str | Path, output_dir: str | Path | None = None, mode: str = "roformer_ensemble", cancel_check: Any = None,
) -> StemResult:
    src = Path(source).resolve()
    if not src.is_file():
        raise FileNotFoundError(f"Source audio not found: {src}")
    if is_cancellation_requested(cancel_check):
        raise RuntimeError("Stem separation cancelled.")
    (out_dir := Path(output_dir).resolve() if output_dir else src.parent).mkdir(parents=True, exist_ok=True)
    voc_dst, inst_dst = unique_export_path(out_dir, f"{src.stem}_[Vocals].wav"), unique_export_path(out_dir, f"{src.stem}_[Instrumental].wav")
    with tempfile.TemporaryDirectory(prefix="wavrik-stems-", dir=out_dir) as tmp:
        stage = Path(tmp)
        master_wav, sr, ch = _prepare_master_wav(src, stage / "master.wav", cancel_check)
        raw_inst, actual_mode = _extract_instrumental(master_wav, stage, mode, (sr, ch), cancel_check)
        if is_cancellation_requested(cancel_check):
            raise RuntimeError("Stem separation cancelled.")
        tmp_v, tmp_i = stage / "v.wav", stage / "i.wav"
        phase_lock_stems(master_wav, raw_inst, tmp_v, tmp_i, cancel_check)
        if is_cancellation_requested(cancel_check):
            raise RuntimeError("Stem separation cancelled.")
        os.replace(tmp_v, voc_dst)
        os.replace(tmp_i, inst_dst)
    return StemResult(vocals_path=voc_dst, instrumental_path=inst_dst, mode_used=actual_mode)


def phase_lock_stems(master_wav: Path, inst_est_wav: Path, voc_dst: Path, inst_dst: Path, cancel_check: Any = None) -> None:
    if is_cancellation_requested(cancel_check):
        raise RuntimeError("Stem separation cancelled.")
    m_pcm, sr, ch = _read_pcm16(master_wav)
    i_pcm, _, _ = _read_pcm16(inst_est_wav)
    total, n_inst = len(m_pcm), len(i_pcm)
    v_pcm, i_locked = array("h", [0] * total), array("h", [0] * total)
    for idx, m in enumerate(m_pcm):
        v = max(-32768, min(32767, m - (i_pcm[idx] if idx < n_inst else 0)))
        i = max(-32768, min(32767, m - v))
        v_pcm[idx], i_locked[idx] = m - i, i
    if is_cancellation_requested(cancel_check):
        raise RuntimeError("Stem separation cancelled.")
    _write_pcm16(voc_dst, v_pcm, sr, ch)
    _write_pcm16(inst_dst, i_locked, sr, ch)


def fuse_min_magnitude(inst_a: Path, inst_b: Path, out_wav: Path) -> Path:
    pcm_a, sr, ch = _read_pcm16(inst_a)
    pcm_b, _, _ = _read_pcm16(inst_b)
    fused = array("h", [pcm_a[i] if abs(pcm_a[i]) <= abs(pcm_b[i]) else pcm_b[i] for i in range(min(len(pcm_a), len(pcm_b)))])
    _write_pcm16(out_wav, fused, sr, ch)
    return out_wav


def _extract_instrumental(master_wav: Path, stage: Path, mode: str, sr_ch: tuple[int, int], cancel_check: Any = None) -> tuple[Path, str]:
    if mode in {"roformer_ensemble", "roformer_fast"} and (sep := _find_separator_bin()) and "PYTEST_CURRENT_TEST" not in os.environ:
        if (ai_inst := _try_roformer_cli(sep, master_wav, stage, mode, sr_ch, cancel_check)) and ai_inst.is_file():
            return ai_inst, mode
    return _extract_inst_dsp(master_wav, stage / "inst_dsp.wav", sr_ch, cancel_check), "dsp_2stem"


def _try_roformer_cli(sep_bin: str, master_wav: Path, stage: Path, mode: str, sr_ch: tuple[int, int], cancel_check: Any = None) -> Path | None:
    if not (m1 := _run_sep_model(sep_bin, master_wav, stage / "pass1", _MEL_MODEL, sr_ch, cancel_check)) or mode != "roformer_ensemble":
        return m1
    m2 = _run_sep_model(sep_bin, master_wav, stage / "pass2", _BS_MODEL, sr_ch, cancel_check)
    return fuse_min_magnitude(m1, m2 or _extract_inst_dsp(master_wav, stage / "inst_ref.wav", sr_ch, cancel_check), stage / "ensemble_inst.wav")


def _run_sep_model(sep_bin: str, master_wav: Path, out_dir: Path, model: str, sr_ch: tuple[int, int], cancel_check: Any = None) -> Path | None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (model_dir := Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "MediaDownloaderPRO" / "models").mkdir(parents=True, exist_ok=True)
    cmd = [sep_bin, str(master_wav), "-m", model, "--model_file_dir", str(model_dir), "--output_dir", str(out_dir), "--single_stem", "Instrumental", "--use_autocast"]
    proc = run_cancellable_process(cmd, timeout=900, cancel_check=cancel_check)
    cands = sorted(out_dir.glob("*Instrumental*.wav"))
    return _normalize_wav_spec(cands[0], out_dir / "norm.wav", sr_ch, cancel_check) if (proc.returncode == 0 and cands) else None


def _extract_inst_dsp(master_wav: Path, out_wav: Path, sr_ch: tuple[int, int], cancel_check: Any = None) -> Path:
    sr, ch = sr_ch
    if (ffmpeg := _ffmpeg_exe()):
        af = "pan=stereo|c0=c0-0.85*c1|c1=c1-0.85*c0,highpass=f=35" if ch >= 2 else "bandreject=f=1100:width_type=h:w=1600"
        cmd = [ffmpeg, "-hide_banner", "-loglevel", "error", "-nostdin", "-y", "-i", str(master_wav), "-af", af, "-ar", str(sr), "-ac", str(ch), "-c:a", "pcm_s16le", str(out_wav)]
        if run_cancellable_process(cmd, timeout=180, cancel_check=cancel_check).returncode == 0 and out_wav.is_file():
            return out_wav
    pcm, sr, ch = _read_pcm16(master_wav)
    _write_pcm16(out_wav, array("h", [int(s * 0.45) for s in pcm]), sr, ch)
    return out_wav


def _prepare_master_wav(src: Path, dst: Path, cancel_check: Any = None) -> tuple[Path, int, int]:
    if src.suffix.lower() == ".wav":
        with wave.open(str(src), "rb") as wf:
            if wf.getsampwidth() == 2 and wf.getnchannels() in (1, 2):
                return src, wf.getframerate(), wf.getnchannels()
    return _normalize_wav_spec(src, dst, (44100, 2), cancel_check), 44100, 2


def _normalize_wav_spec(src: Path, dst: Path, sr_ch: tuple[int, int], cancel_check: Any = None) -> Path:
    if not (ffmpeg := _ffmpeg_exe()):
        raise RuntimeError("FFmpeg is required to decode audio for stem separation.")
    sr, ch = sr_ch
    cmd = [ffmpeg, "-hide_banner", "-loglevel", "error", "-nostdin", "-y", "-i", str(src), "-vn", "-ar", str(sr), "-ac", str(ch), "-c:a", "pcm_s16le", str(dst)]
    if run_cancellable_process(cmd, timeout=180, cancel_check=cancel_check).returncode != 0:
        raise RuntimeError("Failed to decode audio stream for stem separation.")
    return dst


def _read_pcm16(path: Path) -> tuple[array, int, int]:
    with wave.open(str(path), "rb") as wf:
        sr, ch, frames = wf.getframerate(), wf.getnchannels(), wf.readframes(wf.getnframes())
    (pcm := array("h")).frombytes(frames[: (len(frames) // 2) * 2])
    return pcm, sr, ch


def _write_pcm16(path: Path, pcm: array, sr: int, ch: int) -> None:
    with wave.open(str(path), "wb") as wf:
        wf.setparams((ch, 2, sr, len(pcm) // max(1, ch), "NONE", "not compressed"))
        wf.writeframes(pcm.tobytes())


def _find_separator_bin() -> str | None:
    local = Path(sys.executable).resolve().parent / ("audio-separator.exe" if sys.platform == "win32" else "audio-separator")
    return str(local) if local.is_file() else shutil.which("audio-separator")


def _ffmpeg_exe() -> str | None:
    folder, exe = find_ffmpeg(), ("ffmpeg.exe" if sys.platform == "win32" else "ffmpeg")
    return str(Path(folder) / exe) if (folder and (Path(folder) / exe).is_file()) else shutil.which("ffmpeg")
