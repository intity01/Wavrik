from __future__ import annotations

import threading
from typing import ClassVar
from unittest.mock import patch

import requests

from src.domain.native_downloader import NativeDownloader, native_kind
from src.domain.presets import getPreset


def test_native_kind_only_claims_known_media_routes():
    assert native_kind("https://files.example/video.mp4") == "file"
    assert native_kind("https://cdn.example/live.m3u8?token=abc") == "hls"
    assert native_kind("https://cdn.example/video.mpd") == "dash"
    assert native_kind("https://example.com/watch?id=123") is None


class _Response:
    status_code = 200
    headers: ClassVar = {"content-length": "4", "content-disposition": 'attachment; filename="sample.mp4"'}

    def raise_for_status(self):
        return None

    def iter_content(self, _size):
        yield b"test"

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


class _FailingResponse(_Response):
    headers: ClassVar = {"content-length": "20", "content-disposition": 'attachment; filename="partial.mp4"'}

    def iter_content(self, _size):
        yield b"partial"
        raise requests.ConnectionError("connection dropped")


@patch("src.domain.native_downloader.requests.get")
def test_native_direct_file_saves_and_reports_progress(mock_get, tmp_path):
    mock_get.return_value = _Response()
    updates = []
    result = NativeDownloader(threading.Event()).download(
        "https://files.example/video.mp4", tmp_path, getPreset("video_mp4_720"), updates.append,
    )
    assert result.success
    assert result.engine == "native"
    assert result.file_path and result.file_path.read_bytes() == b"test"
    assert updates[-1]["status"] == "processing"


@patch("src.domain.native_downloader.requests.get")
def test_native_rejects_a_page_url_with_an_actionable_error(mock_get, tmp_path):
    response = _Response()
    response.headers = {"content-type": "text/html"}
    mock_get.return_value = response
    result = NativeDownloader(threading.Event()).download("https://example.com/watch?id=123", tmp_path, getPreset("video_mp4_720"))
    assert not result.success
    assert "web page" in result.error


@patch("src.domain.native_downloader.requests.get")
def test_native_removes_partial_file_after_stream_failure(mock_get, tmp_path):
    mock_get.return_value = _FailingResponse()
    result = NativeDownloader(threading.Event()).download(
        "https://files.example/partial.mp4", tmp_path, getPreset("video_mp4_720"),
    )
    assert not result.success
    assert not list(tmp_path.glob("*.part"))
