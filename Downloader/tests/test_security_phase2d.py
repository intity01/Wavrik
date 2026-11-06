"""Security regression and hardening test suite for Phase 2d.

Covers:
- [C1] FFmpeg HLS protocol whitelist (-protocol_whitelist "http,https,tcp,tls,crypto")
- [C2] Path traversal prevention in rename_pattern and audio_pitch
- [C3] Native file download size ceiling (MAX_FILE_BYTES)
- [C6] Windows MAX_PATH truncation and DOS device name sanitization
- [C10] UNC path injection prevention for downloadPath and cookieFile
"""

from __future__ import annotations

import json
from pathlib import Path
import threading
from unittest.mock import MagicMock, patch

import pytest

from src.core.config import DEFAULT_SETTINGS, Config
from src.domain.models import DownloadPreset, JobState
from src.domain.native_downloader import NativeDownloader
from src.domain.native_file import (
    MAX_FILE_BYTES,
    NativeDownloadError,
    _stream,
    download_file,
)
from src.domain.native_paths import MAX_STEM_LENGTH, target_path
from src.domain.presets import getPreset
from src.domain.yt_options import (
    YtDownloadSettings,
    buildOptions,
    sanitize_rename_pattern,
)
from src.services.audio_pitch import (
    build_export_filename,
    unique_export_path,
)


# ==============================================================================
# [C1] FFmpeg HLS protocol whitelist
# ==============================================================================


@patch("src.domain.native_downloader.subprocess.Popen")
@patch("src.domain.native_downloader._ffmpeg_executable", return_value="ffmpeg")
def test_c1_ffmpeg_hls_command_includes_protocol_whitelist(mock_ffmpeg, mock_popen, tmp_path):
    mock_proc = MagicMock()
    mock_proc.communicate.return_value = ("", "")
    mock_proc.returncode = 0
    mock_popen.return_value = mock_proc

    test_preset = getPreset("video_mp4_720")
    mock_proc.communicate.side_effect = lambda *_args, **_kwargs: (
        (tmp_path / f"manifest.{test_preset.container}").write_bytes(b"dummy media content") and None,
        "",
    )

    downloader = NativeDownloader(cancel=threading.Event())
    url = "https://cdn.example.com/live/manifest.m3u8"
    result = downloader.download(url, tmp_path, test_preset)
    assert result.success

    assert mock_popen.called
    cmd_args = mock_popen.call_args[0][0]

    # Verify protocol whitelist flag and its argument
    assert "-protocol_whitelist" in cmd_args
    idx = cmd_args.index("-protocol_whitelist")
    assert cmd_args[idx + 1] == "http,https,tcp,tls,crypto"

    # Verify whitelist appears BEFORE -i <url> input option
    i_idx = cmd_args.index("-i")
    assert idx < i_idx
    assert cmd_args[i_idx + 1] == url


@patch("src.domain.native_downloader.subprocess.Popen")
@patch("src.domain.native_downloader._ffmpeg_executable", return_value="ffmpeg")
def test_c1_ffmpeg_dash_command_includes_protocol_whitelist(mock_ffmpeg, mock_popen, tmp_path):
    mock_proc = MagicMock()
    mock_proc.returncode = 0
    mock_popen.return_value = mock_proc

    test_preset = getPreset("video_mp4_720")
    mock_proc.communicate.side_effect = lambda *_args, **_kwargs: (
        (tmp_path / f"video.{test_preset.container}").write_bytes(b"dummy dash content") and None,
        "",
    )

    downloader = NativeDownloader(cancel=threading.Event())
    url = "https://cdn.example.com/streams/video.mpd"
    result = downloader.download(url, tmp_path, test_preset)
    assert result.success

    cmd_args = mock_popen.call_args[0][0]
    assert "-protocol_whitelist" in cmd_args
    idx = cmd_args.index("-protocol_whitelist")
    assert cmd_args[idx + 1] == "http,https,tcp,tls,crypto"
    assert idx < cmd_args.index("-i")


# ==============================================================================
# [C2] Path Traversal Prevention
# ==============================================================================


@pytest.mark.parametrize(
    ("malicious_pattern", "expected_substring"),
    [
        ("../../escaped", "____escaped"),
        ("..\\..\\windows\\system32", "____windows_system32"),
        ("foo/bar/baz", "foo_bar_baz"),
        ("C:/malicious/path", "C__malicious_path"),
        ("..", "_"),
        ("....//", "____"),
    ],
)
def test_c2_sanitize_rename_pattern_replaces_traversal_sequences(malicious_pattern, expected_substring):
    sanitized = sanitize_rename_pattern(malicious_pattern)
    assert ".." not in sanitized
    assert "/" not in sanitized
    assert "\\" not in sanitized
    assert ":" not in sanitized
    assert sanitized == expected_substring


