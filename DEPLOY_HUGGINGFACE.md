# นำ Bookvice ขึ้น Hugging Face Space

คู่มือนี้ทำให้เว็บเปิดสาธารณะได้ **โดยไม่แตะโครงเดิมที่ใช้ส่งอาจารย์**
`docker-compose.yml` และ `Dockerfile` หลักยังทำงานเหมือนเดิมทุกอย่าง

---

## ทำไมต้องมีไฟล์แยก

| | ในเครื่อง (ส่งอาจารย์) | บน Hugging Face |
|---|---|---|
| จำนวน container | 4 (db · api · web · pgadmin) | **1 เท่านั้น** |
| จำนวนพอร์ต | 3000 · 8000 · 8080 · 5433 | **1 เท่านั้น (7860)** |
| ใครเสิร์ฟหน้าเว็บ | nginx | FastAPI เสิร์ฟเอง |
| ฐานข้อมูล | PostgreSQL ใน container | PostgreSQL ภายนอก (Neon) |
| ไฟล์ที่ใช้ | `Dockerfile` + `docker-compose.yml` | `Dockerfile.hf` |

Space **ไม่รองรับ docker-compose** จึงต้องรวมทุกอย่างเป็น container เดียว

---

## ขั้นที่ 1 — เตรียมฐานข้อมูล (Neon)

Space ไม่มี PostgreSQL ให้ และดิสก์หายทุกครั้งที่รีสตาร์ต จึงต้องใช้ฐานข้อมูลภายนอก

1. เข้า **https://neon.tech** สมัครด้วย GitHub (แผนฟรีไม่ต้องผูกบัตร)
2. กด **Create project** ตั้งชื่อ `bookvice` เลือก region **Singapore** (ใกล้ไทยที่สุด)
3. หน้า **Connection string** เลือกแบบ **psycopg2** จะได้ประมาณนี้

```
postgresql://bookvice_owner:xxxxxxxx@ep-xxxx.ap-southeast-1.aws.neon.tech/bookvice?sslmode=require
```

4. **แก้ตรงหัวให้เป็น `postgresql+psycopg2://`** เพราะ SQLAlchemy ต้องรู้ว่าใช้ไดรเวอร์ตัวไหน

```
postgresql+psycopg2://bookvice_owner:xxxxxxxx@ep-xxxx.ap-southeast-1.aws.neon.tech/bookvice?sslmode=require
```

> เก็บสตริงนี้ไว้ **อย่าใส่ลงในไฟล์ใด ๆ ที่จะอัปขึ้น Space** — เดี๋ยวใส่เป็น secret

**ข้อดีของวิธีนี้:** โค้ด Python ไม่ต้องแก้สักบรรทัด เพราะยังเป็น PostgreSQL เหมือนเดิม
(ถ้าเปลี่ยนเป็น SQLite จะต้องแก้ 8 จุดที่ใช้คำสั่งเฉพาะของ PostgreSQL)

---

## ขั้นที่ 2 — สร้าง Space

1. เข้า **https://huggingface.co/new-space**
2. ตั้งค่าตามนี้

| ช่อง | ค่า |
|---|---|
| Space name | `bookvice` |
| License | `mit` |
| Space SDK | **Docker** → **Blank** |
| Visibility | Public (หรือ Private ถ้ายังไม่อยากให้ใครเห็น) |
| Hardware | CPU basic · free |

---

## ขั้นที่ 3 — ตั้งค่าลับ (Secrets)

ใน Space กด **Settings → Variables and secrets**

### Secrets (ความลับ — ไม่แสดงในหน้าเว็บ)

| Name | Value |
|---|---|
| `DATABASE_URL` | connection string จาก Neon (ที่แก้หัวเป็น `+psycopg2` แล้ว) |
| `JWT_SECRET` | สุ่มมาสัก 40 ตัวอักษร เช่นจาก `python -c "import secrets;print(secrets.token_urlsafe(32))"` |
| `ADMIN_PASSWORD` | รหัสผ่านผู้ดูแลระบบที่คุณตั้งเอง |

> **`ADMIN_PASSWORD` สำคัญมาก** — บัญชี `admin` ลบร้าน ลบผู้ใช้ และเปลี่ยนสิทธิ์คนอื่นได้
> ถ้าไม่ตั้ง ระบบจะสุ่มให้แล้วพิมพ์ลง log ครั้งเดียวตอนสร้างฐานข้อมูลครั้งแรก
> (ดูได้ที่แท็บ **Logs** ของ Space) แต่ตั้งเองสะดวกกว่า

### Variables (ค่าธรรมดา)

| Name | Value |
|---|---|
| `SEED_ON_START` | `true` |

---

## ขั้นที่ 4 — อัปไฟล์

### วิธีที่ 1 — ลากวางบนเว็บ (ง่ายกว่า)

แท็บ **Files → Add file → Upload files** แล้วอัปตามนี้

```
README.md              ← ไฟล์ README_HF.md ในโปรเจกต์ เปลี่ยนชื่อเป็น README.md
Dockerfile             ← ไฟล์ Dockerfile.hf ในโปรเจกต์ เปลี่ยนชื่อเป็น Dockerfile
requirements.txt
app/       (ทั้งโฟลเดอร์)
web/       (ทั้งโฟลเดอร์)
```

