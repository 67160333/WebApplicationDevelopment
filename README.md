# Bookvice — REST API + Docker Compose

> **จองง่าย ได้ครบ จบที่เดียว**

แพลตฟอร์มจองคิวบริการ สร้างด้วย **FastAPI** และจัดการ container ด้วย **Docker & Docker Compose**
งานส่งรายวิชา **89033167 Web Application Development** · อาจารย์ผู้สอน JAKAPONG BOONYAI

รองรับ 8 หมวดบริการ — สปา · ทำเล็บ · ทำผม · คลินิกความงาม · สักลาย · สนามฟุตบอล · สนามแบดมินตัน · ส่งของด่วน

---

## ตรวจตามใบงาน — ครบทั้ง 10 เส้นทาง

โจทย์ยกตัวอย่างเส้นทางไว้แบบ **ไม่มี `/api` นำหน้า** ระบบนี้จึงเปิดไว้ทั้งสองแบบ
โดยผูกไปที่ฟังก์ชันตัวเดียวกัน ไม่ได้เขียนโค้ดซ้ำ (ดู `app/routers/aliases.py`)

เปิด **http://localhost:8000/docs** แล้วดูหมวด **"9. เส้นทางตามรูปแบบในโจทย์"** จะเห็นครบในที่เดียว

### 1. Authentication

| ใบงานระบุ | สถานะ | เส้นทางเต็มของระบบ |
|---|:--:|---|
| `POST /register` — สมัครสมาชิก | ✅ | `POST /api/auth/register` |
| `POST /login` — เข้าสู่ระบบ | ✅ | `POST /api/auth/login` |
| `POST /logout` — ออกจากระบบ | ✅ | `POST /api/auth/logout` |
| `POST /change-password` — เปลี่ยนรหัสผ่าน | ✅ | `POST /api/auth/change-password` |

### 2. User Management

| ใบงานระบุ | สถานะ | เส้นทางเต็มของระบบ |
|---|:--:|---|
| `GET /me` — ดึงข้อมูลตัวเอง | ✅ | `GET /api/users/me` |
| `GET /users/{id}` — ดึงข้อมูล user | ✅ | `GET /api/users/{user_id}` |
| `GET /users` — ทั้งหมด (pagination) | ✅ | `GET /api/users?page=1&limit=20` |
| `PUT /users/{id}` — แก้ไขข้อมูล user | ✅ | `PUT /api/users/{user_id}` |
| `DELETE /users/{id}` — ลบ user | ✅ | `DELETE /api/users/{user_id}` |
| `GET /check-username/{name}` — ตรวจว่าว่างไหม | ✅ | `GET /api/users/check-username/{name}` |

### Docker & Docker Compose

`docker compose up -d --build` คำสั่งเดียวได้ครบ 4 container

| Container | หน้าที่ | พอร์ต |
|---|---|---|
| `bookvice-api` | FastAPI | 8000 |
| `bookvice-db` | PostgreSQL 16 | 5433 |
| `bookvice-web` | nginx เสิร์ฟหน้าเว็บ | 3000 |
| `bookvice-pgadmin` | จัดการฐานข้อมูลผ่านเว็บ | 8080 |

### นอกเหนือจากที่ใบงานขอ

ระบบนี้มี **56 เส้นทางภายใต้ `/api`** ไม่ใช่แค่ 10 เส้นตามตัวอย่าง เพราะทำเป็นระบบจองคิวที่ใช้งานได้จริง
ส่วนที่เพิ่มมาคือ ร้านและบริการ · ผู้ให้บริการ · การจองและช่วงเวลาว่าง · รีวิว · แจ้งเตือน · รูปภาพ · การชำระเงิน

---

## เริ่มใช้งาน

### สิ่งที่ต้องมี
Docker Desktop (มี Docker Compose มาให้แล้ว)

```bash
cd bookvice

# สร้างไฟล์ตั้งค่าจากตัวอย่าง
copy .env.example .env          # Windows
# cp .env.example .env          # macOS / Linux

docker compose up -d --build

# ดู log ว่าระบบพร้อมหรือยัง
docker compose logs -f api
```

เมื่อขึ้นข้อความ `Bookvice API พร้อมใช้งานที่ http://localhost:8000/docs` แปลว่าเรียบร้อย

| บริการ | ที่อยู่ |
|---|---|
| **หน้าเว็บ** | **http://localhost:3000** |
| Swagger UI (ทดสอบ API) | http://localhost:8000/docs |
| ReDoc (เอกสารอ่านง่าย) | http://localhost:8000/redoc |
| ตรวจสอบสถานะ | http://localhost:8000/health |
| pgAdmin (ดูฐานข้อมูล) | http://localhost:8080 |
| PostgreSQL (ต่อจากโปรแกรมภายนอก) | localhost:5433 |

