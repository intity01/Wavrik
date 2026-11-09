"""Tests for Cobalt Engine: Models, Client, Downloader, and Hybrid Dispatch."""

from __future__ import annotations

import threading
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import requests

from src.core.config import Config
from src.domain.cobalt_client import CobaltClient, CobaltError, preset_to_cobalt_request
from src.domain.cobalt_downloader import CobaltDownloader
from src.domain.cobalt_models import CobaltPickerItem, CobaltRequest, CobaltResponse, CobaltStatus
from src.domain.media_downloader import MediaDownloader
from src.domain.models import DownloadResult, JobState
from src.domain.presets import getPreset
from src.ui.components.download_options_view import engine_combo


class MockResponse:
    """Mock context-managed requests.Response for offline deterministic testing."""

    def __init__(self, status_code: int = 200, json_data: dict | None = None, content: bytes = b"mock_media_data", headers: dict | None = None):
        self.status_code = status_code
        self._json_data = json_data or {}
        self._content = content
        self.headers = headers or {"content-length": str(len(content)), "content-type": "video/mp4"}

    def json(self):
        return self._json_data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}", response=self)

    def iter_content(self, chunk_size: int = 8192):
        yield self._content

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return False


def test_cobalt_models():
    assert CobaltStatus.REDIRECT == "redirect"
    assert CobaltStatus.TUNNEL == "tunnel"
    assert CobaltStatus.PICKER == "picker"
    assert CobaltStatus.ERROR == "error"

    req = CobaltRequest(url="https://youtube.com/watch?v=123", videoQuality="1080", downloadMode="auto")
    data = req.to_dict()
    assert data["url"] == "https://youtube.com/watch?v=123"
    assert data["videoQuality"] == "1080"
    assert data["downloadMode"] == "auto"

    item = CobaltPickerItem(type="video", url="https://cdn.example.com/item.mp4", thumb="https://cdn.example.com/thumb.jpg")
    assert item.type == "video"
    assert item.url == "https://cdn.example.com/item.mp4"

    # Test from_dict on tunnel response
    tunnel_resp = CobaltResponse.from_dict({
        "status": "tunnel",
        "url": "https://api.cobalt.tools/tunnel/abc",
        "filename": "track.mp3",
    })
    assert tunnel_resp.status == CobaltStatus.TUNNEL
    assert tunnel_resp.url == "https://api.cobalt.tools/tunnel/abc"
    assert tunnel_resp.filename == "track.mp3"

    # Test from_dict on picker response
    picker_resp = CobaltResponse.from_dict({
        "status": "picker",
        "audio": "https://api.cobalt.tools/audio.mp3",
        "picker": [{"type": "video", "url": "https://v.mp4", "thumb": "https://t.jpg"}],
    })
    assert picker_resp.status == CobaltStatus.PICKER
    assert len(picker_resp.picker) == 1
    assert picker_resp.picker[0].url == "https://v.mp4"

    # Test from_dict on error response
    err_resp = CobaltResponse.from_dict({
        "status": "error",
        "error": {"code": "error.api.fetch.fail", "context": {"service": "youtube"}},
    })
    assert err_resp.status == CobaltStatus.ERROR
    assert err_resp.error_code == "error.api.fetch.fail"


def test_preset_to_cobalt_request():
    audio_preset = getPreset("audio_mp3_320")
    req_audio = preset_to_cobalt_request("https://youtube.com/watch?v=1", audio_preset)
    assert req_audio.downloadMode == "audio"
    assert req_audio.audioFormat == "mp3"
    assert req_audio.audioBitrate == "320"

    video_preset = getPreset("video_mp4_1080")
    req_video = preset_to_cobalt_request("https://youtube.com/watch?v=2", video_preset)
    assert req_video.downloadMode == "auto"
    assert req_video.videoQuality == "1080"


def test_cobalt_client_is_alive_and_resolve():
    client = CobaltClient("https://api.cobalt.tools", api_key="test-key")
    assert client.base_url == "https://api.cobalt.tools/"
    assert "Api-Key test-key" in client._headers()["Authorization"]

    # is_alive True
    with patch("requests.get", return_value=MockResponse(200, {"cobalt": {"version": "10.4.0"}})):
        assert client.is_alive() is True

    # is_alive False
    with patch("requests.get", side_effect=requests.RequestException("connection refused")):
        assert client.is_alive() is False

    # resolve_stream success
    req = CobaltRequest(url="https://youtube.com/watch?v=abc")
    with patch("requests.post", return_value=MockResponse(200, {"status": "redirect", "url": "https://direct.cdn/video.mp4"})):
        res = client.resolve_stream(req)
        assert res.status == CobaltStatus.REDIRECT
        assert res.url == "https://direct.cdn/video.mp4"

    # resolve_stream 400 error
    with patch("requests.post", return_value=MockResponse(400, {"error": {"code": "unsupported_url"}})):
        with pytest.raises(CobaltError, match="Cobalt API rejected request"):
            client.resolve_stream(req)

    # resolve_stream 429 error
    with patch("requests.post", return_value=MockResponse(429, {})):
        with pytest.raises(CobaltError, match="rate limit reached"):
            client.resolve_stream(req)