> **สังเกตการเปลี่ยนชื่อ** — Space มองหาไฟล์ชื่อ `Dockerfile` เท่านั้น
> ส่วน `Dockerfile` เดิมของเรากับ `docker-compose.yml` **ไม่ต้องอัป**

### วิธีที่ 2 — ผ่าน git

```bash
git clone https://huggingface.co/spaces/<ชื่อผู้ใช้>/bookvice
cd bookvice

cp "<โฟลเดอร์โปรเจกต์>/Dockerfile.hf"  Dockerfile
cp "<โฟลเดอร์โปรเจกต์>/README_HF.md"   README.md
cp "<โฟลเดอร์โปรเจกต์>/requirements.txt" .
cp -r "<โฟลเดอร์โปรเจกต์>/app" "<โฟลเดอร์โปรเจกต์>/web" .

git add -A
git commit -m "Bookvice booking platform"
git push
```

---

## ขั้นที่ 5 — ตรวจว่าทำงาน

Space จะ build เอง ใช้เวลาราว 3–5 นาที ดูความคืบหน้าที่แท็บ **Logs**

**สัญญาณว่าสำเร็จ** — ใน log ต้องเห็นตามลำดับนี้

```
เชื่อมต่อฐานข้อมูลสำเร็จ
กำลังใส่ข้อมูลตัวอย่าง...
เพิ่มสนามและศูนย์บริการ 16 แห่ง
เติมพิกัดให้ร้าน N ร้าน
เสิร์ฟหน้าเว็บจาก /app/web
Bookvice API พร้อมใช้งาน
```

**ที่อยู่หลัง deploy**

| | |
|---|---|
| หน้าเว็บ | `https://<ชื่อผู้ใช้>-bookvice.hf.space/` |
| เอกสาร API | `https://<ชื่อผู้ใช้>-bookvice.hf.space/docs` |
| ตรวจสถานะ | `https://<ชื่อผู้ใช้>-bookvice.hf.space/health` |

---

## ข้อจำกัดที่ต้องรู้

| เรื่อง | รายละเอียด |
|---|---|
| **รูปที่อัปโหลดหาย** | เก็บใน `/tmp` ซึ่งหายทุกครั้งที่ Space รีสตาร์ตหรือ build ใหม่ ข้อมูลในฐานข้อมูลยังอยู่ แต่ไฟล์รูปหาย — การ์ดร้านจะกลับไปเป็นภาพไล่สี |
| **Space หลับ** | แผนฟรีจะหลับเมื่อไม่มีคนเข้า 48 ชั่วโมง ตื่นเองเมื่อมีคนเปิด แต่ครั้งแรกจะช้าราว 30 วินาที |
| **Neon หลับ** | แผนฟรีปิด compute เมื่อไม่มีคนใช้ 5 นาที คำขอแรกหลังหลับจะช้าราว 1–2 วินาที |
| **pgAdmin ไม่มี** | ใช้หน้า SQL Editor ของ Neon แทน |
| **ไม่มีสำรองข้อมูล** | Neon ฟรีเก็บย้อนหลังได้จำกัด อย่าใช้เก็บอะไรที่เสียไม่ได้ |

### ถ้าอยากให้รูปไม่หาย

Space → **Settings → Persistent Storage** (มีค่าใช้จ่าย) แล้วเพิ่ม variable

```
UPLOAD_DIR = /data/uploads
```

---

## แก้ปัญหาที่พบบ่อย

| อาการใน log | สาเหตุ | วิธีแก้ |
|---|---|---|
| `could not translate host name` | `DATABASE_URL` ผิด หรือลืมใส่ | ตรวจ secret ว่าคัดลอกครบ |
| `sslmode value "require" invalid` | หัวสตริงยังเป็น `postgresql://` | เปลี่ยนเป็น `postgresql+psycopg2://` |
| `password authentication failed` | รหัสใน connection string หมดอายุ | สร้าง connection string ใหม่ใน Neon |
| หน้าเว็บขึ้นแต่กดอะไรไม่ได้ | `SERVE_WEB` ไม่ได้ตั้ง | `Dockerfile.hf` ตั้งให้แล้ว ตรวจว่าใช้ไฟล์ถูกตัว |
| `Permission denied: '/app/uploads'` | `UPLOAD_DIR` ยังชี้ที่เดิม | `Dockerfile.hf` ตั้งเป็น `/tmp/uploads` ให้แล้ว |
| หน้าเว็บ 404 ทุกหน้า | ไม่ได้อัปโฟลเดอร์ `web/` | อัปให้ครบทั้งโฟลเดอร์ |

---

## กลับมาทำงานในเครื่อง

ไม่มีอะไรเปลี่ยน — คำสั่งเดิมใช้ได้ทันที

```powershell
cd "C:\Users\Prame\Claude\Projects\WORK WEBSITE UNIVERSITY\bookvice"
docker compose up -d --build
```

เพราะ `SERVE_WEB` ค่าเริ่มต้นเป็น `false` และ `UPLOAD_DIR` ค่าเริ่มต้นเป็น `/app/uploads`
ทั้งคู่ถูกเปลี่ยนเฉพาะใน `Dockerfile.hf` เท่านั้น