### บัญชีทดสอบ — รหัสผ่าน `Password123` ทุกบัญชี

| Username | บทบาท | ใช้ทดสอบอะไร |
|---|---|---|
| `mind` | customer | ฝั่งลูกค้า |
| `nong` | customer | ทดสอบการจองชนกันระหว่างสองคน |
| `spaowner` | owner | เจ้าของร้านความงาม |
| `nailowner` | owner | ทดสอบสิทธิ์ข้ามร้าน (ต้องถูกปฏิเสธ) |
| `venueowner` | owner | เจ้าของสนามกีฬาและศูนย์ส่งของ |
| `admin` | admin | ผู้ดูแลระบบ |

### คำสั่งที่ใช้บ่อย

```bash
docker compose ps              # ดูสถานะ container
docker compose logs -f api     # ดู log ของ API
docker compose restart api     # รีสตาร์ตเฉพาะ API
docker compose down            # หยุดและลบ container (ข้อมูลยังอยู่)
docker compose down -v         # ลบข้อมูลฐานข้อมูลและรูปที่อัปโหลดด้วย
```

> **แก้โค้ดแล้วต้องทำอะไร**
>
> | แก้อะไร | ต้องทำอะไร |
> |---|---|
> | ไฟล์ใน `web/` | แค่ `Ctrl+Shift+R` — โฟลเดอร์นี้ bind-mount เข้า nginx โดยตรง |
> | ไฟล์ใน `app/` | ต้อง `docker compose up -d --build api` |
> | `requirements.txt` · `docker-compose.yml` | ต้อง build ใหม่ |

---

## ทำตามข้อกำหนดของโจทย์อย่างไร

| ข้อกำหนดจากเอกสาร | ทำแล้ว |
|---|---|
| ใช้ FastAPI + Pydantic validation | ทุก endpoint ตรวจข้อมูลด้วย Pydantic (`app/schemas.py`) |
| CRUD ครบ 4 การทำงาน | Create / Read / Update / Delete ครบทุกทรัพยากร |
| ทดสอบผ่าน Swagger UI | เปิด `/docs` ทดลองยิง request ได้ทันที |
| `requirements.txt` มี fastapi + uvicorn[standard] | ครบ |
| Dockerfile ใช้ `python:3.12-slim` | ใช่ |
| รันด้วย `uvicorn --host 0.0.0.0 --port 8000` | ใช่ |
| docker-compose รัน API + ฐานข้อมูลพร้อมกัน | 4 service: `api` + `db` + `web` + `pgadmin` |
| service คุยกันด้วยชื่อ service | API เรียกฐานข้อมูลด้วยชื่อ `db` ไม่ใช้ IP |

### เช็คลิสต์ 10 ข้อตามโจทย์

**Authentication**

- [x] `POST /register` — สมัครสมาชิก
- [x] `POST /login` — เข้าสู่ระบบ
- [x] `POST /logout` — ออกจากระบบ
- [x] `POST /change-password` — เปลี่ยนรหัสผ่าน

**User Management**

- [x] `GET /me` — ดึงข้อมูลตัวเอง
- [x] `GET /users/{id}` — ดึงข้อมูล user
- [x] `GET /users` — ดึง user ทั้งหมด (pagination)
- [x] `PUT /users/{id}` — แก้ไขข้อมูล user
- [x] `DELETE /users/{id}` — ลบ user
- [x] `GET /check-username/{name}` — ตรวจสอบ username ว่าง

> ทุกเส้นทางเรียกได้ **2 แบบ** — ตามโจทย์ (`POST /register`) และแบบจัดกลุ่ม (`POST /api/auth/register`)
> ทั้งสองแบบใช้โค้ดชุดเดียวกัน ไม่ได้เขียนซ้ำ (ดู `app/routers/aliases.py`)

นอกจาก 10 ข้อนี้ ยังมีเอนด์พอยต์ของระบบจริงอีก 46 เส้น รวมทั้งหมด **56 เส้น**

---

## ฟีเจอร์หลัก — ทำไมลูกค้าต้องใช้เราแทนการทัก LINE ร้าน

คู่แข่งจริงของแพลตฟอร์มนี้ไม่ใช่เว็บอื่น แต่คือ **การทัก LINE ไปหาร้านโดยตรง**
ปัญหาของการทัก LINE คือ *ต้องรอ* — ถามราคา รอตอบ ถามคิวว่าง รอตอบอีก อยากเทียบ 3 ร้านต้องทำ 3 รอบ

ระบบนี้จึงออกแบบมาเพื่อ **ตัดเวลารอทิ้ง**

### 1. เห็นช่องเวลาว่างจริงทั้งวัน แล้วกดเลือกได้เลย

เลือกวัน → เลือกผู้ให้บริการ → เห็นช่องไหนว่างช่องไหนเต็ม → กดจอง

