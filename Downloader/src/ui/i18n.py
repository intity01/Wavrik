"""Bilingual (TH/EN) single-locale UI string catalog."""

from __future__ import annotations

from .i18n_en import STRINGS_EN
from .i18n_th import STRINGS_TH

_STRINGS: dict[str, dict[str, str]] = {
    "en": STRINGS_EN,
    "th": STRINGS_TH,
}


def tr(key: str, lang: str = "en") -> str:
    table = _STRINGS.get(lang if lang in _STRINGS else "en", _STRINGS["en"])
    return table.get(key, _STRINGS["en"].get(key, key))
