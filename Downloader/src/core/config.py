"""Validated application settings."""

from __future__ import annotations

import locale
import os
import sys
from pathlib import Path
from typing import Any

from .json_store import JsonStore


def _default_language() -> str:
    loc = (locale.getlocale()[0] or os.getenv("LANG", "")).lower()
    return "th" if loc.startswith(("th", "thai")) else "en"


DEFAULT_SETTINGS = {
    "schemaVersion": 2,
    "theme": "light",
    "accentColor": "#0E1116",
    "language": _default_language(),
    "downloadPath": str(Path.home() / "Downloads" / "Wavrik"),
    "defaultPreset": "audio_best",
    "downloadEngine": "auto",
    "clipboardMonitoring": True,
    "minimizeToTray": False,
    "maxConcurrentDownloads": 2,
    "firstRun": True,
    "checkUpdatesOnStartup": False,
    "cookieFile": "",
    "renamePattern": "{title}",
    "downloadThumbnail": False,
    "thumbnailFormat": "jpg",
    "thumbnailQuality": "original",
    "rateLimitProtection": True,
    "sleepInterval": 1,
    "maxSleepInterval": 10,
}
_LANGUAGES = {"th", "en"}
_THEMES = {"light", "dark"}


class Config:
    """Load, validate, and save user settings."""

    VERSION = "2.1.0"
    APP_NAME = "Wavrik"
    # Set to the public owner/repository slug as part of the release process.
    GITHUB_REPO = "intity01/Wavrik"

    def __init__(self, app_data_dir: Path | None = None):
        self.appDataDir = app_data_dir or self._getAppDataDir()
        self.configFile = self.appDataDir / "settings.json"
        self.historyFile = self.appDataDir / "history.json"
        self._store = JsonStore(self.configFile)
        self.settings = self._load_settings()

    def _getAppDataDir(self) -> Path:
        if os.name == "nt":
            base = Path(os.getenv("APPDATA", Path.home() / "AppData" / "Roaming"))
        elif sys.platform == "darwin":
            base = Path.home() / "Library" / "Application Support"
        else:
            base = Path.home() / ".config"
        path = base / self.APP_NAME
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _load_settings(self) -> dict[str, Any]:
        loaded = self._store.read({})
        if not isinstance(loaded, dict):
            self._store.backup()
            return dict(DEFAULT_SETTINGS)
        settings = {**DEFAULT_SETTINGS, **loaded}
        if not _supported_schema(settings.get("schemaVersion")):
            self._store.backup()
            return dict(DEFAULT_SETTINGS)
        settings["schemaVersion"] = DEFAULT_SETTINGS["schemaVersion"]
        settings["theme"] = settings.get("theme") if settings.get("theme") in _THEMES else DEFAULT_SETTINGS["theme"]
        settings["accentColor"] = DEFAULT_SETTINGS["accentColor"]
        lang = settings.get("language")
        settings["language"] = lang if lang in _LANGUAGES else DEFAULT_SETTINGS["language"]
        settings["downloadPath"] = _valid_text(settings.get("downloadPath"), DEFAULT_SETTINGS["downloadPath"])
        settings["defaultPreset"] = _valid_text(settings.get("defaultPreset"), DEFAULT_SETTINGS["defaultPreset"])
        settings["downloadEngine"] = settings.get("downloadEngine") if settings.get("downloadEngine") in {"auto", "native", "yt-dlp"} else "auto"
        settings["maxConcurrentDownloads"] = _bounded_int(settings.get("maxConcurrentDownloads"), 2, 1, 5)
        for key in ("clipboardMonitoring", "minimizeToTray", "firstRun", "checkUpdatesOnStartup", "downloadThumbnail", "rateLimitProtection"):
            settings[key] = _valid_bool(settings.get(key), DEFAULT_SETTINGS[key])
        for key in ("cookieFile", "renamePattern", "thumbnailFormat", "thumbnailQuality"):
            settings[key] = _valid_text(settings.get(key), DEFAULT_SETTINGS[key])
        settings["sleepInterval"] = _bounded_int(settings.get("sleepInterval"), 1, 1, 10)
        settings["maxSleepInterval"] = _bounded_int(settings.get("maxSleepInterval"), 10, 10, 120)
        return settings

    def saveSettings(self) -> bool:
        try:
            self._store.write(self.settings)
            return True
        except OSError:
            return False

    def get(self, key: str, default: Any = None) -> Any:
        return self.settings.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self.settings[key] = value

    def update(self, **values: Any) -> None:
        self.settings.update(values)
        self.saveSettings()

    def getDownloadPath(self, mediaType: str = "video") -> Path:
        folder = "Audio" if mediaType == "audio" else "Videos"
        path = Path(self.get("downloadPath")) / folder
        path.mkdir(parents=True, exist_ok=True)
        return path


def _supported_schema(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value in {1, 2}


def _bounded_int(value: Any, default: int, minimum: int, maximum: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return default
    return max(minimum, min(maximum, number))


def _valid_bool(value: Any, default: bool) -> bool:
    return value if isinstance(value, bool) else default


def _valid_text(value: Any, default: str) -> str:
    return value.strip() if isinstance(value, str) and value.strip() else default

