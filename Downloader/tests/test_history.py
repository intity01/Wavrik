import json
from pathlib import Path

from src.core.config import Config
from src.services.history_manager import HistoryManager


def test_history_records_actual_file_and_stats(history, tmp_path: Path):
    media = tmp_path / "song.mp3"
    media.write_bytes(b"123456")
    history.addEntry(
        "https://example.com/a", "Song", "audio", "MP3 320",
        str(media), True, media.stat().st_size, status="completed",
    )
    entry = history.getHistory()[0]
    assert entry["filePath"] == str(media)
    assert history.getStats()["successful"] == 1
    payload = json.loads(history.historyFile.read_text(encoding="utf-8"))
    assert payload["schemaVersion"] == HistoryManager.SCHEMA_VERSION


def test_corrupt_history_is_backed_up(config, logger):
    config.historyFile.write_text("{broken", encoding="utf-8")
    history = HistoryManager(config, logger)
    assert history.getHistory() == []
    assert config.historyFile.with_suffix(".json.corrupt").exists()


def test_invalid_history_schema_is_backed_up(config, logger):
    config.historyFile.write_text('{"schemaVersion": 99, "entries": []}', encoding="utf-8")
    history = HistoryManager(config, logger)
    assert history.getHistory() == []
    assert config.historyFile.with_suffix(".json.corrupt").exists()


def test_invalid_settings_are_recovered(tmp_path: Path):
    app_data = tmp_path / "appdata"
    app_data.mkdir()
    (app_data / "settings.json").write_text(
        '{"schemaVersion": 2, "theme": 42, "maxConcurrentDownloads": "many"}',
        encoding="utf-8",
    )
    config = Config(app_data)
    assert config.get("theme") == "dark"
    assert config.get("maxConcurrentDownloads") == 2


def test_invalid_settings_root_is_backed_up(tmp_path: Path):
    app_data = tmp_path / "appdata"
    app_data.mkdir()
    settings = app_data / "settings.json"
    settings.write_text("[]", encoding="utf-8")
    config = Config(app_data)
    assert config.get("theme") == "dark"
    assert settings.with_suffix(".json.corrupt").exists()
