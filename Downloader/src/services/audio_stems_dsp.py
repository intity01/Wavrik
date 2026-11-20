"""FFmpeg filter runner for the instant DSP stem fallback."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from src.core.process import run_cancellable_process


def run_dsp_filter(
    ffmpeg: str, src: Path, dst: Path, af: str, sr_ch: tuple[int, int], cancel_check: Any = None,
) -> bool:
    """Render one filtered WAV; True only when ffmpeg exited 0 and left a non-empty file.

    A failed, cancelled or timed-out run never leaves a partial WAV behind.
    """
    cmd = [
        ffmpeg, "-hide_banner", "-loglevel", "error", "-nostdin", "-y", "-i", str(src), "-af", af,
        "-ar", str(sr_ch[0]), "-ac", str(sr_ch[1]), "-c:a", "pcm_s16le", str(dst),
    ]
    try:
        succeeded = run_cancellable_process(cmd, timeout=180, cancel_check=cancel_check).returncode == 0
    except BaseException:
        dst.unlink(missing_ok=True)
        raise
    if not succeeded or not dst.is_file() or dst.stat().st_size == 0:
        dst.unlink(missing_ok=True)
        return False
    return True
