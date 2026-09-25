"""Window dependency and platform setup helpers."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

from typing import Any

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon


@dataclass(frozen=True)
class WindowDependencies:
    config: object
    logger: object
    downloader: object
    updater: object
    tray: object
    history: object


def initialize(window, dependencies: WindowDependencies) -> None:
    window._cfg = dependencies.config
    window._log = dependencies.logger
    window._dl = dependencies.downloader
    window._updater = dependencies.updater
    window._tray = dependencies.tray
    window._hist = dependencies.history
    window._lastClip = ""
    window._fullscreen_action = None
    window.setWindowTitle("Media Downloader PRO")
    window.setMinimumSize(760, 600)
    window.resize(1120, 760)
    _configure_platform(window)
    _set_icon(window)
    _sync_first_run_appearance(window)
    window._build_shell()
    window._build_pages()
    window._build_navigation()
    window._refresh_theme()
    window._setup_clipboard()
    window._schedule_update_check()


def _sync_first_run_appearance(window: Any) -> None:
    if sys.platform == "darwin" and getattr(window, "_cfg", None) and window._cfg.get("firstRun", True):
        try:
            from .macos.appearance import is_system_dark_mode

            theme = "dark" if is_system_dark_mode() else "light"
            window._cfg.set("theme", theme)
        except Exception:
            pass


def _configure_platform(window) -> None:
    if sys.platform != "darwin":
        return
    window.setWindowFlags(
        Qt.WindowType.Window | Qt.WindowType.CustomizeWindowHint |
        Qt.WindowType.WindowCloseButtonHint | Qt.WindowType.WindowMinimizeButtonHint |
        Qt.WindowType.WindowMaximizeButtonHint | Qt.WindowType.WindowFullscreenButtonHint
    )
    window.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
    from src.ui.macos import setup_macos_menu_bar
    _, window._fullscreen_action = setup_macos_menu_bar(window, "Media Downloader PRO")


def _set_icon(window) -> None:
    icon_path = Path(__file__).parents[1] / "core" / "app.ico"
    if icon_path.exists():
        window.setWindowIcon(QIcon(str(icon_path)))
