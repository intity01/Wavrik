# Wavrik · Media Downloader PRO 2.2.0

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

ผลลัพธ์อยู่ที่:
- โปรแกรมหลัก: `dist\MediaDownloaderPRO\MediaDownloaderPRO.exe`
- ไฟล์ติดตั้ง (Installer): `dist\MediaDownloaderPRO-v2.2.0-Setup.exe` (และ `.sha256`)
- แพ็กเกจพกพา (Portable Zip): `dist\MediaDownloaderPRO-v2.2.0-Windows-x64.zip` (และ `.sha256`)

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

## บันทึกการเปลี่ยนแปลง (Changelog)

### เวอร์ชัน 2.2.0 (Phase 4 — Packaging, Installer & Release)
- **ตัวติดตั้ง Windows Installer (Inno Setup)**: เพิ่มสคริปต์ `installer.iss` สำหรับคอมไพล์ `MediaDownloaderPRO-v2.2.0-Setup.exe` พร้อมสร้างทางลัดบน Start Menu และ Desktop รวมถึงลงทะเบียนในระบบ Add/Remove Programs (Apps & Features) อย่างสมบูรณ์
- **แพ็กเกจ Portable Zip**: สร้าง `MediaDownloaderPRO-v2.2.0-Windows-x64.zip` พร้อมไฟล์ตรวจสอบความถูกต้อง `.sha256` สำหรับการใช้งานแบบพกพาโดยไม่ต้องติดตั้ง
- **ระบบ CI/CD Release อัตโนมัติ (GitHub Actions)**: แก้ไขปัญหา Critical B1 โดยเพิ่มขั้นตอนดาวน์โหลด `ffmpeg.exe` เวอร์ชัน 8.1.1 (Essentials Build) ที่ผ่านการรับรองและตรวจค่าแฮช SHA-256 อัตโนมัติใน `.github/workflows/release.yml` พร้อมเผยแพร่ทั้ง Installer และ Portable Zip
- **ระบบตรวจจับ AI Stem Separation และคำแนะนำการใช้งาน**: ตรวจสอบความพร้อมของ `audio-separator` และ GPU หากยังไม่ได้ติดตั้ง จะแสดงข้อความแนะนำขั้นตอนการติดตั้งชัดเจนแทนการลดระดับไปใช้ DSP แบบเงียบ
- **ปรับปรุงข้อกำหนดสิทธิ์ใช้งาน (Third-Party Notices)**: เพิ่มประกาศสิทธิ์ใช้งานสำหรับ `NumPy` (BSD-3-Clause) และ `packaging` (Apache-2.0 / BSD-2-Clause) ใน `THIRD_PARTY_NOTICES.md`

### เวอร์ชัน 2.1.0 (Phase 3 — UI/UX Redesign & Precision Pro-Utility)
- **สถาปัตยกรรมการออกแบบใหม่ (Wavrik Key Colors & Precision Pro-Utility)**: ออกแบบหน้าจอตามข้อกำหนดใน `DESIGN.md` สลับธีมสว่าง/มืดได้ ป้ายคีย์และ waveform แสดงสีตามวงล้อ Camelot 1–12
- **Downloads (Compact Command Toolbar)**: ยุบรวมการตั้งค่า Media Type, Format/Quality, Download Engine และ Save Location ไว้ในแถบควบคุมระนาบเดียว
- **Library (Unified Media & Analysis Table)**: แสดงประวัติไฟล์ดาวน์โหลดจริง จัดการสถานะ และบันทึกผลวิเคราะห์ Key, Camelot, BPM ลงในแคชถาวร
- **Audio Tools (Studio Inspector & DSP Rack)**: วิเคราะห์ Key / Camelot / BPM, ปรับ Pitch Shift (-12 ถึง +12 st), Time-Stretch (0.5x ถึง 2.0x), พร้อมระบบแยกเสียงร้อง/ดนตรี (Stem Separation) และระบบ Phase-Locked Bit-Perfect
- **Single-Locale UX**: รองรับภาษาไทยและอังกฤษแบบสมบูรณ์โดยไม่ผสมภาษา (No Tinglish) และรองรับการนำทางด้วยคีย์บอร์ด (Tab Navigation Order)

### การปรับปรุงความปลอดภัยและประสิทธิภาพ (Phase 2a – 2d)
- **Phase 2d (Security Hardening)**: ป้องกัน Path Traversal ครอบคลุม Windows drive-relative path, ป้องกัน UNC Path bypass, ตรวจสอบความยาวของ Content-Length และป้องกันความผิดพลาดจาก slash key
- **Phase 2c (Performance & DSP Optimization)**: แปลงลูปการประมวลผลสัญญาณเสียงทั้งหมด (BPM spectral flux, HPCP chroma extraction, Rubber Band rendering) ให้เป็น Vectorized Operations ด้วย NumPy พร้อมทั้งเลื่อนการโหลดโมดูล PyQt6 ใน CLI startup
- **Phase 2b (Subprocess & Player Stability)**: เพิ่มการยกเลิกกระบวนการภายนอกที่ปลอดภัย, ปรับปรุงการเลื่อนตำแหน่งเล่นเสียง (Audio Transport Seeking) ให้ราบรื่น และบันทึกแคชผลวิเคราะห์ทันที
- **Phase 2a (Worker & Cache Reliability)**: แยก Cancellation Token สำหรับแต่ละงานดาวน์โหลด, จำกัดขนาดหน่วยความจำแคช และปรับปรุงการระบุพาธไฟล์ให้แม่นยำ

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
- `installer.iss` — สคริปต์คอมไพล์ Windows Installer ด้วย Inno Setup

## หมายเหตุด้านสิทธิ์ใช้งาน

ผู้ใช้ต้องรับผิดชอบในการดาวน์โหลดเฉพาะเนื้อหาที่ตนมีสิทธิ์เข้าถึงและใช้งาน โปรเจกต์นี้ไม่ข้าม DRM และไม่ได้รับรองเว็บไซต์ภายนอกใด ๆ
