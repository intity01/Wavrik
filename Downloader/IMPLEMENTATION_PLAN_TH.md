# แผนพัฒนา Media Downloader PRO 2.1

## เป้าหมายผลิตภัณฑ์

ทำให้ผู้ใช้ที่ไม่รู้เรื่อง Python, yt-dlp หรือ FFmpeg เปิดโปรแกรม วางลิงก์ เลือกผลลัพธ์ ดาวน์โหลด และหาไฟล์เจอได้โดยไม่ต้องอ่านคู่มือหรือสลับไปมาระหว่างหลายหน้า

## Product promise

**Paste. Choose. Download.**

หน้า Downloads ต้องตอบคำถามของผู้ใช้ครบ:

- ลิงก์ที่จะโหลดคืออะไร
- จะได้ Audio หรือ Video
- Format/Quality คืออะไร
- ไฟล์จะถูกเก็บที่ไหน
- งานกำลังทำอะไรและเสร็จเมื่อไร

## จุดขายสำหรับ GitHub

1. **One-page download setup** — ตัวเลือกหลักอยู่หน้าเดียวกับ URL และ queue
2. **Human-readable output choices** — ไม่มี format code ที่ต้องเดา
3. **Reliable queue isolation** — session/cancellation แยกต่อ job และบังคับ concurrency
4. **Status-first feedback** — progress, speed, ETA และ processing แยกชัด
5. **File-aware history** — เก็บ actual path, size, missing-file state และ re-download
6. **Safe GitHub updates** — background check, immutable release, SHA-256 และ no auto-run
7. **Anti-slop product design** — ไม่มี gradient/glass/glow, duplicate controls หรือ marketing filler

## สถานะที่ implement แล้ว

### Core reliability

- typed audio/video presets และ yt-dlp options ที่ไม่ cross-wire
- per-job downloader session และ cancellation
- metadata/download thread pools พร้อม concurrency limit
- URL validation/normalization เฉพาะ HTTP/HTTPS
- atomic settings/history พร้อม lock, schema และ corrupt backup
- explicit FFmpeg discovery

### One-page UX

- Media type และ filtered Format/Quality บนหน้า Downloads
- Save location พร้อม Change folder ในหน้าเดียวกัน
- Download all แสดงจำนวนงานและ disable ตาม queue state
- Queue card แสดง preset summary แทน dropdown ซ้ำทุกใบ
- active jobs รักษา preset/output path ที่เริ่มไว้
- FFmpeg warning แสดงเฉพาะเมื่อผู้ใช้ต้องแก้ไข

### GitHub updates

- GitHub Releases API ทำงานใน background worker
- API version, timeout และ User-Agent ชัดเจน
- stable/latest full release check
- update banner ไปยัง Settings
- direct package download เฉพาะ immutable release + GitHub SHA-256 digest
- stream download, size guard, host validation, hash verification และ atomic rename
- ไม่ execute installer อัตโนมัติ

### Quality gates

- production file ≤150 lines, function ≤35, class ≤120
- no-gradient/no-glow/no-inline-color checks
- dedicated AI-slop heuristic + manual checklist
- compile, Ruff, pytest และ offscreen GUI review

## ระยะถัดไป

### Release readiness

- ตั้ง `Config.GITHUB_REPO` ให้ตรง repository จริง
- เปิด immutable releases ใน GitHub repository/organization settings
- ใช้ workflow สร้าง Windows x64 asset จาก tag
- ทดสอบ package บน Windows 10/11 เครื่องสะอาด
- ทำ Authenticode signing และเพิ่ม publisher verification ก่อนรองรับ auto-install
- เพิ่ม LICENSE และ third-party notices

### Product polish

- localization ไทย/อังกฤษจาก translation service เดียว
- playlist item selection ก่อน Add all
- desktop notification เมื่อ queue ทั้งหมดเสร็จ
- per-item override ผ่าน progressive disclosure เฉพาะเมื่อมี use case จริง
- keyboard shortcuts: focus URL, add, download all, open history

### Showcase

- Hero screenshot 1600×900: URL + Download Options + queue 3 states
- Feature image 1200×675: One-page setup
- Feature image 1200×675: Live progress และ cancellation
- Feature image 1200×675: Verified GitHub update
- Social preview 1280×640 พร้อมข้อความ `Paste. Choose. Download.`
