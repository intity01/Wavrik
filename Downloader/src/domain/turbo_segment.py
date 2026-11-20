"""Per-segment workers for the multi-segment turbo engine."""

from __future__ import annotations

import re
import threading
import time
from collections.abc import Callable
from contextlib import nullcontext
from dataclasses import dataclass
from pathlib import Path

MAX_RETRIES = 3
_CONTENT_RANGE = re.compile(r"^bytes\s+(\d+)-(\d+)/(\d+|\*)$", re.IGNORECASE)


class RangeNotHonored(RuntimeError):
    """The server did not answer a Range request with the exact requested bytes."""


@dataclass
class ChunkSegment:
    start: int
    end: int
    downloaded: int = 0


class SegmentFileWriter:
    def __init__(self, path: Path):
        self._handle = path.open("r+b")
        self._lock = threading.Lock()

    def write_at(self, offset: int, data: bytes) -> None:
        with self._lock:
            self._handle.seek(offset)
            self._handle.write(data)

    def close(self) -> None:
        with self._lock:
            if not self._handle.closed:
                self._handle.flush()
                self._handle.close()

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        self.close()


class ProgressThrottle:
    def __init__(self, total: int, progress: Callable | None):
        self._total, self._progress, self._written = total, progress, 0
        self._started, self._last, self._lock = time.monotonic(), 0.0, threading.Lock()

    def update(self, delta: int) -> None:
        if not self._progress:
            return
        with self._lock:
            self._written += delta
            now = time.monotonic()
            if now - self._last < 0.05 and self._written < self._total:
                return
            self._last = now
            elapsed = max(now - self._started, 0.01)
            spd = self._written / elapsed
            eta = max(self._total - self._written, 0) / spd if spd else 0.0
            s_txt = f"{spd / 1048576:.1f} MB/s" if spd >= 1048576 else f"{spd / 1024:.0f} KB/s"
            t_txt = f"{int(eta) // 60:02d}:{int(eta) % 60:02d}" if self._total else "—"
            self._progress({
                "status": "downloading",
                "percent": (self._written * 100.0 / self._total) if self._total else 0.0,
                "speed": s_txt,
                "eta": t_txt,
            })


def _require_exact_range(resp, want_start: int, seg_end: int) -> None:
    status = getattr(resp, "status_code", 0)
    if status != 206:
        raise RangeNotHonored(f"HTTP {status} instead of 206 Partial Content")
    value = str(getattr(resp, "headers", {}).get("content-range", "")).strip()
    match = _CONTENT_RANGE.match(value)
    if not match or int(match.group(1)) != want_start or not want_start <= int(match.group(2)) <= seg_end:
        raise RangeNotHonored("Content-Range does not match the requested segment")


def _fetch_range(cancel, request_get, url: str, seg: ChunkSegment, writer, throttle) -> None:
    want = seg.start + seg.downloaded
    resp = request_get(url, stream=True, timeout=(10, 30), headers={"Range": f"bytes={want}-{seg.end}"})
    with resp if hasattr(resp, "__enter__") else nullcontext(resp):
        _require_exact_range(resp, want, seg.end)
        seg_len = seg.end - seg.start + 1
        for chunk in resp.iter_content(64 * 1024):
            if cancel.is_set():
                return
            chunk = chunk[: seg_len - seg.downloaded]
            if chunk:
                writer.write_at(seg.start + seg.downloaded, chunk)
                seg.downloaded += len(chunk)
                throttle.update(len(chunk))
            if seg.downloaded >= seg_len:
                return


def download_segment(cancel, request_get, url: str, seg: ChunkSegment, writer, throttle) -> None:
    """Fill one segment, retrying from the written offset; progress resets the retry budget."""
    retries, seg_len = 0, seg.end - seg.start + 1
    while seg.downloaded < seg_len and not cancel.is_set():
        before, error = seg.downloaded, None
        try:
            _fetch_range(cancel, request_get, url, seg, writer, throttle)
        except RangeNotHonored:
            raise
        except Exception as exc:  # noqa: BLE001 - adapters raise provider-specific errors.
            error = exc
        if cancel.is_set():
            return
        if seg.downloaded > before:
            retries = 0
            if error is None:
                continue
        else:
            retries += 1
        if retries > MAX_RETRIES:
            raise error or RuntimeError("Server returned no data for this segment.")
        cancel.wait(0.2 * max(retries, 1))
