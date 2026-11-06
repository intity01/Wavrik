"""Comprehensive regression test suite for Phase 2b: Subprocess cancellation, Player seeking, and Analysis cache."""

from array import array
import math
from pathlib import Path
import subprocess
import sys
import threading
import time
import wave
from unittest.mock import MagicMock, patch

from PyQt6.QtMultimedia import QMediaPlayer

from src.core.process import is_cancellation_requested, kill_process_tree, run_cancellable_process
from src.services.audio_batch import BatchJobConfig
from src.services.audio_pitch import render_audio_clip
from src.services.audio_stems import separate_stems
from src.ui.components.audio_transport import AudioTransportController
from src.ui.pages.audio_tools_page import AudioToolsInterface
from src.ui.workers.audio_worker import AudioToolSignals, PitchJob, RenderPitchWorker
from src.ui.workers.batch_worker import BatchAudioSignals, BatchAudioWorker
from src.ui.workers.stem_worker import StemSeparationWorker, StemSignals


def _create_wav(path: Path, seconds: float = 1.0, sr: int = 8000) -> Path:
    total = int(seconds * sr)
    samples = array("h", [int(0.5 * 32767 * math.sin(2 * math.pi * 440 * i / sr)) for i in range(total)])
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(samples.tobytes())
    return path


def test_a5_cancellable_process_early_cancel():
    cmd = [sys.executable, "-c", "import time; time.sleep(1)"]
    try:
        run_cancellable_process(cmd, timeout=5.0, cancel_check=lambda: True)
        assert False, "Should have raised RuntimeError"
    except RuntimeError as exc:
        assert "cancelled before execution" in str(exc)


def test_a5_cancellable_process_active_cancel():
    cmd = [sys.executable, "-c", "import time; time.sleep(5)"]
    start = time.monotonic()
    cancel_flag = False

    def check():
        nonlocal cancel_flag
        if time.monotonic() - start > 0.2:
            cancel_flag = True
        return cancel_flag

    try:
        run_cancellable_process(cmd, timeout=10.0, cancel_check=check)
        assert False, "Should have raised RuntimeError on cancellation"
    except RuntimeError as exc:
        assert "execution cancelled" in str(exc)
        assert time.monotonic() - start < 3.0


def test_a5_cancellable_process_timeout():
    cmd = [sys.executable, "-c", "import time; time.sleep(5)"]
    try:
        run_cancellable_process(cmd, timeout=0.3)
        assert False, "Should have timed out"
    except subprocess.TimeoutExpired:
        pass


def test_a5_cancellable_process_normal_run():
    cmd = [sys.executable, "-c", "print('success_output')"]
    proc = run_cancellable_process(cmd, timeout=5.0)
    assert proc.returncode == 0
    assert "success_output" in proc.stdout


def test_a5_kill_process_tree():
    cmd = [sys.executable, "-c", "import time; time.sleep(5)"]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    assert proc.poll() is None
    kill_process_tree(proc)
    assert proc.poll() is not None
    # Calling kill_process_tree again on a finished process is safe
    kill_process_tree(proc)


def test_a5_is_cancellation_requested():
    assert not is_cancellation_requested(None)
    assert is_cancellation_requested(lambda: True)
    assert not is_cancellation_requested(lambda: False)

    event_mock = MagicMock()
    event_mock.is_set.return_value = True
    assert is_cancellation_requested(event_mock)

    worker_mock = MagicMock(spec=["is_cancelled"])
    worker_mock.is_cancelled.return_value = True
    assert is_cancellation_requested(worker_mock)


def test_a5_render_pitch_worker_cancellation(tmp_path: Path):
    src = _create_wav(tmp_path / "in.wav")
    dst = tmp_path / "out.wav"
    signals = AudioToolSignals()

    rendered_mock = MagicMock()
    error_mock = MagicMock()
    signals.rendered.connect(rendered_mock)
    signals.error.connect(error_mock)

    job = PitchJob(src, dst, 2)
    worker = RenderPitchWorker(job, signals)

    # Cancel before running
    worker.cancel()
    assert worker.is_cancelled()
    worker.run()
    assert not rendered_mock.called
    assert not error_mock.called

    # Cancel during execution
    worker_running = RenderPitchWorker(job, signals)
    with patch("src.ui.workers.audio_worker.render_audio_clip") as mock_clip:
        def fake_clip(*args, **kwargs):
            cancel_check = kwargs.get("cancel_check")
            assert cancel_check is not None
            assert not cancel_check()
            worker_running.cancel()
            assert cancel_check()
            raise RuntimeError("Process execution cancelled.")

        mock_clip.side_effect = fake_clip
        worker_running.run()

    # Neither rendered nor error emitted when cancelled
    assert not rendered_mock.called
    assert not error_mock.called


