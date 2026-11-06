"""Application entry point."""

from __future__ import annotations

import sys
from pathlib import Path

from src.core.config import Config
from src.core.logger import Logger
from src.core.runtime import application_root, find_deno, find_ffmpeg, resource_root
from src.core.updater import UpdateManager
from src.domain.media_downloader import MediaDownloader
from src.services.history_manager import HistoryManager


def __getattr__(name: str):
    if name == "TrayIcon":
        from src.core.tray import TrayIcon
        return TrayIcon
    if name == "WindowDependencies":
        from src.ui.window_setup import WindowDependencies
        return WindowDependencies
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def _create_app():
    from PyQt6.QtCore import Qt
    from PyQt6.QtWidgets import QApplication

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


def _mod_attr(name: str):
    return getattr(sys.modules[__name__], name)


def _test_startup() -> int:
    config = Config()
    logger = Logger(logDir=config.appDataDir / "logs")
    try:
        tray = _mod_attr("TrayIcon")()
        downloader = MediaDownloader(logger, config)
        updater = UpdateManager(Config.VERSION, Config.GITHUB_REPO, logger)
        history = HistoryManager(config, logger)
        _mod_attr("WindowDependencies")(
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


def _handle_cli(args: list[str]) -> int | None:
    if "--version" in args or "--test-startup" in args or "--help" in args or "-h" in args:
        _attach_console()
    if "--version" in args:
        if sys.stdout is not None:
            sys.stdout.write(f"{Config.VERSION}\n")
            sys.stdout.flush()
        return 0
    if "--help" in args or "-h" in args:
        if sys.stdout is not None:
            sys.stdout.write("usage: MediaDownloaderPRO [--version] [--test-startup] [--help]\n")
            sys.stdout.flush()
        return 0
    if "--test-startup" in args:
        return _test_startup()
    return None


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if (cli_code := _handle_cli(args)) is not None:
        return cli_code
    from src.core.crash_handler import install_crash_handler
    from src.ui.main_window import MediaDownloaderUI

    app = _create_app()
    config = Config()
    logger = Logger(logDir=config.appDataDir / "logs")
    install_crash_handler(logger)
    tray = _mod_attr("TrayIcon")()
    tray.start()
    deps = _mod_attr("WindowDependencies")(
        config=config, logger=logger,
        downloader=MediaDownloader(logger, config),
        updater=UpdateManager(Config.VERSION, Config.GITHUB_REPO, logger),
        tray=tray, history=HistoryManager(config, logger),
    )
    window = MediaDownloaderUI(deps)
    tray.setCallbacks(window.show, app.quit)
    app.aboutToQuit.connect(lambda: _cleanup_before_quit(window, tray))
    window.show()
    return app.exec()


def _cleanup_before_quit(window, tray) -> None:
    """Perform unified cleanup before application quits."""
    if hasattr(window, "cleanup"):
        window.cleanup()
    elif hasattr(window, "pageWorkspace") and hasattr(window.pageWorkspace, "_cleanup"):
        window.pageWorkspace._cleanup()
    tray.stop()


if __name__ == "__main__":
    raise SystemExit(main())
