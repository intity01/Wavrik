"""Backward-compatibility shim for TrayIcon."""

from __future__ import annotations

from ..ui.components.tray_icon import SystemTrayIcon, TrayIcon, run_applescript

__all__ = ["SystemTrayIcon", "TrayIcon", "run_applescript"]
