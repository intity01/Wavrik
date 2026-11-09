"""Comprehensive unit and integration tests for AcoustID audio fingerprinting and metadata tagging."""

from __future__ import annotations

from array import array
import math
from pathlib import Path
from unittest.mock import MagicMock
import wave

import numpy as np
from PyQt6.QtWidgets import QApplication
import pytest

from src.core.config import Config
from src.services.audio_acoustid import (
    lookup_acoustid,
    lookup_audio_file,
    lookup_musicbrainz_recording,
    parse_filename_heuristic,
)
from src.services.audio_fingerprint import (
    decode_fingerprint_base64,
    encode_fingerprint_base64,
    fingerprint_audio_file,
    fingerprint_similarity,
    generate_chromaprint,
)
from src.services.audio_tagger import AudioMetadata, apply_audio_metadata, read_audio_metadata
from src.ui.components.audio_tag_dialog import AudioTagDialog
from src.ui.pages.audio_tools_page import AudioToolsInterface


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def _create_wav(path: Path, duration: float = 3.0, sr: int = 16000) -> Path:
    freqs = (440.0, 554.37, 659.25)
    samples = array("h")
    total = int(duration * sr)
    for i in range(total):
        t = i / float(sr)
        val = sum(math.sin(2.0 * math.pi * f * t) for f in freqs) / len(freqs)
        samples.append(int(val * 0.8 * 32767))
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(samples.tobytes())
    return path


def test_chromaprint_synthetic_signal():
    sr = 16000
    t = np.linspace(0, 3.0, sr * 3, endpoint=False, dtype=np.float32)
    sig = 0.5 * np.sin(2 * np.pi * 440.0 * t) + 0.3 * np.sin(2 * np.pi * 880.0 * t)
    fp = generate_chromaprint (sig, sr)
    assert isinstance(fp, list)
    assert len(fp) > 0
    assert all(isinstance(x, int) for x in fp)

    short_sig = sig[:500]
    fp_short = generate_chromaprint (short_sig, sr)
    assert fp_short == []


def test_fingerprint_base64_roundtrip():
    test_ints = [1048576, 2097152, 4194304, 8388608, 16777216]
    b64 = encode_fingerprint_base64 (test_ints)
    assert isinstance(b64, str)
    assert len(b64) > 0
    recovered = decode_fingerprint_base64 (b64)
    assert recovered == test_ints

    assert encode_fingerprint_base64 ([]) == ""
    assert decode_fingerprint_base64 ("") == []


def test_fingerprint_similarity_metrics():
    fp1 = [0xAAAAAAAA, 0x55555555, 0x0F0F0F0F, 0xF0F0F0F0]
    assert fingerprint_similarity (fp1, fp1) == 1.0

    fp2 = [0xAAAAAAAA, 0x55555555, 0x0F0F0F0F, 0xF0F0F0F1]
    sim = fingerprint_similarity (fp1, fp2)
    assert 0.95 <= sim <= 1.0

    fp3 = [0x00000000, 0x00000000, 0x00000000, 0x00000000]
    assert fingerprint_similarity (fp1, fp3) <= 0.6
    assert fingerprint_similarity ([], fp1) == 0.0


def test_fingerprint_audio_file(tmp_path: Path):
    wav = _create_wav(tmp_path / "test_synth.wav", duration=2.5)
    dur, b64 = fingerprint_audio_file (wav, max_sec=10)
    assert dur >= 2
    assert isinstance(b64, str)
    assert len(b64) > 10


def test_acoustid_response_parser_mock():
    mock_payload = {
        "status": "ok",
        "results": [
            {
                "score": 0.95,
                "recordings": [
                    {
                        "id": "rec-123",
                        "title": "Bohemian Rhapsody",
                        "artists": [{"name": "Queen"}],
                        "releasegroups": [{"title": "A Night at the Opera"}],
                    }
                ],
            }
        ],
    }
    mock_fn = MagicMock(return_value=mock_payload)
    res = lookup_acoustid(180, "AQAA...", request_fn=mock_fn)
    assert res["status"] == "ok"
    assert res["title"] == "Bohemian Rhapsody"
    assert res["artist"] == "Queen"
    assert res["album"] == "A Night at the Opera"
    assert res["mbid"] == "rec-123"
    assert res["score"] == 0.95


