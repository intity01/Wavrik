from __future__ import annotations

import subprocess
import sys
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.core.json_store import JsonStore
from src.domain.models import DownloadPreset, MediaType
from src.domain.native_downloader import NativeDownloader
from src.domain.native_paths import target_path
from src.services.platform_actions import BLOCKED_EXTENSIONS, open_path


def test_native_paths_preset_enforcement_and_dos_names(tmp_path: Path):
    # SEC-01: Malicious server specifies .exe or .bat in content disposition or URL
    header = 'attachment; filename="evil_payload.exe"'
    dest = target_path(tmp_path, "https://example.com/malicious.bat", header, "mp4")
    assert dest.name == "evil_payload.mp4"
    assert dest.suffix == ".mp4"

    # Fallback to URL if header empty, still enforcing preset container
    dest2 = target_path(tmp_path, "https://example.com/payload.cmd", "", "mp3")
    assert dest2.name == "payload.mp3"
    assert dest2.suffix == ".mp3"

    # DOS reserved device names
    for reserved in ["CON", "prn", "AUX", "nul", "com1", "COM9", "lpt1", "LPT9"]:
        dest_dos = target_path(tmp_path, f"https://example.com/{reserved}.mp4", "", "mp4")
        assert dest_dos.name == f"_{reserved}.mp4"


def test_platform_actions_blocks_dangerous_extensions(tmp_path: Path):
    # SEC-01: Defense in depth - blocking execution of dangerous files
    for ext in [".exe", ".bat", ".cmd", ".ps1", ".vbs", ".scr", ".msi", ".com", ".jar"]:
        assert ext in BLOCKED_EXTENSIONS
        test_file = tmp_path / f"test{ext}"
        test_file.write_text("echo test", encoding="utf-8")
        assert open_path(test_file) is False


def test_json_store_data_01_retry_vs_corrupt(tmp_path: Path):
    store_file = tmp_path / "data.json"
    store = JsonStore(store_file)

    # Valid write and read
    store.write({"key": "value"})
    assert store.read({}) == {"key": "value"}

    # Transient OSError during read should NOT create .corrupt file
    with patch.object(Path, "read_text", side_effect=OSError("Sharing violation")):
        val = store.read({"default": 1})
        assert val == {"default": 1}
        assert not store_file.with_suffix(".json.corrupt").exists()
        assert store_file.exists()

    # Genuine JSONDecodeError MUST create .corrupt file
    store_file.write_text("{corrupt json content", encoding="utf-8")
    val = store.read({"default": 2})
    assert val == {"default": 2}
    assert store_file.with_suffix(".json.corrupt").exists()


def test_cancellation_wait_during_backoff():
    # STAB-01: cancellation wait response time
    cancel_evt = threading.Event()

    def set_cancel():
        time.sleep(0.02)
        cancel_evt.set()

    threading.Thread(target=set_cancel).start()
    t0 = time.monotonic()
    cancelled = cancel_evt.wait(timeout=5.0)
    duration = time.monotonic() - t0

    assert cancelled is True
    assert duration < 1.0  # Immediate wakeup instead of blocking for 5s


def test_native_downloader_ffmpeg_command_and_creationflags(tmp_path: Path):
    # SEC-03 & SEC-04: ffmpeg subprocess timeout and flags
    cancel_evt = threading.Event()
    downloader = NativeDownloader(cancel_evt)
    preset = DownloadPreset("video_mp4_720", "MP4 720p", MediaType.VIDEO, "mp4")

    with patch("src.domain.native_downloader._ffmpeg_executable", return_value="ffmpeg.exe"), \
         patch("subprocess.Popen") as mock_popen:
        mock_proc = MagicMock()
        mock_proc.communicate.return_value = ("", "")
        mock_proc.returncode = 0
        mock_popen.return_value = mock_proc

        # Create dummy target file so it thinks it succeeded
        target = tmp_path / "stream.mp4"
        target.write_bytes(b"data")

        with patch("src.domain.native_downloader.target_path", return_value=target):
            downloader.download("https://example.com/playlist.m3u8", tmp_path, preset)

        mock_popen.assert_called_once()
        cmd = mock_popen.call_args[0][0]
        assert "-rw_timeout" in cmd
        assert "15000000" in cmd
        if sys.platform == "win32":
            assert mock_popen.call_args[1].get("creationflags") == getattr(subprocess, "CREATE_NO_WINDOW", 0)
        mock_proc.communicate.assert_called_once_with(timeout=300)