- `GET /api/services/{id}/availability` คำนวณจากเวลาทำการร้าน ตารางงานของแต่ละคน ระยะเวลาบริการ และคิวที่จองไปแล้ว
- ช่องที่ผ่านมาแล้วหรือชนคิวเดิมจะถูกปิดพร้อมบอกเหตุผล
- ตรวจการชนแบบ **คาบเกี่ยว** ไม่ใช่แค่เวลาเริ่มตรงกัน (นวด 90 นาทีเริ่ม 14:00 บล็อกถึง 15:30)
- รองรับร้านที่เปิดคร่อมเที่ยงคืนและเปิดตลอด 24 ชั่วโมง

### 2. เลือกคนหรือคอร์ทที่ต้องการได้

- คิวว่างคำนวณ **แยกรายคน** — ช่างมิ้นไม่ว่าง ไม่ได้แปลว่าช่างแนนไม่ว่าง
- เลือก "ให้ร้านจัดให้" ก็ได้ ระบบจะรับคิวได้เท่าจำนวนคนที่เข้างานวันนั้นจริง
- ดูโปรไฟล์ คะแนน และรีวิวของแต่ละคนก่อนเลือกได้

### 3. บอกความต้องการล่วงหน้า ไม่ต้องอธิบายซ้ำหน้างาน

| ช่อง | ใช้ทำอะไร |
|---|---|
| สิ่งที่อยากได้ | สีที่ต้องการ ทรงที่อยากได้ ระดับแรงนวด |
| ลิงก์รูปตัวอย่าง | แนบรูปจาก Instagram/Pinterest |
| ข้อมูลสุขภาพ | แพ้สารเคมี ตั้งครรภ์ โรคประจำตัว — ร้านเห็นเป็นข้อความสีเตือน |
| หมายเหตุ | เช่น ขอห้องส่วนตัว |

### 4. จองสนามกีฬาและเรียกส่งของด่วนได้ในระบบเดียวกัน

**สนามบอล คอร์ทแบด และพนักงานส่ง ใช้ตาราง `staff` ตัวเดียวกับช่างทำผม**
ต่างกันแค่ *คำเรียก* ซึ่งเก็บที่ `categories.resource_label` แล้วส่งมากับ API
หน้าเว็บใช้ค่านี้แทนคำว่า "ช่าง" ทุกที่ที่ผู้ใช้เห็น

| หมวด | คำเรียก |
|---|---|
| spa-massage · nail · hair | ช่าง |
| beauty-clinic | แพทย์/ผู้ดูแล |
| tattoo | ช่างสัก |
| football | สนาม |
| badminton | คอร์ท |
| delivery | พนักงานส่ง |

บริการส่งของด่วนใช้ `booking_mode = instant` — **ไม่มีปฏิทิน** กรอกต้นทาง-ปลายทางแล้วกดเรียก
ระบบคิดเงินจาก `price + price_per_km × distance_km` และยืนยันงานให้ทันที

---

## หน้าเว็บ

เปิดที่ **http://localhost:3000** ใช้งานได้ครบทั้ง 3 บทบาท เมนูบนแถบนำทางเปลี่ยนตามบทบาทที่ล็อกอิน

### ฝั่งลูกค้า

| หน้า | ไฟล์ |
|---|---|
| หน้าแรก — ค้นหา หมวดหมู่ ร้านแนะนำ รีวิวจริง คำถามที่พบบ่อย | `index.html` |
| สมัครสมาชิก (เช็คชื่อซ้ำเรียลไทม์) | `register.html` |
| เข้าสู่ระบบ | `login.html` |
| ค้นหาร้าน — กรอง 6 เงื่อนไข · ใกล้ฉัน · ว่างวันนี้ · ร้านโปรด | `shops.html` |
| รายละเอียดร้าน + จองคิว + แผนที่ + รีวิว | `shop.html` |
| การจองของฉัน — ยกเลิก เลื่อนนัด ชำระเงิน ใบเสร็จ รีวิว | `bookings.html` |
| บัญชีของฉัน | `profile.html` |
| ราคาและดีล | `promotions.html` |

### ฝั่งเจ้าของร้าน — `manage.html`

ล็อกอินด้วย `spaowner` หรือ `venueowner`

| แท็บ | ทำอะไรได้ |
|---|---|
| คิวที่จองเข้ามา | ยืนยัน · ปิดงาน · ยกเลิก · รับเงินสด · พิมพ์สลิป · **เห็นความต้องการและข้อมูลสุขภาพที่ลูกค้าแจ้ง** |
| บันทึกคิวหน้าร้าน | จองแทนลูกค้าที่โทรมาหรือเดินเข้าร้าน (walk-in) |
| บริการของร้าน | เพิ่ม / แก้ไข / ลบ |
| ผู้ให้บริการ | เพิ่ม / แก้ไข / ลบ · ตั้งวันและเวลาทำงานรายคน |
| รูปภาพ | อัปโหลด · ตั้งรูปปก · ลบ |
| ข้อมูลร้าน | ชื่อ คำอธิบาย ที่อยู่ เวลาทำการ **ปักหมุดบนแผนที่** |
| รายงานยอดขาย | รายรับที่รับชำระจริง แยกตามวิธีชำระเงิน |

