"""Regression test suite for Phase 2a critical and high stability fixes."""

import os
import sys
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock

from PyQt6.QtCore import QCoreApplication

from src.core.crash_handler import install_crash_handler
from src.core.json_store import JsonStore
from src.domain.download_files import resolve_output, resolve_thumbnail
from src.domain.models import DownloadPreset, MediaType
from src.domain.native_downloader import NativeDownloader
from src.domain.yt_options import YtDownloadSettings, buildOptions
from src.services.history_manager import HistoryManager
from src.ui.components.batch_audio_dialog import BatchAudioDialog
from src.ui.pages.audio_tools_page import AudioToolsInterface
from src.ui.pages.library_page import LibraryInterface
from src.ui.pages.settings_page import SettingsInterface
from src.ui.window_lifecycle import WindowLifecycleMixin
from src.ui.workers.audio_worker import AnalyzeAudioWorker, AudioToolSignals, PitchJob, RenderPitchWorker
from src.ui.workers.stem_worker import StemSeparationWorker, StemSignals


def test_a1_audio_tools_error_signals_and_busy_reset(qtbot, config, history, tmp_path: Path):
    audio_file = tmp_path / "test.wav"
    audio_file.write_bytes(b"RIFF" + b"\x00" * 100)
    page = AudioToolsInterface(config, history)
    qtbot.addWidget(page)
    page.loadFile(audio_file)

    assert page._signals is not None
    # Verify error signal is actually connected to _on_error
    assert page._signals.receivers(page._signals.error) > 0
    assert page._signals.receivers(page._signals.analyzed) > 0

    page._busy = True
    page._signals.error.emit("Analysis crashed")
    assert page._busy is False
    assert page.statusLabel.text() == "Analysis crashed"
    assert page.separateStemsBtn.isEnabled()
    assert page.exportBtn.isEnabled()

    page.cleanup()
    assert page._busy is False


def test_a2_window_lifecycle_unified_cleanup():
    class DummyWindow(WindowLifecycleMixin):
        def __init__(self):
            self.pageWorkspace = MagicMock()
            self.pageLibrary = MagicMock()
            self.pageAudioTools = MagicMock()
            self._tray = MagicMock()

    win = DummyWindow()
    win.cleanup()
    win.pageWorkspace._cleanup.assert_called_once()
    win.pageLibrary.cleanup.assert_called_once()
    win.pageAudioTools.cleanup.assert_called_once()
    win._tray.stop.assert_called_once()

    # Idempotent: second call should be no-op
    win.cleanup()
    assert win.pageWorkspace._cleanup.call_count == 1


def test_a3_resolve_output_ignores_temp_files(tmp_path: Path):
    preset = DownloadPreset(
        key="best_video", label="Best Video", media_type=MediaType.VIDEO,
        container="mp4", video_height=1080,
    )
    started = time.time()
    folder = tmp_path / "downloads"
    folder.mkdir()

    part_file = folder / "video.mp4.part"
    part_file.write_bytes(b"temp")
    ytdl_file = folder / "video.mp4.ytdl"
    ytdl_file.write_bytes(b"temp")
    tmp_file = folder / "video.tmp"
    tmp_file.write_bytes(b"temp")
    temp_file = folder / "video.temp"
    temp_file.write_bytes(b"temp")

    # When only temp files exist, resolve_output must return None
    assert resolve_output(folder, {}, preset, started) is None

    # When a valid completed file exists, resolve_output returns it
    valid_file = folder / "video.mp4"
    valid_file.write_bytes(b"valid content")
    resolved = resolve_output(folder, {}, preset, started)
    assert resolved == valid_file


def test_a4_yt_dlp_options_ignoreerrors_false(tmp_path: Path):
    preset = DownloadPreset(
        key="best_audio", label="Best Audio", media_type=MediaType.AUDIO,
        container="mp3", audio_bitrate="320k",
    )
    settings = YtDownloadSettings()
    options = buildOptions(tmp_path, preset, lambda d: None, settings)
    assert options.get("ignoreerrors") is False


def test_a7_batch_audio_dialog_lifecycle(qtbot, config, tmp_path: Path):
    src = tmp_path / "sample.wav"
    src.write_bytes(b"audio data")
    dialog = BatchAudioDialog([src], config)
    qtbot.addWidget(dialog)

    assert dialog._worker is None
    # Simulate start batch
    dialog._start_batch()
    assert dialog._worker is not None
    assert dialog.closeBtn.text() == "Cancel"

    # Close dialog triggers _cancel_and_wait
    dialog.reject()
    assert dialog._worker is None
    assert dialog.startBtn.isEnabled() or not dialog.isVisible()


