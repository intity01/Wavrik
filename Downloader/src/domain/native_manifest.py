"""Supervision of the FFmpeg process that copies an HLS/DASH stream."""

from __future__ import annotations

import subprocess
import time
from pathlib import Path

POLL_SECONDS = 1.0
IDLE_TIMEOUT_SECONDS = 300.0
MAX_RUNTIME_SECONDS = 12 * 3600.0


def _size(path: Path) -> int:
    try:
        return path.stat().st_size
    except OSError:
        return -1


def wait_for_ffmpeg(proc: subprocess.Popen, target: Path, cancel) -> str | None:
    """Wait for FFmpeg and return its stderr.

    A long stream may legitimately take hours, so only a stalled output file (no growth for
    ``IDLE_TIMEOUT_SECONDS``) or an absurd total runtime raises ``subprocess.TimeoutExpired``.
    """
    started = last_growth = time.monotonic()
    last_size = -1
    terminated = False
    while True:
        try:
            return proc.communicate(timeout=POLL_SECONDS)[1]
        except subprocess.TimeoutExpired:
            pass
        now = time.monotonic()
        if cancel.is_set() and not terminated:
            terminated = True
            proc.terminate()
        size = _size(target)
        if size != last_size:
            last_size, last_growth = size, now
        if now - last_growth > IDLE_TIMEOUT_SECONDS or now - started > MAX_RUNTIME_SECONDS:
            raise subprocess.TimeoutExpired(proc.args, now - started)


def build_command(executable: str, url: str, target: Path) -> list[str]:
    return [
        executable, "-y", "-nostdin", "-hide_banner", "-loglevel", "error",
        "-protocol_whitelist", "http,https,tcp,tls,crypto",
        "-reconnect", "1", "-reconnect_streamed", "1", "-reconnect_delay_max", "5",
        "-rw_timeout", "15000000", "-i", url, "-map", "0", "-c", "copy", str(target),
    ]
