# Wavrik · Media Downloader PRO 2.3.0

[![CI](https://github.com/intity01/Wavrik/actions/workflows/ci.yml/badge.svg)](https://github.com/intity01/Wavrik/actions/workflows/ci.yml)
[![Latest release](https://img.shields.io/github/v/release/intity01/Wavrik)](https://github.com/intity01/Wavrik/releases/latest)
[![License: GPL-3.0-or-later](https://img.shields.io/badge/license-GPL--3.0--or--later-blue)](LICENSE)

> [!NOTE]
> **Language Policy**: The official documentation, design files, and project rules for Wavrik / Media Downloader PRO are maintained in Thai.

แอปเดสก์ท็อป Windows สำหรับดาวน์โหลดสื่อ วิเคราะห์คีย์ดนตรี/ความเร็ว (Key & BPM) และปรับแต่งคีย์/เทมโป (Pitch Shift & Time-Stretch) ด้วยสถาปัตยกรรม **Precision Pro-Utility**:

**วางลิงก์ → เลือกชนิด/คุณภาพ → ดาวน์โหลด → วิเคราะห์คีย์/BPM → ปรับคีย์หรือเทมโปในสตูดิโอ**

## จุดเด่น

- **Downloads (Compact Command Toolbar)**: แถบตั้งค่า Media Type, Format/Quality, Engine (`Auto` / `Native` / `yt-dlp`) และ Save Folder ในระนาบเดียว พร้อมตารางคิวงานที่กระชับและรองรับการลากไฟล์เข้าโดยตรง
- **Library (Unified Media & Analysis Table)**: เก็บประวัติไฟล์จริง ขนาดไฟล์ และแคชผลวิเคราะห์ Key, Camelot Code, BPM และ Waveform ลงใน `history.json` ถาวร ไม่ต้องวิเคราะห์ซ้ำเมื่อเปิดโปรแกรมใหม่
- **Audio Tools (Studio Inspector & Rack)**:
  - วิเคราะห์ Key / Camelot Wheel (Essentia-compatible SpectralWhitening + HPCP + bgate profile) และ BPM (Multi-band Spectral Flux + Sparse Lag Autocorrelation)
  - ปรับ Pitch Shift (`-12` ถึง `+12` semitones) และ Time-Stretch (`0.50x` ถึง `2.00x`) ด้วย Rubber Band R3 Finer Engine หรือ FFmpeg Formant Preserved
  - แนะนำคีย์ผสมตามวงล้อ Camelot (`Match`, `Relative`, `+1 Boost`, `-1 Drop`) พร้อมปุ่มพรีวิวเสียง 25 วินาที และ Batch Processing
  - แยกแทร็กเสียงร้องและดนตรี (Stem Separation) ด้วย Bit-Perfect Phase Locking พร้อมระบบตรวจสอบความพร้อมของ `audio-separator` และให้คำแนะนำการติดตั้งอย่างชัดเจน
- **Download engines**: Native HTTP/HLS, yt-dlp และ Cobalt (ทางเลือก) พร้อม Turbo multi-segment HTTP Range download และ fallback อัตโนมัติ
- **DJ Suite & Spectrogram**: dual-deck transport, crossfader, harmonic/tempo sync, spectrogram และ beat grid
- **Tagging & Fingerprint**: แก้ไข metadata แบบ lossless ผ่าน FFmpeg และค้นหาเพลงด้วย Chromaprint + AcoustID/MusicBrainz
- **Single-Locale UX (TH / EN)**: สลับภาษาไทยและอังกฤษได้ทันทีจากหน้า Settings โดยไม่ปนภาษา (No Tinglish)
- **Wavrik Key Colors Design System**: ธีมสว่างเป็นค่าเริ่มต้น สลับเป็นธีมมืดได้ ทุกคีย์บนวงล้อ Camelot มีสีประจำของตัวเอง ใช้กับป้ายคีย์และ waveform มีมาสคอตไอคอน "วาวี่" ลำดับขั้นปุ่ม 4 ระดับ และฟอนต์ Monospace สำหรับตัวเลขทางเทคนิค
- **โอเพนซอร์ส GPL-3.0**: ใช้ฟรี แก้ไขและแจกจ่ายต่อได้ภายใต้เงื่อนไขของ GPL-3.0 (ดู `LICENSE`)

## ติดตั้ง (สำหรับผู้ใช้ทั่วไป)

1. ไปที่ [Releases ล่าสุด](https://github.com/intity01/Wavrik/releases/latest)
2. ดาวน์โหลด `MediaDownloaderPRO-v2.3.0-Setup.exe` แล้วดับเบิลคลิกเพื่อติดตั้ง (ไม่ต้องใช้สิทธิ์ผู้ดูแลระบบ เลือกติดตั้งให้ทุกผู้ใช้ได้ในหน้าติดตั้ง)
3. เปิดโปรแกรมจาก Start Menu — FFmpeg รวมมาในตัวติดตั้งแล้ว ไม่ต้องติดตั้งอะไรเพิ่ม

ถ้าไม่อยากติดตั้ง ให้ใช้ `MediaDownloaderPRO-v2.3.0-Windows-x64.zip` แตกไฟล์แล้วเปิด `MediaDownloaderPRO.exe` ได้เลย ตรวจความถูกต้องของไฟล์ได้ด้วย `.sha256` ที่แนบมา:

```powershell
(Get-FileHash .\MediaDownloaderPRO-v2.3.0-Setup.exe -Algorithm SHA256).Hash
```

> Windows SmartScreen อาจเตือนเพราะไฟล์ยังไม่มี code-signing certificate ให้กด **More info → Run anyway** หลังตรวจ SHA-256 แล้ว

## เริ่มใช้งานจาก source บน Windows

1. วาง `ffmpeg.exe` (และ `rubberband.exe` + `sndfile.dll` สำหรับ R3 Engine) ไว้ข้าง `RunApp.bat`
2. ดับเบิลคลิก `RunApp.bat`
3. ครั้งแรกสคริปต์จะสร้าง `.venv` และติดตั้ง dependency อัตโนมัติ

## ตั้งค่า GitHub Updates

แอปตรวจสอบอัปเดตจาก GitHub Releases ของ `intity01/Wavrik` (ตั้งไว้ที่ `GITHUB_REPO` ใน `Downloader/src/core/config.py`) ถ้า fork ไปเผยแพร่เอง ให้เปลี่ยนค่านี้เป็น repository ของคุณก่อนสร้าง release ระบบรองรับเฉพาะ immutable release ที่มี SHA-256 digest และไม่รัน installer อัตโนมัติ

## สร้าง Windows release

```bat
build_windows.bat
```

ผลลัพธ์อยู่ที่:
- โปรแกรมหลัก: `dist\MediaDownloaderPRO\MediaDownloaderPRO.exe`
- ไฟล์ติดตั้ง (Installer): `dist\MediaDownloaderPRO-v<version>-Setup.exe` (และ `.sha256`) — ต้องมี [Inno Setup 6](https://jrsoftware.org/isinfo.php)
- แพ็กเกจพกพา (Portable Zip): `dist\MediaDownloaderPRO-v<version>-Windows-x64.zip` (และ `.sha256`)

เวอร์ชันอ่านจาก `VERSION` ใน `Downloader/src/core/config.py` ที่เดียว การออก release อย่างเป็นทางการ: อัปเดต `VERSION`, `pyproject.toml`, `installer.iss` และ `CHANGELOG.md` แล้ว push tag `v<version>` — GitHub Actions จะ build, ทดสอบ และเผยแพร่ installer ให้อัตโนมัติ

## ทดสอบและตรวจสอบคุณภาพโค้ด

```bash
cd Downloader
python -m pip install -r requirements-dev.txt
python -m compileall -q src main.py
python tools/check_rules.py
python tools/check_ai_slop.py
ruff check src tests
pytest -q
```

## บันทึกการเปลี่ยนแปลง

ดู [`CHANGELOG.md`](CHANGELOG.md)

## ร่วมพัฒนา

อ่าน [`CONTRIBUTING.md`](CONTRIBUTING.md) ก่อนเปิด pull request และแจ้งช่องโหว่ด้านความปลอดภัยตาม [`SECURITY.md`](SECURITY.md)

## โครงสร้างโปรเจกต์

- `Downloader/src/core` — config, json_store, logger, URL parser, runtime discovery และ GitHub updater
- `Downloader/src/domain` — typed models, presets, native HTTP/HLS downloader และ yt-dlp session engine
- `Downloader/src/services` — DSP (BPM spectral flux, HPCP key detection, Camelot wheel, Rubber Band R3 / FFmpeg pitch & tempo rendering, batch processor), history manager และ platform actions
- `Downloader/src/ui` — main window, single-locale i18n, Precision Graphite theme tokens/QSS, pages (`Downloads`, `Library`, `Audio Tools`, `Settings`), components และ background workers
- `Downloader/tests` — automated unit, security, DSP และ UI regression test suite
- `Downloader/tools` — static rule checker (`check_rules.py`) และ anti-AI-slop linter (`check_ai_slop.py`)
- `docs/PROJECT_RULES.md` — กฎวิศวกรรม ความปลอดภัย และขีดจำกัดขนาดโค้ด
- `docs/DESIGN.md` — มาตรฐานระบบการออกแบบ Precision Pro-Utility
- `docs/AI_SLOP_REVIEW.md` — เกณฑ์ตรวจสอบป้องกัน UI Slop
- `THIRD_PARTY_NOTICES.md` — ข้อกำหนดสิทธิ์ใช้งานสำหรับ dependency และ binary ที่แจกจ่าย
- `installer.iss` — สคริปต์คอมไพล์ Windows Installer ด้วย Inno Setup

## หมายเหตุด้านสิทธิ์ใช้งาน

ผู้ใช้ต้องรับผิดชอบในการดาวน์โหลดเฉพาะเนื้อหาที่ตนมีสิทธิ์เข้าถึงและใช้งาน โปรเจกต์นี้ไม่ข้าม DRM และไม่ได้รับรองเว็บไซต์ภายนอกใด ๆ
