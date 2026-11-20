"""Regression tests for the audio tagging review fixes."""

from __future__ import annotations

import json
import subprocess
import threading
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from PyQt6.QtCore import QThreadPool
from PyQt6.QtWidgets import QApplication

from src.services import audio_acoustid, audio_fingerprint, audio_transcriber
from src.services.audio_tagger import AudioMetadata
from src.ui.components.audio_tag_dialog import AudioTagDialog

_DIALOG = "src.ui.components.audio_tag_dialog"


def _dialog(qtbot, monkeypatch, tmp_path: Path, **patches) -> AudioTagDialog:
    audio = tmp_path / "Artist - Song.mp3"
    audio.write_bytes(b"x")
    monkeypatch.setattr(f"{_DIALOG}.read_audio_metadata", patches.get("read", lambda _p: AudioMetadata()))
    for name in ("lookup_audio_file", "apply_audio_metadata"):
        if name in patches:
            monkeypatch.setattr(f"{_DIALOG}.{name}", patches[name])
    dialog = AudioTagDialog(audio)
    qtbot.addWidget(dialog)
    return dialog


@pytest.fixture(autouse=True)
def _drain_pool():
    yield
    QThreadPool.globalInstance().waitForDone(15000)
    QApplication.processEvents()


def test_dialog_lookup_runs_off_ui_thread_and_disables_buttons(qtbot, monkeypatch, tmp_path):
    gate, seen = threading.Event(), {}

    def slow_lookup(_path):
        seen["thread"] = threading.get_ident()
        gate.wait(10)
        return {"status": "ok", "title": "T", "artist": "A", "score": 0.9}

    dialog = _dialog(qtbot, monkeypatch, tmp_path, lookup_audio_file=slow_lookup)
    qtbot.waitUntil(dialog.detectBtn.isEnabled, timeout=15000)
    dialog._auto_detect()
    assert not dialog.detectBtn.isEnabled()
    assert not dialog.applyBtn.isEnabled()
    qtbot.waitUntil(lambda: "thread" in seen, timeout=5000)
    assert seen["thread"] != threading.get_ident()
    gate.set()
    qtbot.waitUntil(dialog.detectBtn.isEnabled, timeout=15000)
    assert dialog.titleEdit.text() == "T"


def test_dialog_ignores_result_after_reject(qtbot, monkeypatch, tmp_path):
    gate = threading.Event()

    def slow_lookup(_path):
        gate.wait(10)
        return {"status": "ok", "title": "Late", "artist": "Late", "score": 1.0}

    dialog = _dialog(qtbot, monkeypatch, tmp_path, lookup_audio_file=slow_lookup)
    qtbot.waitUntil(dialog.detectBtn.isEnabled, timeout=15000)
    dialog._auto_detect()
    dialog.reject()
    gate.set()
    QThreadPool.globalInstance().waitForDone(15000)
    QApplication.processEvents()
    assert dialog.titleEdit.text() == ""
    assert "Auto-detection" not in dialog.statusLabel.text()


def test_dialog_errors_hide_raw_exception_text(qtbot, monkeypatch, tmp_path):
    def boom(_path, _meta):
        raise RuntimeError("SECRET-C:/internal/path traceback")

    dialog = _dialog(qtbot, monkeypatch, tmp_path, apply_audio_metadata=boom)
    qtbot.waitUntil(dialog.applyBtn.isEnabled, timeout=15000)
    dialog._apply_tags()
    qtbot.waitUntil(lambda: dialog.statusLabel.text().startswith("Could not"), timeout=15000)
    qtbot.waitUntil(dialog.applyBtn.isEnabled, timeout=15000)
    assert "SECRET" not in dialog.statusLabel.text()
    assert dialog.statusLabel.text().startswith("Could not save the tags")
    assert dialog.result() == 0


