"""Window dependency and platform setup helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PyQt6.QtGui import QIcon


@dataclass(frozen=True)
class WindowDependencies:
    config: object
    logger: object
    downloader: object
    updater: object
    tray: object
    history: object


def resolve_dependencies(
    first: Any, args: tuple[Any, ...], kwargs: dict[str, Any],
) -> WindowDependencies:
    if isinstance(first, WindowDependencies):
        return first
    k = kwargs.get
    config = first if first is not None else k("config", k("settings"))
    logger = args[0] if len(args) > 0 else k("logger")
    downloader = args[1] if len(args) > 1 else k("downloader", k("downloads", k("engine")))
    updater = args[2] if len(args) > 2 else k("updater")
    tray = args[3] if len(args) > 3 else k("tray", k("trayIcon"))
    history = args[4] if len(args) > 4 else k("history", k("historyManager"))
    return WindowDependencies(config, logger, downloader, updater, tray, history)


def initialize(window, dependencies: WindowDependencies) -> None:
    window._cfg = dependencies.config
    window._log = dependencies.logger
    window._dl = dependencies.downloader
    window._updater = dependencies.updater
    window._tray = dependencies.tray
    window._hist = dependencies.history
    window._lastClip = ""
    window._fullscreen_action = None
    window.setWindowTitle("Wavrik")
    window.setMinimumSize(760, 600)
    window.resize(1120, 760)
    _set_icon(window)
    _sync_first_run_appearance(window)
    window._build_shell()
    window._build_pages()
    window._build_navigation()
    window._refresh_theme()
    window._setup_clipboard()
    window._schedule_update_check()


def _sync_first_run_appearance(window: Any) -> None:
    if getattr(window, "_cfg", None):
        window._cfg.set("theme", "dark")


def _set_icon(window) -> None:
    icon_path = Path(__file__).parents[1] / "core" / "app.ico"
    if icon_path.exists():
        window.setWindowIcon(QIcon(str(icon_path)))
