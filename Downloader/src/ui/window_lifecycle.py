"""Window lifecycle behavior shared by the main application shell."""

from __future__ import annotations

import sys


class WindowLifecycleMixin:
    def cleanup(self) -> None:
        if getattr(self, "_cleaned_up", False):
            return
        self._cleaned_up = True
        try:
            if hasattr(self, "pageWorkspace"):
                fn = getattr(self.pageWorkspace, "_cleanup", None) or getattr(self.pageWorkspace, "cleanup", None)
                if callable(fn):
                    fn()
        except Exception:
            pass
        try:
            if hasattr(self, "pageLibrary") and hasattr(self.pageLibrary, "cleanup"):
                self.pageLibrary.cleanup()
        except Exception:
            pass
        try:
            if hasattr(self, "pageAudioTools") and hasattr(self.pageAudioTools, "cleanup"):
                self.pageAudioTools.cleanup()
        except Exception:
            pass
        try:
            if hasattr(self, "_tray") and hasattr(self._tray, "stop"):
                self._tray.stop()
        except Exception:
            pass

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
        self.cleanup()
        event.accept()

    def changeEvent(self, event) -> None:
        super().changeEvent(event)
        if sys.platform == "darwin" and event.type() == event.Type.WindowStateChange:
            if self._fullscreen_action and hasattr(self._fullscreen_action, "setText"):
                fullscreen = self.isFullScreen()
                self._fullscreen_action.setText("Exit Full Screen" if fullscreen else "Enter Full Screen")
                self._fullscreen_action.setChecked(fullscreen)
