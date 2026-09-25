import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.core.updater import UpdateManager
from src.domain.models import DownloadResult, JobState
from src.ui.components.queue_card import QueueItemCard
from src.ui.main_window import MediaDownloaderUI
from src.ui.workers.download_worker import DownloadWorker
from src.ui.workers.signals import WorkerSignals


def _window(qtbot, config, logger, fake_downloader, history):
    tray = MagicMock()
    tray.isAvailable.return_value = False
    window = MediaDownloaderUI(
        config, logger, fake_downloader,
        UpdateManager("2.0.0", "owner/repo", logger), tray, history,
    )
    qtbot.addWidget(window)
    window.show()
    return window


def test_beginner_flow_add_download_and_history(qtbot, config, logger, fake_downloader, history):
    window = _window(qtbot, config, logger, fake_downloader, history)
    page = window.pageWorkspace
    page.addUrl("https://example.com/video")
    qtbot.waitUntil(lambda: page._cards["https://example.com/video"].getVideoTitle() == "Example media")
    card = page._cards["https://example.com/video"]
    card._handle_action()
    qtbot.waitUntil(lambda: card._state == "completed")
    assert history.getHistory()[0]["success"] is True
    assert history.getHistory()[0]["filePath"]


def test_invalid_and_duplicate_urls_are_explained(qtbot, config, logger, fake_downloader, history):
    window = _window(qtbot, config, logger, fake_downloader, history)
    page = window.pageWorkspace
    page.addUrl("not a url")
    assert page.inputBar.errorLabel.isVisible()
    page.addUrl("https://example.com/video")
    page.addUrl("https://example.com/video")
    assert "already" in page.inputBar.errorLabel.text().lower()


def test_history_redownload_returns_to_workspace(qtbot, config, logger, fake_downloader, history):
    history.addEntry("https://example.com/retry", "Retry", "video", "MP4", "", False, status="failed")
    window = _window(qtbot, config, logger, fake_downloader, history)
    window.pageHistory.redownloadRequested.emit("https://example.com/retry")
    assert window.stackedWidget.currentWidget() is window.pageWorkspace
    assert "https://example.com/retry" in window.pageWorkspace._cards


def test_download_options_are_on_workspace_and_apply_to_pending_items(
    qtbot, config, logger, fake_downloader, history,
):
    window = _window(qtbot, config, logger, fake_downloader, history)
    page = window.pageWorkspace
    options = page.downloadOptions
    options.mediaCombo.setCurrentText("Video")
    index = next(
        i for i in range(options.presetCombo.count())
        if options.presetCombo.itemData(i) == "video_mp4_720"
    )
    options.presetCombo.setCurrentIndex(index)
    page.addUrl("https://example.com/video-options")
    card = page._cards["https://example.com/video-options"]
    assert card.selectedPreset().key == "video_mp4_720"
    assert not hasattr(card, "comboFormat")
    assert page.downloadOptions.downloadAllButton.isEnabled()


def test_download_engine_is_visible_and_snapshotted_for_a_queued_item(
    qtbot, config, logger, fake_downloader, history,
):
    window = _window(qtbot, config, logger, fake_downloader, history)
    options = window.pageWorkspace.downloadOptions
    options.engineCombo.setCurrentIndex(options.engineCombo.findData("native"))
    window.pageWorkspace.addUrl("https://example.com/video-native")
    card = window.pageWorkspace._cards["https://example.com/video-native"]
    assert card.selectedEngine() == "native"
    assert "Native" in card._engineLabel.text()


def test_download_waits_for_link_check_before_enabling_action(qtbot, config):
    card = QueueItemCard("https://example.com/wait", config)
    qtbot.addWidget(card)
    assert not card._btnDl.isEnabled()
    card.setStatus("ready", "Ready to download")
    assert card._btnDl.isEnabled()
    assert "start" in card._btnDl.accessibleDescription().lower()


def test_state_toggles_expose_on_and_off_text(
    qtbot, config, logger, fake_downloader, history,
):
    window = _window(qtbot, config, logger, fake_downloader, history)
    toggle = window.pageSettings.clipboardCheck
    assert toggle.text() == "On"
    toggle.setChecked(False)
    assert toggle.text() == "Off"
    assert "off" in toggle.accessibleDescription()


def test_returning_users_see_a_compact_empty_queue(qtbot, config, logger, fake_downloader, history):
    config.update(firstRun=False)
    window = _window(qtbot, config, logger, fake_downloader, history)
    assert window.pageWorkspace.emptyState.title.text() == "Your queue is empty"
    labels = [label.text() for label in window.pageWorkspace.emptyState.findChildren(type(window.pageWorkspace.emptyState.title))]
    assert "Add a link" not in labels


