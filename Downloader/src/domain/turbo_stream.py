"""Multi-segment HTTP range streaming turbo engine."""

from __future__ import annotations

import concurrent.futures
import threading
from collections.abc import Callable
from contextlib import nullcontext
from pathlib import Path

from .turbo_segment import ChunkSegment, RangeNotHonored, SegmentFileWriter, download_segment
from .turbo_segment import ProgressThrottle as _ProgressThrottle
from .turbo_settings import settings_of

_download_segment = download_segment

__all__ = [
    "ChunkSegment", "RangeNotHonored", "SegmentFileWriter", "_ProgressThrottle", "_download_segment",
    "calculate_chunk_boundaries", "download_turbo_stream", "probe_range_support",
]


def probe_range_support(request_get, url: str) -> tuple[bool, int]:
    try:
        resp = request_get(url, stream=True, timeout=(5, 10), headers={"Range": "bytes=0-0"})
        with resp if hasattr(resp, "__enter__") else nullcontext(resp):
            status, headers = getattr(resp, "status_code", 0), getattr(resp, "headers", {})
            if status == 206:
                cr = headers.get("content-range", "")
                total = cr.split("/")[-1].strip() if "/" in cr else ""
                return True, int(total) if total.isdigit() else 0
            if status == 200:
                cl = str(headers.get("content-length", "0"))
                return False, int(cl) if cl.isdigit() else 0
    except Exception:
        pass
    return False, 0


def calculate_chunk_boundaries(
    total_size: int, min_chunk_size: int = 2 * 1024 * 1024, max_threads: int = 4
) -> list[ChunkSegment]:
    if total_size <= 0:
        return []
    threads = max(1, min(max_threads, total_size // max(1, min_chunk_size)))
    step = total_size // threads
    segments = [
        ChunkSegment(i * step, ((i + 1) * step - 1) if i < threads - 1 else (total_size - 1))
        for i in range(threads)
    ]
    assert segments[0].start == 0 and segments[-1].end == total_size - 1
    assert sum(s.end - s.start + 1 for s in segments) == total_size
    return segments


class _LinkedCancel:
    """User cancellation plus a failure flag shared by every segment of one download."""

    def __init__(self, cancel) -> None:
        self._cancel = cancel
        self._failed = threading.Event()

    def is_set(self) -> bool:
        return self._cancel.is_set() or self._failed.is_set()

    def wait(self, timeout: float | None = None) -> bool:
        return self._cancel.wait(timeout)

    def fail(self) -> None:
        self._failed.set()


def _run_segment(stop: _LinkedCancel, request_get, url: str, seg: ChunkSegment, writer, throttle) -> None:
    try:
        download_segment(stop, request_get, url, seg, writer, throttle)
    except BaseException:
        stop.fail()
        raise


def download_turbo_stream(
    cancel, request_get, url: str, target_part: Path, total_size: int, progress: Callable | None = None
) -> bool:
    """Download `url` into `target_part` using the thread count set on `request_get`."""
    settings = settings_of(request_get)
    if not settings.enabled or total_size <= 0:
        return False
    segments = calculate_chunk_boundaries(total_size, max_threads=settings.threads)
    if not segments:
        return False
    target_part.parent.mkdir(parents=True, exist_ok=True)
    with target_part.open("wb") as handle:
        handle.truncate(total_size)
    stop, throttle = _LinkedCancel(cancel), _ProgressThrottle(total_size, progress)
    with SegmentFileWriter(target_part) as writer:
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(segments)) as pool:
            futs = [pool.submit(_run_segment, stop, request_get, url, s, writer, throttle) for s in segments]
            for fut in concurrent.futures.as_completed(futs):
                fut.result()
    return not cancel.is_set() and sum(s.downloaded for s in segments) == total_size