### ฝั่งผู้ดูแลระบบ — `admin.html`

สรุปจำนวนผู้ใช้แยกตามบทบาท · ค้นหาและกรอง · แก้ไขข้อมูล · เปลี่ยนบทบาท · ระงับบัญชี · ลบบัญชี

### เทคโนโลยีฝั่งหน้าเว็บ

HTML + CSS + JavaScript ล้วน — **ไม่ต้อง build ไม่ต้องติดตั้ง Node และไม่พึ่ง CDN ภายนอก** เปิดใช้งานได้แม้ไม่มีอินเทอร์เน็ต
เสิร์ฟด้วย nginx container โดย mount ไฟล์เข้าไปตรง ๆ แก้โค้ดแล้วรีเฟรชเห็นผลทันที

| หัวข้อ | รายละเอียด |
|---|---|
| ฟอนต์หัวข้อ | **FC Mittraphap** (Fontcraft Studio) ไฟล์อยู่ที่ `web/fonts/` |
| ฟอนต์เนื้อความ | IBM Plex Sans Thai |
| ชุดสี | น้ำเงินกรมท่า `#0f294b` เป็นสีหลัก · ฟ้าสด `#1a63d8` สำหรับปุ่มและลิงก์ · ส้มและเขียวน้ำทะเลเป็นสีเสริมจากโลโก้ |
| ไอคอน | SVG เส้นที่วาดเอง 30 ตัว ไม่ใช้อิโมจิ ไม่มีลิขสิทธิ์ |
| โลโก้ | ฟังก์ชัน `brandMark()` ใน `web/js/ui.js` — ตัว B จากห่วงสองวง ห่วงบนเป็นปฏิทิน ห่วงล่างเป็นเครื่องหมายถูก |
| ตัวเลข | `font-variant-numeric: tabular-nums` ราคาและรหัสจองเรียงตรงหลัก |
| การเข้าถึง | focus ring ทุกปุ่ม · ขังโฟกัสในกล่องซ้อน · ปิดด้วย Esc · `aria-pressed` บนปุ่มที่เป็นตัวสลับสถานะ · เคารพ `prefers-reduced-motion` |

> **สัญญาอนุญาตฟอนต์ FC Mittraphap:** ฟรีสำหรับงานที่ไม่ใช่เชิงพาณิชย์ (โปรเจกต์รายวิชาเข้าข่าย)
> ถ้าใช้เชิงพาณิชย์ต้องสนับสนุน 500 บาทที่ fontcraftstudio.com/support
> สำเนาสัญญาอยู่ที่ `web/fonts/LICENSE-FCMittraphap.txt` — **อย่าลบ**

---

## โครงสร้างโปรเจกต์

```
bookvice/
├── docker-compose.yml      # 4 service: api · db · web · pgadmin
├── Dockerfile              # image ของ API
├── Dockerfile.hf           # สำหรับ deploy บน Hugging Face (container เดียว)
├── requirements.txt
├── .env.example
├── app/
│   ├── main.py             # ประกอบแอป · lifespan: รอ db → create_all → migrate → seed
│   ├── config.py           # อ่านค่าจาก environment
│   ├── database.py         # เชื่อมต่อฐานข้อมูล + รอ db พร้อม
│   ├── models.py           # 12 ตาราง (SQLAlchemy 2.0)
│   ├── schemas.py          # Pydantic — ตรวจข้อมูลเข้า/ออก + สร้างเอกสาร Swagger
│   ├── migrate.py          # เติมคอลัมน์/เงื่อนไข/ดัชนีที่ขาด โดยไม่ลบข้อมูลเดิม
│   ├── security.py         # JWT · bcrypt · require_roles()
│   ├── storage.py          # จัดการรูปที่อัปโหลด (ตรวจ · ย่อ · แปลง WebP)
│   ├── seed*.py            # ข้อมูลตัวอย่าง
│   └── routers/            # auth · users · shops · staff · bookings
│                           # notifications · images · payments · aliases
└── web/
    ├── *.html              # 10 หน้า
    ├── css/app.css         # design system เขียนเอง
    ├── fonts/              # FC Mittraphap + สัญญาอนุญาต
    ├── nginx.conf
    └── js/
        ├── api.js          # เรียก API + จัดการ token
        └── ui.js           # ไอคอน โลโก้ แถบเมนู กล่องซ้อน ส่วนประกอบร่วม
```

---

## รายการ API ทั้งหมด (56 เส้น)

