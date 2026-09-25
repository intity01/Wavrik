"""Supported beginner-friendly presets."""

from __future__ import annotations

from .models import DownloadPreset, MediaType

PRESETS = (
    DownloadPreset("audio_mp3_320", "Audio · MP3 · 320 kbps", MediaType.AUDIO, "mp3", audio_bitrate="320"),
    DownloadPreset("audio_mp3_256", "Audio · MP3 · 256 kbps", MediaType.AUDIO, "mp3", audio_bitrate="256"),
    DownloadPreset("audio_mp3_192", "Audio · MP3 · 192 kbps", MediaType.AUDIO, "mp3", audio_bitrate="192"),
    DownloadPreset("audio_mp3_128", "Audio · MP3 · 128 kbps", MediaType.AUDIO, "mp3", audio_bitrate="128"),
    DownloadPreset("audio_m4a_best", "Audio · M4A · Best available", MediaType.AUDIO, "m4a", audio_bitrate="0"),
    DownloadPreset("audio_aac_256", "Audio · AAC · 256 kbps", MediaType.AUDIO, "aac", audio_bitrate="256"),
    DownloadPreset("audio_aac_192", "Audio · AAC · 192 kbps", MediaType.AUDIO, "aac", audio_bitrate="192"),
    DownloadPreset("audio_aac_128", "Audio · AAC · 128 kbps", MediaType.AUDIO, "aac", audio_bitrate="128"),
    DownloadPreset("audio_vorbis_256", "Audio · Vorbis · 256 kbps", MediaType.AUDIO, "vorbis", audio_bitrate="256"),
    DownloadPreset("audio_vorbis_192", "Audio · Vorbis · 192 kbps", MediaType.AUDIO, "vorbis", audio_bitrate="192"),
    DownloadPreset("audio_vorbis_128", "Audio · Vorbis · 128 kbps", MediaType.AUDIO, "vorbis", audio_bitrate="128"),
    DownloadPreset("audio_opus_256", "Audio · OPUS · 256 kbps", MediaType.AUDIO, "opus", audio_bitrate="256"),
    DownloadPreset("audio_opus_192", "Audio · OPUS · 192 kbps", MediaType.AUDIO, "opus", audio_bitrate="192"),
    DownloadPreset("audio_opus_128", "Audio · OPUS · 128 kbps", MediaType.AUDIO, "opus", audio_bitrate="128"),
    DownloadPreset("audio_flac_lossless", "Audio · FLAC · Lossless", MediaType.AUDIO, "flac", audio_bitrate="0"),
    DownloadPreset("audio_wav_lossless", "Audio · WAV · Lossless", MediaType.AUDIO, "wav", audio_bitrate="0"),
    DownloadPreset("audio_alac_lossless", "Audio · ALAC · Lossless", MediaType.AUDIO, "alac", audio_bitrate="0"),
    DownloadPreset("audio_best", "Audio · Best quality available", MediaType.AUDIO, "best", audio_bitrate="0"),
    DownloadPreset("audio_all", "Audio · All formats (batch)", MediaType.AUDIO, "all", audio_bitrate="0"),
    DownloadPreset("video_mp4_2160", "Video · MP4 · Up to 2160p", MediaType.VIDEO, "mp4", video_height=2160),
    DownloadPreset("video_mp4_1440", "Video · MP4 · Up to 1440p", MediaType.VIDEO, "mp4", video_height=1440),
    DownloadPreset("video_mp4_1080", "Video · MP4 · Up to 1080p", MediaType.VIDEO, "mp4", video_height=1080),
    DownloadPreset("video_mp4_720", "Video · MP4 · Up to 720p", MediaType.VIDEO, "mp4", video_height=720),
    DownloadPreset("video_mp4_480", "Video · MP4 · Up to 480p", MediaType.VIDEO, "mp4", video_height=480),
    DownloadPreset("video_mp4_best", "Video · MP4 · Best available", MediaType.VIDEO, "mp4"),
    DownloadPreset("video_mkv_1080", "Video · MKV · Up to 1080p", MediaType.VIDEO, "mkv", video_height=1080),
    DownloadPreset("video_webm_1080", "Video · WEBM · Up to 1080p", MediaType.VIDEO, "webm", video_height=1080),
    DownloadPreset("video_avi_720", "Video · AVI · Up to 720p", MediaType.VIDEO, "avi", video_height=720),
)

_BY_KEY = {preset.key: preset for preset in PRESETS}
_BY_LABEL = {preset.label: preset for preset in PRESETS}


def getPreset(key_or_label: str | None) -> DownloadPreset:
    if key_or_label in _BY_KEY:
        return _BY_KEY[key_or_label]
    if key_or_label in _BY_LABEL:
        return _BY_LABEL[key_or_label]
    return PRESETS[0]


def labels() -> list[str]:
    return [preset.label for preset in PRESETS]
