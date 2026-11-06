"""Subprocess execution with cancellation token support and process tree cleanup."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
import subprocess
import sys
import time
from typing import Any


def kill_process_tree(proc: subprocess.Popen) -> None:
    """Terminate or kill a process and all its child processes."""
    if proc.poll() is not None:
        return
    try:
        if sys.platform == "win32":
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                capture_output=True,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                check=False,
            )
        proc.kill()
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass
    try:
        proc.wait(timeout=1.0)
    except Exception:
        pass


def is_cancellation_requested(cancel_check: Callable[[], bool] | Any | None) -> bool:
    """Evaluate whether cancellation has been requested."""
    if cancel_check is None:
        return False
    if callable(cancel_check):
        return bool(cancel_check())
    if hasattr(cancel_check, "is_set"):
        return bool(cancel_check.is_set())
    if hasattr(cancel_check, "is_cancelled"):
        return bool(cancel_check.is_cancelled())
    return False


def run_cancellable_process(
    cmd: list[str], timeout: float = 300.0, cancel_check: Callable[[], bool] | Any | None = None, cwd: str | Path | None = None,
) -> subprocess.CompletedProcess[str]:
    """Execute command with active cancellation polling and tree termination."""
    if is_cancellation_requested(cancel_check):
        raise RuntimeError("Process cancelled before execution.")
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if sys.platform == "win32" else 0
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.DEVNULL, text=True, cwd=cwd, creationflags=flags)
    start_time = time.monotonic()
    try:
        while True:
            if is_cancellation_requested(cancel_check):
                kill_process_tree(proc)
                raise RuntimeError("Process execution cancelled.")
            try:
                stdout, stderr = proc.communicate(timeout=0.1)
                return subprocess.CompletedProcess(cmd, proc.returncode, stdout, stderr)
            except subprocess.TimeoutExpired:
                pass
            if (time.monotonic() - start_time) > timeout:
                kill_process_tree(proc)
                raise subprocess.TimeoutExpired(cmd, timeout)
    except Exception:
        kill_process_tree(proc)
        raise