🔒 = ต้องล็อกอินก่อน

### 1. Authentication — 4

| Method | Endpoint | คำอธิบาย |
|---|---|---|
| POST | `/api/auth/register` | สมัครสมาชิก |
| POST | `/api/auth/login` | เข้าสู่ระบบ (ใช้ username หรือ email) |
| POST | `/api/auth/logout` | 🔒 ออกจากระบบ (token เข้า blacklist) |
| POST | `/api/auth/change-password` | 🔒 เปลี่ยนรหัสผ่าน |

### 2. User Management — 6

| Method | Endpoint | คำอธิบาย |
|---|---|---|
| GET | `/api/users/me` | 🔒 ดึงข้อมูลตัวเอง |
| GET | `/api/users` | 🔒 ดึง user ทั้งหมด (แบ่งหน้า) — admin |
| GET | `/api/users/{user_id}` | 🔒 ดึงข้อมูล user รายคน |
| PUT | `/api/users/{user_id}` | 🔒 แก้ไขข้อมูล user |
| DELETE | `/api/users/{user_id}` | 🔒 ลบ user — admin |
| GET | `/api/users/check-username/{name}` | ตรวจสอบชื่อผู้ใช้ว่าง |

### 3. Shops & Services — 17

| Method | Endpoint | คำอธิบาย |
|---|---|---|
| GET | `/api/categories` | หมวดหมู่บริการทั้งหมด |
| GET | `/api/shops` | ค้นหาร้าน — กรอง · แบ่งหน้า · **ใกล้ฉัน** · **ว่างวันนี้** |
| GET | `/api/shops/{shop_id}` | รายละเอียดร้าน พร้อมบริการ ผู้ให้บริการ และรูป |
| POST | `/api/shops` | 🔒 สร้างร้าน — owner/admin |
| PUT | `/api/shops/{shop_id}` | 🔒 แก้ไขร้าน |
| DELETE | `/api/shops/{shop_id}` | 🔒 ลบร้าน |
| GET | `/api/shops/{shop_id}/services` | บริการทั้งหมดของร้าน |
| POST | `/api/shops/{shop_id}/services` | 🔒 เพิ่มบริการ |
| PUT | `/api/services/{service_id}` | 🔒 แก้ไขบริการ |
| DELETE | `/api/services/{service_id}` | 🔒 ลบบริการ |
| GET | `/api/shops/{shop_id}/staff` | รายชื่อผู้ให้บริการของร้าน |
| POST | `/api/shops/{shop_id}/staff` | 🔒 เพิ่มผู้ให้บริการ |
| PUT | `/api/staff/{staff_id}` | 🔒 แก้ไขข้อมูลผู้ให้บริการ |
| DELETE | `/api/staff/{staff_id}` | 🔒 ลบผู้ให้บริการ |
| GET | `/api/shops/{shop_id}/closures` | วันที่ร้านปิดเป็นกรณีพิเศษ |
| POST | `/api/shops/{shop_id}/closures` | 🔒 ประกาศวันหยุด |
| DELETE | `/api/closures/{closure_id}` | 🔒 ยกเลิกวันหยุดที่ประกาศไว้ |

### 4. Bookings & Reviews — 14

| Method | Endpoint | คำอธิบาย |
|---|---|---|
| GET | `/api/services/{service_id}/availability` | **ช่องเวลาว่างทั้งวัน** พร้อมเหตุผลของช่องที่จองไม่ได้ |
| GET | `/api/bookings` | 🔒 รายการจอง (ลูกค้าเห็นของตัวเอง · ร้านเห็นของร้าน · admin เห็นทั้งหมด) |
| GET | `/api/bookings/{booking_id}` | 🔒 รายละเอียดการจอง |
| POST | `/api/bookings` | 🔒 จองคิว |
| POST | `/api/bookings/instant` | 🔒 **เรียกใช้บริการทันที** (ส่งของด่วน) |
| PATCH | `/api/bookings/{booking_id}/status` | 🔒 เปลี่ยนสถานะ |
| PATCH | `/api/bookings/{booking_id}/reschedule` | 🔒 **เลื่อนนัด** โดยรหัสการจองไม่เปลี่ยน |
| DELETE | `/api/bookings/{booking_id}` | 🔒 ยกเลิกการจอง |
| GET | `/api/shops/{shop_id}/reviews` | รีวิวของร้าน — กรองตามผู้ให้บริการ คะแนน และเรียงลำดับได้ |
| GET | `/api/shops/{shop_id}/review-summary` | สรุปการกระจายดาวและคะแนนแยกหัวข้อ |
| POST | `/api/reviews` | 🔒 เขียนรีวิว |
| POST | `/api/reviews/{review_id}/reply` | 🔒 เจ้าของร้านตอบกลับรีวิว |
| DELETE | `/api/reviews/{review_id}/reply` | 🔒 ลบคำตอบกลับ |
| DELETE | `/api/reviews/{review_id}` | 🔒 ลบรีวิวของตัวเอง (เจ้าของร้านลบไม่ได้) |

