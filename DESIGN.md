# Design System — Precision Pro-Utility (Wavrik 2.1)

## Product scene

โปรแกรมเดสก์ท็อปสำหรับดาวน์โหลดสื่อและวิเคราะห์/ปรับแต่งเสียงระดับสตูดิโอ ผู้ใช้ต้องมองเห็นสถานะของลิงก์ รูปแบบไฟล์ปลายทาง พาธที่บันทึก ตลอดจนค่าทางเทคนิค (Key, Camelot, BPM, Semitone Shift, Tempo Ratio) ได้อย่างแม่นยำในหน้าจอเดียว

## Design direction

ใช้แนวทาง **Precision Pro-Utility** (แรงบันดาลใจจาก Linear, Ableton Live, FabFilter):
- ลำดับชั้นพื้นผิว 4 ระดับด้วยความสว่าง (Luminance Stepping) และเส้นขอบ 1px
- จำกัดพื้นที่สี Accent (`#2BC3B0`) ไม่เกิน 5% ของหน้าจอ เฉพาะ Primary CTA, Active Navigation Indicator, Focus Ring และ Playhead
- ใช้ฟอนต์ Monospace (`Consolas` / `JetBrains Mono`) กับตัวเลขทางเทคนิคทั้งหมด (Key, Camelot, BPM, Semitones, Ratio, เปอร์เซ็นต์, ขนาดไฟล์)
- ห้ามใช้ gradient, glow, glassmorphism, เงาฟุ้ง หรือการวางการ์ดซ้อนการ์ด (No Card-in-Card)

## Semantic palette (Precision Graphite)

- Level 0 App Shell (`bg`): `#0F1113`
- Level 1 Sidebar & Workspace (`panel`): `#14171A`
- Level 2 Rack Module / Row (`surface`): `#191D21`
- Level 3 Input Well / Hover (`hover` / `input`): `#1F252B` / `#111417`
- Border (`border` / `border_strong`): `#262C33` / `#363F49`
- Text (`text` / `muted`): `#ECEFF4` / `#8A94A2`
- Accent (`ACCENT`): `#2BC3B0`
- Status: Success `#2EA043`, Warning `#D29922`, Danger `#F85149`

สีทั้งหมดเรียกผ่าน semantic tokens ใน `src/ui/theme/tokens.py` เท่านั้น

## 4-Tier Button Hierarchy

1. **Tier 1 (`PrimaryButton`)**: เติมสี `#2BC3B0` ตัวอักษรเข้ม `#0B0E11` — มีได้เพียงปุ่มหลักเดียวต่อมุมมอง (`Add to queue`, `Export Audio`)
2. **Tier 2 (`SecondaryButton`)**: พื้น `#1F252B` ขอบ `#363F49` — สำหรับคำสั่งรอง (`Download all`, `Preview Shifted`, `Batch Process...`)
3. **Tier 3 (`GhostButton` / `IconActionButton`)**: พื้นโปร่งใส ขอบบาง — สำหรับคำสั่งระดับแถว (`Folder`, `Audio Tools`, `×2`, `÷2`, `Import .txt`)
4. **Tier 4 (`DangerButton`)**: พื้นโปร่งใส ขอบและตัวอักษรสีแดง `#F85149` — สำหรับการลบหรือล้างประวัติ (`Clear history`)

## Single-Locale Rule (TH / EN)

รองรับการสลับภาษาไทย (`th`) และอังกฤษ (`en`) จากหน้า Settings โดยเปลี่ยนข้อความทุกหน้าทันที ห้ามผสมคำไทยปนอังกฤษในประโยคเดียว (No Tinglish) ยกเว้นชื่อเฉพาะทางเทคนิคสากล (`WAV`, `FLAC`, `MP3`, `BPM`, `Camelot`, `FFmpeg`, `Rubber Band R3`)

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
