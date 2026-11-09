from __future__ import annotations

from pathlib import Path

import numpy as np

from src.core.runtime import find_node
from src.domain.presets import getPreset
from src.domain.native_paths import target_path
from src.domain.yt_options import YtDownloadSettings, _apply_js_runtime, buildOptions
from src.domain.yt_policy import apply_rate_limit_protection
from src.services.audio_hpcp import _whiten_to_hpcp


def test_find_node_discovery(monkeypatch, tmp_path: Path):
    fake_node = tmp_path / "node.exe"
    fake_node.write_text("", encoding="utf-8")
    monkeypatch.setattr("shutil.which", lambda cmd: str(fake_node) if cmd == "node" else None)
    found = find_node()
    assert found is not None
    assert "node" in found.lower()


def test_apply_js_runtime_fallback_to_node(monkeypatch):
    monkeypatch.setattr("src.domain.yt_options.find_deno", lambda: None)
    monkeypatch.setattr("src.domain.yt_options.find_node", lambda: "/usr/local/bin/node")
    opts = {}
    _apply_js_runtime(opts)
    assert "js_runtimes" in opts
    assert opts["js_runtimes"] == {"node": {"path": "/usr/local/bin/node"}}


def test_concurrent_fragment_downloads_and_buffer_performance(tmp_path: Path):
    preset = getPreset("audio_best")
    settings = YtDownloadSettings()
    options = buildOptions(tmp_path, preset, lambda _: None, settings)
    assert options.get("concurrent_fragment_downloads") == 4
    assert options.get("buffersize") == 65536
    assert options.get("http_chunk_size") == 10485760


def test_enhanced_anti_throttling_player_clients():
    options = {}
    settings = YtDownloadSettings(rate_limit_protection=True)
    apply_rate_limit_protection(options, settings)
    yt_args = options.get("extractor_args", {}).get("youtube", {})
    clients = yt_args.get("player_client", [])
    assert "web_embedded" in clients
    assert "mweb" in clients
    assert "android" in clients


def test_target_path_traversal_hardening(tmp_path: Path):
    dest = target_path(tmp_path, "https://example.com/normal.mp4", "", "mp4")
    assert dest.resolve().is_relative_to(tmp_path.resolve())

    # Traversal should either be sanitized into tmp_path or raise ValueError
    try:
        dest_escaped = target_path(tmp_path, "https://example.com/../../etc/passwd", "", "mp4")
        assert dest_escaped.resolve().is_relative_to(tmp_path.resolve())
    except ValueError as exc:
        assert "Path traversal detected" in str(exc)


def test_audio_hpcp_whiten_accumulates_correctly():
    spec = np.ones(1425, dtype=np.float64) * 0.1
    peaks = [(1.0, 440.0), (0.8, 880.0)]
    hpcp = [0.0] * 12
    _whiten_to_hpcp(spec, peaks, hpcp)
    assert sum(hpcp) > 0.0
    # In Essentia HPCP, ref_hz=440.0 maps A to index 0 (ESSENTIA_KEYS starts with A)
    top_bin = int(np.argmax(hpcp))
    assert top_bin == 0


def test_schedule_update_check_wiring():
    from unittest.mock import MagicMock
    from src.ui.main_window import MediaDownloaderUI

    mock_ui = MagicMock(spec=MediaDownloaderUI)
    mock_ui._cfg = {"checkUpdatesOnStartup": True}
    mock_ui.pageSettings = MagicMock()
    MediaDownloaderUI._schedule_update_check(mock_ui)
    mock_ui.pageSettings.triggerUpdateCheck.assert_called_once()

    mock_ui_disabled = MagicMock(spec=MediaDownloaderUI)
    mock_ui_disabled._cfg = {"checkUpdatesOnStartup": False}
    mock_ui_disabled.pageSettings = MagicMock()
    MediaDownloaderUI._schedule_update_check(mock_ui_disabled)
    mock_ui_disabled.pageSettings.triggerUpdateCheck.assert_not_called()
