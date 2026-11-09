"""Comprehensive test suite for Turbo Download Engine.

Tests cover:
- MockRangeResponse simulating RFC 7233 206 Partial Content / 200 OK responses.
- Range probe support detection (206, 200, HTTP errors, exceptions).
- Chunk boundary partitioning invariants (coverage, contiguity, prime and odd sizes).
- Thread-safe SegmentFileWriter concurrent writes and lifecycle.
- Complete multi-segment turbo download byte-for-byte SHA-256 integrity.
- Per-chunk failure with resume offset on retry.
- Cancellation cleanup in turbo stream and native file routes.
- Seamless fallback to single-stream when range requests are unsupported.
- Config turbo defaults and thread count boundary clamping.
- Settings page turbo card UI interaction and localization via qtbot.
"""

from __future__ import annotations

import concurrent.futures
import hashlib
from pathlib import Path
import re
import threading
from unittest.mock import MagicMock

import pytest
import requests

from src.core.config import DEFAULT_SETTINGS, Config
from src.domain.models import JobState
from src.domain.native_file import download_file
from src.domain.presets import getPreset
from src.domain.turbo_stream import (
    ChunkSegment,
    SegmentFileWriter,
    _download_segment,
    _ProgressThrottle,
    calculate_chunk_boundaries,
    download_turbo_stream,
    probe_range_support,
)
from src.ui.pages.settings_page import SettingsInterface


def _make_payload(size: int) -> bytes:
    """Generate deterministic byte payload for integrity checks."""
    pattern = bytes(range(256)) * 64  # 16 KB pattern block
    repeats = (size // len(pattern)) + 1
    return (pattern * repeats)[:size]


class MockRangeResponse:
    """Simulate RFC 7233 206 Partial Content and 200 OK HTTP responses."""

    def __init__(
        self,
        data: bytes,
        status_code: int = 200,
        headers: dict[str, str] | None = None,
        chunk_size: int = 64 * 1024,
        fail_after_bytes: int | None = None,
        fail_exception: Exception | None = None,
    ):
        self._data = data
        self.status_code = status_code
        self.headers = headers or {}
        self._chunk_size = chunk_size
        self._fail_after_bytes = fail_after_bytes
        self._fail_exception = fail_exception or requests.ConnectionError("Simulated connection drop")

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}", response=self)

    def iter_content(self, chunk_size: int | None = None):
        step = chunk_size or self._chunk_size
        yielded = 0
        for i in range(0, len(self._data), step):
            chunk = self._data[i : i + step]
            if self._fail_after_bytes is not None and (yielded + len(chunk)) > self._fail_after_bytes:
                allowed = self._fail_after_bytes - yielded
                if allowed > 0:
                    yield chunk[:allowed]
                raise self._fail_exception
            yield chunk
            yielded += len(chunk)

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


class RangeServerSimulator:
    """Deterministic mock HTTP server simulating RFC 7233 byte-range serving."""

    def __init__(
        self,
        payload: bytes,
        support_range: bool = True,
        fail_on_attempt: int = 0,
        fail_after_bytes: int | None = None,
    ):
        self.payload = payload
        self.support_range = support_range
        self.fail_on_attempt = fail_on_attempt
        self.fail_after_bytes = fail_after_bytes
        self.requests_log: list[dict] = []
        self._call_count = 0
        self._lock = threading.Lock()

    def __call__(self, url: str, stream: bool = True, timeout=None, headers: dict | None = None):
        headers = headers or {}
        with self._lock:
            self._call_count += 1
            call_idx = self._call_count
            self.requests_log.append({"url": url, "headers": dict(headers)})

        range_header = headers.get("Range")
        if range_header and self.support_range:
            match = re.match(r"bytes=(\d+)-(\d+)", range_header)
            if match:
                start = int(match.group(1))
                end = int(match.group(2))
                slice_data = self.payload[start : end + 1]
                resp_headers = {
                    "content-range": f"bytes {start}-{end}/{len(self.payload)}",
                    "content-length": str(len(slice_data)),
                    "content-type": "video/mp4",
                    "content-disposition": 'attachment; filename="turbo_test.mp4"',
                }
                should_fail = (call_idx == self.fail_on_attempt)
                return MockRangeResponse(
                    slice_data,
                    status_code=206,
                    headers=resp_headers,
                    fail_after_bytes=self.fail_after_bytes if should_fail else None,
                )

        resp_headers = {
            "content-length": str(len(self.payload)),
            "content-type": "video/mp4",
            "content-disposition": 'attachment; filename="turbo_test.mp4"',
        }
        return MockRangeResponse(self.payload, status_code=200, headers=resp_headers)


