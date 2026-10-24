"""Essentia-compatible SpectralWhitening, HPCP, and bgate key profile correlation."""

from __future__ import annotations

import cmath
import math

ESSENTIA_KEYS = ("A", "A#", "B", "C", "C#", "D", "D#", "E", "F", "F#", "G", "G#")
BGATE_M = (1.00, 0.00, 0.42, 0.00, 0.53, 0.37, 0.00, 0.77, 0.00, 0.38, 0.21, 0.30)
BGATE_m = (1.00, 0.00, 0.36, 0.39, 0.00, 0.38, 0.00, 0.74, 0.27, 0.00, 0.42, 0.23)
_HARM_TABLE = ((0.0, 1.0), (7.019550008653875, 0.17), (3.863137138648348, 0.02))
_N = 4096
_SPEC_SIZE = _N // 2 + 1


def _bit_reverse(n: int) -> list[int]:
    bits = n.bit_length() - 1
    return [int(f"{i:0{bits}b}"[::-1], 2) for i in range(n)]


def _build_sw_bands() -> list[tuple[int, int, list[float]]]:
    bands: list[tuple[int, int, list[float]]] = []
    for idx_pt in range(71):
        freq = 50.0 * idx_pt
        bf, ef = freq - max(50.0, freq * 0.34), freq + max(50.0, freq * 0.58)
        b = max(0, min(_SPEC_SIZE - 1, int(bf / 8000.0 * (_SPEC_SIZE - 1.0) + 0.5)))
        e = max(b + 1, min(_SPEC_SIZE, int(ef / 8000.0 * (_SPEC_SIZE - 1.0) + 0.5)))
        c, hw = 0.5 * (b + e), e - 0.5 * (b + e)
        bands.append((b, e, [((1.0 - abs(k - c) / hw) ** 4) for k in range(b, e)]))
    return bands


_REV = _bit_reverse(_N)
_TWIDDLES = [[cmath.exp(-1j * math.pi * k / h) for k in range(h)] for h in (1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024, 2048)]
_HANN = [0.5 - 0.5 * math.cos(2.0 * math.pi * i / (_N - 1)) for i in range(_N)]
_WIN = [w * (2.0 / sum(_HANN)) for w in _HANN]
_SW_BANDS = _build_sw_bands()


def extract_key_candidates(samples: list[float], sr: int = 16000) -> list[dict]:
    return extract_key_and_sections(samples, sr)[0]