def test_unconfigured_updater_is_disabled(qtbot, config, logger, fake_downloader, history):
    tray = MagicMock()
    tray.isAvailable.return_value = False
    window = MediaDownloaderUI(
        config, logger, fake_downloader,
        UpdateManager("2.0.0", "", logger), tray, history,
    )
    qtbot.addWidget(window)
    assert not window.pageSettings.updateCard.checkButton.isEnabled()
    assert "not configured" in window.pageSettings.updateCard.statusLabel.text().lower()


def test_empty_history_explains_what_will_appear(qtbot, config, logger, fake_downloader, history):
    window = _window(qtbot, config, logger, fake_downloader, history)
    assert window.pageHistory.summary.text() == "No downloads recorded yet."
    assert "will appear" in window.pageHistory.emptyLabel.text()


def test_folder_creation_failure_shows_error_on_card(qtbot, config, logger, fake_downloader, history):
    window = _window(qtbot, config, logger, fake_downloader, history)
    page = window.pageWorkspace
    page.addUrl("https://example.com/video")
    qtbot.waitUntil(lambda: page._cards["https://example.com/video"].getVideoTitle() == "Example media")
    
    card = page._cards["https://example.com/video"]
    
    # Mock getDownloadPath to raise permission error
    with patch.object(page._cfg, 'getDownloadPath', side_effect=PermissionError("Access denied")):
        card._handle_action()
        qtbot.waitUntil(lambda: card._state == "failed")
        assert "access" in card._lblStatus.text().lower() or "denied" in card._lblStatus.text().lower()


def test_direct_media_url_becomes_ready_without_yt_dlp(qtbot, config, logger, fake_downloader, history):
    window = _window(qtbot, config, logger, fake_downloader, history)
    page = window.pageWorkspace
    
    # Add a direct .mp4 URL - should become ready without yt-dlp metadata
    page.addUrl("https://example.com/video.mp4")
    qtbot.waitUntil(lambda: page._cards["https://example.com/video.mp4"]._state == "ready")
    
    card = page._cards["https://example.com/video.mp4"]
    assert card._state == "ready"
    assert "video.mp4" in card.getVideoTitle()


def test_download_worker_exception_handling(qtbot, config, logger, fake_downloader, history):
    window = _window(qtbot, config, logger, fake_downloader, history)
    page = window.pageWorkspace
    page.addUrl("https://example.com/video")
    qtbot.waitUntil(lambda: page._cards["https://example.com/video"].getVideoTitle() == "Example media")
    
    card = page._cards["https://example.com/video"]
    
    # Create a worker that will raise an exception
    signals = WorkerSignals()
    error_received = []
    
    def on_error(url, message):
        error_received.append(message)
    
    signals.error.connect(on_error)
    
    # Mock the downloader to raise an exception
    with patch.object(fake_downloader, 'newSession', return_value=fake_downloader), patch.object(
        fake_downloader, 'download', side_effect=RuntimeError("Test error")
    ):
        worker = DownloadWorker(
            "https://example.com/video", fake_downloader, card.selectedPreset(),
            page._cfg.getDownloadPath("video"), signals, history, card.getVideoTitle(), "auto"
        )
        worker.run()
    
    # Verify error was caught and reported
    assert len(error_received) > 0
    assert "download failed" in error_received[0].lower()


def test_error_message_preserved_after_finish(qtbot, config, logger, fake_downloader, history):
    window = _window(qtbot, config, logger, fake_downloader, history)
    page = window.pageWorkspace
    page.addUrl("https://example.com/video")
    qtbot.waitUntil(lambda: page._cards["https://example.com/video"].getVideoTitle() == "Example media")
    
    card = page._cards["https://example.com/video"]
    
    # Simulate a failed download with specific error message
    result = DownloadResult(False, JobState.FAILED, error="This is a specific error message", engine="auto")
    card.finish(result)
    
    # Verify the specific error message is preserved
    assert "specific error message" in card._lblStatus.text()


def test_completed_card_handles_missing_file(qtbot, config, logger, fake_downloader, history):
    window = _window(qtbot, config, logger, fake_downloader, history)
    page = window.pageWorkspace
    page.addUrl("https://example.com/video")
    qtbot.waitUntil(lambda: page._cards["https://example.com/video"].getVideoTitle() == "Example media")
    
    card = page._cards["https://example.com/video"]
    
    # Create a temporary file and then delete it
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        temp_path = Path(tmp.name)
    
    # Set card to completed with the temp file path
    result = DownloadResult(True, JobState.COMPLETED, file_path=temp_path, engine="auto")
    card.finish(result)
    
    # Delete the file
    temp_path.unlink()
    
    # Try to open folder - should show error
    card._handle_action()
    assert card._state == "failed"
    assert "no longer exists" in card._lblStatus.text().lower() or "moved" in card._lblStatus.text().lower()