def test_dialog_unavailable_lookup_falls_back_to_filename_with_reason(qtbot, monkeypatch, tmp_path):
    unavailable = {"status": "unavailable", "error": "fpcalc (Chromaprint) is not installed"}
    dialog = _dialog(qtbot, monkeypatch, tmp_path, lookup_audio_file=lambda _p: unavailable)
    qtbot.waitUntil(dialog.detectBtn.isEnabled, timeout=15000)
    dialog._auto_detect()
    qtbot.waitUntil(lambda: "Auto-detection" in dialog.statusLabel.text(), timeout=15000)
    assert dialog.artistEdit.text() == "Artist"
    assert dialog.titleEdit.text() == "Song"
    assert "fpcalc (Chromaprint) is not installed" in dialog.statusLabel.text()


def test_dialog_initial_load_does_not_overwrite_user_edits(qtbot, monkeypatch, tmp_path):
    gate = threading.Event()

    def slow_read(_path):
        gate.wait(10)
        return AudioMetadata(title="Old", album="Old Album")

    dialog = _dialog(qtbot, monkeypatch, tmp_path, read=slow_read)
    assert not dialog.applyBtn.isEnabled()
    dialog.titleEdit.setText("Typed")
    gate.set()
    qtbot.waitUntil(dialog.applyBtn.isEnabled, timeout=15000)
    assert dialog.titleEdit.text() == "Typed"
    assert dialog.albumEdit.text() == "Old Album"


def test_fpcalc_missing_returns_unavailable_without_network(monkeypatch, tmp_path):
    monkeypatch.setattr(audio_fingerprint, "find_fpcalc", lambda: None)
    request = MagicMock()
    res = audio_acoustid.lookup_audio_file(tmp_path / "a.mp3", api_key="k", request_fn=request)
    assert res == {"status": "unavailable", "error": "fpcalc (Chromaprint) is not installed"}
    request.assert_not_called()


def test_run_fpcalc_uses_full_duration_and_safe_subprocess(monkeypatch, tmp_path):
    calls = {}

    def fake_run(cmd, **kwargs):
        calls.update(cmd=cmd, kwargs=kwargs)
        out = json.dumps({"duration": 245.6, "fingerprint": "AQAD-real"})
        return subprocess.CompletedProcess(cmd, 0, stdout=out, stderr="")

    monkeypatch.setattr(audio_fingerprint.subprocess, "run", fake_run)
    dur, fp = audio_fingerprint.run_fpcalc(tmp_path / "a.mp3", exe="fpcalc")
    assert (dur, fp) == (246, "AQAD-real")
    assert calls["cmd"][:2] == ["fpcalc", "-json"]
    assert calls["kwargs"]["encoding"] == "utf-8"
    assert calls["kwargs"]["errors"] == "replace"
    assert calls["kwargs"]["timeout"] > 0


def test_lookup_audio_file_sends_run_fpcalc(monkeypatch, tmp_path):
    monkeypatch.setattr(audio_fingerprint, "find_fpcalc", lambda: "fpcalc")
    monkeypatch.setattr(audio_fingerprint, "run_fpcalc", lambda *_a, **_k: (300, "AQAD-real"))
    sent = {}

    def fake_post(_url, data=None, timeout=None):
        sent.update(data)
        return {"status": "ok", "results": []}

    res = audio_acoustid.lookup_audio_file(tmp_path / "a.mp3", api_key="k", request_fn=fake_post)
    assert res["status"] == "not_found"
    assert sent["duration"] == "300"
    assert sent["fingerprint"] == "AQAD-real"


def test_no_api_key_skips_network_and_hardcoded_key_is_gone(monkeypatch):
    monkeypatch.delenv("WAVRIK_ACOUSTID_KEY", raising=False)
    request = MagicMock()
    res = audio_acoustid.lookup_acoustid(10, "fp", request_fn=request)
    assert res == {"status": "unavailable", "error": "AcoustID API key is not configured"}
    request.assert_not_called()
    assert "8XaBELgH" not in Path(audio_acoustid.__file__).read_text(encoding="utf-8")


