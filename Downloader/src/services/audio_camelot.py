"""Camelot wheel calculations and harmonic mixing neighbor advisory."""

from __future__ import annotations

from src.services.audio_analysis import NOTES, _norm_note, camelot_code

_CAM_TO_KEY = {
    "1A": "G# minor", "2A": "D# minor", "3A": "A# minor", "4A": "F minor",
    "5A": "C minor", "6A": "G minor", "7A": "D minor", "8A": "A minor",
    "9A": "E minor", "10A": "B minor", "11A": "F# minor", "12A": "C# minor",
    "1B": "B major", "2B": "F# major", "3B": "C# major", "4B": "G# major",
    "5B": "D# major", "6B": "A# major", "7B": "F major", "8B": "C major",
    "9B": "G major", "10B": "D major", "11B": "A major", "12B": "E major",
}


def key_from_camelot(code: str) -> str:
    return _CAM_TO_KEY.get(code.strip().upper(), "")


def semitone_distance(source_key: str, target_key: str) -> int:
    s_parts, t_parts = source_key.strip().split(), target_key.strip().split()
    if len(s_parts) != 2 or len(t_parts) != 2:
        return 0
    s_note, t_note = _norm_note(s_parts[0]), _norm_note(t_parts[0])
    if s_note not in NOTES or t_note not in NOTES:
        return 0
    diff = (NOTES.index(t_note) - NOTES.index(s_note)) % 12
    return diff - 12 if diff > 6 else diff


def get_harmonic_neighbors(key_name: str) -> list[dict]:
    code = camelot_code(key_name)
    if code == "--" or len(code) < 2:
        return []
    num, letter = int(code[:-1]), code[-1].upper()
    opp_letter = "B" if letter == "A" else "A"
    next_num = 1 if num == 12 else num + 1
    prev_num = 12 if num == 1 else num - 1
    slots = (
        (f"{num}{letter}", "Match", "Same key / Energy match"),
        (f"{num}{opp_letter}", "Relative", "Mood shift (Rel. Major/Minor)"),
        (f"{next_num}{letter}", "+1 Boost", "Energy boost (Clockwise)"),
        (f"{prev_num}{letter}", "-1 Drop", "Energy drop (Counter-clockwise)"),
    )
    res = []
    for c_code, label, desc in slots:
        k = key_from_camelot(c_code)
        if k:
            res.append({"code": c_code, "key": k, "label": label, "desc": desc, "semitones": semitone_distance(key_name, k)})
    return res