def test_a5_render_audio_clip_direct_cancellation(tmp_path: Path):
    src = _create_wav(tmp_path / "src.wav")
    dst = tmp_path / "dst.wav"
    try:
        render_audio_clip(src, dst, 0, ("r3_finer", "wav", 1.0, 0.0, 0.0), cancel_check=lambda: True)
        assert False, "Should have raised cancelled"
    except RuntimeError as exc:
        assert "cancelled" in str(exc).lower()


def test_a5_stem_worker_cancellation(tmp_path: Path):
    src = _create_wav(tmp_path / "song.wav")
    signals = StemSignals()
    sep_mock, err_mock = MagicMock(), MagicMock()
    signals.separated.connect(sep_mock)
    signals.error.connect(err_mock)

    worker = StemSeparationWorker(src, tmp_path, "dsp_2stem", signals)
    worker.cancel()
    assert worker.is_cancelled()
    worker.run()
    assert not sep_mock.called
    assert not err_mock.called

    # Active cancel during separate_stems
    worker_running = StemSeparationWorker(src, tmp_path, "dsp_2stem", signals)
    with patch("src.ui.workers.stem_worker.separate_stems") as mock_sep:
        def fake_sep(*args, **kwargs):
            cancel_check = kwargs.get("cancel_check")
            assert cancel_check is not None
            worker_running.cancel()
            assert cancel_check()
            raise RuntimeError("Stem separation cancelled.")

        mock_sep.side_effect = fake_sep
        worker_running.run()

    assert not sep_mock.called
    assert not err_mock.called


def test_a5_separate_stems_direct_cancellation(tmp_path: Path):
    src = _create_wav(tmp_path / "stems_in.wav")
    try:
        separate_stems(src, tmp_path, cancel_check=lambda: True)
        assert False, "Should have raised cancelled"
    except RuntimeError as exc:
        assert "cancelled" in str(exc).lower()


def test_a5_batch_audio_worker_cancellation(tmp_path: Path):
    f1 = _create_wav(tmp_path / "b1.wav")
    f2 = _create_wav(tmp_path / "b2.wav")
    f3 = _create_wav(tmp_path / "b3.wav")

    cfg = BatchJobConfig(semitones=2, output_dir=tmp_path / "out")
    signals = BatchAudioSignals()
    item_mock, finish_mock, err_mock = MagicMock(), MagicMock(), MagicMock()
    signals.itemProcessed.connect(item_mock)
    signals.finished.connect(finish_mock)
    signals.error.connect(err_mock)

    worker = BatchAudioWorker([f1, f2, f3], cfg, signals)

    # Cancel after 1 item processed
    processed_count = 0

    def fake_process(src, cfg, key, cancel_check=None):
        nonlocal processed_count
        processed_count += 1
        assert cancel_check is not None
        if processed_count == 1:
            worker.cancel()
        return src

    with patch("src.ui.workers.batch_worker.process_batch_file", side_effect=fake_process):
        worker.run()

    assert processed_count == 1
    assert item_mock.call_count == 1
    finish_mock.assert_called_once_with(1, 0)
    assert not err_mock.called


def test_a8_transport_smooth_seeking_no_reload(tmp_path: Path):
    transport = AudioTransportController()
    wav_a = _create_wav(tmp_path / "track_a.wav")
    transport.setSlotA(wav_a)

    mock_player = MagicMock()
    mock_player.playbackState.return_value = QMediaPlayer.PlaybackState.StoppedState
    mock_player.mediaStatus.return_value = QMediaPlayer.MediaStatus.LoadedMedia
    transport._player = mock_player

    # First playback loads track_a
    assert transport.playSlot("A", 2.0)
    assert transport._current_source == wav_a
    assert mock_player.setSource.call_count == 1
    assert mock_player.play.call_count == 1

    # Seeking within track_a does NOT call setSource again!
    mock_player.playbackState.return_value = QMediaPlayer.PlaybackState.PlayingState
    assert transport.playSlot("A", 8.5)
    assert mock_player.setSource.call_count == 1  # Still 1! Not reloaded
    mock_player.setPosition.assert_called_with(8500)

    # Direct seek method
    transport.seek(12.0)
    mock_player.setPosition.assert_called_with(12000)
    assert mock_player.setSource.call_count == 1  # Never reloaded


