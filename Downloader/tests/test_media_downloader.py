import os
import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

from src.domain.media_downloader import MediaDownloader
from src.domain.models import DownloadPreset, DownloadResult, JobState, MediaType
from src.domain.presets import PRESETS
from src.domain.utils import friendly_error


class SimulatedDownloadError(RuntimeError):
    """Failure raised by the fake provider in a retry-path test."""


def test_validate_url():
    dl = MediaDownloader()
    assert dl.validateUrl("https://youtube.com/watch?v=123") is True
    assert dl.validateUrl("http://example.com/file") is True
    assert dl.validateUrl("not_a_url") is False
    assert dl.validateUrl("ftp://example.com") is False


@patch("yt_dlp.YoutubeDL")
def test_inspect_video(mock_ydl):
    mock_instance = MagicMock()
    mock_instance.extract_info.return_value = {
        "title": "Test Video",
        "duration": 60,
        "thumbnail": "http://img.com",
        "uploader": "Test Uploader",
    }
    mock_ydl.return_value.__enter__.return_value = mock_instance

    dl = MediaDownloader()
    res = dl.inspect("https://example.com/video")
    assert res["type"] == "video"
    assert res["metadata"]["title"] == "Test Video"
    assert res["metadata"]["duration"] == 60
    assert res["metadata"]["uploader"] == "Test Uploader"


@patch("yt_dlp.YoutubeDL")
def test_inspect_playlist(mock_ydl):
    mock_instance = MagicMock()
    mock_instance.extract_info.return_value = {
        "title": "Test Playlist",
        "entries": [
            {"title": "Song 1", "webpage_url": "https://example.com/1"},
            {"title": "Song 2", "webpage_url": "https://example.com/2"},
        ]
    }
    mock_ydl.return_value.__enter__.return_value = mock_instance

    dl = MediaDownloader()
    res = dl.inspect("https://example.com/playlist")
    assert res["type"] == "playlist"
    assert res["title"] == "Test Playlist"
    assert res["count"] == 2
    assert res["entries"][0]["title"] == "Song 1"


@patch("yt_dlp.YoutubeDL")
def test_download_success(mock_ydl, tmp_path):
    mock_instance = MagicMock()
    mock_instance.extract_info.return_value = {
        "requested_downloads": [{"filepath": str(tmp_path / "downloaded.mp4")}],
        "_filename": str(tmp_path / "downloaded.mp4"),
    }
    mock_ydl.return_value.__enter__.return_value = mock_instance

    # Create dummy output file
    output_file = tmp_path / "downloaded.mp4"
    output_file.write_bytes(b"data")

    preset = DownloadPreset("video_mp4_720", "MP4 720p", MediaType.VIDEO, "mp4", video_height=720)
    dl = MediaDownloader()
    res = dl.download("https://example.com/video", tmp_path, preset)

    assert res.success is True
    assert res.state == JobState.COMPLETED
    assert res.file_path == output_file


def test_resolve_output_candidate_exists(tmp_path):
    dl = MediaDownloader()
    preset = DownloadPreset("video_mp4_720", "MP4 720p", MediaType.VIDEO, "mp4")
    
    file_path = tmp_path / "exist.mp4"
    file_path.write_bytes(b"data")

    info = {"_filename": str(file_path)}
    resolved = dl._resolve_output(tmp_path, info, preset, time.time())
    assert resolved == file_path


def test_resolve_output_mtime_fallback(tmp_path):
    dl = MediaDownloader()
    preset = DownloadPreset("video_mp4_720", "MP4 720p", MediaType.VIDEO, "mp4")

    # Write a file and simulate it was written during the download
    file_path = tmp_path / "fallback.mp4"
    file_path.write_bytes(b"data")

    info = {}  # Empty info to trigger mtime fallback
    resolved = dl._resolve_output(tmp_path, info, preset, time.time() - 1)
    assert resolved == file_path


