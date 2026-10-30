# Wavrik · Media Downloader PRO 2.1

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
- **Single-Locale UX (TH / EN)**: สลับภาษาไทยและอังกฤษได้ทันทีจากหน้า Settings โดยไม่ปนภาษา (No Tinglish)
- **Wavrik Key Colors Design System**: ธีมสว่างเป็นค่าเริ่มต้น สลับเป็นธีมมืดได้ ทุกคีย์บนวงล้อ Camelot มีสีประจำของตัวเอง ใช้กับป้ายคีย์และ waveform มีมาสคอตไอคอน "วาวี่" ลำดับขั้นปุ่ม 4 ระดับ และฟอนต์ Monospace สำหรับตัวเลขทางเทคนิค
- **โอเพนซอร์ส GPL-3.0**: ใช้ฟรี แก้ไขและแจกจ่ายต่อได้ภายใต้เงื่อนไขของ GPL-3.0 (ดู `LICENSE`)

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

ผลลัพธ์อยู่ที่ `dist\MediaDownloaderPRO\MediaDownloaderPRO.exe`

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

## โครงสร้างโปรเจกต์

- `Downloader/src/core` — config, json_store, logger, URL parser, runtime discovery และ GitHub updater
- `Downloader/src/domain` — typed models, presets, native HTTP/HLS downloader และ yt-dlp session engine
- `Downloader/src/services` — DSP (BPM spectral flux, HPCP key detection, Camelot wheel, Rubber Band R3 / FFmpeg pitch & tempo rendering, batch processor), history manager และ platform actions
- `Downloader/src/ui` — main window, single-locale i18n, Precision Graphite theme tokens/QSS, pages (`Downloads`, `Library`, `Audio Tools`, `Settings`), components และ background workers
- `Downloader/tests` — automated unit, security, DSP และ UI regression test suite
- `Downloader/tools` — static rule checker (`check_rules.py`) และ anti-AI-slop linter (`check_ai_slop.py`)
- `PROJECT_RULES.md` — กฎวิศวกรรม ความปลอดภัย และขีดจำกัดขนาดโค้ด
- `DESIGN.md` — มาตรฐานระบบการออกแบบ Precision Pro-Utility
- `AI_SLOP_REVIEW.md` — เกณฑ์ตรวจสอบป้องกัน UI Slop
- `THIRD_PARTY_NOTICES.md` — ข้อกำหนดสิทธิ์ใช้งานสำหรับ dependency และ binary ที่แจกจ่าย

## หมายเหตุด้านสิทธิ์ใช้งาน

ผู้ใช้ต้องรับผิดชอบในการดาวน์โหลดเฉพาะเนื้อหาที่ตนมีสิทธิ์เข้าถึงและใช้งาน โปรเจกต์นี้ไม่ข้าม DRM และไม่ได้รับรองเว็บไซต์ภายนอกใด ๆ
