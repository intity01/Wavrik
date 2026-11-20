# AI-slop Review — Media Downloader PRO 2.1

## Automated result

รันจาก `Downloader`:

```bash
python tools/check_ai_slop.py
```

ตัวตรวจค้นหา gradient/glass/glow/shadow, emoji UI, radius เกิน 12px, decorative side stripe, placeholder copy, vague CTA และ marketing filler ที่พบบ่อยในงาน AI-generated

## Manual product review

| Check | Result | Evidence |
|---|---|---|
| Primary task is visible without onboarding modal | Pass | URL input และ Download Options อยู่หน้าเดียวกัน |
| No repeated controls on every card | Pass | Preset selector อยู่ส่วนกลาง; card แสดง summary |
| No decorative success state | Pass | FFmpeg banner แสดงเฉพาะเมื่อมีปัญหา |
| No nested-card hierarchy | Pass | Input, options, queue เป็น sibling regions |
| No fake metrics/testimonials/badges | Pass | มีเฉพาะ queue count และสถานะงานจริง |
| No generic marketing copy | Pass | Copy อธิบาย action/state โดยตรง |
| Familiar desktop controls | Pass | Native combo box, file dialog, text-labelled toggle, progress bar |
| No emoji functional icons | Pass | Navigation และ actions เป็น text-first |
| No gradient/glass/glow | Pass | QSS ใช้ solid token surfaces และ 1px borders |
| No excessive rounding | Pass | Radius 4–10px, hard limit 12px |
| Update flow earns trust | Pass | Background check, explicit confirmation, SHA-256, no auto-run |
| Empty/error/loading states teach or recover | Pass | Empty state สอน flow; errors มี Retry/แก้ไขได้ |
| Minimum-height layout stays usable | Pass | Downloads ทั้งหน้ามี vertical scroll ที่ 760×600; controls ไม่ถูกบีบหรือซ้อน |

## Human review questions before every release

1. มี panel ใดที่ลบแล้วผู้ใช้ยังทำงานได้เหมือนเดิมหรือไม่ ถ้ามีให้ลบ
2. มีคำที่ฟังดีแต่ไม่บอกผลลัพธ์ของ action หรือไม่
3. ข้อมูลเดียวกันถูกแสดงซ้ำใน Settings และ Downloads หรือไม่
4. สีหรือ decoration แย่งความสนใจจาก primary task หรือไม่
5. ผู้ใช้ที่เปิดครั้งแรกตอบได้หรือไม่ว่าไฟล์แบบไหน จะไปที่ไหน และต้องกดอะไรต่อ
