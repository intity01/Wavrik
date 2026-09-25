"""macOS-specific UI components and behaviors."""

from .dialogs import get_open_file_path, get_save_directory, get_save_file_path
from .menubar import setup_macos_menu_bar

__all__ = [
    "get_open_file_path",
    "get_save_directory",
    "get_save_file_path",
    "setup_macos_menu_bar",
]

# Note: appearance.py is imported directly where needed to avoid circular imports
# Note: touchbar.py is a placeholder for future Touch Bar integration