# ---------------------------------------------------------------------------
# Range Probe Tests
# ---------------------------------------------------------------------------

def test_probe_range_support_returns_true_on_206():
    """Verify probe recognizes HTTP 206 with Content-Range header."""
    def mock_get(url, **_kwargs):
        headers = {"content-range": "bytes 0-0/10485760"}
        return MockRangeResponse(b"\x00", status_code=206, headers=headers)

    supported, total = probe_range_support(mock_get, "https://example.com/video.mp4")
    assert supported is True
    assert total == 10485760


def test_probe_range_support_returns_false_on_200():
    """Verify probe detects server ignoring Range (HTTP 200 OK)."""
    def mock_get(url, **_kwargs):
        headers = {"content-length": "5242880"}
        return MockRangeResponse(b"\x00" * 100, status_code=200, headers=headers)

    supported, total = probe_range_support(mock_get, "https://example.com/video.mp4")
    assert supported is False
    assert total == 5242880


def test_probe_range_support_handles_errors_and_exceptions():
    """Verify probe returns (False, 0) on network failures or 4xx/5xx responses."""
    def mock_failing_get(url, **_kwargs):
        raise requests.ConnectionError("Host unreachable")

    assert probe_range_support(mock_failing_get, "https://example.com/video.mp4") == (False, 0)

    def mock_500_get(url, **_kwargs):
        return MockRangeResponse(b"Error", status_code=500)

    assert probe_range_support(mock_500_get, "https://example.com/video.mp4") == (False, 0)


def test_probe_range_support_handles_malformed_content_range():
    """Verify malformed content-range without slash returns 0 total safely."""
    def mock_malformed_get(url, **_kwargs):
        headers = {"content-range": "bytes 0-0"}
        return MockRangeResponse(b"\x00", status_code=206, headers=headers)

    supported, total = probe_range_support(mock_malformed_get, "https://example.com/video.mp4")
    assert supported is True
    assert total == 0


# ---------------------------------------------------------------------------
# Boundary Partitioning Math Tests
# ---------------------------------------------------------------------------

def test_chunk_boundaries_empty_and_negative():
    """Verify non-positive file sizes return empty chunk lists."""
    assert calculate_chunk_boundaries(0) == []
    assert calculate_chunk_boundaries(-1) == []
    assert calculate_chunk_boundaries(-1024) == []


def test_chunk_boundaries_small_file_single_thread():
    """Verify file smaller than min_chunk_size gets a single segment."""
    size = 1024 * 1024  # 1 MB < 2 MB min_chunk_size
    segments = calculate_chunk_boundaries(size, min_chunk_size=2 * 1024 * 1024)
    assert len(segments) == 1
    assert segments[0].start == 0
    assert segments[0].end == size - 1


def test_chunk_boundaries_exact_partition():
    """Verify power-of-two 8 MB partitions evenly into 4 2 MB segments."""
    size = 8 * 1024 * 1024
    segments = calculate_chunk_boundaries(size, min_chunk_size=2 * 1024 * 1024, max_threads=4)
    assert len(segments) == 4
    for i, seg in enumerate(segments):
        expected_start = i * (2 * 1024 * 1024)
        expected_end = (i + 1) * (2 * 1024 * 1024) - 1
        assert seg.start == expected_start
        assert seg.end == expected_end


@pytest.mark.parametrize("file_size", [
    10_000_019,   # Prime file size
    7_777_777,    # Repdigit odd file size
    2_000_001,    # Slightly over min chunk size
    15_432_987,   # Arbitrary non-aligned size
])
def test_chunk_boundaries_invariants_prime_and_odd_sizes(file_size: int):
    """Verify partitioning invariants: coverage, contiguity, and exact byte sum."""
    segments = calculate_chunk_boundaries(file_size, min_chunk_size=2 * 1024 * 1024, max_threads=4)
    assert len(segments) >= 1
    assert segments[0].start == 0
    assert segments[-1].end == file_size - 1

    # Invariant: contiguous segments without overlaps or holes
    for i in range(len(segments) - 1):
        assert segments[i].end + 1 == segments[i + 1].start

    # Invariant: exact byte sum matches total size
    total_covered = sum(s.end - s.start + 1 for s in segments)
    assert total_covered == file_size


