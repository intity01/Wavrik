"""Harmonic and tempo synchronization DSP service for dual-deck DJ mixing."""

from __future__ import annotations

from src.services.audio_analysis import camelot_code
from src.services.audio_camelot import key_from_camelot, semitone_distance

_COMPAT = {"Match": 1.0, "Relative": 1.0, "+1 Boost": 0.9, "-1 Drop": 0.9, "+2 Energy Boost": 0.85, "-2 Energy Drop": 0.8}


def _resolve_key_and_code(key_or_code: str) -> tuple[str, str]:
    raw = key_or_code.strip()
    if not raw:
        return "", ""
    k = key_from_camelot(raw.upper())
    if k:
        return raw.upper(), k
    parts = raw.split()
    if len(parts) == 2:
        canonical_key = f"{parts[0][:1].upper()}{parts[0][1:].lower()} {parts[1].lower()}"
        code = camelot_code(canonical_key)
        if code != "--":
            return code, canonical_key
    code = camelot_code(raw)
    return (code, raw) if code != "--" else ("", "")


def calculate_harmonic_tempo_ratio(
    bpm_a: float, bpm_b: float, allow_half_double: bool = True
) -> tuple[float, str]:
    """Calculate target playback rate for deck B to match deck A tempo."""
    if bpm_a <= 0.0 or bpm_b <= 0.0:
        return 1.0, "direct"
    if allow_half_double:
        half_ratio = bpm_a / (2.0 * bpm_b)
        if 0.85 <= half_ratio <= 1.15:
            return max(0.5, min(2.0, float(half_ratio))), "half_time"
        double_ratio = (2.0 * bpm_a) / bpm_b
        if 0.85 <= double_ratio <= 1.15:
            return max(0.5, min(2.0, float(double_ratio))), "double_time"
    return max(0.5, min(2.0, float(bpm_a / bpm_b))), "direct"


def get_extended_camelot_transitions(key_or_code: str) -> list[dict]:
    """Return 6 extended Camelot transitions: Match, Relative, +/-1, +/-2."""
    code, key_name = _resolve_key_and_code(key_or_code)
    if not code or len(code) < 2:
        return []
    num, letter = int(code[:-1]), code[-1].upper()
    opp_letter = "B" if letter == "A" else "A"
    next_num = 1 if num == 12 else num + 1
    prev_num = 12 if num == 1 else num - 1
    boost2, drop2 = ((num + 1) % 12) + 1, ((num - 3) % 12) + 1
    slots = (
        (f"{num}{letter}", "Match", "Same key / Energy match"),
        (f"{num}{opp_letter}", "Relative", "Mood shift (Rel. Major/Minor)"),
        (f"{next_num}{letter}", "+1 Boost", "Energy boost (Clockwise)"),
        (f"{prev_num}{letter}", "-1 Drop", "Energy drop (Counter-clockwise)"),
        (f"{boost2}{letter}", "+2 Energy Boost", "Energy modulation (Whole step up)"),
        (f"{drop2}{letter}", "-2 Energy Drop", "Energy drop (Whole step down)"),
    )
    res = []
    for c_code, label, desc in slots:
        k = key_from_camelot(c_code)
        if k:
            res.append({
                "code": c_code, "key": k, "label": label, "desc": desc,
                "semitones": semitone_distance(key_name, k),
                "compatibility": _COMPAT.get(label, 0.7),
            })
    return res


def recommend_harmonic_shifts(deck_a_key: str, deck_b_key: str) -> list[dict]:
    """Compute minimal semitone shifts [-6, +6] to align Deck B with Deck A."""
    code_a, _ = _resolve_key_and_code(deck_a_key)
    _, key_b = _resolve_key_and_code(deck_b_key)
    if not code_a or not key_b:
        return []
    recs: list[dict] = []
    for t in get_extended_camelot_transitions(code_a):
        shift = semitone_distance(key_b, t["key"])
        recs.append({
            "code": t["code"], "target_code": t["code"], "key": t["key"],
            "target_key": t["key"], "label": t["label"], "desc": t["desc"],
            "semitones": shift, "diff": shift, "compatibility": t.get("compatibility", 0.7),
        })
    recs.sort(key=lambda r: (abs(r["semitones"]), r["semitones"]))
    return recs


def calculate_beat_phase_error(
    pos_a: float, bpm_a: float, t0_a: float, pos_b: float, bpm_b: float, t0_b: float
) -> float:
    """Calculate beat phase error wrapped in [-T/2, +T/2]."""
    if bpm_a <= 0.0 or bpm_b <= 0.0:
        return 0.0
    t_a, t_b = 60.0 / bpm_a, 60.0 / bpm_b
    phi_a, phi_b = (pos_a - t0_a) % t_a, (pos_b - t0_b) % t_b
    err = (phi_a - phi_b) % t_a
    if err > t_a / 2.0:
        err -= t_a
    elif err < -t_a / 2.0:
        err += t_a
    return float(err)


def calculate_momentary_nudge_rate(
    base_rate: float, direction: str, intensity: float = 0.02
) -> float:
    """Compute momentary playback rate for pitch bend nudge."""
    norm = direction.strip().lower()
    if norm in ("forward", "fwd", "+", "faster", "up", "ahead"):
        rate = base_rate * (1.0 + abs(intensity))
    elif norm in ("backward", "back", "bwd", "-", "slower", "down"):
        rate = base_rate * (1.0 - abs(intensity))
    else:
        rate = base_rate
    return max(0.5, min(2.0, float(rate)))
