# สรุปการพัฒนา Media Downloader PRO 2.1

## การตัดสินใจหลัก

ย้ายตัวเลือกดาวน์โหลดจาก queue card ทุกใบมาไว้ในหน้า Downloads เป็นจุดควบคุมเดียว เพราะผู้ใช้ไม่ควรต้องเลือกค่าซ้ำต่อรายการใน use case ปกติ

Flow ใหม่คือ:

**วางลิงก์ → เลือก Audio/Video + Format/Quality → เลือกโฟลเดอร์ → Download all หรือ Download รายการเดียว**

งานที่ยังไม่เริ่มจะรับค่าล่าสุด ส่วนงาน active รักษาค่าที่เริ่มไว้เพื่อไม่ให้ผลลัพธ์เปลี่ยนกลางทาง

## สิ่งที่ implement เพิ่ม

- Download Options panel บนหน้า Downloads
- Media type filter แยก Audio และ Video
- Format/Quality options ที่สั้นและอ่านง่าย
- Save location + Change folder บนหน้าเดียวกัน
- Download all แสดงจำนวนรายการ
- Queue card เปลี่ยนเป็น preset summary ไม่มี dropdown ซ้ำ
- `Download all` เปิดได้ตั้งแต่มีงานรออ่าน metadata และเริ่มงานต่อเมื่อ link check พร้อม
- error ของ save folder, worker และ history ถูกแปลงเป็นข้อความแก้ไขได้โดยไม่ปล่อย exception ดิบออกสู่ UI
- URL ที่มี malformed port ถูกปฏิเสธอย่างปลอดภัย และ native downloader ลบ `.part` เมื่อ stream ล้มเหลว
- `RunApp.bat`/`build_windows.bat` ตรวจสอบ interpreter ที่ใช้ได้จริงก่อน fallback และซ่อม `.venv` ที่เสีย
- FFmpeg banner แสดงเฉพาะเมื่อมีปัญหา ไม่แสดง success banner ค้าง
- Settings ลดข้อมูลซ้ำ เหลือ appearance, concurrency, behavior และ updates
- Toggle แสดง On/Off เป็นข้อความ ไม่พึ่งสีเพียงอย่างเดียว
- หน้า Downloads ใช้ scroll เดียวทั้งหน้า จึงไม่บีบ controls ที่ขนาดขั้นต่ำ 760×600

## GitHub update system

- ตรวจ latest full release ผ่าน GitHub Releases API นอก UI thread
- แจ้ง update บนหน้า Downloads และเปิดรายละเอียดใน Settings
- ผู้ใช้เลือกเปิด release page ได้เสมอ
- ดาวน์โหลดในแอปได้เมื่อ GitHub ระบุ release เป็น immutable และ asset มี SHA-256 digest
- ตรวจ host, ขนาด, hash และเขียนไฟล์แบบ `.part → atomic replace`
- ยืนยันกับผู้ใช้ก่อนดาวน์โหลด
- ไม่รัน installer อัตโนมัติ

## Anti AI-slop

เพิ่มกฎและตัวตรวจสำหรับ:

- gradient, glassmorphism, glow, shadow decoration
- border radius เกิน 12px และ decorative side stripe
- emoji functional icon
- generic CTA และ marketing filler
- placeholder copy

พร้อม manual checklist ที่ตรวจ duplicate controls, nested cards, fake metrics, decorative success state และความชัดเจนของ primary task

## การตรวจสอบ

- `python -m compileall -q src main.py`
- `python tools/check_rules.py`
- `python tools/check_ai_slop.py`
- `ruff check src tests`
- `pytest -q` ครอบคลุม parser, presets, history, one-page options และ GitHub updater
- UI regression ผ่านใน QA environment และทดสอบ flow queue, direct media, failure, history และ worker
- automated regression tests 55 รายการผ่าน
- compile, project rules, anti-slop และ Ruff ผ่านทั้งหมด

## ข้อจำกัดที่ยังคงไว้โดยตั้งใจ

ระบบ update ยังไม่ auto-install เพราะ SHA-256 ยืนยัน integrity แต่ไม่แทน publisher signature ทั้งหมด ขั้น auto-install ควรเปิดหลังเพิ่ม Authenticode หรือการตรวจ attestation/signature ที่เชื่อถือได้เท่านั้น

การตรวจสอบ physical Windows launch กับ provider จริงยังต้องทำบน interactive desktop; ผล `55 passed` เป็นหลักฐานของ source และ offscreen/UI regression candidate นี้ ไม่ใช่หลักฐานว่าเว็บไซต์ภายนอกทุกแห่งจะดาวน์โหลดได้