def test_chunk_boundaries_thread_count_capping():
    """Verify chunk boundary generator respects max_threads limits."""
    large_size = 64 * 1024 * 1024  # 64 MB
    segs_2 = calculate_chunk_boundaries(large_size, min_chunk_size=2 * 1024 * 1024, max_threads=2)
    assert len(segs_2) == 2

    segs_8 = calculate_chunk_boundaries(large_size, min_chunk_size=2 * 1024 * 1024, max_threads=8)
    assert len(segs_8) == 8


# ---------------------------------------------------------------------------
# SegmentFileWriter Concurrent Write Tests
# ---------------------------------------------------------------------------

def test_segment_file_writer_concurrent_thread_safety(tmp_path: Path):
    """Verify SegmentFileWriter writes from multiple concurrent threads without corruption."""
    test_file = tmp_path / "concurrent_test.part"
    block_size = 2048
    num_blocks = 16
    total_size = block_size * num_blocks

    test_file.write_bytes(b"\x00" * total_size)
    blocks_data = [bytes([(b_idx * 17 + i) % 256 for i in range(block_size)]) for b_idx in range(num_blocks)]

    def write_worker(writer: SegmentFileWriter, index: int):
        writer.write_at(index * block_size, blocks_data[index])

    with SegmentFileWriter(test_file) as writer:
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            futures = [pool.submit(write_worker, writer, idx) for idx in range(num_blocks)]
            for fut in concurrent.futures.as_completed(futures):
                fut.result()

    written_bytes = test_file.read_bytes()
    assert len(written_bytes) == total_size
    for idx, expected in enumerate(blocks_data):
        actual = written_bytes[idx * block_size : (idx + 1) * block_size]
        assert actual == expected


def test_segment_file_writer_lifecycle(tmp_path: Path):
    """Verify SegmentFileWriter context manager properly flushes and closes handle."""
    target = tmp_path / "lifecycle.part"
    target.write_bytes(b"\x00" * 10)
    with SegmentFileWriter(target) as writer:
        writer.write_at(0, b"01234")
        assert not writer._handle.closed
    assert writer._handle.closed
    assert target.read_bytes() == b"01234\x00\x00\x00\x00\x00"


# ---------------------------------------------------------------------------
# Full Multi-Segment Turbo Download & SHA-256 Byte Integrity
# ---------------------------------------------------------------------------

def test_turbo_download_sha256_byte_integrity(tmp_path: Path):
    """Verify complete multi-segment turbo download byte-for-byte SHA256 integrity."""
    size = 4 * 1024 * 1024 + 321  # ~4.0003 MB with non-aligned tail
    payload = _make_payload(size)
    expected_sha256 = hashlib.sha256(payload).hexdigest()

    server = RangeServerSimulator(payload, support_range=True)
    target_part = tmp_path / "integrity_test.mp4.part"
    cancel = threading.Event()
    progress_updates: list[dict] = []

    success = download_turbo_stream(
        cancel, server, "https://example.com/integrity.mp4", target_part, size, progress_updates.append
    )

    assert success is True
    assert target_part.exists()
    assert target_part.stat().st_size == size

    actual_sha256 = hashlib.sha256(target_part.read_bytes()).hexdigest()
    assert actual_sha256 == expected_sha256

    # Verify progress aggregator fired updates and finished at 100%
    assert len(progress_updates) > 0
    assert progress_updates[-1]["percent"] == 100.0
    assert progress_updates[-1]["status"] == "downloading"


# ---------------------------------------------------------------------------
# Per-Chunk Retry and Resume Offset Tests
# ---------------------------------------------------------------------------

def test_download_segment_retry_resumes_from_downloaded_offset(tmp_path: Path, monkeypatch):
    """Verify worker requests bytes={start + downloaded}-{end} on retry after network drop."""
    target_file = tmp_path / "resume_chunk.part"
    seg_size = 2000
    target_file.write_bytes(b"\x00" * 5000)

    full_chunk_data = bytes([(i % 256) for i in range(seg_size)])
    seg = ChunkSegment(start=1000, end=2999)

    attempts: list[str] = []

    def mock_request_get(url, **kwargs):
        headers = kwargs.get("headers", {})
        rng = headers.get("Range", "")
        attempts.append(rng)

        if len(attempts) == 1:
            # First attempt: drops after 600 bytes
            partial = full_chunk_data[:600]
            resp_headers = {"content-range": f"bytes 1000-1599/{seg_size}"}
            return MockRangeResponse(partial, status_code=206, headers=resp_headers, fail_after_bytes=600)

        # Second attempt: resumes from 1600 to 2999 (1400 bytes)
        remainder = full_chunk_data[600:]
        resp_headers = {"content-range": f"bytes 1600-2999/{seg_size}"}
        return MockRangeResponse(remainder, status_code=206, headers=resp_headers)

    cancel = threading.Event()
    # Accelerate backoff delay during test
    monkeypatch.setattr(cancel, "wait", lambda _timeout=None: False)

    throttle = _ProgressThrottle(seg_size, None)
    with SegmentFileWriter(target_file) as writer:
        _download_segment(cancel, mock_request_get, "https://example.com/test", seg, writer, throttle)

    # First attempt requested full segment; second attempt requested resumed offset
    assert attempts == ["bytes=1000-2999", "bytes=1600-2999"]
    assert seg.downloaded == seg_size

    # Verify written bytes at offset 1000 match full chunk
    actual = target_file.read_bytes()[1000:3000]
    assert actual == full_chunk_data


