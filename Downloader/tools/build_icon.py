"""Render assets/icon/wavrik*.svg into the multi-size Windows icon at src/core/app.ico.

Sizes up to SMALL_MAX use wavrik-small.svg (bigger eyes, no cheeks or mouth) so the face stays legible.

Run from the Downloader folder after changing the SVG:
    python tools/build_icon.py
"""

from __future__ import annotations

import struct
import sys
from pathlib import Path

from PyQt6.QtCore import QBuffer, QByteArray, QIODevice, Qt
from PyQt6.QtGui import QGuiApplication, QImage, QPainter, QPainterPath
from PyQt6.QtSvg import QSvgRenderer

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "assets" / "icon" / "wavrik.svg"
SMALL_SOURCE = ROOT / "assets" / "icon" / "wavrik-small.svg"
TARGET = ROOT / "src" / "core" / "app.ico"
SIZES = (16, 20, 24, 32, 40, 48, 64, 128, 256)
SMALL_MAX = 32


def render_png(renderer: QSvgRenderer, size: int) -> bytes:
    image = QImage(size, size, QImage.Format.Format_ARGB32)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    # QtSvg ignores <clipPath>, so apply the 58/256 squircle corner here.
    corner = QPainterPath()
    corner.addRoundedRect(0, 0, size, size, size * 58 / 256, size * 58 / 256)
    painter.setClipPath(corner)
    renderer.render(painter)
    painter.end()
    data = QByteArray()
    buffer = QBuffer(data)
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    image.save(buffer, "PNG")
    return bytes(data.data())


def build_ico(pngs: list[tuple[int, bytes]]) -> bytes:
    header = struct.pack("<HHH", 0, 1, len(pngs))
    offset = 6 + 16 * len(pngs)
    entries, blobs = b"", b""
    for size, png in pngs:
        dim = 0 if size >= 256 else size
        entries += struct.pack("<BBBBHHII", dim, dim, 0, 0, 1, 32, len(png), offset)
        blobs += png
        offset += len(png)
    return header + entries + blobs


def main() -> int:
    app = QGuiApplication.instance() or QGuiApplication(sys.argv[:1])
    large, small = QSvgRenderer(str(SOURCE)), QSvgRenderer(str(SMALL_SOURCE))
    for path, renderer in ((SOURCE, large), (SMALL_SOURCE, small)):
        if not renderer.isValid():
            sys.stderr.write(f"Cannot read {path}\n")
            return 1
    pngs = [(s, render_png(small if s <= SMALL_MAX else large, s)) for s in SIZES]
    TARGET.write_bytes(build_ico(pngs))
    sys.stdout.write(f"Wrote {TARGET} ({', '.join(map(str, SIZES))} px)\n")
    del app
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
