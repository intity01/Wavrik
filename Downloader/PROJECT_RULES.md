# PROJECT_RULES.md — Media Downloader PRO

กฎนี้เป็นแหล่งอ้างอิงหลัก โดยเรียงความสำคัญ: security/data integrity → correctness → accessibility/UX → maintainability → performance → visual polish

## Code limits

- Production Python ทุกไฟล์ต้องไม่เกิน **150 physical lines**
- function/method ไม่เกิน 35 บรรทัด, class ไม่เกิน 120 บรรทัด
- parameter ไม่เกิน 6 ตัว หากมากกว่านั้นใช้ dataclass/config object
- nesting ไม่เกิน 3 ชั้น และหนึ่งฟังก์ชันทำงานที่สังเกตได้เพียงอย่างเดียว
- ไฟล์ทั้งหมดต้องใช้ `snake_case.py`

## Architecture

- UI ห้ามทำ network, yt-dlp หรือเขียนไฟล์ดาวน์โหลดโดยตรง
- domain/service ห้าม import UI
- หนึ่งงานดาวน์โหลดต้องมี session และ cancellation token ของตนเอง
- ห้าม mutable global downloader state
- queue manager/thread pool ต้องบังคับ `maxConcurrentDownloads`
- download job ใช้ state `queued → downloading → processing → completed|failed|cancelled`
- `fetching` และ `ready` เป็น presentation state สำหรับ metadata ก่อนเริ่ม job
- preset ต้องเป็น typed model ห้ามใช้ audio bitrate แทน video height
- completed ได้เมื่อพบ output file จริงเท่านั้น

## Download workflow

- ตัวเลือก Media type, Format/Quality และ Save location ต้องอยู่บนหน้า Downloads
- ตัวเลือกส่วนกลางใช้กับงานที่ยังไม่เริ่ม; งาน active ต้องรักษาค่าที่เริ่มไว้
- Queue card แสดง preset summary แต่ไม่ทำซ้ำ selector ทุกใบ
- `Download all` ต้องสะท้อนจำนวนงานและ disabled เมื่อไม่มีงานที่เริ่มได้
- Settings ใช้สำหรับค่าระดับแอป เช่น concurrency, theme, behavior และ updates ไม่ทำซ้ำ download options

## URL and network

- รับเฉพาะ `http` และ `https`
- ปฏิเสธ URL ที่ฝัง username/password, local file scheme และ scheme อื่น
- normalize ก่อนตรวจ duplicate และตัด tracking parameter ที่รู้จัก
- network ทุกครั้งมี connect/read timeout
- จำกัดขนาด thumbnail และตรวจ content type
- network ห้ามทำงานบน UI thread
- error ที่แสดงผู้ใช้ต้องแก้ไขได้และไม่แสดง exception ดิบ

## Persistence and logging

- settings/history มี schema version และ validate ตอน load
- เขียน JSON แบบ temp → flush/fsync → atomic replace
- shared persistence ใช้ lock
- ไฟล์เสียหายต้อง backup ก่อนเริ่มใหม่
- history เก็บ actual file path, size, status และ error summary
- Logger รองรับ `exc_info`; error handler ห้ามล้มจาก logging
- ห้าม log cookies, token หรือ URL query ที่มีข้อมูลลับ
- ห้าม `print()` ใน production modules

## GitHub updates and security

- Update check ใช้ public GitHub Releases API ผ่าน background worker เท่านั้น
- ต้องระบุ GitHub API version, timeout และ User-Agent
- In-app package download เปิดได้เมื่อ release เป็น immutable และ asset มี GitHub SHA-256 digest
- ต้องตรวจ SHA-256 ก่อน atomic rename และให้ผู้ใช้ยืนยันก่อนดาวน์โหลด
- ห้าม auto-run installer; auto-install ต้องมี publisher signature/attestation verification เพิ่มเติม
- release ต้องไม่รวม `.git`, cache, logs, settings, history หรือ agent metadata
- path ของ FFmpeg ต้องกำหนดและตรวจได้ชัดเจน
- ห้ามข้าม DRM หรือเพิ่มกลไกหลบข้อจำกัดการเข้าถึง

## UX and accessibility

- ผู้ใช้ใหม่ต้องทำ flow `เปิด → วางลิงก์ → เลือกตัวเลือก → ดาวน์โหลด → เปิดไฟล์` ได้โดยไม่ใช้ terminal
- minimum window 760×600 และทดสอบที่ 760, 900, 1200, 1440px
- body text อย่างน้อย 9pt, target 10pt
- contrast ปกติอย่างน้อย 4.5:1
- interactive target ควรสูงอย่างน้อย 38–40px
- ทุก action ใช้คำกริยาชัดเจน และ status ห้ามสื่อด้วยสีอย่างเดียว
- icon-only control ต้องมี accessible name/tooltip; ห้ามใช้ emoji เป็น functional icon
- Settings ต้อง scroll ได้ และ theme เปลี่ยนกับ widget ที่มีอยู่ทันที
- ใช้ locale เดียวต่อหน้าจอ ห้ามไทย/อังกฤษปนใน active locale
- แสดง warning เมื่อผู้ใช้ต้องทำบางอย่างเท่านั้น ห้ามใช้ persistent success banner ที่ไม่ช่วยตัดสินใจ

## Visual design

- **ห้าม gradient ทุกชนิด** ใน QSS/CSS/asset ที่สร้างเพื่อ UI
- ห้าม accent glow, glassmorphism, blur และ colored drop shadow
- component/page ห้ามมี inline stylesheet ที่กำหนดสี
- สีอยู่ใน semantic token files เท่านั้น ยกเว้นข้อมูลตัวเลือก accent
- ใช้ solid surface + border สร้าง hierarchy
- radius สูงสุด 12px ยกเว้นวงกลม
- ห้าม decorative side stripe หนากว่า 1px
- accent ไม่เกินประมาณ 10% ของพื้นที่หน้าจอ
- red ใช้กับ error/destructive เท่านั้น

## Anti AI-slop

- ใช้ pattern ที่คุ้นเคยและมีเหตุผล ห้ามประดิษฐ์ affordance แปลกเพื่อให้ดู “ล้ำ”
- ห้าม nested cards, card grid ที่ไม่มีเหตุผล, badge จำนวนมาก หรือ metric ปลอม
- ห้าม hero copy, marketing filler และคำกว้าง ๆ เช่น revolutionary, game-changing, magic, seamless experience
- ปุ่มต้องระบุผลลัพธ์ เช่น `Download all`, `Open release`, `Change folder` ไม่ใช้ `Get started` หรือ `Learn more`
- ห้าม emoji icon, gradient text, cream/beige AI-default, excessive rounding และ decorative motion
- ทุก panel ต้องตอบคำถามเชิงงานอย่างน้อยหนึ่งข้อ; ถ้าไม่มี action/state/information ที่จำเป็นให้ลบออก
- ก่อนส่งงานต้องผ่าน automated heuristic และ manual checklist ใน `AI_SLOP_REVIEW.md`

## Testing and Definition of Done

ทุก bug fix ต้องมี regression test และก่อนส่งงานต้องรัน:

```bash
python -m compileall -q src main.py
python tools/check_rules.py
python tools/check_ai_slop.py
ruff check src tests
pytest -q
```

งานถือว่าเสร็จเมื่อ flow ทำงาน end-to-end, loading/error/cancel/empty/update states ครบ, ไม่มีไฟล์เกิน limit, ไม่มี gradient/AI-slop pattern, tests ผ่าน และเอกสารตรงกับ implementation