def test_resolve_output_collision_mtime(tmp_path):
    dl = MediaDownloader()
    preset = DownloadPreset("video_mp4_720", "MP4 720p", MediaType.VIDEO, "mp4")

    # Create two files inside output folder with different mtimes
    file1 = tmp_path / "file1.mp4"
    file2 = tmp_path / "file2.mp4"
    
    file1.write_bytes(b"data1")
    file2.write_bytes(b"data2")
    
    # Explicitly set mtimes: file2 is newer
    now = time.time()
    os.utime(file1, (now - 1, now - 1))
    os.utime(file2, (now, now))

    # The fallback should return the newest file
    info = {}
    resolved = dl._resolve_output(tmp_path, info, preset, now - 2)
    assert resolved == file2


def test_friendly_error_names_a_recoverable_cause():
    assert "limiting requests" in friendly_error("HTTP Error 429: Too Many Requests")
    assert "partial download" in friendly_error("The read operation timed out")
    assert "DRM-protected" in friendly_error("This is DRM protected content")


@patch("yt_dlp.YoutubeDL")
def test_inspect_enables_deno_when_available(mock_ydl):
    mock_ydl.return_value.__enter__.return_value.extract_info.return_value = {"title": "Test"}
    MediaDownloader().inspect("https://example.com/video")
    options = mock_ydl.call_args.args[0]
    assert options["js_runtimes"]["deno"]["path"].lower().endswith(("deno.exe", "deno"))


def test_audio_all_preset_exists():
    """Verify the audio_all preset is defined in PRESETS."""
    audio_all = [p for p in PRESETS if p.key == "audio_all"]
    assert len(audio_all) == 1
    preset = audio_all[0]
    assert preset.media_type == MediaType.AUDIO
    assert preset.container == "all"
    assert "All formats" in preset.label


@patch("yt_dlp.YoutubeDL")
def test_download_all_audio_formats_routes_to_batch_download(mock_ydl):
    """Test that audio_all preset triggers the batch download method."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        dl = MediaDownloader()
        
        # Mock the batch download method to verify it's called
        with patch.object(dl, '_download_all_audio_formats') as mock_batch:
            mock_batch.return_value = MagicMock(success=True, state=JobState.COMPLETED)
            
            preset = DownloadPreset("audio_all", "Audio · All formats", MediaType.AUDIO, "all")
            dl.download("https://example.com/video", tmp_path, preset)
            
            mock_batch.assert_called_once()


@patch("yt_dlp.YoutubeDL")
def test_download_all_audio_formats_downloads_multiple_formats(mock_ydl):
    """Test that _download_all_audio_formats downloads each audio format."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        dl = MediaDownloader()
        
        # Track which formats were requested
        downloaded_formats = []
        
        def mock_extract_info(url, download=False):
            if download:
                # Simulate successful download for each format
                format_name = downloaded_formats[-1] if downloaded_formats else "mp3"
                output_file = tmp_path / f"test.{format_name}"
                output_file.write_bytes(b"fake audio data")
                return {
                    "requested_downloads": [{"filepath": str(output_file)}],
                    "_filename": str(output_file),
                }
            return {"title": "Test", "duration": 60}
        
        mock_instance = MagicMock()
        mock_instance.extract_info.side_effect = mock_extract_info
        mock_ydl.return_value.__enter__.return_value = mock_instance
        
        preset = DownloadPreset("audio_all", "Audio · All formats", MediaType.AUDIO, "all")
        
        # Mock native_kind to return False so we use yt-dlp
        with patch("src.domain.media_downloader.native_kind", return_value=False):
            result = dl._download_all_audio_formats("https://example.com/video", tmp_path, preset)
        
        # Verify the result indicates success
        assert result.success is True
        assert result.state == JobState.COMPLETED
        assert result.file_path is not None
        # Verify additional_files contains the other downloaded formats
        assert result.additional_files is not None
        assert len(result.additional_files) > 0


