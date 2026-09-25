# Design System — Midnight Utility 2.1

## Product scene

โปรแกรมนี้ถูกใช้บน Windows desktop ระหว่างที่ผู้ใช้กำลังทำงานอื่นอยู่ ผู้ใช้ต้องมองเห็นว่า “ลิงก์ถูกต้องไหม”, “จะได้ไฟล์แบบไหน”, “ไฟล์จะไปอยู่ที่ไหน” และ “งานคืบหน้าถึงไหน” โดยไม่ต้องเรียนรู้ศัพท์ของ yt-dlp

## Design direction

อินเทอร์เฟซเป็นเครื่องมือที่สงบ ตรงไปตรงมา และไว้ใจได้ ใช้ native product patterns, solid surfaces, border และ spacing เพื่อสร้างลำดับชั้น ไม่มี gradient, glow, glassmorphism หรือ decoration ที่ไม่ช่วยงาน

## Semantic palette

### Dark

- Background `#0B0F16`
- Panel `#101722`
- Surface `#151E2B`
- Hover `#1A2636`
- Border `#263449`
- Strong border `#3A4B63`
- Text `#F3F6FA`
- Muted `#9AA8BA`

### Light

- Background `#F4F7FB`
- Panel/Surface `#FFFFFF`
- Hover `#EEF3F9`
- Border `#D6DFEA`
- Strong border `#AAB8C9`
- Text `#111827`
- Muted `#526173`

Default accent `#2563EB`; success `#22C55E`; warning `#F59E0B`; danger `#EF4444`

สีทั้งหมดเรียกผ่าน semantic tokens ใน `src/ui/theme/tokens.py` และ accent ใช้เฉพาะ primary action, focus, selected state และ progress

## Typography

ใช้ Inter เมื่อไฟล์ font พร้อม และ fallback เป็น Segoe UI/Sans Serif

- Page title 20pt / 700
- Section title 11pt / 700
- Body 10pt
- Supporting text 9–10pt
- ไม่ใช้ display font, all caps หรือ tracking ที่รบกวนการอ่าน

## Downloads information architecture

ลำดับบนหน้า Downloads ต้องคงที่:

1. Page title + queue count
2. URL input และ import actions
3. Download Options
4. Context banner เฉพาะเมื่อจำเป็น เช่น playlist, clipboard, update หรือ FFmpeg warning
5. Queue / empty state

### Download Options

เป็นแหล่งควบคุมเดียวสำหรับงานใหม่ ประกอบด้วย:

- Media type: Audio / Video
- Format and quality: รายการที่กรองตาม media type
- Save location: path แบบ read-only พร้อม `Change folder`
- Primary action: `Download all (N)`

ข้อความกำกับต้องบอกตรง ๆ ว่างาน active จะรักษาค่าที่เริ่มไว้ Queue card แสดง preset summary แต่ไม่ทำซ้ำ dropdown ทุกใบ

### Queue item

- Thumbnail 96×54
- Title, duration, creator
- Text status ที่อ่านได้โดยไม่พึ่งสี
- Progress, speed, ETA เฉพาะเมื่อ active
- Preset summary
- Action เดียวที่เปลี่ยนตาม state: Download / Cancel / Retry / Open folder
- Remove เป็น secondary action

### Health and update banners

- FFmpeg banner แสดงเฉพาะเมื่อผู้ใช้ต้องแก้ไข
- ห้ามแสดง “Ready” success banner ค้างตลอด เพราะซ้ำกับสถานะปกติ
- Update banner แสดงเฉพาะเมื่อพบ version ใหม่ และนำไปหน้า Settings

## Settings information architecture

- Appearance: theme และ accent
- Queue: concurrency เท่านั้น
- Behavior: clipboard/tray
- Software updates: current version, startup preference, check state, release action, verified download state

Format, quality และ save location ไม่ทำซ้ำใน Settings

## Components and spacing

- Navigation width 176px
- Page padding 24px
- Main vertical spacing 14px
- Panel/card padding 12–16px
- Control heightอย่างน้อย 38px
- Radius 8–10px; สูงสุด 12px
- Border 1px; ไม่มี decorative side stripe
- ไม่มี nested cards

## Responsive rules

- Minimum window 760×600
- Subtitle wrap ได้และห้ามผลัก action ออกจาก viewport
- Download Options ใช้สองคอลัมน์สำหรับ media/quality และแถวเต็มสำหรับ save location
- Queue title/status ต้องยอม wrap ก่อนลดขนาดตัวอักษร
- Settings อยู่ใน scroll area
- ทดสอบที่ 760, 900, 1120, 1200 และ 1440px

## Interaction and feedback

- Network และ download ทำงานนอก UI thread
- ปุ่ม async disabled ขณะทำงาน
- Error อยู่ใกล้จุดที่แก้ได้และใช้ภาษาคน
- Update download แสดง progress และไม่รัน installer อัตโนมัติ
- Focus state ชัดเจนสำหรับ keyboard
- Motion มีเฉพาะ state feedback ระยะ 150–250ms เมื่อ Qt implementation รองรับ และต้องไม่จำเป็นต่อความเข้าใจ

## Anti AI-slop review

อินเทอร์เฟซต้องผ่านหลักต่อไปนี้:

- ไม่มี marketing hero, fake metric, testimonial หรือ badge ที่ไม่เกี่ยวกับงาน
- ไม่มี gradient, glass, glow, cream background, giant heading หรือ excessive rounding
- ไม่มี emoji functional icon
- ไม่มี generic CTA เช่น “Get started” หรือ “Learn more”
- ทุก panel มีหน้าที่ชัดและไม่ทำซ้ำข้อมูล
- ใช้ familiar desktop affordances มากกว่าการประดิษฐ์ control ใหม่
