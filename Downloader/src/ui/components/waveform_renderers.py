"""Stateless QPainter routines for waveform, spectrogram, and beat grid rendering."""

from __future__ import annotations

import numpy as np
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont, QFontMetrics, QPainter, QPen


def draw_background(painter: QPainter, w: int, h: int, tokens: dict) -> None:
    painter.fillRect(0, 0, w, h, QColor(tokens["surface"]))
    painter.setPen(QPen(QColor(tokens["border"]), 1))
    painter.drawRoundedRect(0, 0, w - 1, h - 1, 5, 5)


def draw_empty_state(painter: QPainter, w: int, h: int, tokens: dict) -> None:
    painter.setPen(QColor(tokens["text_subtle"]))
    painter.setFont(QFont("Segoe UI", 9))
    painter.drawText(0, 0, w, h, Qt.AlignmentFlag.AlignCenter, "Waveform preview loads on analysis (Click to seek)")


def draw_bars(painter: QPainter, bars: tuple, w: int, h: int) -> None:
    peaks, played_count, played_hue, unplayed_hue = bars
    n = len(peaks)
    bar_width = max(2.0, (w - 16) / max(1, n))
    c1, c2 = QColor(played_hue), QColor(unplayed_hue)
    for i, p in enumerate(peaks):
        x = 8 + i * bar_width
        bar_h = max(3.0, p * (h - 24))
        y = (h / 2.0) - (bar_h / 2.0) + 2
        painter.fillRect(int(x), int(y), max(1, int(bar_width - 1.5)), int(bar_h), c1 if i < played_count else c2)


def draw_midpoint(painter: QPainter, w: int, h: int, info: tuple) -> None:
    label, tokens = info
    mid = w // 2
    painter.setPen(QPen(QColor(tokens["text_subtle"]), 1, Qt.PenStyle.DashLine))
    painter.drawLine(mid, 4, mid, h - 4)
    font = QFont("Segoe UI", 9, QFont.Weight.Bold)
    painter.setFont(font)
    painter.setPen(QColor(tokens["text_muted"]))
    elided = QFontMetrics(font).elidedText(label or "1st Half | 2nd Half", Qt.TextElideMode.ElideRight, max(40, (w - mid) - 10))
    painter.drawText(mid + 5, 13, elided)


def draw_playhead(painter: QPainter, w: int, h: int, timing: tuple, tokens: dict) -> None:
    seek_sec, duration = timing
    if duration <= 0:
        return
    px = int(8 + (seek_sec / duration) * max(1, w - 16))
    painter.setPen(QPen(QColor(tokens["text"]), 2))
    painter.drawLine(px, 2, px, h - 2)
    mins, secs = int(seek_sec // 60), int(seek_sec % 60)
    painter.setFont(QFont("Consolas", 9, QFont.Weight.Bold))
    painter.drawText(min(w - 52, max(10, px + 4)), 13, f"@{mins}:{secs:02d}")


def draw_time_markers(painter: QPainter, w: int, h: int, duration: float, tokens: dict) -> None:
    if duration <= 0:
        return
    painter.setFont(QFont("Consolas", 9))
    painter.setPen(QColor(tokens["text_muted"]))
    painter.drawText(8, h - 5, "0:00")
    mins, secs = int(duration // 60), int(duration % 60)
    painter.drawText(w - 36, h - 5, f"{mins}:{secs:02d}")


def draw_spectrogram(painter: QPainter, spec: np.ndarray, w: int, h: int, tokens: dict) -> None:
    if spec is None or spec.size == 0 or spec.ndim != 2:
        return
    n_cols, n_bands = spec.shape
    if n_cols == 0 or n_bands == 0 or w <= 16 or h <= 16:
        return
    if n_cols > (w - 16):
        from src.services.audio_spectrogram import downsample_spectrogram_columns
        spec = downsample_spectrogram_columns(spec, max(16, (w - 16) // 4))
        n_cols, n_bands = spec.shape
    c1 = QColor(tokens.get("surface_hover", tokens["border"]))
    c2 = QColor(tokens.get("border_strong", tokens["border"]))
    c3 = QColor(tokens.get("text_subtle", tokens["accent"]))
    c4 = QColor(tokens.get("accent", tokens["text"]))
    cell_w, cell_h = (w - 16.0) / float(n_cols), (h - 16.0) / float(n_bands)
    for c in range(n_cols):
        x0 = int(8.0 + c * cell_w)
        cw = max(1, int(8.0 + (c + 1) * cell_w) - x0)
        for b in range(n_bands):
            val = float(spec[c, b])
            if val < 0.15:
                continue
            color = c4 if val >= 0.85 else (c3 if val >= 0.6 else (c2 if val >= 0.35 else c1))
            y0 = int((h - 8.0) - (b + 1) * cell_h)
            ch = max(1, int((h - 8.0) - b * cell_h) - y0)
            painter.fillRect(x0, y0, cw, ch, color)


def draw_beat_grid(
    painter: QPainter, markers: list[tuple[float, str]], duration: float, w: int, h: int, tokens: dict
) -> None:
    if duration <= 0.0 or not markers or w <= 16:
        return
    pen_phrase = QPen(QColor(tokens.get("accent", tokens["text"])), 1.5, Qt.PenStyle.SolidLine)
    pen_down = QPen(QColor(tokens.get("border_strong", tokens["text_muted"])), 1.5, Qt.PenStyle.SolidLine)
    pen_beat = QPen(QColor(tokens.get("border_strong", tokens["border"])), 1.0, Qt.PenStyle.DashLine)

    for t, kind in markers:
        px = int(8.0 + (t / duration) * max(1.0, w - 16.0))
        if px < 8 or px > w - 8:
            continue
        if kind == "phrase":
            painter.setPen(pen_phrase)
        elif kind == "downbeat":
            painter.setPen(pen_down)
        else:
            painter.setPen(pen_beat)
        painter.drawLine(px, 4, px, h - 4)