def test_a9_json_store_unique_temp_and_retry(tmp_path: Path, monkeypatch):
    store_file = tmp_path / "store.json"
    store = JsonStore(store_file)

    attempts = {"count": 0}
    orig_replace = os.replace

    def mock_replace(src, dst):
        if str(src).endswith(".tmp"):
            attempts["count"] += 1
            if attempts["count"] < 3:
                raise PermissionError("Access is denied")
        return orig_replace(src, dst)

    monkeypatch.setattr(os, "replace", mock_replace)
    store.write({"key": "value"})
    assert attempts["count"] >= 3
    assert store.read({}) == {"key": "value"}


def test_a9_json_store_corrupt_backup_preserves_old(tmp_path: Path):
    store_file = tmp_path / "store.json"
    corrupt_file = store_file.with_suffix(".json.corrupt")
    corrupt_file.write_text("old corrupt", encoding="utf-8")

    store = JsonStore(store_file)
    store_file.write_text("new corrupt", encoding="utf-8")
    store.backup()

    assert corrupt_file.exists()
    assert corrupt_file.read_text(encoding="utf-8") == "new corrupt"
    # An archived timestamped backup should also exist
    backups = list(tmp_path.glob("store.json.*.corrupt"))
    assert len(backups) == 1
    assert backups[0].read_text(encoding="utf-8") == "old corrupt"


def test_a9_history_path_normalization(config, logger, tmp_path: Path):
    history = HistoryManager(config, logger)
    file_on_disk = tmp_path / "MySong.mp3"
    file_on_disk.write_bytes(b"data")

    # Add entry with upper-case / forward-slash representation
    raw_path = str(file_on_disk).replace("\\", "/")
    history.addEntry("http://example.com/song", "Song", "audio", "MP3", raw_path, True, 100, status="completed")

    # Update analysis using lower-case / native back-slash path
    lookup_path = os.path.normpath(str(file_on_disk)).lower()
    analysis = {"key": "G# minor", "bpm": 140.0, "camelot": "1A"}
    history.updateAnalysis(lookup_path, analysis)

    entries = history.getHistory()
    assert len(entries) == 1
    assert entries[0].get("analysis", {}).get("key") == "G# minor"


def test_a11_library_bgsignals_cleanup_and_cache_bound(qtbot, history, config, tmp_path: Path):
    library = LibraryInterface(history, config)
    qtbot.addWidget(library)

    audio = tmp_path / "track.mp3"
    audio.write_bytes(b"ID3" + b"\x00" * 200)

    library.enqueueAutoAnalyze(str(audio))
    assert len(library._bgSignals) == 1
    sig = library._bgSignals[0]

    # Emitting analyzed signal cleans up the signal reference
    sig.analyzed.emit({"filePath": str(audio), "key": "C major", "bpm": 120.0})
    QCoreApplication.processEvents()
    assert sig not in library._bgSignals

    # Cache bounding check (> 500 items)
    for i in range(510):
        library.storeAnalysisResult({"filePath": f"/dummy/{i}.mp3", "key": "A minor"})
    assert len(library._analysisCache) <= 500

    library.cleanup()
    assert len(library._bgSignals) == 0


def test_a12_native_downloader_ffmpeg_timeout_logging(tmp_path: Path):
    mock_logger = MagicMock()
    cancel = threading.Event()
    downloader = NativeDownloader(cancel, mock_logger)
    target = tmp_path / "output.mp4"
    target.write_bytes(b"partial")

    downloader._process = MagicMock()
    downloader._process.communicate.side_effect = Exception("pipe dead")

    res = downloader._handle_timeout(target)
    assert res.success is False
    assert "timed out" in res.error
    assert not target.exists()
    assert mock_logger.warning.call_count >= 2


def test_crash_handler_logs_traceback():
    mock_logger = MagicMock()
    install_crash_handler(mock_logger)

    try:
        raise ValueError("Simulated crash")
    except ValueError:
        exc_type, exc_val, exc_tb = sys.exc_info()
        sys.excepthook(exc_type, exc_val, exc_tb)

    mock_logger.critical.assert_called_once()
    msg = mock_logger.critical.call_args[0][0]
    assert "Unhandled exception" in msg

    # Thread excepthook
    hook_args = threading.ExceptHookArgs(
        (RuntimeError, RuntimeError("Thread error"), None, threading.current_thread()),
    )
    threading.excepthook(hook_args)
    assert mock_logger.critical.call_count == 2


def test_settings_open_log_folder(qtbot, config, monkeypatch, tmp_path: Path):
    mock_updater = MagicMock()
    mock_updater.getCurrentVersion.return_value = "2.1.0"
    page = SettingsInterface(config, mock_updater)
    qtbot.addWidget(page)
    opened = []

    def mock_open(path):
        opened.append(Path(path))
        return True

    monkeypatch.setattr("src.ui.pages.settings_page.open_path", mock_open)
    page.openLogsBtn.click()

    assert len(opened) == 1
    assert opened[0] == config.appDataDir / "logs"
    assert opened[0].exists()