### 5. Staff Profiles — 2

| Method | Endpoint | คำอธิบาย |
|---|---|---|
| GET | `/api/staff/{staff_id}` | โปรไฟล์ คะแนน และจำนวนงานที่ทำเสร็จ |
| GET | `/api/staff/{staff_id}/reviews` | รีวิวที่กล่าวถึงผู้ให้บริการคนนี้ |

### 6. Notifications — 4

| Method | Endpoint | คำอธิบาย |
|---|---|---|
| GET | `/api/notifications` | 🔒 การแจ้งเตือนของฉัน |
| GET | `/api/notifications/unread-count` | 🔒 จำนวนที่ยังไม่ได้อ่าน (ใช้กับกระดิ่ง) |
| PATCH | `/api/notifications/{id}/read` | 🔒 ทำเครื่องหมายว่าอ่านแล้ว |
| POST | `/api/notifications/read-all` | 🔒 อ่านทั้งหมดแล้ว |

### 7. Shop Images — 4

| Method | Endpoint | คำอธิบาย |
|---|---|---|
| GET | `/api/shops/{shop_id}/images` | รูปทั้งหมดของร้าน |
| POST | `/api/shops/{shop_id}/images` | 🔒 อัปโหลดรูป (ย่อและแปลง WebP ให้อัตโนมัติ) |
| PATCH | `/api/shop-images/{image_id}` | 🔒 แก้คำบรรยาย หรือตั้งเป็นรูปปก |
| DELETE | `/api/shop-images/{image_id}` | 🔒 ลบรูป |

### 8. Payments — 5

| Method | Endpoint | คำอธิบาย |
|---|---|---|
| GET | `/api/bookings/{booking_id}/payment` | 🔒 สถานะการชำระเงินของคิวนี้ |
| POST | `/api/bookings/{booking_id}/payment` | 🔒 ชำระมัดจำหรือยอดคงเหลือ |
| POST | `/api/payments/{payment_id}/refund` | 🔒 คืนเงิน — เจ้าของร้าน |
| GET | `/api/payments/{payment_id}/receipt` | 🔒 ข้อมูลใบเสร็จ |
| GET | `/api/shops/{shop_id}/revenue` | 🔒 สรุปรายรับที่รับชำระจริง |

---

## ตัวอย่างการเรียกใช้งานด้วย curl

```bash
# เข้าสู่ระบบ
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d "{\"username\":\"mind\",\"password\":\"Password123\"}"

# ดึงข้อมูลตัวเอง
curl http://localhost:8000/api/users/me \
  -H "Authorization: Bearer <access_token>"

# ค้นหาร้านใกล้ตัว ในรัศมี 5 กิโลเมตร
curl "http://localhost:8000/api/shops?near_lat=13.7563&near_lng=100.5018&radius_km=5"

# ดูช่องเวลาว่างของบริการ
curl "http://localhost:8000/api/services/1/availability?date=2026-12-15"

# จองคิว
curl -X POST http://localhost:8000/api/bookings \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <access_token>" \
  -d "{\"service_id\":1,\"booking_date\":\"2026-12-15\",\"booking_time\":\"14:00\"}"
```

### วิธีทดสอบผ่าน Swagger UI

1. เปิด http://localhost:8000/docs
2. กาง **`POST /api/auth/login`** → **Try it out**
3. ใส่ `{"username": "mind", "password": "Password123"}` → **Execute**
4. คัดลอก `access_token` จากผลลัพธ์
5. กดปุ่ม **Authorize** 🔓 มุมขวาบน → วาง token → Authorize
6. จากนี้ทดสอบ endpoint ที่ต้องล็อกอินได้ทุกตัว

> **ลองทดสอบ validation:** ที่ `POST /api/reviews` ใส่ `rating: 10` แล้ว Execute
> จะได้ error **422** พร้อมบอกว่า field ไหนผิด โดยที่เราไม่ต้องเขียนโค้ดตรวจเอง

---

## ฐานข้อมูล — 12 ตาราง

| ตาราง | หน้าที่ |
|---|---|
| `users` | ผู้ใช้งาน (customer / owner / admin) |
| `token_blacklist` | token ที่ logout แล้ว |
| `categories` | หมวดหมู่บริการ + คำเรียกทรัพยากรที่จองได้ |
| `shops` | ร้าน / ผู้ให้บริการ พร้อมพิกัดบนแผนที่ |
| `shop_images` | รูปของร้าน (เก็บชื่อไฟล์ ตัวไฟล์อยู่บนดิสก์) |
| `services` | บริการที่เปิดให้จอง + วิธีจอง (scheduled / instant) |
| `staff` | ช่าง / คอร์ท / สนาม / พนักงานส่ง + ตารางเวลาทำงาน |
| `shop_closures` | วันที่ร้านปิดเป็นกรณีพิเศษ |
| `bookings` | การจองคิว |
| `reviews` | รีวิวหลังใช้บริการ + คำตอบจากร้าน |
| `payments` | การชำระเงิน (จำลอง) + ใบเสร็จ |
| `notifications` | แจ้งเตือนในเว็บ |

