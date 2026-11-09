"""Validation and path helpers for configuration settings."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def _supported_schema(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value in {1, 2}


def _bounded_int(value: Any, default: int, minimum: int, maximum: int) -> int:
    try:
        return max(minimum, min(maximum, int(value)))
    except (TypeError, ValueError):
        return default


def _valid_bool(value: Any, default: bool) -> bool:
    return value if isinstance(value, bool) else default


def _valid_text(value: Any, default: str) -> str:
    return value.strip() if isinstance(value, str) and value.strip() else default


def _is_unc(value: Any) -> bool:
    return bool(value) and str(value).strip().startswith(("\\\\", "//"))


def _clean_path(value: Any, default: str) -> str:
    text = _valid_text(str(value) if isinstance(value, Path) else value, default)
    return default if _is_unc(text) else text
