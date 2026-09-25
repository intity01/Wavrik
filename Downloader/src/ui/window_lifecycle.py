"""Window lifecycle behavior shared by the main application shell."""

from __future__ import annotations

import sys


class WindowLifecycleMixin:
    def closeEvent(self, event) -> None:
        if sys.platform == "darwin":
            event.ignore()
            self.hide()
            if self._tray.isAvailable():
                self._tray.notify("Still Running", "Media Downloader PRO is running in the background. Use Cmd+Q to quit.")
            return
        if self._cfg.get("minimizeToTray", False) and self._tray.isAvailable():
            event.ignore()
            self.hide()
            self._tray.notify("Still running", "Downloads continue in the system tray.")
            return
        self.pageWorkspace._cleanup()
        self._tray.stop()
        event.accept()

    def changeEvent(self, event) -> None:
        super().changeEvent(event)
        if sys.platform == "darwin" and event.type() == event.Type.WindowStateChange:
            if self._fullscreen_action and hasattr(self._fullscreen_action, "setText"):
                fullscreen = self.isFullScreen()
                self._fullscreen_action.setText("Exit Full Screen" if fullscreen else "Enter Full Screen")
                self._fullscreen_action.setChecked(fullscreen)