def test_a8_transport_slot_b_seek_sync(tmp_path: Path):
    transport = AudioTransportController()
    wav_a = _create_wav(tmp_path / "track_a.wav")
    wav_b = _create_wav(tmp_path / "track_b.wav")
    transport.setSlotA(wav_a)
    transport.setSlotB(wav_b)

    mock_player = MagicMock()
    mock_player.playbackState.return_value = QMediaPlayer.PlaybackState.StoppedState
    mock_player.mediaStatus.return_value = QMediaPlayer.MediaStatus.LoadedMedia
    transport._player = mock_player

    # Play Slot B with seek position 14.5s
    assert transport.playSlot("B", 14.5)
    assert transport.activeSlot() == "B"
    assert transport._current_source == wav_b
    assert mock_player.setSource.call_count == 1
    # Slot B position set properly, not ignored or forced to 0
    mock_player.setPosition.assert_called_with(14500)

    # Seeking within Slot B doesn't reload
    mock_player.playbackState.return_value = QMediaPlayer.PlaybackState.PlayingState
    assert transport.playSlot("B", 20.0)
    assert mock_player.setSource.call_count == 1
    mock_player.setPosition.assert_called_with(20000)


def test_a8_transport_deferred_seek_on_media_status(tmp_path: Path):
    transport = AudioTransportController()
    wav = _create_wav(tmp_path / "async_track.wav")
    transport.setSlotA(wav)

    mock_player = MagicMock()
    mock_player.playbackState.return_value = QMediaPlayer.PlaybackState.StoppedState
    # Initially loading media (not loaded yet)
    mock_player.mediaStatus.return_value = QMediaPlayer.MediaStatus.LoadingMedia
    transport._player = mock_player

    transport.playSlot("A", 16.0)
    assert transport._pending_seek_ms == 16000

    # Media finishes loading asynchronously
    transport._on_media_status(QMediaPlayer.MediaStatus.LoadedMedia)
    mock_player.setPosition.assert_called_with(16000)
    assert transport._pending_seek_ms is None


def test_a8_transport_toggle_ab_preserves_position(tmp_path: Path):
    transport = AudioTransportController()
    wav_a = _create_wav(tmp_path / "track_a.wav")
    wav_b = _create_wav(tmp_path / "track_b.wav")
    transport.setSlotA(wav_a)
    transport.setSlotB(wav_b)

    mock_player = MagicMock()
    mock_player.playbackState.return_value = QMediaPlayer.PlaybackState.PlayingState
    mock_player.mediaStatus.return_value = QMediaPlayer.MediaStatus.LoadedMedia
    mock_player.position.return_value = 17500  # Currently at 17.5s
    transport._player = mock_player

    transport.playSlot("A", 17.5)
    assert transport.activeSlot() == "A"

    # Toggle to Slot B preserves current position (17.5s)
    new_slot = transport.toggleAB()
    assert new_slot == "B"
    mock_player.setPosition.assert_called_with(17500)


def test_a8_audio_tools_seek_on_active_slot_b(qtbot, config, history, tmp_path: Path):
    wav_a = _create_wav(tmp_path / "orig.wav")
    wav_b = _create_wav(tmp_path / "preview.wav")
    page = AudioToolsInterface(config, history)
    qtbot.addWidget(page)

    page.loadFile(wav_a, {"key": "C major", "bpm": 120.0})
    page.transport.setSlotB(wav_b)

    mock_player = MagicMock()
    mock_player.playbackState.return_value = QMediaPlayer.PlaybackState.PlayingState
    mock_player.mediaStatus.return_value = QMediaPlayer.MediaStatus.LoadedMedia
    page.transport._player = mock_player

    page.transport.playSlot("B", 5.0)
    assert page.transport.activeSlot() == "B"
    assert page.transport.isPlaying()

    # Waveform seek requested while playing Slot B
    page._on_seek_requested(22.0)
    assert "0:22" in page.statusLabel.text()
    # Verified it sought Slot B directly without resetting or forcing Slot A
    assert page.transport.activeSlot() == "B"
    mock_player.setPosition.assert_called_with(22000)