def test_c2_sanitize_rename_pattern_empty_fallback():
    assert sanitize_rename_pattern("") == "{title}"
    assert sanitize_rename_pattern("   ") == "{title}"
    assert sanitize_rename_pattern(None) == "{title}"


def test_c2_build_options_outtmpl_stays_inside_output_dir(tmp_path):
    evil_settings = YtDownloadSettings(rename_pattern="../../etc/passwd")
    preset = getPreset("video_mp4_720")
    options = buildOptions(tmp_path, preset, lambda _d: None, evil_settings)

    outtmpl = Path(options["outtmpl"])
    # outtmpl must resolve under tmp_path, never outside
    assert not str(outtmpl).startswith("..")
    assert ".." not in str(outtmpl)
    assert outtmpl.parent == tmp_path


def test_c2_build_export_filename_strips_directory_traversal():
    assert build_export_filename("../../secret.wav", 0) == "secret_[0st].wav"
    assert build_export_filename("../../secret.wav", 2) == "secret_[+2st].wav"
    assert build_export_filename("C:\\Windows\\system32\\calc.exe", 2) == "calc_[+2st].wav"
    assert build_export_filename("/etc/shadow", -3, target_key="A minor", fmt="mp3") == "shadow_[Key_Am_-3st].mp3"


def test_c2_unique_export_path_prevents_traversal(tmp_path):
    target = unique_export_path(tmp_path, "../../evil_export.wav")
    assert target.parent == tmp_path
    assert target.name == "evil_export.wav"
    assert target.resolve().is_relative_to(tmp_path.resolve())


def test_c2_unique_export_path_rejects_empty_or_pure_dots(tmp_path):
    with pytest.raises(ValueError, match="(Invalid export filename|Path traversal detected)"):
        unique_export_path(tmp_path, "..")
    with pytest.raises(ValueError, match="Invalid export filename"):
        unique_export_path(tmp_path, "")


def test_c2_unique_export_path_handles_collision_safely(tmp_path):
    file1 = tmp_path / "track.wav"
    file1.write_bytes(b"existing")

    candidate = unique_export_path(tmp_path, "track.wav")
    assert candidate == tmp_path / "track_1.wav"
    assert candidate.resolve().is_relative_to(tmp_path.resolve())


# ==============================================================================
# [C3] Native File Download Size Ceiling
# ==============================================================================


class _ChunkMockResponse:
    def __init__(self, chunks: list[bytes], content_length: int | None = None, content_type: str = "video/mp4"):
        self.chunks = chunks
        self.status_code = 200
        self.headers = {
            "content-type": content_type,
            "content-disposition": 'attachment; filename="clip.mp4"',
        }
        if content_length is not None:
            self.headers["content-length"] = str(content_length)

    def raise_for_status(self):
        pass

    def iter_content(self, _size):
        for chunk in self.chunks:
            yield chunk

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


def test_c3_stream_rejects_declared_oversized_content_length(tmp_path):
    resp = _ChunkMockResponse([b"x" * 1024], content_length=MAX_FILE_BYTES + 1024)
    target = tmp_path / "test.part"

    with pytest.raises(NativeDownloadError, match="maximum permitted limit"):
        _stream(threading.Event(), resp, target, total=MAX_FILE_BYTES + 1024, progress=None)


def test_c3_stream_aborts_when_downloaded_bytes_exceed_ceiling(tmp_path):
    # Simulated 2 KB chunks with ceiling set to 1 KB (1024 bytes)
    resp = _ChunkMockResponse([b"A" * 600, b"B" * 600], content_length=0)
    target = tmp_path / "test.part"

    with pytest.raises(NativeDownloadError, match="maximum permitted limit"):
        _stream(threading.Event(), resp, target, total=0, progress=None, max_bytes=1024)


def test_c3_download_file_cleans_temporary_part_on_size_overflow(tmp_path, monkeypatch):
    monkeypatch.setattr("src.domain.native_file.MAX_FILE_BYTES", 500)
    oversized_response = _ChunkMockResponse([b"Z" * 300, b"Z" * 300], content_length=600)

    preset = DownloadPreset("video", "mp4", 720, "aac", "128k")
    result = download_file(
        threading.Event(),
        lambda *_args, **_kwargs: oversized_response,
        "https://example.com/big_file.mp4",
        tmp_path,
        preset,
        progress=None,
    )

    assert not result.success
    assert result.state == JobState.FAILED
    assert "maximum permitted limit" in (result.error or "")

    # Ensure no leftover .part files exist in tmp_path
    leftovers = list(tmp_path.glob("*.part"))
    assert len(leftovers) == 0


