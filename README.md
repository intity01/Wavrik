# Media Downloader PRO 2.1

> [!NOTE]
> **Language Policy**: The official documentation, design files, and project rules for Media Downloader PRO are maintained in Thai.

แอปเดสก์ท็อป Windows สำหรับดาวน์โหลดเสียง วิดีโอ และ playlist ด้วย flow ที่มองเห็นครบในหน้าเดียว:

**วางลิงก์ → เลือกชนิด/คุณภาพ → ดาวน์โหลด → เปิดไฟล์**

## จุดเด่น

- Download Options อยู่หน้า Downloads โดยตรง: Audio/Video, Format/Quality และ Save location
- ตัวเลือกส่วนกลางใช้กับงานที่ยังไม่เริ่ม ทำให้ queue card ไม่เต็มไปด้วย dropdown ซ้ำ
- Preset ใช้ภาษาคน เช่น `MP3 · 320 kbps` และ `MP4 · Up to 1080p`
- เลือก Download engine ได้: `Auto` สำหรับเลือก route ตาม URL, `Native` สำหรับไฟล์ตรง/HLS/DASH ที่ไม่มี DRM และ `yt-dlp` สำหรับเว็บไซต์ที่ต้องใช้ compatibility extractor
- Queue จำกัดจำนวนงานพร้อมกันจริง และแต่ละงานยกเลิกแยกกันได้
- แสดงสถานะ เปอร์เซ็นต์ ความเร็ว ETA และ processing
- History เก็บ path/ขนาดไฟล์จริง พร้อมบอกเมื่อไฟล์ถูกย้ายหรือลบ
- รองรับ playlist, import `.txt`, clipboard detection และ dark/light theme
- ตรวจ GitHub Releases ใน background และแจ้งเมื่อมี version ใหม่
- ดาวน์โหลด package ในแอปได้เฉพาะ immutable release ที่มี SHA-256 digest; โปรแกรมไม่รัน installer อัตโนมัติ
- Design system แบบ solid surface ไม่มี gradient, glow, glassmorphism หรือ emoji functional icon

## เริ่มใช้งานจาก source บน Windows

1. แตกไฟล์โดยให้ `ffmpeg.exe` อยู่ข้าง `RunApp.bat`
2. ดับเบิลคลิก `RunApp.bat`
3. ครั้งแรกสคริปต์จะสร้าง environment และติดตั้ง dependency ให้; ถ้า `.venv` เดิมเสีย สคริปต์จะตรวจพบและสร้างใหม่

`RunApp.bat` จะตรวจสอบว่า `py -3` ใช้งานได้จริงก่อน แล้วจึง fallback ไปที่ `python` หรือ Python per-user ใต้ `%LocalAppData%` เพื่อรองรับเครื่องที่มี `py.exe` แต่ไม่มี interpreter ที่ลงทะเบียนไว้

ผู้ใช้ทั่วไปควรใช้ GitHub Release ที่ build เป็น Windows package แล้ว เพื่อไม่ต้องติดตั้ง Python

## ตั้งค่า GitHub Updates

Repository ที่ใช้ตรวจ update ต้องตั้งก่อนสร้าง release ใน:

```python
# Downloader/src/core/config.py
GITHUB_REPO = "owner/repository"
```

เปลี่ยนเป็น `owner/repository` ของโปรเจกต์ก่อน build release จริง จากนั้นสร้าง release พร้อม Windows asset ชื่อที่มีคำว่า `Windows`, `x64`, `Setup` หรือ `Installer` เพื่อให้ updater เลือก asset ที่เหมาะสม

รายละเอียดอยู่ที่ `docs/GITHUB_UPDATES.md`

## สร้าง Windows release

```bat
build_windows.bat
```

ผลลัพธ์อยู่ที่ `dist\MediaDownloaderPRO\MediaDownloaderPRO.exe`

GitHub workflow ตัวอย่างอยู่ที่ `.github/workflows/release.yml`

## ทดสอบ

```bash
cd Downloader
python -m pip install -r requirements-dev.txt
python -m compileall -q src main.py
python tools/check_rules.py
python tools/check_ai_slop.py
ruff check src tests
pytest -q
```

## โครงสร้าง

- `Downloader/src/core` — config, logging, runtime และ GitHub updater
- `Downloader/src/domain` — typed presets, result models และ yt-dlp engine
- `Downloader/src/services` — history และ platform actions
- `Downloader/src/ui` — pages, components, theme และ background workers
- `Downloader/tests` — regression, updater และ UI smoke tests
- `PROJECT_RULES.md` — กฎ engineering/UX/security
- `AI_SLOP_REVIEW.md` — automated + manual product UI review
- `THIRD_PARTY_NOTICES.md` — ข้อควรตรวจสอบสำหรับ dependency และ binary ที่แจกจ่าย

## หมายเหตุด้านสิทธิ์ใช้งาน

ผู้ใช้ต้องรับผิดชอบในการดาวน์โหลดเฉพาะเนื้อหาที่ตนมีสิทธิ์เข้าถึงและใช้งาน โปรเจกต์นี้ไม่ข้าม DRM และไม่ได้รับรองเว็บไซต์ภายนอกใด ๆ