def test_a14_history_manager_get_cached_analysis(history, tmp_path: Path):
    audio_path = tmp_path / "song.mp3"
    audio_path.write_bytes(b"data")

    # Initially empty
    assert history.getCachedAnalysis(audio_path) is None

    # Add entry without analysis
    history.addEntry("http://example.com", "Song", "audio", "MP3", str(audio_path), True, 100)
    assert history.getCachedAnalysis(audio_path) is None

    # Update with analysis
    analysis_data = {"key": "F# minor", "bpm": 128.0, "camelot": "11A", "confidence": 92}
    history.updateAnalysis(str(audio_path), analysis_data)

    cached = history.getCachedAnalysis(audio_path)
    assert cached is not None
    assert cached["key"] == "F# minor"
    assert cached["bpm"] == 128.0

    # Path normalization and case-insensitivity check
    case_path = Path(str(audio_path).upper() if sys.platform == "win32" else str(audio_path))
    cached_case = history.getCachedAnalysis(case_path)
    assert cached_case is not None
    assert cached_case["key"] == "F# minor"


def test_a14_audio_tools_instant_cache_hit(qtbot, config, history, tmp_path: Path):
    track = _create_wav(tmp_path / "cached_track.wav")
    analysis = {
        "key": "A minor",
        "bpm": 125.0,
        "camelot": "8A",
        "confidence": 95,
        "section_summary": "Stable: A minor",
        "peaks": [0.1, 0.4, 0.8],
        "duration_sec": 30.0,
    }

    # Add entry to history with analysis
    history.addEntry("http://example.com/track", "Track", "audio", "WAV", str(track), True, 1000)
    history.updateAnalysis(str(track), analysis)

    page = AudioToolsInterface(config, history)
    qtbot.addWidget(page)

    with patch.object(page, "_reanalyze") as mock_reanalyze:
        # Load without providing cached dict argument
        page.loadFile(track)
        # Should NOT trigger DSP re-analysis!
        assert not mock_reanalyze.called

    assert not page._busy
    assert page.detectedKeyCombo.currentText() == "A minor"
    assert page.bpmSpin.value() == 125.0
    assert "8A" in page.camelotLabel.text()


def test_a14_audio_tools_cache_miss_triggers_reanalyze(qtbot, config, history, tmp_path: Path):
    track = _create_wav(tmp_path / "uncached_track.wav")
    page = AudioToolsInterface(config, history)
    qtbot.addWidget(page)

    with patch.object(page, "_reanalyze") as mock_reanalyze:
        page.loadFile(track)
        assert mock_reanalyze.called


def test_a14_audio_tools_on_analyzed_updates_history(qtbot, config, history, tmp_path: Path):
    track = _create_wav(tmp_path / "fresh_track.wav")
    history.addEntry("http://example.com/fresh", "Fresh", "audio", "WAV", str(track), True, 500)

    page = AudioToolsInterface(config, history)
    qtbot.addWidget(page)
    page._source = track

    new_analysis = {"key": "D major", "bpm": 130.0, "camelot": "10B"}
    page._on_analyzed(new_analysis)

    cached = history.getCachedAnalysis(track)
    assert cached is not None
    assert cached["key"] == "D major"
    assert cached["bpm"] == 130.0


def test_a5_stem_separation_event_token_cancellation(tmp_path: Path):
    src = _create_wav(tmp_path / "event_song.wav")
    ev = threading.Event()
    ev.set()
    try:
        separate_stems(src, tmp_path, cancel_check=ev)
        assert False, "Should have raised cancelled on Event token"
    except RuntimeError as exc:
        assert "cancelled" in str(exc).lower()


def test_a5_audio_pitch_whitespace_stderr_handling(tmp_path: Path):
    from src.services.audio_pitch import _run_cmd

    with patch("src.services.audio_pitch.run_cancellable_process") as mock_proc:
        mock_proc.return_value = subprocess.CompletedProcess(
            args=["ffmpeg"], returncode=1, stdout="", stderr="   \n   \n   ",
        )
        try:
            _run_cmd(["ffmpeg", "-i", "dummy.wav"])
            assert False, "Should have raised RuntimeError"
        except RuntimeError as exc:
            assert "Audio processing failed" in str(exc)


