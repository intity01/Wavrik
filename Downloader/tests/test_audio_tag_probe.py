"""Tag reading must work with only the bundled ffmpeg.exe (no ffprobe shipped)."""

from __future__ import annotations

import wave
from pathlib import Path
from unittest.mock import patch

import pytest
from src.services import audio_tag_probe
from src.services.audio_tag_probe import parse_ffmetadata
from src.services.audio_tagger import AudioMetadata, apply_audio_metadata, read_audio_metadata


def test_parse_ffmetadata_handles_escapes_and_stops_at_sections():
    text = ";FFMETADATA1\ntitle=A \\= B\\;x\nartist=Multi\\\nline\n#comment=no\nencoder=Lavf\n[STREAM]\ntitle=stream\n"
    tags = parse_ffmetadata(text)
    assert tags["title"] == "A = B;x"
    assert tags["artist"] == "Multi\nline"
    assert "#comment" not in tags
    assert tags["encoder"] == "Lavf"


def test_parse_ffmetadata_crlf_and_empty():
    assert parse_ffmetadata("") == {}
    assert parse_ffmetadata(";FFMETADATA1\r\nTitle=X\r\n") == {"title": "X"}


def _real_ffmpeg() -> str | None:
    return audio_tag_probe._bin("ffmpeg")


@pytest.mark.skipif(_real_ffmpeg() is None, reason="FFmpeg not available")
def test_read_tags_without_ffprobe(tmp_path: Path):
    wav = tmp_path / "track.wav"
    with wave.open(str(wav), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(8000)
        w.writeframes(b"\x00\x00" * 8000)
    apply_audio_metadata(wav, AudioMetadata(title="No Probe Title", artist="Bundled FFmpeg"))
    ffmpeg = _real_ffmpeg()
    with patch.object(audio_tag_probe, "_bin", side_effect=lambda name: ffmpeg if name == "ffmpeg" else None):
        meta = read_audio_metadata(wav)
    assert meta.title == "No Probe Title"
    assert meta.artist == "Bundled FFmpeg"
