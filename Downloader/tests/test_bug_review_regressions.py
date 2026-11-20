"""Regression tests for bugs found during the code review."""

from __future__ import annotations

import threading
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.core.config import Config
from src.domain import yt_download
from src.domain.models import DownloadPreset, JobState, MediaType
from src.services.audio_lyrics import format_lrc_timestamp, format_srt_timestamp
from src.ui.components.queue_card import QueueItemCard
from src.ui.components.queue_card_state import engine_label
from src.ui.pages.audio_tools_page import AudioToolsInterface
from src.ui.workers.audio_worker import AudioToolSignals
from src.ui.workers.update_worker import CheckUpdateWorker, DownloadUpdateWorker, UpdateSignals


@pytest.mark.parametrize(
    ("seconds", "expected"),
    [(0, "[00:00.00]"), (59.996, "[01:00.00]"), (119.996, "[02:00.00]"), (75.5, "[01:15.50]")],
)
def test_lrc_timestamp_never_renders_sixty_seconds(seconds, expected):
    assert format_lrc_timestamp(seconds) == expected


@pytest.mark.parametrize(
    ("seconds", "expected"),
    [(1.2, "00:00:01,200"), (59.9996, "00:01:00,000"), (3661.001, "01:01:01,001")],
)
def test_srt_timestamp_rounds_milliseconds(seconds, expected):
    assert format_srt_timestamp(seconds) == expected


def test_failed_analysis_placeholder_is_not_cached(history, tmp_path: Path):
    track = tmp_path / "broken.mp3"
    track.write_bytes(b"x")
    placeholder = {"key": "C major", "camelot": "8B", "bpm": 120.0, "status": "unavailable"}
    history.updateAnalysis(track, placeholder)
    assert history.getCachedAnalysis(track) is None
    assert history.getHistory() == []


def test_unreadable_settings_file_is_not_quarantined(tmp_path: Path):
    app_dir = tmp_path / "appdata"
    first = Config(app_dir)
    first.set("theme", "dark")
    assert first.saveSettings()
    with patch.object(Path, "read_text", side_effect=OSError("Sharing violation")):
        Config(app_dir)
    assert (app_dir / "settings.json").exists()
    assert not list(app_dir.glob("settings.json*.corrupt")) and not (app_dir / "settings.json.corrupt").exists()


def test_cobalt_engine_choice_is_kept_on_queue_card(qtbot, config):
    card = QueueItemCard("https://example.com/video", config)
    qtbot.addWidget(card)
    card.setStatus("ready", "Ready")
    card.setEngine("cobalt")
    assert card.selectedEngine() == "cobalt"
    assert engine_label("cobalt") == "Cobalt"
    assert engine_label("unknown") == "Auto"


class _ExplodingManager:
    def checkForUpdates(self):
        raise OSError("disk full")

    def downloadVerified(self, *_args):
        raise ValueError("bad content-length")


@pytest.mark.parametrize("make_worker", [
    lambda manager, signals: CheckUpdateWorker(manager, signals),
    lambda manager, signals: DownloadUpdateWorker(manager, object(), Path("."), signals),
])
def test_update_workers_report_unexpected_errors(qtbot, make_worker):
    signals = UpdateSignals()
    with qtbot.waitSignal(signals.error, timeout=1000) as blocker:
        make_worker(_ExplodingManager(), signals).run()
    assert "update" in blocker.args[0].lower()


def test_superseded_job_results_are_ignored(qtbot, config, history, tmp_path: Path):
    first, second = tmp_path / "a.wav", tmp_path / "b.wav"
    first.write_bytes(b"RIFF")
    second.write_bytes(b"RIFF")
    page = AudioToolsInterface(config, history)
    qtbot.addWidget(page)
    cached = {"key": "D major", "bpm": 100.0, "camelot": "10B"}
    page.loadFile(first, cached=cached)

    stale = AudioToolSignals()
    stale.analyzed.connect(page._on_analyzed)
    page._signals = stale
    page.loadFile(second, cached=cached)

    completed: list[dict] = []
    page.analysisCompleted.connect(completed.append)
    stale.analyzed.emit({"key": "A minor", "bpm": 70.0, "camelot": "8A"})
    assert completed == []
    assert page._source == second


class _CancelEvent(threading.Event):
    def wait(self, timeout=None):
        return False


class _FakeOwner:
    def __init__(self):
        self._cancel = _CancelEvent()
        self.config = None
        self.logger = MagicMock()
        self.lastDownloadedFile = None

    def _progress_hook(self, _callback):
        return lambda _data: None


def test_yt_download_reports_last_error_after_retries(tmp_path: Path):
    preset = DownloadPreset("audio_best", "Best", MediaType.AUDIO, "best", audio_bitrate="0")
    attempts = []

    class FailingYoutubeDL:
        def __init__(self, _options):
            attempts.append(1)

        def __enter__(self):
            return self

        def __exit__(self, *_exc):
            return False

        def extract_info(self, *_args, **_kwargs):
            raise RuntimeError("HTTP Error 429: Too Many Requests")

    with patch("yt_dlp.YoutubeDL", FailingYoutubeDL):
        result = yt_download.download(_FakeOwner(), "https://example.com/v", tmp_path, preset, None)
    assert len(attempts) == yt_download.MAX_ATTEMPTS
    assert result.state == JobState.FAILED
    assert "limiting requests" in result.error
