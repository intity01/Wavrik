"""Regression tests for the network/security review fixes (Cobalt, turbo, updater, parser, ...)."""

from __future__ import annotations

import hashlib
import os
import subprocess
import threading
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
import requests

from src.core.parser import normalizeUrl
from src.core.update_models import ReleaseAsset, UpdateInfo
from src.core.updater import UpdateError, UpdateManager
from src.domain.cobalt_client import CobaltClient, CobaltError
from src.domain.cobalt_downloader import CobaltDownloader
from src.domain.cobalt_models import CobaltRequest, CobaltResponse, CobaltStatus
from src.domain.cobalt_security import safe_media_filename, validate_instance_url
from src.domain.cobalt_stream import write_stream
from src.domain.models import JobState
from src.domain.native_file import download_file
from src.domain.presets import getPreset
from src.domain.turbo_segment import ChunkSegment, ProgressThrottle, RangeNotHonored, SegmentFileWriter
from src.domain.turbo_segment import download_segment
from src.domain.turbo_settings import TurboRequests, TurboSettings
from src.domain.turbo_stream import download_turbo_stream
from src.services import platform_actions
from src.services.audio_batch import BatchJobConfig, process_batch_file
from src.services.audio_stems import _read_pcm16, _write_pcm16
from src.services.audio_stems_4stem import _extract_4stem_dsp
from src.services.audio_stems_dsp import run_dsp_filter


# ---------------------------------------------------------------------------
# Shared fakes
# ---------------------------------------------------------------------------

class FakeStream:
    """Context-managed streaming response."""

    def __init__(self, body=b"", status=200, headers=None, chunk=64 * 1024, on_chunk=None, drop_after=None):
        self.status_code, self.headers, self._body = status, headers or {}, body
        self._chunk, self._on_chunk, self._drop_after = chunk, on_chunk, drop_after
        self.url = ""

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}", response=self)

    def iter_content(self, size=None):
        step = min(size or self._chunk, self._chunk)
        for i in range(0, len(self._body), step):
            if self._drop_after is not None and i >= self._drop_after:
                raise requests.ConnectionError("dropped")
            if self._on_chunk:
                self._on_chunk(i)
            yield self._body[i:i + step]

    def close(self):
        return None

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


