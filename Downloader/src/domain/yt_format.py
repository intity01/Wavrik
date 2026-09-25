"""Format selectors and post-processing options."""

from __future__ import annotations

from .models import DownloadPreset


def format_selector(preset: DownloadPreset) -> str:
    if preset.media_type == "audio":
        return _audio_selector(preset.container)
    if preset.video_height:
        height = preset.video_height
        return f"bestvideo[height<={height}]+bestaudio/best[height<={height}]/best"
    return "bestvideo+bestaudio/best"


def apply_preset_options(options: dict, preset: DownloadPreset) -> None:
    if preset.media_type == "audio" and preset.container not in {"best", "all"}:
        options["postprocessors"] = [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": preset.container,
            "preferredquality": preset.audio_bitrate or "0",
        }]
    elif preset.media_type != "audio":
        options["merge_output_format"] = preset.container


def template(pattern: str) -> str:
    safe = pattern or "{title}"
    for key, value in {
        "{title}": "%(title)s",
        "{uploader}": "%(uploader)s",
        "{id}": "%(id)s",
    }.items():
        safe = safe.replace(key, value)
    return safe


def _audio_selector(container: str) -> str:
    selectors = {
        "best": "bestaudio/best",
        "all": "bestaudio",
        "mp3": "bestaudio[ext=mp3]/bestaudio/best",
        "m4a": "bestaudio[ext=m4a]/bestaudio[ext=aac]/bestaudio/best",
        "aac": "bestaudio[ext=aac]/bestaudio[ext=m4a]/bestaudio/best",
        "vorbis": "bestaudio[ext=ogg]/bestaudio/best",
        "opus": "bestaudio[ext=opus]/bestaudio/best",
        "flac": "bestaudio[ext=flac]/bestaudio/best",
        "wav": "bestaudio[ext=wav]/bestaudio/best",
        "alac": "bestaudio[ext=m4a]/bestaudio/best",
    }
    return selectors.get(container, "bestaudio/best")
