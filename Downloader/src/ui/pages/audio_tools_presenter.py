"""Presentation helpers for Audio Tools UI."""

from __future__ import annotations

from src.services.audio_analysis import camelot_code, enharmonic_key, mirex_key_score


def populate_candidate_buttons(buttons: list, candidates: list[dict], top_key: str) -> None:
    for idx, btn in enumerate(buttons):
        ck = str(candidates[idx]["key"]) if idx < len(candidates) else ""
        btn.setText(f"#{idx + 1} {ck} ({camelot_code(ck)} · {mirex_key_score(ck, top_key)[1] if idx > 0 else 'Top'})" if ck else f"#{idx + 1} --")


def populate_harmonic_buttons(buttons: list, neighbors: list[dict]) -> None:
    for idx, btn in enumerate(buttons):
        if idx < len(neighbors):
            nb = neighbors[idx]
            sign = f"+{nb['semitones']}" if nb["semitones"] > 0 else f"{nb['semitones']}"
            btn.setText(f"{nb['code']} {nb['label']} ({sign}st)")
            btn.setToolTip(f"{nb['key']} · {nb['desc']}")
        else:
            btn.setText("--")


def format_analysis_status(key: str, bpm: float, result: dict) -> str:
    enh, conf = enharmonic_key(key), result.get("confidence", "")
    return f"Estimated {f'{key} / {enh}' if enh != key else key} ({camelot_code(key)}){f' [{conf}%]' if conf else ''} · {bpm:.1f} BPM"