def _payload(size: int) -> bytes:
    block = bytes(range(256)) * 64
    return (block * (size // len(block) + 1))[:size]


# ---------------------------------------------------------------------------
# A. Cobalt instance URL, returned URL, filename and size cap
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("url", [
    "https://api.cobalt.tools/", "https://cobalt.example.com:8443/", "http://localhost:9000/",
    "http://127.0.0.1:9000", "http://[::1]:9000/",
])
def test_instance_url_accepts_https_and_loopback_http(url):
    assert validate_instance_url(url) == url


@pytest.mark.parametrize("url", [
    "", "cobalt", "http://cobalt.example.com/", "ftp://cobalt.example.com/", "file:///etc/passwd",
    "https://user:pw@cobalt.example.com/", "https://@cobalt.example.com/", "http://user@localhost:9000/",
    "https://cobalt.example.com:notaport/",
])
def test_instance_url_rejects_insecure_or_credentialed_urls(url):
    assert validate_instance_url(url) == ""


def test_client_refuses_insecure_instance_and_never_sends_key():
    client = CobaltClient("http://cobalt.example.com/", api_key="secret")
    assert "Authorization" not in client._headers()
    assert client.is_alive() is False
    with patch("requests.post") as post, pytest.raises(CobaltError, match="https"):
        client.resolve_stream(CobaltRequest(url="https://example.com/v"))
    post.assert_not_called()


def test_client_sends_key_over_https_and_loopback_only():
    assert CobaltClient("https://c.example.com/", api_key="k")._headers()["Authorization"] == "Api-Key k"
    assert CobaltClient("http://localhost:9000/", api_key="k")._headers()["Authorization"] == "Api-Key k"


def _resolved(url: str, filename: str = "clip.mp4") -> MagicMock:
    client = MagicMock(spec=CobaltClient)
    client.resolve_stream.return_value = CobaltResponse(CobaltStatus.TUNNEL, url=url, filename=filename)
    return client


@pytest.mark.parametrize("media_url", [
    "http://127.0.0.1:8080/x.mp4", "https://169.254.169.254/latest/meta-data", "https://10.0.0.5/a.mp4",
    "https://[::1]/a.mp4", "https://localhost/a.mp4", "https://2130706433/a.mp4",
    "https://user:pw@cdn.example.com/a.mp4", "file:///C:/Windows/win.ini", "ftp://cdn.example.com/a.mp4",
])
def test_cobalt_rejects_unsafe_returned_media_urls(tmp_path: Path, media_url):
    downloader = CobaltDownloader(threading.Event(), _resolved(media_url))
    with patch("requests.get") as get:
        result = downloader.download("https://example.com/v", tmp_path, getPreset("video_mp4_1080"))
    assert result.state == JobState.FAILED
    assert "unsafe media URL" in result.error
    get.assert_not_called()


def test_cobalt_allows_private_media_when_instance_is_loopback(tmp_path: Path):
    client = CobaltClient("http://localhost:9000/")
    resolved = CobaltResponse(CobaltStatus.TUNNEL, url="http://127.0.0.1:9000/tunnel/1", filename="a.mp4")
    body = b"x" * 100
    stream = FakeStream(body, headers={"content-length": "100"})
    with patch.object(client, "resolve_stream", return_value=resolved), patch("requests.get", return_value=stream):
        result = CobaltDownloader(threading.Event(), client).download("https://e.com/v", tmp_path, getPreset("video_mp4_1080"))
    assert result.success and result.file_path.read_bytes() == body


def test_cobalt_redirect_hop_to_private_address_is_blocked(tmp_path: Path):
    hop = FakeStream(status=302, headers={"location": "http://192.168.1.10/secret.mp4"})
    downloader = CobaltDownloader(threading.Event(), _resolved("https://cdn.example.com/a.mp4"))
    with patch("requests.get", return_value=hop) as get:
        result = downloader.download("https://e.com/v", tmp_path, getPreset("video_mp4_1080"))
    assert result.state == JobState.FAILED
    assert get.call_count == 1
    assert get.call_args.kwargs["allow_redirects"] is False


@pytest.mark.parametrize(("raw", "expected"), [
    ("song.mp3", "song.mp3"), ("../../evil.exe", "evil.mp4"), ("..\\..\\run.bat", "run.mp4"),
    ("a/b/c.flac", "c.flac"), ("..", "download.mp4"), ("", "download.mp4"),
    ("CON.mp3", "download.mp3"), ("nul", "download.mp4"), ("bad;name\".mkv", "bad_name_.mkv"),
])
def test_safe_media_filename(raw, expected):
    assert safe_media_filename(raw, "mp4") == expected


def test_cobalt_download_never_uses_server_extension_or_path(tmp_path: Path):
    stream = FakeStream(b"data", headers={"content-length": "4"})
    downloader = CobaltDownloader(threading.Event(), _resolved("https://cdn.example.com/t", "..\\..\\evil.exe"))
    with patch("requests.get", return_value=stream):
        result = downloader.download("https://e.com/v", tmp_path / "out", getPreset("video_mp4_1080"))
    assert result.success
    assert result.file_path.parent == tmp_path / "out"
    assert result.file_path.name == "evil.mp4"


def test_cobalt_write_stream_enforces_byte_cap(tmp_path: Path):
    target = tmp_path / "f.part"
    with pytest.raises(CobaltError, match="10 GB"):
        write_stream(threading.Event(), FakeStream(b"x" * 3000, chunk=1000), target, 0, None, max_bytes=2000)
    with pytest.raises(CobaltError, match="10 GB"):
        CobaltDownloader(threading.Event())._write_stream(FakeStream(b"x"), target, 5000, None, max_bytes=2000)


def test_cobalt_download_rejects_declared_oversize_and_cleans_part(tmp_path: Path):
    stream = FakeStream(b"x", headers={"content-length": str(20 * 1024**3)})
    downloader = CobaltDownloader(threading.Event(), _resolved("https://cdn.example.com/big.mp4"))
    with patch("requests.get", return_value=stream):
        result = downloader.download("https://e.com/v", tmp_path, getPreset("video_mp4_1080"))
    assert result.state == JobState.FAILED
    assert list(tmp_path.glob("*")) == []


def test_settings_only_persist_valid_cobalt_url(qtbot, config):
    from src.ui.pages.settings_page import SettingsInterface

    updater = MagicMock()
    updater.getCurrentVersion.return_value = "2.2.0"
    page = SettingsInterface(config, updater)
    qtbot.addWidget(page)
    original = config.get("cobaltUrl")
    page.cobaltUrlInput.setText("http://evil.example.com/")
    assert config.get("cobaltUrl") == original
    assert not page.cobaltUrlError.isHidden()
    page.cobaltUrlInput.setText("https://user:pw@cobalt.example.com/")
    assert config.get("cobaltUrl") == original
    page.cobaltUrlInput.setText("https://cobalt.example.com/")
    assert config.get("cobaltUrl") == "https://cobalt.example.com/"
    assert page.cobaltUrlError.isHidden()


# ---------------------------------------------------------------------------
# B / C. Turbo settings wiring and segment hardening
# ---------------------------------------------------------------------------

class RangeServer:
    """Range-capable fake. `mode` selects misbehaviour for segment requests."""

    def __init__(self, payload: bytes, mode: str = "ok"):
        self.payload, self.mode = payload, mode
        self.log: list[str] = []
        self._lock = threading.Lock()

    def __call__(self, url, stream=True, timeout=None, headers=None):
        rng = (headers or {}).get("Range", "")
        with self._lock:
            self.log.append(rng)
        if not rng:
            return FakeStream(self.payload, headers={"content-length": str(len(self.payload))})
        start, end = (int(v) for v in rng.removeprefix("bytes=").split("-"))
        if rng == "bytes=0-0" or self.mode == "ok":
            return self._partial(start, end)
        return FakeStream(self.payload, headers={"content-length": str(len(self.payload))})

    def _partial(self, start: int, end: int) -> FakeStream:
        body = self.payload[start:end + 1]
        return FakeStream(body, 206, {"content-range": f"bytes {start}-{end}/{len(self.payload)}"})

    def segment_requests(self) -> list[str]:
        return [r for r in self.log if r and r != "bytes=0-0"]


def test_turbo_settings_from_config_clamps_and_defaults():
    assert TurboSettings.from_config(None) == TurboSettings(True, 4)
    assert TurboSettings.from_config({"turboDownloadEnabled": False, "turboThreadCount": 99}) == TurboSettings(False, 8)
    assert TurboSettings.from_config({"turboThreadCount": 0}).threads == 1
    assert TurboSettings.from_config({"turboThreadCount": "junk"}).threads == 4


def test_turbo_toggle_off_never_issues_range_requests(tmp_path: Path):
    server = RangeServer(_payload(3 * 1024 * 1024))
    transport = TurboRequests(server, TurboSettings(enabled=False))
    result = download_file(threading.Event(), transport, "https://e.com/a.mp4", tmp_path, getPreset("video_mp4_720"), None)
    assert result.success
    assert result.file_path.read_bytes() == server.payload
    assert server.segment_requests() == [] and "bytes=0-0" not in server.log


@pytest.mark.parametrize("threads", [1, 2, 8])
def test_turbo_thread_count_is_honoured(tmp_path: Path, threads: int):
    server = RangeServer(_payload(17 * 1024 * 1024))
    transport = TurboRequests(server, TurboSettings(True, threads))
    part = tmp_path / "f.part"
    assert download_turbo_stream(threading.Event(), transport, "https://e.com/a", part, len(server.payload))
    assert len(server.segment_requests()) == threads
    assert hashlib.sha256(part.read_bytes()).digest() == hashlib.sha256(server.payload).digest()


def _segment_fixture(tmp_path: Path, size: int = 5000):
    target = tmp_path / "seg.part"
    target.write_bytes(b"\x00" * size)
    return target


def test_segment_requires_206_and_never_writes_outside_segment(tmp_path: Path):
    target = _segment_fixture(tmp_path)
    seg = ChunkSegment(1000, 1999)
    ignoring_range = lambda url, **_kw: FakeStream(b"\xff" * 5000, 200)  # noqa: E731
    with SegmentFileWriter(target) as writer, pytest.raises(RangeNotHonored):
        download_segment(threading.Event(), ignoring_range, "https://e.com/a", seg, writer, ProgressThrottle(1000, None))
    assert target.read_bytes() == b"\x00" * 5000


def test_segment_rejects_mismatched_content_range(tmp_path: Path):
    target = _segment_fixture(tmp_path)
    wrong = lambda url, **_kw: FakeStream(b"\xff" * 1000, 206, {"content-range": "bytes 0-999/5000"})  # noqa: E731
    with SegmentFileWriter(target) as writer, pytest.raises(RangeNotHonored):
        download_segment(threading.Event(), wrong, "u", ChunkSegment(1000, 1999), writer, ProgressThrottle(1000, None))
    assert target.read_bytes() == b"\x00" * 5000


def test_segment_caps_bytes_written_to_segment_length(tmp_path: Path):
    target = _segment_fixture(tmp_path)
    greedy = lambda url, **_kw: FakeStream(b"\xaa" * 4000, 206, {"content-range": "bytes 1000-1999/5000"})  # noqa: E731
    seg = ChunkSegment(1000, 1999)
    with SegmentFileWriter(target) as writer:
        download_segment(threading.Event(), greedy, "u", seg, writer, ProgressThrottle(1000, None))
    data = target.read_bytes()
    assert seg.downloaded == 1000
    assert data[:1000] == b"\x00" * 1000 and data[1000:2000] == b"\xaa" * 1000 and data[2000:] == b"\x00" * 3000


def test_segment_empty_body_backs_off_and_gives_up(tmp_path: Path, monkeypatch):
    target = _segment_fixture(tmp_path)
    calls, waits = [], []
    cancel = threading.Event()
    monkeypatch.setattr(cancel, "wait", lambda timeout=None: waits.append(timeout) or False)

    def empty(url, **_kw):
        calls.append(url)
        return FakeStream(b"", 206, {"content-range": "bytes 0-999/5000"})

    with SegmentFileWriter(target) as writer, pytest.raises(RuntimeError, match="no data"):
        download_segment(cancel, empty, "u", ChunkSegment(0, 999), writer, ProgressThrottle(1000, None))
    assert len(calls) == 4
    assert len(waits) == 3 and all(w and w > 0 for w in waits)


def test_segment_retry_budget_resets_after_progress(tmp_path: Path, monkeypatch):
    size = 640 * 1024
    target = _segment_fixture(tmp_path, size)
    data, attempts = _payload(size), []
    cancel = threading.Event()
    monkeypatch.setattr(cancel, "wait", lambda _timeout=None: False)

    def flaky(url, headers=None, **_kw):
        start = int(headers["Range"].removeprefix("bytes=").split("-")[0])
        attempts.append(start)
        return FakeStream(data[start:], 206, {"content-range": f"bytes {start}-{size - 1}/{size}"}, drop_after=64 * 1024)

    seg = ChunkSegment(0, size - 1)
    with SegmentFileWriter(target) as writer:
        download_segment(cancel, flaky, "u", seg, writer, ProgressThrottle(size, None))
    assert len(attempts) == 10  # far more than 4 attempts, each making progress
    assert target.read_bytes() == data


def test_turbo_first_failure_stops_other_segments(tmp_path: Path, monkeypatch):
    monkeypatch.setattr("src.domain.turbo_segment.MAX_RETRIES", 0)
    size = 8 * 1024 * 1024
    payload, served = _payload(size), []
    lock = threading.Lock()

    def request_get(url, headers=None, **_kw):
        start = int(headers["Range"].removeprefix("bytes=").split("-")[0])
        if start == 0:
            raise requests.ConnectionError("first segment is broken")

        def tick(_offset):
            with lock:
                served.append(64 * 1024)
            threading.Event().wait(0.02)

        end = min(size - 1, start + 2 * 1024 * 1024 - 1)
        return FakeStream(payload[start:end + 1], 206, {"content-range": f"bytes {start}-{end}/{size}"}, on_chunk=tick)

    with pytest.raises(requests.ConnectionError):
        download_turbo_stream(threading.Event(), request_get, "u", tmp_path / "f.part", size)
    other_segments_total = 3 * 2 * 1024 * 1024
    assert sum(served) < other_segments_total // 2


def test_native_file_falls_back_when_segments_ignore_range(tmp_path: Path):
    server = RangeServer(_payload(3 * 1024 * 1024), mode="ignores_segment_range")
    result = download_file(threading.Event(), server, "https://e.com/a.mp4", tmp_path, getPreset("video_mp4_720"), None)
    assert result.success
    assert result.file_path.read_bytes() == server.payload
    assert list(tmp_path.glob("*.part")) == []


# ---------------------------------------------------------------------------
# D. Updater
# ---------------------------------------------------------------------------

ASSET_URL = "https://github.com/owner/repo/releases/download/v2.1.0/app.exe"
CDN_URL = "https://release-assets.githubusercontent.com/package"


class FakeSession:
    def __init__(self, *responses):
        self.responses, self.calls = list(responses), []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return self.responses.pop(0)


def _asset_info(content: bytes, name: str = "app.exe", size: int | None = None) -> UpdateInfo:
    asset = ReleaseAsset(name, ASSET_URL, len(content) if size is None else size, hashlib.sha256(content).hexdigest())
    return UpdateInfo("2.1.0", "", "https://github.com/owner/repo", True, asset)


def _redirect(location: str) -> FakeStream:
    return FakeStream(status=302, headers={"location": location})


def test_updater_validates_every_redirect_hop_before_requesting(tmp_path: Path):
    session = FakeSession(_redirect("https://evil.example.com/pkg"))
    manager = UpdateManager("2.0.0", "owner/repo", session=session)
    with pytest.raises(UpdateError, match="unexpected host"):
        manager.downloadVerified(_asset_info(b"x"), tmp_path)
    assert len(session.calls) == 1
    assert session.calls[0][1]["allow_redirects"] is False
    assert list(tmp_path.iterdir()) == []


def test_updater_rejects_non_https_redirect_even_for_allowed_host(tmp_path: Path):
    session = FakeSession(_redirect("http://release-assets.githubusercontent.com/pkg"))
    with pytest.raises(UpdateError):
        UpdateManager("2.0.0", "owner/repo", session=session).downloadVerified(_asset_info(b"x"), tmp_path)
    assert len(session.calls) == 1


def test_updater_follows_allowed_redirect_and_verifies_digest(tmp_path: Path):
    content = b"trusted package"
    final = FakeStream(content, headers={"content-length": str(len(content))})
    session = FakeSession(_redirect(CDN_URL), final)
    target = UpdateManager("2.0.0", "owner/repo", session=session).downloadVerified(_asset_info(content), tmp_path)
    assert target.read_bytes() == content
    assert [call[0] for call in session.calls] == [ASSET_URL, CDN_URL]


def test_updater_stops_after_too_many_redirects(tmp_path: Path):
    session = FakeSession(*[_redirect(CDN_URL) for _ in range(20)])
    with pytest.raises(UpdateError, match="too many"):
        UpdateManager("2.0.0", "owner/repo", session=session).downloadVerified(_asset_info(b"x"), tmp_path)


def test_updater_bad_content_length_raises_update_error(tmp_path: Path):
    session = FakeSession(FakeStream(b"x", headers={"content-length": "not-a-number"}))
    with pytest.raises(UpdateError):
        UpdateManager("2.0.0", "owner/repo", session=session).downloadVerified(_asset_info(b"x"), tmp_path)


def _release_with_size(size):
    digest = hashlib.sha256(b"x").hexdigest()
    return {
        "tag_name": "v9.0.0", "immutable": True, "html_url": "https://github.com/owner/repo",
        "assets": [{"name": "Setup.exe", "browser_download_url": ASSET_URL, "size": size,
                    "digest": f"sha256:{digest}", "state": "uploaded"}],
    }


def test_updater_null_or_bad_asset_size_is_handled():
    manager = UpdateManager("2.0.0", "owner/repo", session=FakeSession(FakeStream()))
    assert manager._select_asset(_release_with_size(None)["assets"]).size == 0
    with pytest.raises(UpdateError):
        manager._select_asset(_release_with_size("big")["assets"])


@pytest.mark.parametrize(("name", "expected"), [
    ("../../evil.exe", "evil.exe"), ("..", "update-package.bin"), ("", "update-package.bin"),
    ("CON.exe", "update-package.bin"), ("C:\\x\\setup.msi", "setup.msi"),
])
def test_updater_sanitizes_asset_name(tmp_path: Path, name, expected):
    content = b"pkg"
    session = FakeSession(FakeStream(content, headers={"content-length": "3"}))
    target = UpdateManager("2.0.0", "owner/repo", session=session).downloadVerified(_asset_info(content, name), tmp_path)
    assert target.parent == tmp_path and target.name == expected


def test_updater_part_file_names_are_unique_per_download(tmp_path: Path):
    content, seen = b"pkg", []

    def spy(_offset=0):
        seen.append(sorted(p.name for p in tmp_path.glob("*.part")))

    def stream():
        return FakeStream(content, headers={"content-length": "3"}, on_chunk=spy)

    manager = UpdateManager("2.0.0", "owner/repo", session=FakeSession(stream(), stream()))
    manager.downloadVerified(_asset_info(content), tmp_path)
    manager.downloadVerified(_asset_info(content), tmp_path)
    assert len(seen) == 2 and all(len(names) == 1 for names in seen)
    assert seen[0] != seen[1]
    assert "app.exe.part" not in seen[0] + seen[1]


# ---------------------------------------------------------------------------
# E. Parser
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("url", ["http://[::1]:8080/", "https://[2001:db8::1]/watch?v=1", "http://[::1]/"])
def test_normalize_keeps_ipv6_brackets(url):
    assert normalizeUrl(url) == url


@pytest.mark.parametrize("url", [
    "https://cdn.example.com/f.mp4?flag&sig=a%2Bb%3D&si=keep&pp=keep",
    "https://example.com/x?flag", "https://example.com/x?a=1&a=2&b=%20x",
])
def test_normalize_keeps_raw_query_when_nothing_is_tracking(url):
    assert normalizeUrl(url) == url


def test_normalize_removes_only_tracking_params_and_keeps_rest_raw():
    assert normalizeUrl("https://example.com/a?b=%20x&utm_source=q&flag") == "https://example.com/a?b=%20x&flag"
    assert normalizeUrl("https://youtu.be/abc?si=xyz&t=5") == "https://youtu.be/abc?t=5"
    assert normalizeUrl("https://example.com/a?fbclid=1") == "https://example.com/a"


@pytest.mark.parametrize("url", ["file:///etc/passwd", "ftp://example.com/a", "https://u:p@example.com/a", "javascript:alert(1)"])
def test_normalize_still_rejects_bad_schemes_and_credentials(url):
    assert normalizeUrl(url) == ""


# ---------------------------------------------------------------------------
# F. Open-file allow-list
# ---------------------------------------------------------------------------

@pytest.fixture
def launched(monkeypatch):
    calls = []
    monkeypatch.setattr(os, "startfile", lambda p: calls.append(p), raising=False)
    monkeypatch.setattr(subprocess, "Popen", lambda cmd, *a, **k: calls.append(cmd))
    return calls


@pytest.mark.parametrize("ext", [".url", ".py", ".pyw", ".appx", ".msix", ".chm", ".ws", ".wsc", ".scf", ".docm", ".xyz", ".svg", ""])
def test_open_path_refuses_files_outside_media_allow_list(tmp_path: Path, launched, ext):
    target = tmp_path / f"file{ext}"
    target.write_text("x", encoding="utf-8")
    assert platform_actions.open_path(target) is False
    assert launched == []


@pytest.mark.parametrize("ext", [".mp3", ".MP4", ".webm", ".flac", ".png", ".srt", ".lrc", ".txt"])
def test_open_path_opens_known_media_and_text_files(tmp_path: Path, launched, ext):
    target = tmp_path / f"file{ext}"
    target.write_bytes(b"x")
    assert platform_actions.open_path(target) is True
    assert len(launched) == 1


def test_open_path_still_opens_folders(tmp_path: Path, launched):
    assert platform_actions.open_path(tmp_path) is True
    assert len(launched) == 1


# ---------------------------------------------------------------------------
# G. DSP stem fallback
# ---------------------------------------------------------------------------

def _failing_ffmpeg(cmd, **_kwargs):
    Path(cmd[-1]).write_bytes(b"RIFF-truncated")
    return subprocess.CompletedProcess(cmd, 1, "", "boom")


def test_run_dsp_filter_discards_partial_output_on_nonzero_exit(tmp_path: Path):
    dst = tmp_path / "out.wav"
    with patch("src.services.audio_stems_dsp.run_cancellable_process", side_effect=_failing_ffmpeg):
        assert run_dsp_filter("ffmpeg", tmp_path / "in.wav", dst, "lowpass=f=200", (44100, 2)) is False
    assert not dst.exists()


def test_run_dsp_filter_accepts_clean_exit(tmp_path: Path):
    def ok(cmd, **_kwargs):
        Path(cmd[-1]).write_bytes(b"RIFF....data")
        return subprocess.CompletedProcess(cmd, 0, "", "")

    dst = tmp_path / "out.wav"
    with patch("src.services.audio_stems_dsp.run_cancellable_process", side_effect=ok):
        assert run_dsp_filter("ffmpeg", tmp_path / "in.wav", dst, "lowpass=f=200", (44100, 2)) is True
    assert dst.is_file()


def test_failed_ffmpeg_falls_through_to_numpy_fallback(tmp_path: Path):
    master = tmp_path / "master.wav"
    pcm = (np.arange(4000) % 2000 - 1000).astype(np.int16)
    _write_pcm16(master, pcm, 44100, 2)
    with patch("src.services.audio_stems_4stem._ffmpeg_exe", return_value="ffmpeg"), \
            patch("src.services.audio_stems_dsp.run_cancellable_process", side_effect=_failing_ffmpeg):
        voc, drum, bass, _other = _extract_4stem_dsp(master, tmp_path / "stage", (44100, 2))
    for stem, gain in ((voc, 0.35), (drum, 0.25), (bass, 0.20)):
        data = _read_pcm16(stem)[0]
        assert np.array_equal(data, (pcm.astype(np.float32) * gain).astype(np.int16))


# ---------------------------------------------------------------------------
# H. Batch export naming
# ---------------------------------------------------------------------------

def _batch_names(tmp_path: Path, known_key: str, ratio: float, known_bpm: float = 0.0) -> str:
    tmp_path.mkdir(parents=True, exist_ok=True)
    source = tmp_path / "track.wav"
    source.write_bytes(b"x")
    cfg = BatchJobConfig(semitones=-2, tempo_ratio=ratio, output_dir=tmp_path / "out")

    def fake_render(_src, dest, _semitones, _opts, cancel_check=None):
        Path(dest).write_bytes(b"x")
        return Path(dest)

    with patch("src.services.audio_batch.render_audio_clip", side_effect=fake_render):
        return process_batch_file(source, cfg, known_key, known_bpm=known_bpm).name


@pytest.mark.parametrize("key", ["", "unknown", "Unknown key", "--", "None"])
def test_batch_export_is_untagged_when_key_is_unknown(tmp_path: Path, key):
    name = _batch_names(tmp_path, key, ratio=1.1)
    assert name == "track_[-2st].wav"
    assert "BPM" not in name and "Key" not in name


def test_batch_export_tags_only_known_key_and_bpm(tmp_path: Path):
    name = _batch_names(tmp_path, "C major", ratio=1.0)
    assert name.startswith("track_[Key_") and "BPM" not in name
    assert "110BPM" in _batch_names(tmp_path / "b", "C major", ratio=1.1, known_bpm=100.0)
    assert "120BPM" not in _batch_names(tmp_path / "c", "C major", ratio=1.0)
