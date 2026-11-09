"""Validated application settings."""

from __future__ import annotations

import locale
import os
import sys
from pathlib import Path
from typing import Any

from src.core.config_helpers import (
    _bounded_int,
    _clean_path,
    _is_unc,
    _supported_schema,
    _valid_bool,
    _valid_text,
)
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
    "cobaltEnabled": True,
    "cobaltUrl": "https://api.cobalt.tools/",
    "cobaltApiKey": "",
}
_LANGUAGES = {"th", "en"}
_THEMES = {"light", "dark"}
_ENGINES = {"auto", "cobalt", "native", "yt-dlp"}


class Config:
    """Load, validate, and save user settings."""

    VERSION = "2.2.0"
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
        base = Path(os.getenv("APPDATA", Path.home() / "AppData" / "Roaming")) if os.name == "nt" else (
            Path.home() / ("Library/Application Support" if sys.platform == "darwin" else ".config")
        )
        (path := base / self.APP_NAME).mkdir(parents=True, exist_ok=True)
        return path

    def _load_settings(self) -> dict[str, Any]:
        loaded = self._store.read({})
        if not isinstance(loaded, dict) or not _supported_schema(loaded.get("schemaVersion")):
            self._store.backup()
            return dict(DEFAULT_SETTINGS)
        settings = {**DEFAULT_SETTINGS, **loaded, "schemaVersion": DEFAULT_SETTINGS["schemaVersion"]}
        settings["theme"] = settings.get("theme") if settings.get("theme") in _THEMES else DEFAULT_SETTINGS["theme"]
        settings["accentColor"] = DEFAULT_SETTINGS["accentColor"]
        settings["language"] = settings.get("language") if settings.get("language") in _LANGUAGES else DEFAULT_SETTINGS["language"]
        settings["downloadPath"] = _clean_path(settings.get("downloadPath"), DEFAULT_SETTINGS["downloadPath"])
        settings["defaultPreset"] = _valid_text(settings.get("defaultPreset"), DEFAULT_SETTINGS["defaultPreset"])
        settings["downloadEngine"] = settings.get("downloadEngine") if settings.get("downloadEngine") in _ENGINES else "auto"
        settings["maxConcurrentDownloads"] = _bounded_int(settings.get("maxConcurrentDownloads"), 2, 1, 5)
        for key in ("clipboardMonitoring", "minimizeToTray", "firstRun", "checkUpdatesOnStartup", "downloadThumbnail", "rateLimitProtection", "cobaltEnabled"):
            settings[key] = _valid_bool(settings.get(key), DEFAULT_SETTINGS[key])
        settings["cookieFile"] = _clean_path(settings.get("cookieFile"), DEFAULT_SETTINGS["cookieFile"])
        for key in ("renamePattern", "thumbnailFormat", "thumbnailQuality", "cobaltUrl", "cobaltApiKey"):
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
        if key in {"downloadPath", "cookieFile"}:
            value = DEFAULT_SETTINGS[key] if _is_unc(value) else str(value)
        self.settings[key] = value

    def update(self, **values: Any) -> None:
        safe = {
            k: (DEFAULT_SETTINGS[k] if _is_unc(v) else str(v)) if k in {"downloadPath", "cookieFile"} else v
            for k, v in values.items()
        }
        self.settings.update(safe)
        self.saveSettings()

    def getDownloadPath(self, mediaType: str = "video") -> Path:
        raw = self.get("downloadPath")
        base = DEFAULT_SETTINGS["downloadPath"] if (_is_unc(raw) or not raw) else raw
        (path := Path(base) / ("Audio" if mediaType == "audio" else "Videos")).mkdir(parents=True, exist_ok=True)
        return path
