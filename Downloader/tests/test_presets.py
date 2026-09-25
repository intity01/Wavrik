import tempfile
from pathlib import Path

from src.domain.presets import PRESETS, getPreset
from src.domain.yt_options import YtDownloadSettings, buildOptions


def test_audio_and_video_quality_are_not_cross_wired(tmp_path: Path):
    audio = getPreset("audio_mp3_320")
    video = getPreset("video_mp4_1080")
    settings = YtDownloadSettings()
    audio_options = buildOptions(tmp_path, audio, lambda _data: None, settings)
    video_options = buildOptions(tmp_path, video, lambda _data: None, settings)
    assert audio_options["postprocessors"][0]["preferredquality"] == "320"
    assert "height<=1080" in video_options["format"]
    assert "postprocessors" not in video_options
    assert video_options["socket_timeout"] == 30


def test_download_options_retry_network_failures_without_skipping_fragments(tmp_path: Path):
    preset = getPreset("video_mp4_1080")
    options = buildOptions(tmp_path, preset, lambda _data: None, YtDownloadSettings())
    assert options["retries"] == 5
    assert options["fragment_retries"] == 5
    assert options["skip_unavailable_fragments"] is False
    assert options["retry_sleep_functions"]["http"](0) == 1
    assert options["retry_sleep_functions"]["http"](4) == 10
    assert options["js_runtimes"]["deno"]["path"].lower().endswith(("deno.exe", "deno"))


def test_audio_all_preset_is_accessible():
    """Verify the audio_all preset exists and can be retrieved."""
    audio_all = getPreset("audio_all")
    assert audio_all is not None
    assert audio_all.key == "audio_all"
    assert audio_all.container == "all"
    assert "All formats" in audio_all.label


def test_audio_all_preset_allows_overwrites():
    """Verify that audio_all preset disables nooverwrites to support batch downloads."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        audio_all = getPreset("audio_all")
        options = buildOptions(tmp_path, audio_all, lambda _data: None, YtDownloadSettings())
        # nooverwrites should be False for "all" container to allow multiple formats
        assert options["nooverwrites"] is False


def test_all_audio_formats_present_in_presets():
    """Verify all expected audio formats are present in PRESETS."""
    audio_containers = {p.container for p in PRESETS if p.media_type.value == "audio"}
    expected_formats = {"mp3", "m4a", "aac", "vorbis", "opus", "flac", "wav", "alac", "best", "all"}
    assert expected_formats.issubset(audio_containers)


def test_audio_all_ui_label_format():
    """Verify the audio_all preset has a proper UI label."""
    audio_all = getPreset("audio_all")
    # The label should be user-friendly and indicate it's a batch download
    assert "batch" in audio_all.label.lower() or "all" in audio_all.label.lower()
    # It should start with "Audio" to indicate media type
    assert audio_all.label.startswith("Audio")


def test_audio_all_included_in_audio_presets_list():
    """Verify audio_all is included when filtering audio presets."""
    audio_presets = [p for p in PRESETS if p.media_type.value == "audio"]
    audio_all_in_list = any(p.key == "audio_all" for p in audio_presets)
    assert audio_all_in_list, "audio_all preset should be in the audio presets list"
