"""macOS system appearance detection for dark/light mode sync."""

from __future__ import annotations

import subprocess
import sys


def is_system_dark_mode() -> bool:
    """Check if macOS is in dark mode.
    
    Returns:
        True if system appearance is dark mode, False for light mode.
        Returns False on non-macOS platforms or if detection fails.
    """
    if sys.platform != "darwin":
        return False
    
    try:
        # Use defaults command to check appearance
        result = subprocess.run(
            ["defaults", "read", "-g", "AppleInterfaceStyle"],
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
        # If "Dark" is returned, system is in dark mode
        return result.stdout.strip() == "Dark"
    except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError):
        # Fallback: assume dark mode if detection fails
        return True


def get_system_accent_color() -> str:
    """Get the current macOS system accent color.
    
    Returns:
        Hex color string of the system accent color, or default blue if detection fails.
    """
    if sys.platform != "darwin":
        return "#2563EB"
    
    try:
        # Get accent color from macOS defaults
        result = subprocess.run(
            ["defaults", "read", "-g", "AppleAccentColor"],
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
        
        # Map macOS accent color indices to hex values
        accent_map = {
            "-1": "#007AFF",  # Blue (default)
            "0": "#FF3B30",   # Red
            "1": "#FF9500",   # Orange
            "2": "#FFCC00",   # Yellow
            "3": "#34C759",   # Green
            "4": "#30B0C7",   # Teal
            "5": "#5856D6",   # Purple
            "6": "#FF2D55",   # Pink
        }
        
        accent_index = result.stdout.strip()
        return accent_map.get(accent_index, "#2563EB")
    except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError):
        return "#2563EB"
