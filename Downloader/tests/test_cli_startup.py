"""Tests for CLI arguments and startup verification."""

from __future__ import annotations

import io
import sys
from unittest.mock import MagicMock

from src.core.config import Config
import main


def test_main_version_prints_config_version(monkeypatch):
    buf = io.StringIO()
    monkeypatch.setattr(sys, "stdout", buf)
    code = main.main(["--version"])
    assert code == 0
    assert buf.getvalue().strip() == Config.VERSION


def test_main_version_when_stdout_is_none(monkeypatch):
    monkeypatch.setattr(sys, "stdout", None)
    code = main.main(["--version"])
    assert code == 0


def test_test_startup_success():
    code = main._test_startup()
    assert code == 0


def test_main_test_startup_arg():
    code = main.main(["--test-startup"])
    assert code == 0


def test_test_startup_fails_when_ffmpeg_missing(monkeypatch):
    monkeypatch.setattr("main.find_ffmpeg", lambda: None)
    code = main._test_startup()
    assert code == 1


def test_test_startup_fails_when_deno_missing(monkeypatch):
    monkeypatch.setattr("main.find_deno", lambda: None)
    code = main._test_startup()
    assert code == 1


def test_test_startup_fails_when_asset_missing(monkeypatch):
    monkeypatch.setattr("main._find_asset", lambda rel: None)
    code = main._test_startup()
    assert code == 1


def test_test_startup_handles_component_init_failure(monkeypatch):
    monkeypatch.setattr("main.TrayIcon", MagicMock(side_effect=RuntimeError("tray boom")))
    code = main._test_startup()
    assert code == 1


def test_find_asset_resolution():
    icon = main._find_asset("src/core/app.ico")
    assert icon is not None and icon.is_file()
    font = main._find_asset("src/ui/theme/fonts/Inter.ttf")
    assert font is not None and font.is_file()
    missing = main._find_asset("non_existent_file.xyz")
    assert missing is None


def test_attach_console_when_stdout_is_none(monkeypatch):
    monkeypatch.setattr(sys, "stdout", None)
    monkeypatch.setattr(sys, "platform", "win32")
    fake_kernel = MagicMock()
    fake_kernel.AttachConsole.return_value = 1
    monkeypatch.setattr("ctypes.windll.kernel32", fake_kernel, raising=False)
    fake_file = io.StringIO()
    monkeypatch.setattr("builtins.open", lambda *a, **kw: fake_file)
    main._attach_console()
    assert fake_kernel.AttachConsole.called


def test_attach_console_safely_ignores_exceptions(monkeypatch):
    monkeypatch.setattr(sys, "stdout", None)
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr("ctypes.windll.kernel32.AttachConsole", MagicMock(side_effect=RuntimeError), raising=False)
    main._attach_console()
    assert sys.stdout is None


def test_test_startup_logs_error_on_failure(monkeypatch):
    monkeypatch.setattr("main.find_ffmpeg", lambda: None)
    fake_logger = MagicMock()
    monkeypatch.setattr("main.Logger", lambda *a, **kw: fake_logger)
    code = main._test_startup()
    assert code == 1
    assert fake_logger.error.called
    error_msg = fake_logger.error.call_args[0][0]
    assert "Startup verification failed" in error_msg