def test_a2_workers_cancellation(tmp_path: Path):
    audio_file = tmp_path / "song.wav"
    audio_file.write_bytes(b"RIFF" + b"\x00" * 200)

    # 1. AnalyzeAudioWorker cancellation
    signals_analysis = AudioToolSignals()
    emitted_analysis = []
    signals_analysis.analyzed.connect(lambda res: emitted_analysis.append(res))
    worker_analysis = AnalyzeAudioWorker(audio_file, signals_analysis)
    worker_analysis.cancel()
    worker_analysis.run()
    assert len(emitted_analysis) == 0

    # 2. RenderPitchWorker cancellation
    signals_render = AudioToolSignals()
    emitted_render = []
    signals_render.rendered.connect(lambda out, prev: emitted_render.append(out))
    job = PitchJob(audio_file, tmp_path / "out.wav", 2)
    worker_render = RenderPitchWorker(job, signals_render)
    worker_render.cancel()
    worker_render.run()
    assert len(emitted_render) == 0

    # 3. StemSeparationWorker cancellation
    signals_stem = StemSignals()
    emitted_stem = []
    signals_stem.separated.connect(lambda v, i, m: emitted_stem.append(v))
    worker_stem = StemSeparationWorker(audio_file, tmp_path, "roformer_ensemble", signals_stem)
    worker_stem.cancel()
    worker_stem.run()
    assert len(emitted_stem) == 0


def test_a2_audio_tools_and_library_cleanup_cancels_workers(qtbot, config, history, tmp_path: Path):
    audio = tmp_path / "test.mp3"
    audio.write_bytes(b"ID3" + b"\x00" * 200)

    # AudioToolsInterface cleanup cancels _activeWorker and _batchDialog
    page = AudioToolsInterface(config, history)
    qtbot.addWidget(page)
    mock_worker = MagicMock()
    page._activeWorker = mock_worker
    mock_dialog = MagicMock()
    page._batchDialog = mock_dialog
    page.cleanup()
    mock_worker.cancel.assert_called_once()
    mock_dialog._cancel_and_wait.assert_called_once()

    # LibraryInterface cleanup cancels active workers in _activeWorkers
    lib = LibraryInterface(history, config)
    qtbot.addWidget(lib)
    lib.enqueueAutoAnalyze(str(audio))
    assert len(lib._activeWorkers) == 1
    w = lib._activeWorkers[0]
    lib.cleanup()
    assert w._cancelled is True
    assert len(lib._activeWorkers) == 0


def test_a3_resolve_output_and_thumbnail_survives_concurrent_file_deletion(tmp_path: Path, monkeypatch):
    folder = tmp_path / "dl"
    folder.mkdir()
    preset = DownloadPreset("best", "Best", MediaType.VIDEO, "mp4")

    target = folder / "video.mp4"
    target.write_bytes(b"content")

    # Simulate OSError during stat check (e.g. file unlinked concurrently)
    orig_stat = Path.stat

    def flaky_stat(self, *args, **kwargs):
        if self.name.endswith(".tmp_vanish"):
            raise FileNotFoundError("File removed concurrently")
        return orig_stat(self, *args, **kwargs)

    monkeypatch.setattr(Path, "stat", flaky_stat)
    (folder / "ghost.tmp_vanish").write_bytes(b"temp")
    # Even if folder contains files that raise OSError during inspection, resolve_output succeeds
    out = resolve_output(folder, {}, preset, time.time())
    assert out == target

    # Same for resolve_thumbnail
    thumb_dir = folder / "thumbnails"
    thumb_dir.mkdir()
    thumb = thumb_dir / "thumb.jpg"
    thumb.write_bytes(b"image")
    resolved_thumb = resolve_thumbnail(folder, time.time())
    assert resolved_thumb == thumb


def test_a7_batch_audio_dialog_error_handling(qtbot, config, tmp_path: Path):
    src = tmp_path / "track.wav"
    src.write_bytes(b"data")
    dialog = BatchAudioDialog([src], config)
    qtbot.addWidget(dialog)

    dialog._start_batch()
    assert dialog._signals is not None

    # Error signal displays error message in status
    dialog._signals.error.emit("Failed to process track.wav: Test error")
    assert "Failed to process track.wav" in dialog.status.text()

    dialog.reject()
    assert dialog._worker is None


def test_a9_json_store_rapid_corrupt_backups_unique(tmp_path: Path):
    store_file = tmp_path / "data.json"
    store = JsonStore(store_file)

    store_file.write_text("corrupt 1", encoding="utf-8")
    store.backup()

    store_file.write_text("corrupt 2", encoding="utf-8")
    store.backup()

    store_file.write_text("corrupt 3", encoding="utf-8")
    store.backup()

    # Three backups must exist: the latest as .corrupt, and two archived timestamped backups
    backups = list(tmp_path.glob("data.json.*.corrupt"))
    assert len(backups) == 2
    corrupt_main = store_file.with_suffix(".json.corrupt")
    assert corrupt_main.exists()
    assert corrupt_main.read_text(encoding="utf-8") == "corrupt 3"
