# Changelog

รูปแบบอ้างอิง [Keep a Changelog](https://keepachangelog.com/) และใช้ [Semantic Versioning](https://semver.org/)

## [Unreleased]

## [2.3.0] - 2026-11-20

### Added
- **Cobalt engine (ทางเลือก)**: ดาวน์โหลดผ่าน Cobalt API พร้อม chunked streaming, การยกเลิก และ fallback ไปยัง Native/yt-dlp อัตโนมัติ
- **Turbo download**: ดาวน์โหลดแบบ multi-segment HTTP Range ตั้งค่าได้จากหน้า Settings พร้อมรองรับ manifest และ stream ที่หยุดตอบสนอง
- **DJ Suite**: dual-deck transport, crossfader, harmonic/tempo sync
- **Spectrogram & beat grid**: แสดงผล spectrogram และ beat grid ที่ซิงก์กับ BPM และตำแหน่งเล่น
- **4-stem separation**: แยก vocals/drums/bass/other พร้อมฟังทีละ stem
- **Audio tagging & fingerprint**: แก้ไข metadata แบบ lossless หลายฟอร์แมตผ่าน FFmpeg, Chromaprint (NumPy ล้วน) และค้นหา AcoustID/MusicBrainz

### Changed
- แยกโมดูลขนาดใหญ่ (Cobalt, Turbo, native manifest, history, audio tools page, tag dialog, library card) ให้ทุกไฟล์อยู่ในเกณฑ์ 150 บรรทัดของ `docs/PROJECT_RULES.md`
- FFmpeg watchdog ตรวจจับ stream ที่หยุดนิ่งแทน timeout ตายตัว 300 วินาที และแสดงข้อความที่ผู้ใช้เข้าใจได้
- ย้ายเอกสารออกแบบและกฎโปรเจกต์ไปที่ `docs/`
- ตัวติดตั้งไม่ต้องใช้สิทธิ์ผู้ดูแลระบบ (เลือกติดตั้งทุกผู้ใช้ได้) และปิดโปรแกรมที่เปิดอยู่ก่อนอัปเดต
- เวอร์ชันของ installer และไฟล์ release อ่านจาก `Config.VERSION` / git tag ที่เดียว

### Fixed
- Scheduled yt-dlp compatibility check ล้มทุกสัปดาห์เพราะไม่มี FFmpeg บน runner — ตอนนี้ใช้ action `setup-ffmpeg` ร่วมกับ CI และ release
- สถิติ history ไม่ล้มเมื่อ `fileSize` เป็น `null`
- แก้บั๊กจาก code review ด้าน network, tagging และ updater (ดู `tests/test_*_review_*.py`)

### Infrastructure
- เพิ่ม CI ทุก push/PR, Dependabot, issue/PR templates, `CONTRIBUTING.md`, `SECURITY.md`, `CODE_OF_CONDUCT.md`, `.gitattributes`

## [2.2.0] - 2026-11-07

Phase 4 — Packaging, Installer & Release
- **ตัวติดตั้ง Windows Installer (Inno Setup)**: เพิ่มสคริปต์ `installer.iss` สำหรับคอมไพล์ `MediaDownloaderPRO-v2.2.0-Setup.exe` พร้อมสร้างทางลัดบน Start Menu และ Desktop รวมถึงลงทะเบียนในระบบ Add/Remove Programs (Apps & Features) อย่างสมบูรณ์
- **แพ็กเกจ Portable Zip**: สร้าง `MediaDownloaderPRO-v2.2.0-Windows-x64.zip` พร้อมไฟล์ตรวจสอบความถูกต้อง `.sha256` สำหรับการใช้งานแบบพกพาโดยไม่ต้องติดตั้ง
- **ระบบ CI/CD Release อัตโนมัติ (GitHub Actions)**: แก้ไขปัญหา Critical B1 โดยเพิ่มขั้นตอนดาวน์โหลด `ffmpeg.exe` เวอร์ชัน 8.1.1 (Essentials Build) ที่ผ่านการรับรองและตรวจค่าแฮช SHA-256 อัตโนมัติใน `.github/workflows/release.yml` พร้อมเผยแพร่ทั้ง Installer และ Portable Zip
- **ระบบตรวจจับ AI Stem Separation และคำแนะนำการใช้งาน**: ตรวจสอบความพร้อมของ `audio-separator` และ GPU หากยังไม่ได้ติดตั้ง จะแสดงข้อความแนะนำขั้นตอนการติดตั้งชัดเจนแทนการลดระดับไปใช้ DSP แบบเงียบ
- **ปรับปรุงข้อกำหนดสิทธิ์ใช้งาน (Third-Party Notices)**: เพิ่มประกาศสิทธิ์ใช้งานสำหรับ `NumPy` (BSD-3-Clause) และ `packaging` (Apache-2.0 / BSD-2-Clause) ใน `THIRD_PARTY_NOTICES.md`

## [2.1.0]

Phase 3 — UI/UX Redesign & Precision Pro-Utility
- **สถาปัตยกรรมการออกแบบใหม่ (Wavrik Key Colors & Precision Pro-Utility)**: ออกแบบหน้าจอตามข้อกำหนดใน `docs/DESIGN.md` สลับธีมสว่าง/มืดได้ ป้ายคีย์และ waveform แสดงสีตามวงล้อ Camelot 1–12
- **Downloads (Compact Command Toolbar)**: ยุบรวมการตั้งค่า Media Type, Format/Quality, Download Engine และ Save Location ไว้ในแถบควบคุมระนาบเดียว
- **Library (Unified Media & Analysis Table)**: แสดงประวัติไฟล์ดาวน์โหลดจริง จัดการสถานะ และบันทึกผลวิเคราะห์ Key, Camelot, BPM ลงในแคชถาวร
- **Audio Tools (Studio Inspector & DSP Rack)**: วิเคราะห์ Key / Camelot / BPM, ปรับ Pitch Shift (-12 ถึง +12 st), Time-Stretch (0.5x ถึง 2.0x), พร้อมระบบแยกเสียงร้อง/ดนตรี (Stem Separation) และระบบ Phase-Locked Bit-Perfect
- **Single-Locale UX**: รองรับภาษาไทยและอังกฤษแบบสมบูรณ์โดยไม่ผสมภาษา (No Tinglish) และรองรับการนำทางด้วยคีย์บอร์ด (Tab Navigation Order)

## [2.0.x]

การปรับปรุงความปลอดภัยและประสิทธิภาพ (Phase 2a – 2d)
- **Phase 2d (Security Hardening)**: ป้องกัน Path Traversal ครอบคลุม Windows drive-relative path, ป้องกัน UNC Path bypass, ตรวจสอบความยาวของ Content-Length และป้องกันความผิดพลาดจาก slash key
- **Phase 2c (Performance & DSP Optimization)**: แปลงลูปการประมวลผลสัญญาณเสียงทั้งหมด (BPM spectral flux, HPCP chroma extraction, Rubber Band rendering) ให้เป็น Vectorized Operations ด้วย NumPy พร้อมทั้งเลื่อนการโหลดโมดูล PyQt6 ใน CLI startup
- **Phase 2b (Subprocess & Player Stability)**: เพิ่มการยกเลิกกระบวนการภายนอกที่ปลอดภัย, ปรับปรุงการเลื่อนตำแหน่งเล่นเสียง (Audio Transport Seeking) ให้ราบรื่น และบันทึกแคชผลวิเคราะห์ทันที
- **Phase 2a (Worker & Cache Reliability)**: แยก Cancellation Token สำหรับแต่ละงานดาวน์โหลด, จำกัดขนาดหน่วยความจำแคช และปรับปรุงการระบุพาธไฟล์ให้แม่นยำ
