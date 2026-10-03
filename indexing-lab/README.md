# Indexing Lab ของ Bookvice

ทดลองทำ index บนฐานข้อมูลของ Bookvice เอง แล้วเอาผลไปใช้กับโปรเจกต์จริง
ใช้โครงเดียวกับแล็บตัวอย่างของอาจารย์ (indexing-lab_02) แต่เปลี่ยนจากตาราง `transactions` สมมติ
เป็น**ตารางและ query ที่ Bookvice ยิงจริง** ทุก query ในแล็บบอกไว้ว่ามาจากไฟล์และฟังก์ชันไหน

ผลการทดลองและการตัดสินใจทั้งหมดอยู่ที่ [`docs/INDEXING.md`](../docs/INDEXING.md)

## ข้อมูล

PostgreSQL 16 สองตัว ข้อมูลเหมือนกันทุกแถว ต่างกันแค่ index

| Service | Port | index |
|---|---|---|
| `bv_lab_index` | 55432 | ชุดใหม่ที่ใช้ในโปรเจกต์จริง (`sql/init/03-create-index.sql`) |
| `bv_lab_noindex` | 55433 | มีแค่ Primary Key |

User / Password / DB: `student` / `student` / `appdb`

| ตาราง | จำนวนแถว | หมายเหตุ |
|---|---|---|
| bookings | 1,000,000 | ร้านดังมีคิวมากกว่าร้านทั่วไปมาก (ร้าน 1 ≈ 22,000 คิว) |
| payments | ~1,400,000 | เงินที่ยังพักอยู่มีไม่กี่เปอร์เซ็นต์ |
| reviews | ~180,000 | |
| notifications | 1,000,000 | อ่านแล้ว ~85% |
| users / shops / staff | 200,000 / 2,000 / 6,000 | |

ใช้ port 55432 / 55433 จะได้ไม่ชนกับฐานข้อมูลหลักของโปรเจกต์ (5432)

## รันทั้งหมดในคลิกเดียว (Windows)

ดับเบิลคลิก **`run-lab.bat`** — เปิดฐานข้อมูล รอ seed เสร็จ รันทุกแล็บ แล้วเก็บผลไว้ใน `results/`
ครั้งแรกใช้เวลา seed ประมาณ 2-5 นาที

## รันทีละแล็บเอง

```bash
docker compose up -d
docker compose logs -f bv_lab_noindex      # รอจนเห็น ">>> Lab ready" แล้ว Ctrl+C
docker exec -it bv_lab_index   psql -U student -d appdb -f /labs/01-explain.sql
docker exec -it bv_lab_noindex psql -U student -d appdb -f /labs/01-explain.sql
```

| ไฟล์ | รันบน | เนื้อหา |
|---|---|---|
| `01-explain.sql` | ทั้ง 2 ตัว | query จริง 9 ข้อของ Bookvice: หน้าจอง การจองของฉัน หน้าจัดการร้าน รีวิว ระบบพักเงิน แจ้งเตือน |
| `02-size.sql` | ทั้ง 2 ตัว | ขนาดตาราง vs index · partial index เล็กกว่าแค่ไหน |
| `03-old-vs-new.sql` | bv_lab_index | index ชุดเดิมของโปรเจกต์ vs ชุดใหม่ (ROLLBACK คืนค่าเอง) |
| `04-pitfalls.sql` | bv_lab_index | มี index แต่ไม่ถูกใช้ — กรณีที่เจอในโค้ดเราเอง |
| `05-insert-cost.sql` | ทั้ง 2 ตัว | จองคิวใหม่ 100,000 รายการ ช้าลงแค่ไหนเมื่อมี index |
| `06-usage.sql` | bv_lab_index | index ไหนถูกใช้จริง (รันหลังแล็บอื่น) |

## ใช้กับ DBeaver

localhost / port 55432 (มี index) และ 55433 (ไม่มี index) / appdb / student / student
บรรทัดที่ขึ้นต้นด้วย `\` (เช่น `\timing`, `\echo`) เป็นคำสั่งของ psql ต้องลบออกก่อนรันใน DBeaver

## ปิด / ลบ

```bash
docker compose down        # ปิด เก็บข้อมูลไว้
docker compose down -v     # ลบข้อมูลทั้งหมด (ครั้งหน้าจะ seed ใหม่)
```
