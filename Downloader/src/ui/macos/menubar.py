"""macOS-specific menu bar integration."""

from __future__ import annotations

import sys

from PyQt6.QtGui import QAction, QKeySequence
from PyQt6.QtWidgets import QApplication, QMenuBar

from .menu_actions import (
    bring_all_to_front,
    hide_others,
    open_preferences,
    show_about,
    show_all,
    toggle_fullscreen,
)


def setup_macos_menu_bar(window, app_name: str = "Media Downloader PRO") -> tuple[QMenuBar | None, QAction | None]:
    if sys.platform != "darwin":
        return None
    menu_bar = QMenuBar()
    _add_app_menu(menu_bar, window, app_name)
    _add_file_menu(menu_bar, window)
    _add_edit_menu(menu_bar, window)
    fullscreen = _add_window_menu(menu_bar, window)
    menu_bar.addMenu("Help")
    window.setMenuBar(menu_bar)
    return menu_bar, fullscreen


def _add_app_menu(menu_bar, window, app_name: str) -> None:
    menu = menu_bar.addMenu(app_name)
    about = QAction(f"About {app_name}", window)
    about.triggered.connect(lambda: show_about(window, app_name))
    menu.addAction(about)
    menu.addSeparator()
    preferences = QAction("Preferences...", window)
    preferences.setShortcut(QKeySequence.StandardKey.Preferences)
    preferences.triggered.connect(lambda: open_preferences(window))
    menu.addAction(preferences)
    menu.addSeparator()
    menu.addMenu("Services").setEnabled(False)
    menu.addSeparator()
    _add_visibility_actions(menu, window, app_name)
    menu.addSeparator()
    quit_action = QAction(f"Quit {app_name}", window)
    quit_action.setShortcut(QKeySequence.StandardKey.Quit)
    quit_action.triggered.connect(QApplication.instance().quit)
    menu.addAction(quit_action)


def _add_visibility_actions(menu, window, app_name: str) -> None:
    hide_action = QAction(f"Hide {app_name}", window)
    hide_action.setShortcut(QKeySequence("Ctrl+H"))
    hide_action.triggered.connect(window.hide)
    menu.addAction(hide_action)
    hide_others_action = QAction("Hide Others", window)
    hide_others_action.setShortcut(QKeySequence("Ctrl+Shift+H"))
    hide_others_action.triggered.connect(hide_others)
    menu.addAction(hide_others_action)
    show_action = QAction("Show All", window)
    show_action.triggered.connect(show_all)
    menu.addAction(show_action)


def _add_file_menu(menu_bar, window) -> None:
    menu = menu_bar.addMenu("File")
    action = QAction("Close Window", window)
    action.setShortcut(QKeySequence.StandardKey.Close)
    action.triggered.connect(window.close)
    menu.addAction(action)


def _add_edit_menu(menu_bar, window) -> None:
    menu = menu_bar.addMenu("Edit")
    for label, shortcut in (("Undo", QKeySequence.StandardKey.Undo), ("Redo", QKeySequence.StandardKey.Redo)):
        action = QAction(label, window)
        action.setShortcut(shortcut)
        menu.addAction(action)
    menu.addSeparator()
    for label, shortcut in (("Cut", QKeySequence.StandardKey.Cut), ("Copy", QKeySequence.StandardKey.Copy), ("Paste", QKeySequence.StandardKey.Paste), ("Select All", QKeySequence.StandardKey.SelectAll)):
        action = QAction(label, window)
        action.setShortcut(shortcut)
        menu.addAction(action)


def _add_window_menu(menu_bar, window) -> QAction:
    menu = menu_bar.addMenu("Window")
    minimize = QAction("Minimize", window)
    minimize.setShortcut(QKeySequence.StandardKey.ZoomIn)
    minimize.triggered.connect(window.showMinimized)
    menu.addAction(minimize)
    fullscreen = QAction("Enter Full Screen", window)
    fullscreen.setShortcut(QKeySequence("Ctrl+Meta+F"))
    fullscreen.setCheckable(True)
    fullscreen.triggered.connect(lambda checked: toggle_fullscreen(window, fullscreen))
    menu.addAction(fullscreen)
    menu.addSeparator()
    front = QAction("Bring All to Front", window)
    front.triggered.connect(bring_all_to_front)
    menu.addAction(front)
    return fullscreen
