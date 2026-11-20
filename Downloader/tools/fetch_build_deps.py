"""Download the pinned native build dependencies into the repository root.

ffmpeg.exe, rubberband.exe and sndfile.dll are too large for git. ffmpeg.exe is taken
from a published Wavrik release zip; rubberband.exe and sndfile.dll from the official
Rubber Band 4.0.0 Windows build. Every file is checked against a pinned SHA-256 hash,
and files already present with the right hash are left alone.

Run from anywhere (standard library only):
    python Downloader/tools/fetch_build_deps.py
"""

from __future__ import annotations

import hashlib
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    "https://github.com/intity01/Wavrik/releases/download/v2.3.0/"
    "MediaDownloaderPRO-v2.3.0-Windows-x64.zip": ("ffmpeg.exe",),
    "https://breakfastquay.com/files/releases/"
    "rubberband-4.0.0-gpl-executable-windows.zip": ("rubberband.exe", "sndfile.dll"),
}
DEPENDENCIES = {
    "ffmpeg.exe": "228d7a8556258de907fdb55f36850078ebc7680b84ec30d84ea02e99bec1d1eb",
    "rubberband.exe": "d26d81e20f48ea33070e638f58bdeb6a61ce7f0946d8f2629f30441caa2905d1",
    "sndfile.dll": "4e3bd2de8e1485110eaebef8e1239471f73d608773831c323bf528e05645655e",
}


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def missing_dependencies() -> list[str]:
    missing = []
    for name, expected in DEPENDENCIES.items():
        target = REPO_ROOT / name
        if not target.is_file() or sha256_of(target) != expected:
            missing.append(name)
    return missing


def download(url: str, destination: Path) -> None:
    sys.stdout.write(f"Downloading {url}\n")
    with urllib.request.urlopen(url) as response, destination.open("wb") as out:
        total = int(response.headers.get("Content-Length") or 0)
        done = 0
        while chunk := response.read(1 << 20):
            out.write(chunk)
            done += len(chunk)
            if total:
                sys.stdout.write(f"\r  {done * 100 // total:3d}%  {done >> 20} / {total >> 20} MB")
                sys.stdout.flush()
    sys.stdout.write("\n")


def extract(archive: Path, url: str, names: list[str]) -> None:
    with zipfile.ZipFile(archive) as bundle:
        members = {Path(info.filename).name: info for info in bundle.infolist() if not info.is_dir()}
        for name in names:
            info = members.get(name)
            if info is None:
                raise RuntimeError(f"{name} is not in {url}")
            target = REPO_ROOT / name
            partial = target.with_suffix(target.suffix + ".part")
            with bundle.open(info) as src, partial.open("wb") as dst:
                while chunk := src.read(1 << 20):
                    dst.write(chunk)
            actual = sha256_of(partial)
            if actual != DEPENDENCIES[name]:
                partial.unlink()
                raise RuntimeError(f"{name} SHA-256 mismatch: expected {DEPENDENCIES[name]}, got {actual}")
            partial.replace(target)
            sys.stdout.write(f"  {name} OK\n")


def main() -> int:
    missing = missing_dependencies()
    if not missing:
        sys.stdout.write("Build dependencies already present and verified.\n")
        return 0
    sys.stdout.write(f"Fetching: {', '.join(missing)}\n")
    try:
        with tempfile.TemporaryDirectory() as tmp:
            for index, (url, provides) in enumerate(SOURCES.items()):
                wanted = [name for name in provides if name in missing]
                if not wanted:
                    continue
                archive = Path(tmp) / f"source{index}.zip"
                download(url, archive)
                extract(archive, url, wanted)
    except Exception as exc:  # noqa: BLE001 - report any failure as a clean exit code
        sys.stderr.write(f"Error: {exc}\n")
        return 1
    sys.stdout.write("Build dependencies ready.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
