"""Objective 4-pillar benchmark and torture-test suite for Wavrik Key & BPM engine."""

from __future__ import annotations

import math
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.services.audio_analysis import (  # noqa: E402
    analyze_audio_file,
    mirex_bpm_score,
    mirex_key_score,
)
from src.services.audio_dsp import estimate_bpm  # noqa: E402
from src.services.audio_hpcp import extract_key_candidates  # noqa: E402

WEB_REFERENCE_BENCHMARK = [
    ("Theater (Instrumental)", "F major", "7B", 119),
    ("offvocal_mst(1)", "D# minor", "2A", 80),
    ("Vocal_only", "G# minor", "1A", 80),
    ("Tell Me About You Tatsuya Kitani.wav", "G major", "9B", 105),
    ("Tell Me About You- リアルカラオケ(Instrumental)Shadowverse_ Worlds BeyondCM_F_major__bpm_105", "F major", "7B", 105),
    ("Chained", "F# minor", "11A", 88),
    ("Akuma_no_Ko_Anime_Special_Ver.wav", "B minor", "10A", 90),
    ("Shinigami.wav", "A minor", "8A", 119),
    ("natori_Cult_FinalMix2_Inst.wav", "A minor", "8A", 81),
    ("Natori_Eureka_Inst.wav", "E major", "12B", 80),
    ("ヨルシカ - 言って。(Music Video).wav", "C major", "8B", 90),
]


def _synth_progression_samples(tonic_midi: int, mode: str, bpm: float, sr: int = 16000, seconds: float = 10.0) -> list[float]:
    """Synthesize a realistic harmonic progression (I-IV-V-I) with pulsed bass + triad harmonics."""
    third = 4 if mode == "major" else 3
    chords = (
        (0, third, 7),
        (5, 8 if mode == "minor" else 9, 12),
        (7, 11, 14),
        (0, third, 7),
    )
    beat_sec = 60.0 / bpm
    total = int(seconds * sr)
    out = [0.0] * total
    for i in range(total):
        t = i / float(sr)
        beat_idx = int(t / beat_sec)
        phase = (t % beat_sec) / beat_sec
        env = math.exp(-3.5 * phase)
        chord = chords[(beat_idx // 2) % 4]
        sig = 0.0
        for st in chord:
            f0 = 440.0 * (2.0 ** ((tonic_midi + st - 69) / 12.0))
            sig += 0.60 * math.sin(2.0 * math.pi * f0 * t)
            sig += 0.25 * math.sin(2.0 * math.pi * (f0 * 0.5) * t)
            sig += 0.20 * math.sin(2.0 * math.pi * (f0 * 2.0) * t)
        out[i] = sig * env * 0.25
    return out


def run_synthetic_ground_truth_suite() -> tuple[int, int, int, int]:
    print("=== PILLAR 1: MATHEMATICAL GROUND-TRUTH SYNTHESIS (I-IV-V-I Progressions) ===")
    test_cases = [
        (60, "C", "major", 120),
        (69, "A", "minor", 90),
        (65, "F", "major", 105),
        (66, "F#", "minor", 88),
        (64, "E", "major", 80),
        (63, "D#", "minor", 118),
    ]
    k_ok, b_ok = 0, 0
    for midi, note, mode, bpm in test_cases:
        exp_k = f"{note} {mode}"
        s = _synth_progression_samples(midi, mode, float(bpm))
        got_k = extract_key_candidates(s, 16000)[0]["key"]
        got_b = estimate_bpm(s, 16000)
        sc_k, rel_k = mirex_key_score(got_k, exp_k)
        sc_b, rel_b = mirex_bpm_score(got_b, float(bpm))
        k_ok += int(sc_k == 1.0)
        b_ok += int(sc_b == 1.0)
        print(f"  Synth {exp_k:9s} @ {bpm:3d} BPM -> Got {got_k:9s} ({rel_k}) @ {got_b:5.1f} BPM ({rel_b})")
    print(f"Pillar 1 Score: Key={k_ok}/{len(test_cases)}, BPM={b_ok}/{len(test_cases)}\n")
    return k_ok, len(test_cases), b_ok, len(test_cases)


def run_web_parity_suite(downloads_dir: Path) -> None:
    if not downloads_dir.is_dir():
        return
    print("=== PILLAR 2: 3-WAY INDUSTRY WEB PARITY (Tunebat.com & VocalRemover.org) ===")
    mirex_k_sum = 0.0
    mirex_b_sum = 0.0
    exact_k, exact_b, count = 0, 0, 0
    for pat, exp_key, exp_cam, exp_bpm in WEB_REFERENCE_BENCHMARK:
        matches = sorted([x for x in downloads_dir.iterdir() if pat.lower() in x.name.lower() and x.suffix.lower() in (".wav", ".mp3")])
        if not matches:
            continue
        p = matches[0]
        t0 = time.perf_counter()
        res = analyze_audio_file(p)
        dt = time.perf_counter() - t0
        sc_k, rel_k = mirex_key_score(res["key"], exp_key)
        sc_b, rel_b = mirex_bpm_score(res["bpm"], float(exp_bpm))
        mirex_k_sum += sc_k
        mirex_b_sum += sc_b
        exact_k += int(sc_k == 1.0)
        exact_b += int(sc_b == 1.0)
        count += 1
        print(
            f"  {p.name[:36]:36s} | Web={exp_key:8s}({exp_cam:3s}) {exp_bpm:3d} | "
            f"Wavrik={res['key']:8s}({res['camelot']:3s}) {res['bpm']:5.1f} | "
            f"Conf={res['confidence']:2d}% | MIREX_K={sc_k:.1f}({rel_k}) MIREX_B={sc_b:.1f} ({dt:.2f}s)"
        )
    if count:
        print(
            f"Pillar 2 Score ({count} tracks): Exact Key={exact_k}/{count} "
            f"(MIREX Weighted={mirex_k_sum / count * 100:.1f}%), "
            f"Exact BPM={exact_b}/{count} (MIREX Acc={mirex_b_sum / count * 100:.1f}%)\n"
        )


def main() -> None:
    run_synthetic_ground_truth_suite()
    run_web_parity_suite(Path(r"C:\Users\Intity01\Downloads"))


if __name__ == "__main__":
    main()