@patch("yt_dlp.YoutubeDL")
def test_download_all_audio_formats_handles_partial_failures(mock_ydl):
    """Test that _download_all_audio_formats continues even if some formats fail."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        dl = MediaDownloader()
        
        download_count = [0]
        
        def mock_extract_info(url, download=False):
            if download:
                download_count[0] += 1
                # Fail on the second download attempt
                if download_count[0] == 2:
                    raise SimulatedDownloadError("Simulated download failure")
                
                format_name = "mp3" if download_count[0] == 1 else "m4a"
                output_file = tmp_path / f"test.{format_name}"
                output_file.write_bytes(b"fake audio data")
                return {
                    "requested_downloads": [{"filepath": str(output_file)}],
                    "_filename": str(output_file),
                }
            return {"title": "Test", "duration": 60}
        
        mock_instance = MagicMock()
        mock_instance.extract_info.side_effect = mock_extract_info
        mock_ydl.return_value.__enter__.return_value = mock_instance
        
        preset = DownloadPreset("audio_all", "Audio · All formats", MediaType.AUDIO, "all")
        
        with patch("src.domain.media_downloader.native_kind", return_value=False):
            result = dl._download_all_audio_formats("https://example.com/video", tmp_path, preset)
        
        # Should still succeed with some files downloaded
        assert result.success is True
        assert result.state == JobState.COMPLETED
        # Error message should mention the failed format
        assert result.error is not None and len(result.error) > 0


@patch("yt_dlp.YoutubeDL")
def test_download_all_audio_formats_cancellation(mock_ydl, tmp_path):
    """Test that _download_all_audio_formats respects cancellation."""
    dl = MediaDownloader()
    
    download_count = [0]
    
    def mock_extract_info(url, download=False):
        if download:
            download_count[0] += 1
            # Cancel after first download
            if download_count[0] == 1:
                dl._cancel.set()
            
            output_file = tmp_path / "test.mp3"
            output_file.write_bytes(b"fake audio data")
            return {
                "requested_downloads": [{"filepath": str(output_file)}],
                "_filename": str(output_file),
            }
        return {"title": "Test", "duration": 60}
    
    mock_instance = MagicMock()
    mock_instance.extract_info.side_effect = mock_extract_info
    mock_ydl.return_value.__enter__.return_value = mock_instance
    
    preset = DownloadPreset("audio_all", "Audio · All formats", MediaType.AUDIO, "all")
    
    with patch("src.domain.media_downloader.native_kind", return_value=False):
        result = dl._download_all_audio_formats("https://example.com/video", tmp_path, preset)
    
    # Should be cancelled
    assert result.success is False
    assert result.state == JobState.CANCELLED


def test_download_all_audio_formats_progress_callback(tmp_path):
    """Test that progress callback properly aggregates batch progress."""
    dl = MediaDownloader()
    progress_updates = []

    def fake_download(_url, _output_dir, preset, callback):
        callback({"status": "downloading", "percent": 50, "speed": "1MB/s", "eta": "10s"})
        return DownloadResult(True, JobState.COMPLETED, file_path=tmp_path / f"test.{preset.container}")

    preset = DownloadPreset("audio_all", "Audio · All formats", MediaType.AUDIO, "all")
    with patch.object(dl, "_download_ytdlp", side_effect=fake_download), patch.object(dl, "_native_kind", return_value=False):
        result = dl._download_all_audio_formats("https://example.com/video", tmp_path, preset, progress_updates.append)

    assert result.success
    assert progress_updates[0]["percent"] == 6.25
    assert progress_updates[-1]["status"] == "processing"


def test_download_all_audio_formats_cleanup_partial_files(tmp_path):
    """Test that partial files are cleaned up before each format download."""
    dl = MediaDownloader()
    
    # Create some partial files
    (tmp_path / "test.mp3.part").write_bytes(b"partial")
    (tmp_path / "test.m4a.temp").write_bytes(b"temp")
    (tmp_path / "test.opus.ytdl").write_bytes(b"ytdl")
    
    # Verify they exist
    assert (tmp_path / "test.mp3.part").exists()
    assert (tmp_path / "test.m4a.temp").exists()
    assert (tmp_path / "test.opus.ytdl").exists()
    
    preset = DownloadPreset("audio_all", "Audio · All formats", MediaType.AUDIO, "all")
    result = MagicMock(success=True, file_path=tmp_path / "test.mp3", error="")
    with patch.object(dl, "_download_ytdlp", return_value=result), patch.object(dl, "_native_kind", return_value=False):
        dl._download_all_audio_formats("https://example.com/video", tmp_path, preset)

    assert not (tmp_path / "test.mp3.part").exists()
    assert not (tmp_path / "test.m4a.temp").exists()
    assert not (tmp_path / "test.opus.ytdl").exists()