def test_cobalt_downloader_success(tmp_path: Path):
    cancel = threading.Event()
    client = MagicMock(spec=CobaltClient)
    client.resolve_stream.return_value = CobaltResponse(
        status=CobaltStatus.TUNNEL,
        url="https://api.cobalt.tools/tunnel/file123",
        filename="song.mp3",
    )
    downloader = CobaltDownloader(cancel, client)
    preset = getPreset("audio_mp3_320")

    mock_resp = MockResponse(200, content=b"12345678" * 1024, headers={"content-length": "8192"})
    progress_calls = []

    with patch("requests.get", return_value=mock_resp):
        res = downloader.download("https://example.com/song", tmp_path, preset, progress=lambda p: progress_calls.append(p))

    assert res.success is True
    assert res.state == JobState.COMPLETED
    assert res.engine == "cobalt"
    assert res.file_path is not None
    assert res.file_path.is_file()
    assert res.file_path.name.endswith(".mp3")
    assert len(progress_calls) > 0


def test_cobalt_downloader_cancellation(tmp_path: Path):
    cancel = threading.Event()
    client = MagicMock(spec=CobaltClient)
    client.resolve_stream.return_value = CobaltResponse(
        status=CobaltStatus.TUNNEL,
        url="https://api.cobalt.tools/tunnel/file123",
        filename="video.mp4",
    )
    downloader = CobaltDownloader(cancel, client)
    preset = getPreset("video_mp4_1080")

    # Cancel before download starts
    cancel.set()
    res = downloader.download("https://example.com/video", tmp_path, preset)
    assert res.success is False
    assert res.state == JobState.CANCELLED

    # Cancel during stream
    cancel.clear()
    class SlowMockResponse(MockResponse):
        def iter_content(self, chunk_size: int = 8192):
            yield b"chunk1"
            cancel.set()
            yield b"chunk2"

    with patch("requests.get", return_value=SlowMockResponse(200)):
        res_during = downloader.download("https://example.com/video", tmp_path, preset)
        assert res_during.success is False
        assert res_during.state == JobState.CANCELLED


def test_media_downloader_cobalt_hybrid(tmp_path: Path):
    cfg = MagicMock(spec=Config)
    cfg.get.side_effect = lambda k, d=None: {
        "cobaltEnabled": True,
        "cobaltUrl": "https://api.cobalt.tools/",
        "cobaltApiKey": "",
        "downloadPath": str(tmp_path),
    }.get(k, d)

    md = MediaDownloader(logger=None, config=cfg)
    preset = getPreset("video_mp4_1080")

    # 1. When engine is "cobalt" and Cobalt succeeds
    target_file = tmp_path / "video.mp4"
    target_file.write_bytes(b"data")
    mock_cobalt_result = DownloadResult(True, JobState.COMPLETED, file_path=target_file, engine="cobalt")

    with patch("src.domain.media_downloader.CobaltDownloader.download", return_value=mock_cobalt_result):
        res = md.download("https://youtube.com/watch?v=good", tmp_path, preset, engine="cobalt")
        assert res.success is True
        assert res.engine == "cobalt"
        assert md.lastDownloadedFile == target_file

    # 2. When engine is "auto" and Cobalt fails, fall back to yt-dlp
    mock_failed_result = DownloadResult(False, JobState.FAILED, error="Cobalt timed out", engine="cobalt")
    mock_ytdlp_result = DownloadResult(True, JobState.COMPLETED, file_path=target_file, engine="yt-dlp")

    with patch("src.domain.media_downloader.CobaltDownloader.download", return_value=mock_failed_result), \
         patch.object(md, "_download_ytdlp", return_value=mock_ytdlp_result):
        res_fallback = md.download("https://youtube.com/watch?v=fallback", tmp_path, preset, engine="auto")
        assert res_fallback.success is True
        assert res_fallback.engine == "yt-dlp"


def test_ui_and_config_cobalt(qtbot, tmp_path: Path):
    # Verify engine_combo includes cobalt
    combo = engine_combo()
    qtbot.addWidget(combo)
    items = [combo.itemData(i) for i in range(combo.count())]
    assert "cobalt" in items
    assert "auto" in items
    assert "native" in items
    assert "yt-dlp" in items

    # Verify Config defaults
    cfg = Config(tmp_path)
    assert cfg.get("cobaltEnabled") is True
    assert "cobalt" in cfg.get("cobaltUrl")
    assert cfg.get("cobaltApiKey") == ""

    # Verify Config validation of engine="cobalt"
    cfg.set("downloadEngine", "cobalt")
    assert cfg.get("downloadEngine") == "cobalt"