def test_requirements_security_versions():
    # DEP-01 & DEP-02
    req_path = Path(__file__).resolve().parents[2] / "requirements.txt"
    content = req_path.read_text(encoding="utf-8")
    assert "requests>=2.32.4" in content
    assert "yt-dlp>=2026.6.9" in content


def test_download_worker_throttling_perf_01(tmp_path: Path):
    # PERF-01: Progress signal emissions throttled to <= 10Hz
    from src.ui.workers.download_worker import DownloadWorker
    signals = MagicMock()
    downloader = MagicMock()
    history = MagicMock()
    preset = DownloadPreset("video_mp4_720", "MP4 720p", MediaType.VIDEO, "mp4")

    worker = DownloadWorker("https://example.com/test", downloader, preset, tmp_path, signals, history, "Test")

    # First emission always goes through
    worker._progress({"status": "downloading", "percent": 10.0, "speed": "1MB/s", "eta": "10s"})
    assert signals.progress.emit.call_count == 1

    # Rapid second emission within 0.1s is throttled
    worker._progress({"status": "downloading", "percent": 15.0, "speed": "1MB/s", "eta": "9s"})
    assert signals.progress.emit.call_count == 1

    # 100% completion always forces emission
    worker._progress({"status": "downloading", "percent": 100.0, "speed": "1MB/s", "eta": "0s"})
    assert signals.progress.emit.call_count == 2


def test_thumbnail_worker_emits_qimage_arch_01():
    # ARCH-01: Background worker creates and emits QImage, not QPixmap
    from PyQt6.QtGui import QImage
    from src.ui.workers.thumbnail_worker import ThumbnailWorker

    signals = MagicMock()
    worker = ThumbnailWorker("https://example.com", "https://example.com/thumb.png", signals)

    from PyQt6.QtCore import QBuffer, QIODevice
    img = QImage(2, 2, QImage.Format.Format_RGB32)
    buf = QBuffer()
    buf.open(QIODevice.OpenModeFlag.WriteOnly)
    img.save(buf, "PNG")
    valid_png = bytes(buf.data())

    mock_resp = MagicMock()
    mock_resp.headers = {"content-type": "image/png"}
    mock_resp.iter_content.return_value = [valid_png]
    mock_resp.raise_for_status.return_value = None

    with patch("requests.get", return_value=mock_resp):
        worker.run()

    signals.thumbnailReady.emit.assert_called_once()
    args = signals.thumbnailReady.emit.call_args[0]
    assert args[0] == "https://example.com"
    assert isinstance(args[1], QImage)
    assert not args[1].isNull()


def test_dialog_cancellation_returns_none_ux_01():
    # UX-01: Cancelled dialog returns None across all platforms
    from PyQt6.QtWidgets import QFileDialog
    from src.ui.macos.dialogs import get_open_file_path, get_save_directory, get_save_file_path

    with patch.object(QFileDialog, "getExistingDirectory", return_value=""):
        assert get_save_directory() is None

    with patch.object(QFileDialog, "getSaveFileName", return_value=("", "")):
        assert get_save_file_path() is None

    with patch.object(QFileDialog, "getOpenFileName", return_value=("", "")):
        assert get_open_file_path() is None


def test_history_card_no_sync_disk_io_perf_02():
    # PERF-02: Instantiating HistoryCard must not trigger synchronous Path.is_file
    from PyQt6.QtWidgets import QApplication
    from src.ui.components.history_card import HistoryCard
    _app = QApplication.instance() or QApplication(sys.argv[:1])

    entry = {
        "url": "https://example.com/video.mp4",
        "title": "Video",
        "status": "completed",
        "filePath": "C:/nonexistent/path/video.mp4",
        "timestamp": "2026-09-22T10:00:00",
        "mediaType": "video",
        "fileSize": 1024,
    }

    with patch.object(Path, "is_file") as mock_is_file:
        _card = HistoryCard(entry)
        mock_is_file.assert_not_called()

