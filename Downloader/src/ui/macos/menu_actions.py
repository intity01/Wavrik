"""Callbacks used by the macOS application menu."""

from __future__ import annotations

from PyQt6.QtWidgets import QApplication, QMessageBox


def show_about(window, app_name: str) -> None:
    version = window._cfg.get("version", "2.1")
    message = f"{app_name}\n\nA professional media downloader.\n\nVersion: {version}\n\nBuilt with PyQt6"
    dialog = QMessageBox(window)
    dialog.setWindowTitle(f"About {app_name}")
    dialog.setText(message)
    dialog.setIcon(QMessageBox.Icon.Information)
    dialog.exec()


def open_preferences(window) -> None:
    if hasattr(window, "pageSettings"):
        window.switchTo(window.pageSettings)


def hide_others() -> None:
    app = QApplication.instance()
    if app:
        for window in app.topLevelWidgets():
            if window.isVisible() and window != app.activeWindow():
                window.hide()


def show_all() -> None:
    app = QApplication.instance()
    if app:
        for window in app.topLevelWidgets():
            window.show()


def bring_all_to_front() -> None:
    app = QApplication.instance()
    if app:
        for window in app.topLevelWidgets():
            window.raise_()
            window.activateWindow()


def toggle_fullscreen(window, action) -> None:
    fullscreen = not window.isFullScreen()
    window.showFullScreen() if fullscreen else window.showNormal()
    action.setText("Exit Full Screen" if fullscreen else "Enter Full Screen")
    action.setChecked(fullscreen)
