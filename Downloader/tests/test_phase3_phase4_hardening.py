"""Comprehensive Phase 3/4 hardening test suite."""

from __future__ import annotations

import ast
import dataclasses
import subprocess
import sys
from logging.handlers import RotatingFileHandler
from unittest.mock import MagicMock

import pytest

from src.core.logger import Logger
from src.core.update_models import ReleaseAsset, UpdateInfo
from src.domain import update_models as shim_update
from src.domain.native_downloader import _ffmpeg_executable
from src.ui.components.tray_icon import SystemTrayIcon, escape_applescript, run_applescript
from tools.check_rules import ROOT, _ast_errors, _param_count


def test_ast_param_count_counts_posonly_vararg_kwarg_and_kwonly():
    fn = ast.parse("def fn(a, /, b, *args, c, **kwargs): pass").body[0]
    assert _param_count(fn) == 5


def test_ast_param_count_excludes_self_and_cls_receivers():
    for src in ("def m1(self, x, y): pass", "def m2(cls, x, y): pass", "def fn(x, y): pass"):
        assert _param_count(ast.parse(src).body[0]) == 2


def test_ast_errors_detects_greater_than_six_parameters():
    code = "def bad(a, b, c, d, e, f, g): pass\ndef ok(a, b, c, d, e, f): pass\n"
    errs = _ast_errors(ROOT / "src" / "dummy.py", code)
    assert any("function bad has 7 parameters (max 6)" in e for e in errs)
    assert not any("function ok" in e for e in errs)


def test_applescript_escaping_special_chars_quotes_newlines():
    assert escape_applescript('say "hello" \\\nline\rbreak') == 'say \\"hello\\" \\\\ line break'


def test_run_applescript_handles_timeout_and_errors(monkeypatch):
    calls, errs = [], [subprocess.TimeoutExpired(["osascript"], 1.0), subprocess.SubprocessError("err"), OSError("err")]

    def fake_run(cmd, check=True, capture_output=True, timeout=3.0):
        calls.append((cmd, timeout))
        raise errs[len(calls) - 1]

    monkeypatch.setattr(subprocess, "run", fake_run)
    for i in (1.0, 2.0, 3.0):
        run_applescript(f"s{int(i)}", timeout=i)
    assert len(calls) == 3 and calls[0] == (["osascript", "-e", "s1"], 1.0)


def test_tray_icon_darwin_notify_escaping_and_fallback(monkeypatch):
    tray, executed = SystemTrayIcon(), []
    tray._tray = MagicMock()
    monkeypatch.setattr(sys, "platform", "darwin")
    monkeypatch.setattr("src.ui.components.tray_icon.run_applescript", lambda cmd, timeout=3.0: executed.append(cmd))
    tray.notify('Title "A"', 'Msg \n "B"')
    assert executed == ['display notification "Msg   \\"B\\"" with title "Title \\"A\\""']
    assert not tray._tray.showMessage.called
    monkeypatch.setattr(sys, "platform", "win32")
    tray.notify("T", "M")
    tray._tray.showMessage.assert_called_once()


def test_logger_windowed_execution_when_stdout_is_none(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, "stdout", None)
    log = Logger(logDir=tmp_path / "stdout_none")
    log.info("windowed msg")
    assert len(log.logger.handlers) == 1
    assert isinstance(log.logger.handlers[0], RotatingFileHandler)


def test_logger_windowed_when_stdout_and_stderr_are_none(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, "stdout", None)
    monkeypatch.setattr(sys, "stderr", None)
    log = Logger(logDir=tmp_path / "headless")
    log.info("headless run")
    log.error("headless err", exc_info=False)
    content = log.logFile.read_text(encoding="utf-8")
    assert "headless run" in content and "headless err" in content


def test_ffmpeg_executable_resolves_win32_binary(tmp_path, monkeypatch):
    (tmp_path / "ffmpeg.exe").write_text("bin", encoding="utf-8")
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr("src.domain.native_downloader.find_ffmpeg", lambda: str(tmp_path))
    assert _ffmpeg_executable() == str(tmp_path / "ffmpeg.exe")


def test_ffmpeg_executable_resolves_posix_binary(tmp_path, monkeypatch):
    (tmp_path / "ffmpeg").write_text("bin", encoding="utf-8")
    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr("src.domain.native_downloader.find_ffmpeg", lambda: str(tmp_path))
    assert _ffmpeg_executable() == str(tmp_path / "ffmpeg")


def test_ffmpeg_executable_falls_back_to_shutil_which(monkeypatch):
    monkeypatch.setattr("src.domain.native_downloader.find_ffmpeg", lambda: None)
    monkeypatch.setattr("shutil.which", lambda _cmd: "/usr/local/bin/ffmpeg")
    assert _ffmpeg_executable() == "/usr/local/bin/ffmpeg"
    monkeypatch.setattr("shutil.which", lambda _cmd: None)
    assert _ffmpeg_executable() is None


def test_update_models_identity_and_shims():
    from src.core import tray as core_tray
    from src.core import update_models as core_update

    assert shim_update.ReleaseAsset is core_update.ReleaseAsset
    assert shim_update.UpdateInfo is core_update.UpdateInfo
    assert core_tray.TrayIcon is SystemTrayIcon
    assert core_tray.run_applescript is run_applescript


def test_update_models_immutability():
    asset = ReleaseAsset("app.zip", "https://example.com/app.zip", 1024, "hash123")
    info = UpdateInfo("2.1.0", "notes", "https://example.com", True, asset)
    with pytest.raises(dataclasses.FrozenInstanceError):
        asset.name = "new.zip"
    with pytest.raises(dataclasses.FrozenInstanceError):
        info.version = "2.2.0"


def test_update_info_can_download_safely():
    asset = ReleaseAsset("app.zip", "https://example.com", 100, "abc")
    assert UpdateInfo("1.0", "n", "u", True, asset).can_download_safely is True
    assert UpdateInfo("1.0", "n", "u", False, asset).can_download_safely is False
    assert UpdateInfo("1.0", "n", "u", True, None).can_download_safely is False
    empty_sha = ReleaseAsset("app.zip", "https://example.com", 100, "")
    assert UpdateInfo("1.0", "n", "u", True, empty_sha).can_download_safely is False
