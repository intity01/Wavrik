"""Thread-safe atomic JSON persistence."""

from __future__ import annotations

import json
import os
import threading
import time
from pathlib import Path
from typing import Any


class JsonStore:
    """Read and atomically write one JSON file."""

    def __init__(self, path: Path):
        self.path = path
        self._lock = threading.RLock()
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def read(self, default: Any) -> Any:
        with self._lock:
            if not self.path.exists():
                return default
            for attempt in range(3):
                try:
                    return json.loads(self.path.read_text(encoding="utf-8"))
                except (json.JSONDecodeError, UnicodeDecodeError):
                    self._backup_corrupt_file()
                    return default
                except OSError:
                    if attempt < 2:
                        time.sleep(0.05 * (attempt + 1))
            return default

    def write(self, payload: Any) -> None:
        encoded = json.dumps(payload, indent=2, ensure_ascii=False)
        temp_path = self.path.with_suffix(self.path.suffix + ".tmp")
        with self._lock:
            with temp_path.open("w", encoding="utf-8") as handle:
                handle.write(encoded)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_path, self.path)

    def backup(self) -> None:
        """Quarantine the current file when its structure is unusable."""
        with self._lock:
            self._backup_corrupt_file()

    def _backup_corrupt_file(self) -> None:
        try:
            backup = self.path.with_suffix(self.path.suffix + ".corrupt")
            os.replace(self.path, backup)
        except OSError:
            pass
