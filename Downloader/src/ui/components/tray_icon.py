"""System tray integration and platform notifications."""

from __future__ import annotations

import subprocess
import sys
from collections.abc import Callable

from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QApplication, QMenu, QStyle, QSystemTrayIcon


def escape_applescript(text: str) -> str:
    """Escape text for safe inclusion in AppleScript string literals."""
    return str(text).replace("\\", "\\\\").replace('"', '\\"').replace("\r", " ").replace("\n", " ")


_escape_applescript = escape_applescript


def run_applescript(script: str, timeout: float = 3.0) -> None:
    """Run an AppleScript command safely with a timeout."""
    try:
        subprocess.run(
            ["osascript", "-e", script],
            check=True,
            capture_output=True,
            timeout=timeout,
        )
    except (subprocess.TimeoutExpired, subprocess.SubprocessError, OSError):
        pass


class SystemTrayIcon:
    """System tray icon and notification manager."""

    def __init__(self, appName: str = "Media Downloader PRO"):
        self.appName = appName
        self._tray: QSystemTrayIcon | None = None
        self._onShow: Callable | None = None
        self._onQuit: Callable | None = None

    def setCallbacks(self, onShow: Callable | None = None, onQuit: Callable | None = None) -> None:
        self._onShow = onShow
        self._onQuit = onQuit

    def start(self) -> None:
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        app = QApplication.instance()
        icon = app.style().standardIcon(QStyle.StandardPixmap.SP_ArrowDown) if app else QIcon()
        self._tray = QSystemTrayIcon(icon)
        self._tray.setToolTip(self.appName)
        menu = QMenu()
        show_action = menu.addAction("Show window")
        quit_action = menu.addAction("Quit")
        show_action.triggered.connect(self._show)
        quit_action.triggered.connect(self._quit)
        self._tray.setContextMenu(menu)
        self._tray.activated.connect(self._activated)
        self._tray.show()

    def stop(self) -> None:
        if self._tray:
            self._tray.hide()
            self._tray = None

    def notify(self, title: str, message: str) -> None:
        if not self._tray:
            return
        if sys.platform == "darwin":
            try:
                safe_title = escape_applescript(title)
                safe_msg = escape_applescript(message)
                run_applescript(
                    f'display notification "{safe_msg}" with title "{safe_title}"',
                    timeout=3.0,
                )
                return
            except (subprocess.TimeoutExpired, subprocess.SubprocessError, OSError):
                pass
        self._tray.showMessage(title, message, QSystemTrayIcon.MessageIcon.Information, 4000)

    def isAvailable(self) -> bool:
        return self._tray is not None

    def _activated(self, reason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._show()

    def _show(self) -> None:
        if self._onShow:
            self._onShow()

    def _quit(self) -> None:
        self.stop()
        if self._onQuit:
            self._onQuit()


TrayIcon = SystemTrayIcon

__all__ = ["SystemTrayIcon", "TrayIcon", "run_applescript", "escape_applescript"]