def test_acoustid_response_not_found_and_error():
    mock_empty = {"status": "ok", "results": []}
    res_empty = lookup_acoustid(60, "fp", request_fn=MagicMock(return_value=mock_empty))
    assert res_empty["status"] == "not_found"

    mock_err = {"status": "error", "error": {"message": "Invalid API key"}}
    res_err = lookup_acoustid(60, "fp", request_fn=MagicMock(return_value=mock_err))
    assert res_err["status"] == "error"
    assert "Invalid API key" in res_err["error"]

    def throwing_fn(*_a, **_kw):
        raise ConnectionResetError("Connection dropped")

    res_throw = lookup_acoustid(60, "fp", request_fn=throwing_fn)
    assert res_throw["status"] == "error"


def test_musicbrainz_lookup_and_cache():
    mb_payload = {
        "title": "Stairway to Heaven",
        "artist-credit": [{"name": "Led Zeppelin", "joinphrase": ""}],
        "releases": [
            {
                "title": "Led Zeppelin IV",
                "date": "1971-11-08",
                "media": [{"track": [{"number": "4"}]}],
            }
        ],
        "genres": [{"name": "hard rock"}],
    }
    mock_fn = MagicMock(return_value=mb_payload)
    res = lookup_musicbrainz_recording("mb-999", request_fn=mock_fn)
    assert res["status"] == "ok"
    assert res["title"] == "Stairway to Heaven"
    assert res["artist"] == "Led Zeppelin"
    assert res["album"] == "Led Zeppelin IV"
    assert res["date"] == "1971-11-08"
    assert res["track"] == "4"
    assert res["genre"] == "Hard rock"

    # Second call uses cache without calling mock_fn
    res2 = lookup_musicbrainz_recording("mb-999", request_fn=mock_fn)
    assert res2["title"] == "Stairway to Heaven"
    assert mock_fn.call_count == 1


def test_parse_filename_heuristic():
    h1 = parse_filename_heuristic("Queen - Bohemian Rhapsody [Official HD].mp3")
    assert h1["artist"] == "Queen"
    assert h1["title"] == "Bohemian Rhapsody"

    h2 = parse_filename_heuristic("03 - Pink Floyd - Time.flac")
    assert h2["track"] == "03"
    assert h2["artist"] == "Pink Floyd"
    assert h2["title"] == "Time"

    h3 = parse_filename_heuristic("Artist - Album - 05 - Track Name.m4a")
    assert h3["artist"] == "Artist"
    assert h3["album"] == "Album"
    assert h3["track"] == "05"
    assert h3["title"] == "Track Name"

    h4 = parse_filename_heuristic("07 Standalone Song.wav")
    assert h4["track"] == "07"
    assert h4["title"] == "Standalone Song"


def test_lookup_audio_file_flow(tmp_path: Path, monkeypatch):
    wav = _create_wav(tmp_path / "test_flow.wav", duration=1.5)
    acoust_res = {
        "status": "ok",
        "title": "Flow Title",
        "artist": "Flow Artist",
        "album": "",
        "mbid": "flow-mbid",
        "score": 0.98,
    }
    mb_res = {
        "status": "ok",
        "title": "Flow Title",
        "artist": "Flow Artist",
        "album": "Flow Album",
        "date": "2024",
        "track": "1",
        "genre": "Rock",
        "mbid": "flow-mbid",
    }
    monkeypatch.setattr("src.services.audio_acoustid.lookup_acoustid", lambda *a, **k: dict(acoust_res))
    monkeypatch.setattr("src.services.audio_acoustid.lookup_musicbrainz_recording", lambda *a, **k: dict(mb_res))

    res = lookup_audio_file(wav)
    assert res["status"] == "ok"
    assert res["album"] == "Flow Album"
    assert res["date"] == "2024"
    assert res["track"] == "1"