```
users (owner) ──< shops ──< services ──< bookings >── users (customer)
                    │  │       │             │
                    │  │       │             └──< payments
                    │  └──< staff >──────────┘
                    ├──────< reviews >───────┘
                    ├──────< shop_images
                    └──────< shop_closures
```

ตารางถูกสร้างอัตโนมัติตอนเริ่มระบบ พร้อมใส่ข้อมูลตัวอย่างให้ (ปิดได้โดยตั้ง `SEED_ON_START=false`)

> **การอัปเดตโครงสร้าง:** `Base.metadata.create_all()` สร้างได้แค่ตารางใหม่ แก้ตารางเดิมไม่ได้
> จึงมี `app/migrate.py` คอยเติมคอลัมน์ เงื่อนไข และดัชนีที่ขาด **โดยไม่ลบข้อมูลเดิม**
> เขียนแบบรันซ้ำกี่รอบก็ได้ผลเหมือนเดิม จึงทำงานทุกครั้งที่ระบบเริ่มต้น

### ข้อมูลตัวอย่าง — 27 ร้าน 8 หมวด

| หมวด | จำนวน | ที่มาของข้อมูล |
|---|---|---|
| ความงาม 5 หมวด | 11 ร้าน | แต่งขึ้น พร้อมรีวิวสมมติ |
| สนามฟุตบอล | 9 แห่ง | **ชื่อสมมติ** แต่พิกัด ราคา และเวลาทำการอ้างอิงสถานที่จริง |
| สนามแบดมินตัน | 5 แห่ง | เช่นเดียวกัน |
| ส่งของด่วน | 2 ศูนย์ | Bookvice Express พระราม 9 / อารีย์ |

**กฎที่ยึดไว้กับข้อมูลสถานที่**

1. ชื่อร้านทั้งหมดเป็นชื่อสมมติ — เว็บนี้เปิดสาธารณะได้ ถ้าใช้ชื่อธุรกิจจริงคู่กับปุ่มจองที่กดได้ จะกลายเป็นการแสดงว่าร้านเหล่านั้นรับจองผ่านเรา ทั้งที่เขาไม่เคยตกลงด้วย
2. ไม่ใส่เบอร์โทรจริง
3. ไม่แต่งรีวิวให้สนาม — สนามทุกแห่งเริ่มที่ 0 รีวิว
4. ใช้ได้แค่พิกัด เขต ช่วงราคาที่ประกาศ และเวลาทำการ ซึ่งเป็นข้อเท็จจริงสาธารณะ
5. ส่วนท้ายเว็บมีข้อความกำกับว่าข้อมูลเป็นตัวอย่างและการชำระเงินเป็นการจำลอง

---

## กฎทางธุรกิจที่ระบบบังคับให้

- **จองย้อนหลังไม่ได้** — ต้องเป็นวันเวลาในอนาคตเท่านั้น
- **บริการต้องเสร็จก่อนร้านปิด** — นวด 90 นาที ร้านปิด 21:00 จองได้ช้าสุด 19:30
- **หนึ่งการจองต้องจบภายในวันปฏิทินเดียวกัน** — จอง 23:30 ยาว 1 ชม. จะถูกปฏิเสธ เพราะถ้าให้คร่อมวันได้ `booking_date` จะกำกวมทันที
- **กันคิวชนแบบคาบเกี่ยว** เทียบช่วง `[เริ่ม, สิ้นสุด)` ทั้งช่วง และมี unique index ระดับฐานข้อมูลกันกรณีสองคนกดพร้อมกัน นับเฉพาะคิวที่ยังใช้งานอยู่ คิวที่ยกเลิกแล้วจึงจองซ้ำได้
- **ความจุนับจากคนที่เข้างานวันนั้นจริง** ไม่ใช่ช่างทั้งหมดที่ยังทำงานอยู่กับร้าน
- **มัดจำ 20%** คำนวณอัตโนมัติ · จ่ายมัดจำแล้วคิวเปลี่ยนเป็น confirmed ทันที
- **เงินสดรับได้เฉพาะที่ร้าน** ลูกค้ากดเองจากบ้านไม่ได้
- **รีวิวได้เมื่อใช้บริการเสร็จแล้วเท่านั้น** และรีวิวได้ครั้งเดียวต่อการจอง
- **เจ้าของร้านลบรีวิวไม่ได้** ตอบกลับได้แทน — ถ้าให้ร้านลบรีวิวที่ตัวเองไม่ชอบ ระบบรีวิวจะไม่มีความหมาย
- **แยกสิทธิ์ตาม role** ลูกค้ายกเลิกได้อย่างเดียว · เจ้าของร้านจัดการเฉพาะร้านตัวเอง · admin ทำได้ทุกอย่าง