def test_a8_transport_set_slot_b_none_cleans_source_and_resets_slot(tmp_path: Path):
    transport = AudioTransportController()
    wav_a = _create_wav(tmp_path / "track_a.wav")
    wav_b = _create_wav(tmp_path / "track_b.wav")
    transport.setSlotA(wav_a)
    transport.setSlotB(wav_b)

    mock_player = MagicMock()
    mock_player.playbackState.return_value = QMediaPlayer.PlaybackState.PlayingState
    mock_player.mediaStatus.return_value = QMediaPlayer.MediaStatus.LoadedMedia
    transport._player = mock_player

    transport.playSlot("B", 5.0)
    assert transport.activeSlot() == "B"
    assert transport._current_source == wav_b

    # Clearing Slot B should reset _current_source and switch slot back to A
    transport.setSlotB(None)
    assert transport._slot_b is None
    assert transport._current_source is None
    assert transport.activeSlot() == "A"
    assert not transport.isPlaying()


def test_a8_audio_tools_seek_while_stopped(qtbot, config, history, tmp_path: Path):
    wav = _create_wav(tmp_path / "stop_seek.wav")
    page = AudioToolsInterface(config, history)
    qtbot.addWidget(page)
    page.loadFile(wav, {"key": "C major", "bpm": 120.0})

    mock_player = MagicMock()
    mock_player.playbackState.return_value = QMediaPlayer.PlaybackState.StoppedState
    mock_player.mediaStatus.return_value = QMediaPlayer.MediaStatus.LoadedMedia
    page.transport._player = mock_player

    # Case 1: Before initial playback, waveform seek records pending seek
    page._on_seek_requested(18.0)
    assert "0:18" in page.statusLabel.text()
    assert page.transport._pending_seek_ms == 18000

    # Case 2: When source is loaded in transport, seeking while stopped calls setPosition directly
    page.transport._current_source = wav
    page._on_seek_requested(24.0)
    assert "0:24" in page.statusLabel.text()
    mock_player.setPosition.assert_called_with(24000)


def test_a8_transport_preserves_pending_seek_when_play_without_time(tmp_path: Path):
    transport = AudioTransportController()
    wav = _create_wav(tmp_path / "pending_seek.wav")
    transport.setSlotA(wav)

    mock_player = MagicMock()
    mock_player.playbackState.return_value = QMediaPlayer.PlaybackState.StoppedState
    mock_player.mediaStatus.return_value = QMediaPlayer.MediaStatus.LoadingMedia
    transport._player = mock_player

    # Set seek before starting playback
    transport.seek(25.0)
    assert transport._pending_seek_ms == 25000

    # Start playback without specifying start_sec (default None)
    transport.playSlot("A")
    # Must preserve the 25000ms pending seek rather than overwriting to 0
    assert transport._pending_seek_ms == 25000

    # Once loaded, deferred seek triggers
    transport._on_media_status(QMediaPlayer.MediaStatus.LoadedMedia)
    mock_player.setPosition.assert_called_with(25000)
    assert transport._pending_seek_ms is None


def test_a14_history_manager_caches_local_file_analysis(history, tmp_path: Path):
    local_song = tmp_path / "local_song.wav"
    local_song.write_bytes(b"RIFF dummy wav data")

    # Local file not yet in history
    assert history.getCachedAnalysis(local_song) is None

    # Audio Tools analyzes the local file and updates history
    analysis_data = {"key": "E minor", "bpm": 140.0, "camelot": "9A"}
    history.updateAnalysis(str(local_song), analysis_data)

    # Must be cached in history and immediately retrievable!
    cached = history.getCachedAnalysis(local_song)
    assert cached is not None
    assert cached["key"] == "E minor"
    assert cached["bpm"] == 140.0


def test_a14_history_manager_get_cached_empty_or_none(history):
    assert history.getCachedAnalysis(None) is None
    assert history.getCachedAnalysis("") is None


def test_a8_cleanup_stops_transport(qtbot, config, history, tmp_path: Path):
    wav = _create_wav(tmp_path / "cleanup_test.wav")
    page = AudioToolsInterface(config, history)
    qtbot.addWidget(page)
    page.loadFile(wav, {"key": "C major", "bpm": 120.0})

    mock_player = MagicMock()
    mock_player.playbackState.return_value = QMediaPlayer.PlaybackState.PlayingState
    page.transport._player = mock_player
    page.transport._playing = True

    page.cleanup()
    assert not page.transport.isPlaying()
    assert mock_player.stop.called
