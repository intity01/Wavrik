"""Application entry point."""

from __future__ import annotations

import sys
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication

from src.core.config import Config
from src.core.logger import Logger
from src.core.runtime import application_root, find_deno, find_ffmpeg, resource_root
from src.core.tray import TrayIcon
from src.core.updater import UpdateManager
from src.domain.media_downloader import MediaDownloader
from src.services.history_manager import HistoryManager
from src.ui.main_window import MediaDownloaderUI
from src.ui.window_setup import WindowDependencies


def _create_app() -> QApplication:
    app = QApplication(sys.argv)
    app.setApplicationName(Config.APP_NAME)
    app.setApplicationVersion(Config.VERSION)
    app.setOrganizationName("MediaDownloaderPRO")
    if sys.platform == "darwin":
        app.setAttribute(Qt.ApplicationAttribute.AA_DontShowIconsInMenus, True)
        app.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling, True)
        app.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)
    return app


def _find_asset(rel_path: str) -> Path | None:
    bases = (resource_root(), application_root(), Path(__file__).resolve().parent)
    for base in bases:
        for candidate in (base / rel_path, base / "_internal" / rel_path):
            if candidate.is_file():
                return candidate
    return None


def _attach_console() -> None:
    if sys.stdout is None and sys.platform == "win32":
        try:
            import ctypes

            if ctypes.windll.kernel32.AttachConsole(-1):
                sys.stdout = open("CONOUT$", "w", encoding="utf-8")
                sys.stderr = open("CONOUT$", "w", encoding="utf-8")
        except Exception:
            pass


def _test_startup() -> int:
    config = Config()
    logger = Logger(logDir=config.appDataDir / "logs")
    try:
        tray = TrayIcon()
        downloader = MediaDownloader(logger, config)
        updater = UpdateManager(Config.VERSION, Config.GITHUB_REPO, logger)
        history = HistoryManager(config, logger)
        WindowDependencies(
            config=config, logger=logger, downloader=downloader,
            updater=updater, tray=tray, history=history,
        )
    except Exception as exc:
        logger.error(f"Component initialization failed: {exc}")
        return 1
    ffmpeg, deno = find_ffmpeg(), find_deno()
    icon = _find_asset("src/core/app.ico")
    font = _find_asset("src/ui/theme/fonts/Inter.ttf")
    ok = bool(ffmpeg and deno and icon and font)
    status = "passed" if ok else "failed"
    log_fn = logger.info if ok else logger.error
    log_fn(
        f"Startup verification {status}: ffmpeg={bool(ffmpeg)}, "
        f"deno={bool(deno)}, icon={bool(icon)}, font={bool(font)}"
    )
    return 0 if ok else 1


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if "--version" in args or "--test-startup" in args:
        _attach_console()
    if "--version" in args:
        if sys.stdout is not None:
            sys.stdout.write(f"{Config.VERSION}\n")
            sys.stdout.flush()
        return 0
    if "--test-startup" in args:
        return _test_startup()
    app = _create_app()
    config = Config()
    logger = Logger(logDir=config.appDataDir / "logs")
    tray = TrayIcon()
    tray.start()
    deps = WindowDependencies(
        config=config, logger=logger,
        downloader=MediaDownloader(logger, config),
        updater=UpdateManager(Config.VERSION, Config.GITHUB_REPO, logger),
        tray=tray, history=HistoryManager(config, logger),
    )
    window = MediaDownloaderUI(deps)
    tray.setCallbacks(window.show, app.quit)
    if sys.platform == "darwin":
        app.aboutToQuit.connect(lambda: _cleanup_before_quit(window, tray))
    window.show()
    return app.exec()


def _cleanup_before_quit(window, tray) -> None:
    """Perform cleanup before application quits (macOS)."""
    window.pageWorkspace._cleanup()
    tray.stop()


if __name__ == "__main__":
    raise SystemExit(main())
