# Run on Windows with: pyinstaller --noconfirm MediaDownloaderPRO.spec
import shutil
import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

root = Path(SPECPATH)
downloader = root / "Downloader"
deno_candidates = [
    Path(sys.executable).resolve().with_name("deno.exe"),
    Path(sys.executable).resolve().parent / "Scripts" / "deno.exe",
]
deno = next((p for p in deno_candidates if p.is_file()), None)
if not deno:
    which_deno = shutil.which("deno")
    if which_deno:
        deno = Path(which_deno)

if not deno or not deno.is_file():
    raise SystemExit("Deno is required. Install the build dependencies before building.")

extra_binaries = [
    (str(root / name), ".")
    for name in ("rubberband.exe", "sndfile.dll")
    if (root / name).is_file()
]

a = Analysis(
    [str(downloader / "main.py")],
    pathex=[str(downloader)],
    binaries=[(str(root / "ffmpeg.exe"), "."), (str(deno), "."), *extra_binaries],
    datas=[
        (str(downloader / "src" / "core" / "app.ico"), "src/core"),
        (str(downloader / "src" / "ui" / "theme" / "fonts" / "Inter.ttf"), "src/ui/theme/fonts"),
        (str(root / "LICENSE"), "."),
        (str(root / "THIRD_PARTY_NOTICES.md"), "."),
        *collect_data_files("yt_dlp_ejs"),
    ],
    hiddenimports=collect_submodules("yt_dlp_ejs"),
    hookspath=[],
    excludes=["PyQt6.QtWebEngineWidgets", "tkinter"],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="MediaDownloaderPRO",
    icon=str(downloader / "src" / "core" / "app.ico"),
    console=False,
)
coll = COLLECT(exe, a.binaries, a.datas, name="MediaDownloaderPRO")