def extract_key_and_sections(samples: list[float], sr: int = 16000) -> tuple[list[dict], str, str]:
    padded = [0.0] * (_N // 2) + samples + [0.0] * (_N // 2)
    stride = _N if len(padded) <= 64 * _N else max(_N, (len(padded) - _N) // 64)
    starts = list(range(0, max(1, len(padded) - _N + 1), stride))
    hp1, hp2, mid = [0.0] * 12, [0.0] * 12, max(1, len(starts) // 2)
    for idx in range(0, len(starts), 2):
        s1 = starts[idx]
        f1 = [padded[s1 + i] * _WIN[i] for i in range(_N)]
        dst1 = hp1 if idx < mid else hp2
        if idx + 1 < len(starts):
            s2 = starts[idx + 1]
            sp1, sp2 = _fft_pair_mag(f1, [padded[s2 + i] * _WIN[i] for i in range(_N)])
            _accumulate_frame_hpcp(sp1, float(sr), dst1)
            _accumulate_frame_hpcp(sp2, float(sr), hp1 if (idx + 1) < mid else hp2)
        else:
            sp1, _ = _fft_pair_mag(f1, [0.0] * _N)
            _accumulate_frame_hpcp(sp1, float(sr), dst1)
    full = _correlate_bgate(_gate_pcp([hp1[i] + hp2[i] for i in range(12)]))
    k1 = _correlate_bgate(_gate_pcp(hp1))[0]["key"] if max(hp1) > 0 else full[0]["key"]
    k2 = _correlate_bgate(_gate_pcp(hp2))[0]["key"] if max(hp2) > 0 else full[0]["key"]
    return full, k1, k2


def _gate_pcp(hpcp: list[float]) -> list[float]:
    mx = max(hpcp, default=1.0) or 1.0
    return [v / mx if (v / mx) >= 0.2 else 0.0 for v in hpcp]


def _fft_pair_mag(x1: list[float], x2: list[float]) -> tuple[list[float], list[float]]:
    buf = [complex(x1[idx], x2[idx]) for idx in _REV]
    for stage, tw in enumerate(_TWIDDLES):
        half, step = 1 << stage, 2 << stage
        for base in range(0, _N, step):
            for k in range(half):
                t, u = tw[k] * buf[base + k + half], buf[base + k]
                buf[base + k + half], buf[base + k] = u - t, u + t
    m1, m2 = [0.0] * 1425, [0.0] * 1425
    m1[0], m2[0] = abs(buf[0].real), abs(buf[0].imag)
    for k in range(1, 1425):
        zk, z_nk = buf[k], buf[_N - k].conjugate()
        m1[k], m2[k] = 0.5 * abs(zk + z_nk), 0.5 * abs(zk - z_nk)
    return m1, m2


def _accumulate_frame_hpcp(spec: list[float], sr: float, hpcp: list[float]) -> None:
    lo_b, hi_b = max(1, int(math.ceil(25.0 * _N / sr))), min(len(spec) - 2, int(math.floor(3500.0 * _N / sr)))
    peaks: list[tuple[float, float]] = []
    for b in range(lo_b, hi_b + 1):
        sb = spec[b]
        if sb > 1e-4 and sb > spec[b - 1] and sb > spec[b + 1]:
            a, bt, g = 20.0 * math.log10(max(1e-20, spec[b - 1])), 20.0 * math.log10(max(1e-20, sb)), 20.0 * math.log10(max(1e-20, spec[b + 1]))
            den = a - 2.0 * bt + g
            p = 0.5 * (a - g) / den if abs(den) > 1e-12 else 0.0
            pf = (b + p) * (sr / _N)
            if 25.0 <= pf <= 3500.0:
                peaks.append((10.0 ** ((bt - 0.25 * (a - g) * p) / 20.0), pf))
    if peaks:
        peaks.sort(reverse=True)
        _whiten_to_hpcp(spec, peaks[:60], hpcp)


def _whiten_to_hpcp(spec: list[float], peaks: list[tuple[float, float]], hpcp: list[float]) -> None:
    spec_e = [s * s for s in spec]
    y_db: list[float] = []
    for b, e, weights in _SW_BANDS:
        num = sum(se * se * w4 for se, w4 in zip(spec_e[b:e], weights))
        den = sum(se * w4 for se, w4 in zip(spec_e[b:e], weights))
        y_db.append(20.0 * math.log10(max(1e-20, math.sqrt(max(0.0, num / den if den > 0.0 else 0.0)))))
    y_db[-1] = y_db[-2]
    for mag, freq in peaks:
        amp = 20.0 * math.log10(max(1e-20, mag))
        pos = max(0.0, min(69.9999, freq / 50.0))
        i0 = int(pos)
        env = y_db[i0] * (1.0 - (pos - i0)) + y_db[i0 + 1] * (pos - i0)
        w = 0.0 if amp > env else (amp - env if amp > env - 30.0 else -200.0)
        wm2 = (10.0 ** ((w - 20.0 * freq / 4000.0) / 20.0)) ** 2
        for semi_shift, hw2 in _HARM_TABLE:
            pc = (12.0 * math.log2(freq * (2.0 ** (-semi_shift / 12.0)) / 440.0)) % 12.0
            for b0 in range(12):
                d = min(abs(pc - b0), 12.0 - abs(pc - b0))
                if d < 0.5:
                    hpcp[b0] += math.cos(math.pi * d) * wm2 * hw2


def _correlate_bgate(pcp: list[float]) -> list[dict]:
    out: list[dict] = []
    for shift, note in enumerate(ESSENTIA_KEYS):
        rot_m_maj = BGATE_M[-shift:] + BGATE_M[:-shift] if shift else BGATE_M
        rot_m_min = BGATE_m[-shift:] + BGATE_m[:-shift] if shift else BGATE_m
        out.append({"key": f"{note} major", "correlation": round(_pearson12(pcp, rot_m_maj), 4)})
        out.append({"key": f"{note} minor", "correlation": round(_pearson12(pcp, rot_m_min), 4)})
    out.sort(key=lambda item: item["correlation"], reverse=True)
    return out


def _pearson12(x: list[float], y: tuple[float, ...]) -> float:
    mx, my = sum(x) / 12.0, sum(y) / 12.0
    num = sum((x[i] - mx) * (y[i] - my) for i in range(12))
    dx = math.sqrt(sum((x[i] - mx) ** 2 for i in range(12)))
    dy = math.sqrt(sum((y[i] - my) ** 2 for i in range(12)))
    return num / (dx * dy + 1e-12)