# ==============================================================================
# [C6] Windows MAX_PATH and DOS Device Names
# ==============================================================================


@pytest.mark.parametrize(
    ("dos_name", "ext"),
    [
        ("CON", "mp4"),
        ("con", "m4a"),
        ("PRN", "mp3"),
        ("AUX", "wav"),
        ("NUL", "flac"),
        ("COM1", "mp4"),
        ("com9", "mp3"),
        ("LPT1", "mkv"),
        ("lpt9", "aac"),
        ("CON.extra", "mp4"),
    ],
)
def test_c6_target_path_prefixes_dos_device_names(tmp_path, dos_name, ext):
    path = target_path(tmp_path, f"https://example.com/{dos_name}.{ext}", "", ext)
    assert path.stem.startswith("_")
    assert not path.stem.upper().startswith("CON.")  # sanitized
    assert path.parent == tmp_path


def test_c6_target_path_truncates_stem_to_max_length(tmp_path):
    super_long_name = "a" * 300 + ".mp4"
    path = target_path(tmp_path, f"https://example.com/{super_long_name}", "", "mp4")

    assert len(path.stem) <= MAX_STEM_LENGTH
    assert len(path.stem) == 150
    assert path.suffix == ".mp4"
    assert path.parent == tmp_path


def test_c6_target_path_strips_trailing_dots_and_spaces(tmp_path):
    malformed_stem = "valid_name...   "
    path = target_path(tmp_path, f"https://example.com/{malformed_stem}.mp4", "", "mp4")

    assert not path.stem.endswith(".")
    assert not path.stem.endswith(" ")
    assert path.stem == "valid_name"


def test_c6_target_path_fallback_for_empty_stem(tmp_path):
    path = target_path(tmp_path, "https://example.com/...   ", "", "mp4")
    assert path.stem == "download"


# ==============================================================================
# [C10] UNC Path Injection Prevention
# ==============================================================================


def test_c10_config_load_settings_rejects_unc_download_path(tmp_path):
    settings_file = tmp_path / "settings.json"
    settings_data = {
        "schemaVersion": 2,
        "downloadPath": "\\\\attacker-server\\share\\downloads",
        "cookieFile": "//malicious.corp/secret_cookies.txt",
    }
    settings_file.write_text(json.dumps(settings_data), encoding="utf-8")

    cfg = Config(app_data_dir=tmp_path)
    assert cfg.get("downloadPath") == DEFAULT_SETTINGS["downloadPath"]
    assert cfg.get("cookieFile") == DEFAULT_SETTINGS["cookieFile"]
    assert not cfg.get("downloadPath").startswith(("\\\\", "//"))
    assert not cfg.get("cookieFile").startswith(("\\\\", "//"))


def test_c10_config_set_rejects_unc_paths(tmp_path):
    cfg = Config(app_data_dir=tmp_path)

    cfg.set("downloadPath", "\\\\smb-share.evil\\loot")
    assert cfg.get("downloadPath") == DEFAULT_SETTINGS["downloadPath"]

    cfg.set("cookieFile", "//smb-share.evil/cookies.txt")
    assert cfg.get("cookieFile") == DEFAULT_SETTINGS["cookieFile"]


def test_c10_config_update_rejects_unc_paths(tmp_path):
    cfg = Config(app_data_dir=tmp_path)

    cfg.update(
        downloadPath="\\\\hash-leak.com\\share",
        cookieFile="//hash-leak.com/cookies",
    )
    assert cfg.get("downloadPath") == DEFAULT_SETTINGS["downloadPath"]
    assert cfg.get("cookieFile") == DEFAULT_SETTINGS["cookieFile"]


def test_c10_get_download_path_falls_back_on_unc(tmp_path):
    cfg = Config(app_data_dir=tmp_path)
    # Directly inject into internal dict to simulate corrupted in-memory state
    cfg.settings["downloadPath"] = "\\\\attacker\\smb"

    safe_path = cfg.getDownloadPath("video")
    assert str(DEFAULT_SETTINGS["downloadPath"]) in str(safe_path)
    assert not str(safe_path).startswith(("\\\\", "//"))