def test_api_key_is_read_from_environment(monkeypatch):
    monkeypatch.setenv("WAVRIK_ACOUSTID_KEY", "env-key")
    sent = {}

    def fake_post(_url, data=None, timeout=None):
        sent.update(data)
        return {"status": "ok", "results": []}

    assert audio_acoustid.lookup_acoustid(10, "fp", request_fn=fake_post)["status"] == "not_found"
    assert sent["client"] == "env-key"


def _fake_whisper(monkeypatch, payload, returncode=0, write=True):
    seen = {}

    def fake_run(cmd, **kwargs):
        seen.update(cmd=cmd, kwargs=kwargs)
        out_dir = Path(cmd[cmd.index("--output_dir") + 1])
        if write:
            (out_dir / f"{Path(cmd[1]).stem}.json").write_text(payload, encoding="utf-8")
        return subprocess.CompletedProcess(cmd, returncode, stdout="", stderr="")

    monkeypatch.setattr(audio_transcriber.subprocess, "run", fake_run)
    return seen


def test_whisper_cli_parses_json_segments(monkeypatch, tmp_path):
    payload = json.dumps({"segments": [
        {"start": 0.0, "end": 1.5, "text": " Hello world ", "avg_logprob": -0.1},
        {"start": 1.5, "end": 2.0, "text": "   "},
        {"start": 2.0, "end": 3.0, "text": "Again"},
    ]})
    seen = _fake_whisper(monkeypatch, payload)
    segs = audio_transcriber._run_whisper_cli("whisper", tmp_path / "song.mp3", None)
    assert [s.text for s in segs] == ["Hello world", "Again"]
    assert (segs[0].start_sec, segs[0].end_sec) == (0.0, 1.5)
    assert 0.0 < segs[0].confidence < 1.0
    assert segs[1].confidence == 1.0
    assert seen["kwargs"]["encoding"] == "utf-8"
    assert seen["kwargs"]["errors"] == "replace"


@pytest.mark.parametrize(
    ("payload", "returncode", "write", "message"),
    [
        ("{}", 0, True, "whisper CLI output unsupported"),
        ("not json", 0, True, "whisper CLI output unsupported"),
        ("", 0, False, "whisper CLI output unsupported"),
        ("{}", 1, True, "whisper CLI failed"),
    ],
)
def test_whisper_cli_raises_clear_errors(monkeypatch, tmp_path, payload, returncode, write, message):
    _fake_whisper(monkeypatch, payload, returncode, write)
    with pytest.raises(RuntimeError, match=message):
        audio_transcriber._run_whisper_cli("whisper", tmp_path / "song.mp3", None)


def test_whisper_cli_cancelled_returns_empty(tmp_path):
    assert audio_transcriber._run_whisper_cli("whisper", tmp_path / "s.mp3", lambda: True) == []


def test_transcribe_audio_falls_back_when_whisper_cli_fails(monkeypatch, tmp_path):
    audio = tmp_path / "voice.wav"
    audio.write_bytes(b"x")
    chunk = MagicMock(start_sec=0.0, end_sec=1.0, index=0)
    monkeypatch.setattr("src.services.audio_analysis._decode_mono_samples", lambda *_a: ([0.1] * 10, 16000))
    monkeypatch.setattr(audio_transcriber, "segment_speech_chunks", lambda *_a: [chunk])
    monkeypatch.setattr(audio_transcriber, "discover_speech_engines", lambda: {"whisper_cli": True})
    monkeypatch.setattr(audio_transcriber.shutil, "which", lambda _n: "whisper")

    def failing(*_a):
        raise RuntimeError("whisper CLI output unsupported")

    monkeypatch.setattr(audio_transcriber, "_run_whisper_cli", failing)
    result = audio_transcriber.transcribe_audio(audio)
    assert result.engine_name == "heuristic_vad"
    assert result.status == "fallback"
