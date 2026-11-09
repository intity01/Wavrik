"""Multi-segment HTTP range streaming turbo engine."""

from __future__ import annotations

import concurrent.futures
from collections.abc import Callable
from contextlib import nullcontext
from dataclasses import dataclass
from pathlib import Path
import threading
import time


@dataclass
class ChunkSegment:
    start: int
    end: int
    downloaded: int = 0


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


class _ProgressThrottle:
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


def _download_segment(cancel, request_get, url: str, seg: ChunkSegment, writer: SegmentFileWriter, throttle: _ProgressThrottle) -> None:
    retries, seg_len = 0, seg.end - seg.start + 1
    while seg.downloaded < seg_len and not cancel.is_set():
        headers = {"Range": f"bytes={seg.start + seg.downloaded}-{seg.end}"}
        try:
            resp = request_get(url, stream=True, timeout=(10, 30), headers=headers)
            with resp if hasattr(resp, "__enter__") else nullcontext(resp):
                if getattr(resp, "status_code", 0) not in (200, 206):
                    raise RuntimeError(f"HTTP {getattr(resp, 'status_code', 0)}")
                for chunk in resp.iter_content(64 * 1024):
                    if cancel.is_set():
                        return
                    if chunk:
                        writer.write_at(seg.start + seg.downloaded, chunk)
                        seg.downloaded += len(chunk)
                        throttle.update(len(chunk))
        except Exception:
            retries += 1
            if retries > 3 or cancel.is_set():
                raise
            cancel.wait(0.2 * retries)


def download_turbo_stream(
    cancel, request_get, url: str, target_part: Path, total_size: int, progress: Callable | None = None
) -> bool:
    if total_size <= 0:
        return False
    target_part.parent.mkdir(parents=True, exist_ok=True)
    with target_part.open("wb") as handle:
        handle.truncate(total_size)
    segments = calculate_chunk_boundaries(total_size)
    if not segments:
        return False
    throttle = _ProgressThrottle(total_size, progress)
    with SegmentFileWriter(target_part) as writer:
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(segments)) as pool:
            futs = [pool.submit(_download_segment, cancel, request_get, url, s, writer, throttle) for s in segments]
            for fut in concurrent.futures.as_completed(futs):
                fut.result()
    return not cancel.is_set() and sum(s.downloaded for s in segments) == total_size
