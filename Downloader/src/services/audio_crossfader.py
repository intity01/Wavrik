"""Pure DSP crossfader gain calculations and volume staging for DJ mixing."""

from __future__ import annotations

import math

CURVE_EQUAL_POWER = "equal_power"
CURVE_LINEAR = "linear"
CURVE_SCRATCH = "scratch"
SUPPORTED_CURVES = (CURVE_EQUAL_POWER, CURVE_LINEAR, CURVE_SCRATCH)


def crossfader_gains(position: float, curve: str = "equal_power") -> tuple[float, float]:
    """Calculate Deck A and Deck B gains for a given crossfader position.

    Args:
        position: Normalized slider position in [0.0, 1.0] (0.0=Deck A, 1.0=Deck B).
        curve: Attenuation curve ('equal_power', 'linear', or 'scratch').

    Returns:
        tuple[float, float]: (gain_deck_a, gain_deck_b) both clamped in [0.0, 1.0].
    """
    pos = max(0.0, min(1.0, float(position)))
    if pos <= 0.0:
        return 1.0, 0.0
    if pos >= 1.0:
        return 0.0, 1.0

    normalized_curve = (curve or "").strip().lower()
    if normalized_curve == CURVE_LINEAR:
        return 1.0 - pos, pos

    if normalized_curve in (CURVE_SCRATCH, "cut"):
        gain_a = 1.0 if pos <= 0.95 else max(0.0, (1.0 - pos) / 0.05)
        gain_b = 1.0 if pos >= 0.05 else max(0.0, pos / 0.05)
        return gain_a, gain_b

    angle = pos * (math.pi / 2.0)
    return math.cos(angle), math.sin(angle)


def calculate_effective_volume(
    master: float, channel: float, gain: float, crossfade: float, muted: bool = False
) -> float:
    """Calculate final linear volume for QAudioOutput from staged mixer parameters."""
    if muted:
        return 0.0
    effective = float(master) * float(channel) * float(gain) * float(crossfade)
    return max(0.0, min(1.0, effective))


def step_crossfader(current: float, target: float, step: float = 0.02) -> float:
    """Step current crossfader position toward target by step magnitude."""
    cur = max(0.0, min(1.0, float(current)))
    tgt = max(0.0, min(1.0, float(target)))
    step_mag = abs(float(step))
    if step_mag == 0.0 or cur == tgt:
        return tgt
    if tgt > cur:
        next_pos = cur + step_mag
        return tgt if next_pos >= tgt else next_pos
    next_pos = cur - step_mag
    return tgt if next_pos <= tgt else next_pos


def bipolar_to_normalized(value: float) -> float:
    """Convert bipolar crossfader [-1.0, 1.0] to normalized [0.0, 1.0]."""
    return max(0.0, min(1.0, (float(value) + 1.0) / 2.0))


def normalized_to_bipolar(value: float) -> float:
    """Convert normalized crossfader [0.0, 1.0] to bipolar [-1.0, 1.0]."""
    return max(-1.0, min(1.0, float(value) * 2.0 - 1.0))