def test_download_segment_fails_after_exceeding_max_retries(tmp_path: Path, monkeypatch):
    """Verify worker raises exception after 3 failed retries (4 attempts total)."""
    target_file = tmp_path / "fail_chunk.part"
    target_file.write_bytes(b"\x00" * 1000)
    seg = ChunkSegment(start=0, end=999)

    call_count = 0

    def always_failing_get(url, **_kwargs):
        nonlocal call_count
        call_count += 1
        raise requests.ConnectionError("Permanent network failure")

    cancel = threading.Event()
    monkeypatch.setattr(cancel, "wait", lambda _timeout=None: False)

    throttle = _ProgressThrottle(1000, None)
    with SegmentFileWriter(target_file) as writer:
        with pytest.raises(requests.ConnectionError):
            _download_segment(cancel, always_failing_get, "https://example.com/fail", seg, writer, throttle)

    assert call_count == 4  # Initial attempt + 3 retries


# ---------------------------------------------------------------------------
# Cancellation & Cleanup Tests
# ---------------------------------------------------------------------------

def test_turbo_stream_cancelled_before_start(tmp_path: Path):
    """Verify download_turbo_stream aborts immediately if cancel is set before start."""
    target_part = tmp_path / "cancelled_early.part"
    cancel = threading.Event()
    cancel.set()

    server = RangeServerSimulator(_make_payload(4 * 1024 * 1024))
    success = download_turbo_stream(cancel, server, "https://example.com/c.mp4", target_part, 4 * 1024 * 1024)
    assert success is False


def test_native_file_cancellation_cleans_up_part_file(tmp_path: Path):
    """Verify download_file removes .part file upon user cancellation."""
    size = 3 * 1024 * 1024
    payload = _make_payload(size)
    server = RangeServerSimulator(payload, support_range=True)

    cancel = threading.Event()
    cancel.set()  # Cancelled before download commences

    preset = getPreset("video_mp4_720")
    result = download_file(cancel, server, "https://example.com/video.mp4", tmp_path, preset, None)

    assert not result.success
    assert result.state == JobState.CANCELLED
    # Verify no .part file remains in output directory
    assert list(tmp_path.glob("*.part")) == []
    assert list(tmp_path.glob("*.mp4")) == []


# ---------------------------------------------------------------------------
# Fallback to Single-Stream Tests
# ---------------------------------------------------------------------------

def test_native_file_fallback_when_server_does_not_support_ranges(tmp_path: Path):
    """Verify transparent fallback to single-stream download when probe returns HTTP 200."""
    size = 3 * 1024 * 1024
    payload = _make_payload(size)
    expected_sha = hashlib.sha256(payload).hexdigest()

    # Simulator with support_range=False returns HTTP 200 to all requests
    server = RangeServerSimulator(payload, support_range=False)
    cancel = threading.Event()
    preset = getPreset("video_mp4_720")

    result = download_file(cancel, server, "https://example.com/nosupport.mp4", tmp_path, preset, None)

    assert result.success is True
    assert result.state == JobState.COMPLETED
    assert result.file_path is not None
    assert result.file_path.exists()
    assert hashlib.sha256(result.file_path.read_bytes()).hexdigest() == expected_sha
    assert list(tmp_path.glob("*.part")) == []