---

## ความปลอดภัย

- รหัสผ่านเข้ารหัสด้วย **bcrypt** ไม่เก็บรหัสจริงในฐานข้อมูล
- **JWT** พร้อม blacklist — token ที่ logout แล้วใช้ต่อไม่ได้ · เปลี่ยนรหัสผ่านแล้ว token เดิมถูกยกเลิกทันที
- **Role-based access control** แยกสิทธิ์ 3 ระดับ
- ใช้ **SQLAlchemy ORM** ป้องกัน SQL Injection
- **Pydantic** ตรวจสอบข้อมูลขาเข้าทุก request
- ข้อความจากผู้ใช้ถูก escape ก่อนแสดงผลทุกจุด ป้องกัน XSS
- **นามสกุลผู้รีวิวถูกย่อเหลือตัวอักษรเดียวเสมอ** ไม่เปิดเผยนามสกุลเต็ม
- หน้าเว็บ **ตัดพิกัดผู้ใช้ออกจาก URL เสมอ** — ตำแหน่งที่อยู่ไม่ควรค้างในประวัติเบราว์เซอร์

### รูปที่อัปโหลด — ความปลอดภัย 4 ชั้น

`app/storage.py` แต่ละชั้นกันคนละอย่าง **อย่าลดชั้นไหนออก**

1. ตรวจ **ไบต์จริงต้นไฟล์** ไม่เชื่อ `Content-Type` ที่ส่งมา เพราะปลอมได้ง่าย
2. **ตั้งชื่อไฟล์ใหม่แบบสุ่ม** ทิ้งชื่อเดิมทั้งหมด (กัน `../../etc/passwd`)
3. **เข้ารหัสรูปใหม่เป็น WebP เสมอ** — สคริปต์ที่แนบท้ายไฟล์รูปหายไปพร้อม EXIF ซึ่งมีพิกัด GPS ของผู้ถ่าย
4. จำกัดขนาด 5 MB และจำกัดจำนวนพิกเซล กัน decompression bomb

---

## ระบบชำระเงิน — เป็นการจำลอง

ระบบนี้ **ไม่ได้เชื่อมต่อกับธนาคารหรือผู้ให้บริการชำระเงินจริง**
ออกแบบให้โครงสร้างข้อมูลเหมือนของจริง เพื่อให้ต่อกับ payment gateway จริงได้โดยแก้แค่ฟังก์ชัน `_mock_charge()` จุดเดียว

- `kind`: `deposit` (20%) / `balance`
- `method`: `promptpay` / `card` / `cash` — `cash` เฉพาะเจ้าของร้าน
- เลขที่ใบเสร็จ `RC-YYMM-00042` สร้างจาก `payment.id` หลัง flush จึงไม่ซ้ำแน่นอนโดยไม่ต้องล็อกตาราง

---

## รันแบบไม่ใช้ Docker (ตอน develop)

```bash
python -m venv venv
venv\Scripts\activate           # Windows
# source venv/bin/activate      # macOS / Linux

pip install -r requirements.txt

# ต้องมี PostgreSQL รันอยู่ หรือรันเฉพาะ db ด้วย Docker
docker compose up -d db

uvicorn app.main:app --reload
```

> ค่า `DATABASE_URL` สำรองใน `app/config.py` ต้องตรงกับ `DB_NAME` / `DB_USER` / `DB_PASSWORD` ใน `.env`

---

## เอกสารอื่นในโปรเจกต์

| ไฟล์ | เนื้อหา |
|---|---|
| `PROJECT_CONTEXT.md` | สถานะปัจจุบันทั้งหมด เขียนไว้ให้คนที่มารับงานต่ออ่านแล้วทำงานต่อได้ทันที |
| `TEST_CHECKLIST.md` | รายการทดสอบ พร้อมสคริปต์ยิง API จาก console |
| `DEPLOY_HUGGINGFACE.md` | คู่มือนำขึ้นเว็บสาธารณะทีละขั้น |
| `README_HF.md` | หน้าแรกของ Hugging Face Space (เปลี่ยนชื่อเป็น `README.md` ตอนอัป) |

---

## ข้อมูลโปรเจกต์

- **ชื่อระบบ:** Bookvice — จองง่าย ได้ครบ จบที่เดียว
- **รายวิชา:** 89033167 Web Application Development
- **อาจารย์ผู้สอน:** JAKAPONG BOONYAI
- **ผู้จัดทำ:** Prame
