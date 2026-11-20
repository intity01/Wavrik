"""Render the Wavrik artwork into the multi-size Windows icon at src/core/app.ico.

Raster masters assets/icon/wavrik.png and wavrik-small.png (1024 px) are used when present;
otherwise the wavrik*.svg sources are rendered. Sizes up to SMALL_MAX use the small artwork
(no cheeks or mouth) so the face stays legible.

Run from the Downloader folder after changing the artwork:
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
PNG_SOURCE = ROOT / "assets" / "icon" / "wavrik.png"
PNG_SMALL_SOURCE = ROOT / "assets" / "icon" / "wavrik-small.png"
TARGET = ROOT / "src" / "core" / "app.ico"
SIZES = (16, 20, 24, 32, 40, 48, 64, 128, 256)
SMALL_MAX = 32


def to_png(image: QImage) -> bytes:
    data = QByteArray()
    buffer = QBuffer(data)
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    image.save(buffer, "PNG")
    return bytes(data.data())


def scale_png(master: QImage, size: int) -> bytes:
    # Halve step by step so tiny sizes average every source pixel instead of aliasing.
    image = master
    while image.width() >= size * 2:
        image = image.scaled(image.width() // 2, image.height() // 2,
                             Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
    image = image.scaled(size, size, Qt.AspectRatioMode.IgnoreAspectRatio, Qt.TransformationMode.SmoothTransformation)
    return to_png(image)


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
    return to_png(image)


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
    if PNG_SOURCE.is_file() and PNG_SMALL_SOURCE.is_file():
        large_img = QImage(str(PNG_SOURCE)).convertToFormat(QImage.Format.Format_ARGB32_Premultiplied)
        small_img = QImage(str(PNG_SMALL_SOURCE)).convertToFormat(QImage.Format.Format_ARGB32_Premultiplied)
        pngs = [(s, scale_png(small_img if s <= SMALL_MAX else large_img, s)) for s in SIZES]
        TARGET.write_bytes(build_ico(pngs))
        sys.stdout.write(f"Wrote {TARGET} from PNG masters ({', '.join(map(str, SIZES))} px)\n")
        del app
        return 0
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