def test_native_file_fallback_when_probe_raises_exception(tmp_path: Path):
    """Verify fallback to single stream if range probe encounters a network error."""
    size = 3 * 1024 * 1024
    payload = _make_payload(size)
    expected_sha = hashlib.sha256(payload).hexdigest()

    def mock_get(url, stream=True, timeout=None, headers=None):
        headers = headers or {}
        if "Range" in headers:
            # Probe or range request fails
            raise requests.ConnectionError("Range probe refused")
        return MockRangeResponse(
            payload,
            status_code=200,
            headers={
                "content-length": str(len(payload)),
                "content-disposition": 'attachment; filename="fallback.mp4"',
            },
        )

    cancel = threading.Event()
    preset = getPreset("video_mp4_720")
    result = download_file(cancel, mock_get, "https://example.com/fallback.mp4", tmp_path, preset, None)

    assert result.success is True
    assert result.state == JobState.COMPLETED
    assert result.file_path is not None
    assert hashlib.sha256(result.file_path.read_bytes()).hexdigest() == expected_sha


# ---------------------------------------------------------------------------
# Configuration Schema and Boundary Tests
# ---------------------------------------------------------------------------

def test_config_turbo_defaults_and_validation(tmp_path: Path):
    """Verify turbo default configuration and thread count boundary clamping."""
    assert DEFAULT_SETTINGS["turboDownloadEnabled"] is True
    assert DEFAULT_SETTINGS["turboThreadCount"] == 4

    app_data = tmp_path / "cfg"
    app_data.mkdir(parents=True, exist_ok=True)
    cfg = Config(app_data)
    assert cfg.get("turboDownloadEnabled") is True
    assert cfg.get("turboThreadCount") == 4

    # Test thread count clamping upon loading settings (min 1, max 8)
    (app_data / "settings.json").write_text(
        '{"schemaVersion": 2, "turboThreadCount": 16, "turboDownloadEnabled": false}',
        encoding="utf-8",
    )
    loaded_cfg = Config(app_data)
    assert loaded_cfg.get("turboThreadCount") == 8
    assert loaded_cfg.get("turboDownloadEnabled") is False

    # Test clamping minimum bound (<= 0 clamps to 1)
    (app_data / "settings.json").write_text(
        '{"schemaVersion": 2, "turboThreadCount": 0}',
        encoding="utf-8",
    )
    assert Config(app_data).get("turboThreadCount") == 1

    (app_data / "settings.json").write_text(
        '{"schemaVersion": 2, "turboThreadCount": -5}',
        encoding="utf-8",
    )
    assert Config(app_data).get("turboThreadCount") == 1

    # Test valid custom thread count
    (app_data / "settings.json").write_text(
        '{"schemaVersion": 2, "turboThreadCount": 6, "turboDownloadEnabled": true}',
        encoding="utf-8",
    )
    custom_cfg = Config(app_data)
    assert custom_cfg.get("turboThreadCount") == 6
    assert custom_cfg.get("turboDownloadEnabled") is True


# ---------------------------------------------------------------------------
# UI Settings Page Turbo Card Tests (qtbot)
# ---------------------------------------------------------------------------

def test_settings_turbo_card_toggle_and_threads(qtbot, config):
    """Verify Settings page turbo card controls update configuration properly."""
    mock_updater = MagicMock()
    mock_updater.getCurrentVersion.return_value = "2.2.0"
    page = SettingsInterface(config, mock_updater)
    qtbot.addWidget(page)

    assert hasattr(page, "turboToggle")
    assert hasattr(page, "turboThreadsCombo")

    # Initial defaults
    assert page.turboToggle.isChecked() is True
    assert page.turboThreadsCombo.currentData() == 4

    # Toggle off
    page.turboToggle.setChecked(False)
    assert config.get("turboDownloadEnabled") is False

    # Toggle on
    page.turboToggle.setChecked(True)
    assert config.get("turboDownloadEnabled") is True

    # Change thread count combo to 8
    idx_8 = page.turboThreadsCombo.findData(8)
    assert idx_8 >= 0
    page.turboThreadsCombo.setCurrentIndex(idx_8)
    assert config.get("turboThreadCount") == 8


def test_settings_turbo_card_localization(qtbot, config):
    """Verify language switching dynamically updates turbo card labels."""
    mock_updater = MagicMock()
    mock_updater.getCurrentVersion.return_value = "2.2.0"
    page = SettingsInterface(config, mock_updater)
    qtbot.addWidget(page)

    # English
    page.setLanguage("en")
    assert page.turboHeading.text() == "Download Acceleration (Turbo)"
    assert "Multi-segment" in page.lblTurboEn.text()

    # Thai
    page.setLanguage("th")
    assert "Turbo" in page.turboHeading.text()
    assert "เปิดใช้งาน" in page.lblTurboEn.text()