def test_audio_tagger_wav_lossless_roundtrip(tmp_path: Path):
    wav = _create_wav(tmp_path / "track.wav", duration=1.0)
    meta = AudioMetadata(
        title="Lossless Title",
        artist="Lossless Artist",
        album="Lossless Album",
        date="2025",
        track="2",
        genre="Ambient",
        comment="Test comment",
    )
    res_path = apply_audio_metadata(wav, meta)
    assert res_path == wav
    assert wav.is_file()

    read_back = read_audio_metadata(wav)
    assert read_back.title == "Lossless Title"
    assert read_back.artist == "Lossless Artist"
    assert read_back.album == "Lossless Album"


def test_audio_tagger_with_target_file(tmp_path: Path):
    src_wav = _create_wav(tmp_path / "source.wav", duration=1.0)
    dst_wav = tmp_path / "output_dir" / "tagged.wav"
    meta = AudioMetadata(title="Target Title", artist="Target Artist")
    out = apply_audio_metadata(src_wav, meta, target=dst_wav)
    assert out == dst_wav
    assert dst_wav.is_file()
    assert src_wav.is_file()


def test_audio_tagger_cover_art_skip_wav(tmp_path: Path):
    wav = _create_wav(tmp_path / "with_cover.wav", duration=1.0)
    cover = tmp_path / "cover.jpg"
    cover.write_bytes(b"\xFF\xD8\xFF\xE0" + b"\x00" * 100)
    meta = AudioMetadata(title="Song", artist="Artist", cover_path=str(cover))
    out = apply_audio_metadata(wav, meta)
    assert out.is_file()


def test_audio_tagger_nonexistent_file(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        apply_audio_metadata(tmp_path / "ghost.mp3", AudioMetadata(title="Ghost"))


def test_audio_tag_dialog_ui(qapp, tmp_path: Path):
    wav = _create_wav(tmp_path / "dialog_test.wav", duration=1.0)
    dialog = AudioTagDialog(wav)
    dialog.titleEdit.setText("Custom Title")
    dialog.artistEdit.setText("Custom Artist")
    dialog.albumEdit.setText("Custom Album")
    dialog.dateEdit.setText("2026")
    dialog.trackEdit.setText("5")
    dialog.genreEdit.setText("Synthwave")
    dialog._apply_tags()

    assert dialog.result() == 1
    meta = read_audio_metadata(wav)
    assert meta.title == "Custom Title"
    assert meta.artist == "Custom Artist"


def test_audio_tag_dialog_auto_detect(qapp, tmp_path: Path, monkeypatch):
    wav = _create_wav(tmp_path / "auto_detect.wav", duration=1.0)
    mock_detected = {
        "status": "ok",
        "title": "Detected Title",
        "artist": "Detected Artist",
        "album": "Detected Album",
        "date": "2023",
        "track": "3",
        "genre": "Electronic",
        "score": 0.99,
    }
    monkeypatch.setattr("src.ui.components.audio_tag_dialog.lookup_audio_file", lambda *a, **k: dict(mock_detected))

    dialog = AudioTagDialog(wav)
    dialog._auto_detect()
    assert dialog.titleEdit.text() == "Detected Title"
    assert dialog.artistEdit.text() == "Detected Artist"
    assert dialog.albumEdit.text() == "Detected Album"
    assert dialog.dateEdit.text() == "2023"
    assert "matched via AcoustID" in dialog.statusLabel.text()


def test_audio_tools_interface_tag_button(qapp, tmp_path: Path):
    cfg = Config()
    page = AudioToolsInterface(cfg)
    try:
        assert hasattr(page, "tagBtn")
        assert not page.tagBtn.isEnabled()
        wav = _create_wav(tmp_path / "page_test.wav", duration=1.0)
        page.loadFile(wav)
        assert page.tagBtn.isEnabled()
    finally:
        page.cleanup()
