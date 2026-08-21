# นำเว็บขึ้นสาธารณะด้วย Render.com

เป้าหมาย: ได้ลิงก์ที่อาจารย์เปิดจากที่ไหนก็ได้ เช่น `https://bookvice.onrender.com`

**ทำไมเลือก Render** — ยังมีแพ็กเกจฟรีจริงในปี 2026 รองรับ Docker และที่สำคัญคือ
**ดึงโค้ดจาก GitHub มา build ให้เอง** ซึ่งตรงกับโจทย์ "base on GitHub" พอดี
ทุกครั้งที่ push โค้ดใหม่ เว็บสาธารณะจะอัปเดตตามอัตโนมัติ

> **อันนี้เป็นของแถม ไม่ใช่ตัวหลัก** — ตอนนำเสนอยังต้องเดโมด้วย `docker compose`
> ในเครื่อง เพราะโจทย์ให้ใช้ Docker Compose จัดการ container ซึ่งของเราแยก 4 ตัว
> ส่วนบน Render รวมเป็น container เดียว (ผู้ให้บริการฟรีรันได้ตัวเดียว)

---

## ภาพรวม 3 ส่วน

| ส่วน | ใช้อะไร | ทำไม |
|---|---|---|
| ฐานข้อมูล | **Neon** (ฟรี) | Render ให้ PostgreSQL ฟรีแค่ 30 วัน ใช้ Neon ยาวกว่า |
| ตัวเว็บ + API | **Render** (ฟรี) | build จาก GitHub อัตโนมัติ |
| โค้ด | **GitHub** repo เดิม | ไม่ต้องอัปไฟล์เอง Render ดึงเอง |

---

## ขั้นที่ 0 — push โค้ดล่าสุดขึ้น GitHub ก่อน

Render จะ build จากสิ่งที่อยู่บน GitHub ถ้าไม่ push ก่อน มันจะได้โค้ดชุดเก่า

```powershell
cd "C:\Users\Prame\Claude\Projects\WORK WEBSITE UNIVERSITY"
git clone https://github.com/67160333/WebApplicationDevelopment.git repo-upload
cd repo-upload
Get-ChildItem -Force | Where-Object { $_.Name -ne '.git' } | Remove-Item -Recurse -Force
robocopy "..\bookvice" . /E /XD .git __pycache__ hf-upload /XF .env
git add -A
git commit -m "รองรับการ deploy บน Render (อ่านพอร์ตจาก PORT)"
git push
```

เช็กว่าไม่มี `.env` ติดไปก่อน commit เสมอ

```powershell
git status --short | Select-String "\.env$"
```

**ต้องไม่ขึ้นอะไรเลย**

> สังเกตว่ามี `hf-upload` เพิ่มใน `/XD` — โฟลเดอร์นั้นเป็นสำเนาซ้ำของ `app/` กับ `web/`
> ไม่ต้องเอาขึ้น GitHub ให้รก

---

## ขั้นที่ 1 — ฐานข้อมูลจาก Neon

1. เข้า **https://neon.tech** → Sign up (ใช้ GitHub ล็อกอินได้)
2. **Create project** → ตั้งชื่อ `bookvice` → เลือก region **Asia Pacific (Singapore)**
   *เลือกสิงคโปร์เพราะใกล้ไทยที่สุด เว็บจะตอบเร็วกว่าเลือกอเมริกาหลายเท่า*
3. คัดลอก **Connection string** เก็บไว้

ต้องหน้าตาแบบนี้ ลงท้ายด้วย `?sslmode=require`

```
postgresql://ชื่อผู้ใช้:รหัสผ่าน@ep-xxxx.ap-southeast-1.aws.neon.tech/neondb?sslmode=require
```

> **อย่าวางสตริงนี้ลงในไฟล์ใด ๆ ในโปรเจกต์ และอย่าส่งให้ใคร**
> ในนั้นมีรหัสผ่านฐานข้อมูล เดี๋ยวเอาไปใส่ในช่องตั้งค่าของ Render โดยตรง
> ถ้าเผลอหลุดออกไปแล้ว ให้เข้า Neon → Roles → Reset password ทันที

---

## ขั้นที่ 2 — สร้าง Web Service บน Render

1. เข้า **https://render.com** → Sign up **ด้วย GitHub** (สำคัญ จะได้เชื่อม repo ได้เลย)
2. กด **New +** → **Web Service**
3. เลือก repo **WebApplicationDevelopment** → กด **Connect**

### กรอกค่าตามนี้

| ช่อง | ใส่อะไร |
|---|---|
| Name | `bookvice` |
| Region | **Singapore** |
| Branch | `main` |
| **Language / Runtime** | **Docker** |
| **Dockerfile Path** | **`./Dockerfile.hf`** |
| Instance Type | **Free** |

> **`Dockerfile Path` คือช่องที่พลาดกันบ่อยที่สุด**
> ถ้าปล่อยว่าง Render จะใช้ `Dockerfile` ตัวหลัก ซึ่งเป็นตัวสำหรับ Docker Compose
> มันจะรันแต่ API ไม่เสิร์ฟหน้าเว็บ และหาฐานข้อมูลไม่เจอ

---

## ขั้นที่ 3 — ใส่ค่าตั้งต้น (Environment Variables)

เลื่อนลงไปที่ **Environment Variables** → กด **Add Environment Variable** ทีละตัว

| Key | Value |
|---|---|
| `DATABASE_URL` | สตริงจาก Neon ที่คัดลอกไว้ (ทั้งเส้น) |
| `JWT_SECRET` | ข้อความยาว ๆ ที่คิดเอง เช่น `bookvice_2026_prame_secret_key_x9f2` |
| `SERVE_WEB` | `true` |
| `SEED_ON_START` | `true` |
| `UPLOAD_DIR` | `/tmp/uploads` |

จากนั้นกด **Deploy Web Service**

> `SERVE_WEB=true` กับ `UPLOAD_DIR` มีอยู่ใน Dockerfile แล้ว แต่ใส่ซ้ำไว้ไม่เสียหาย
> และช่วยให้เห็นชัดว่าระบบตั้งค่าอะไรไว้บ้าง

---

## ขั้นที่ 4 — รอ build แล้วดู Logs

ใช้เวลาราว 3-7 นาที ดูที่แท็บ **Logs**

**สัญญาณว่าสำเร็จ** ต้องเห็นตามลำดับนี้

```
เชื่อมต่อฐานข้อมูลสำเร็จ
กำลังใส่ข้อมูลตัวอย่าง...
เพิ่มสนามและศูนย์บริการ 16 แห่ง
เสิร์ฟหน้าเว็บจาก /app/web
Bookvice API พร้อมใช้งาน
```

แล้วเปิดลิงก์ที่ Render ให้มา — จะอยู่มุมบนซ้ายของหน้า service

| | |
|---|---|
| หน้าเว็บ | `https://bookvice.onrender.com` |
| เอกสาร API | `https://bookvice.onrender.com/docs` |
| ตรวจสถานะ | `https://bookvice.onrender.com/health` |

ลองล็อกอิน `mind` / `Password123` แล้วจองคิวหนึ่งครั้ง ถ้าผ่าน = เสร็จแล้ว

**หลัง deploy ครั้งแรกสำเร็จ ให้เปลี่ยน `SEED_ON_START` เป็น `false`**
(Environment → แก้ค่า → Save) ไม่งั้นทุกครั้งที่รีสตาร์ตจะพยายามใส่ข้อมูลซ้ำ

---

## ข้อจำกัดที่ต้องรู้ก่อนวันนำเสนอ

| เรื่อง | รายละเอียด | รับมือยังไง |
|---|---|---|
| **เซิร์ฟเวอร์หลับ** | ไม่มีคนใช้ 15 นาทีจะหลับ ปลุกใหม่ใช้เวลา 30-50 วินาที | **เปิดลิงก์ทิ้งไว้ 5 นาทีก่อนถึงคิว** |
| **ฐานข้อมูลก็หลับ** | Neon ตัวฟรีพักการทำงานเมื่อไม่มีใครใช้ | เปิดเว็บให้มันตื่นพร้อมกันไปเลย |
| **รูปที่อัปโหลดหาย** | เก็บใน `/tmp` ซึ่งหายทุกครั้งที่ deploy ใหม่ | ใช้เดโมพอ อย่าใช้เก็บของจริง |
| RAM 512 MB | พอสำหรับงานนี้ | ไม่ต้องทำอะไร |

---

## แก้ปัญหาที่พบบ่อย

| อาการใน Logs | สาเหตุ | แก้ยังไง |
|---|---|---|
| `no such file or directory: Dockerfile.hf` | ยังไม่ได้ push โค้ดล่าสุด หรือพิมพ์ path ผิด | ทำขั้นที่ 0 ให้ครบ แล้วเช็กว่าเป็น `./Dockerfile.hf` |
| `could not translate host name` | `DATABASE_URL` ผิดหรือคัดลอกไม่ครบ | คัดลอกใหม่ทั้งเส้น อย่าให้มีเว้นวรรคหรือขึ้นบรรทัดใหม่ |
| `SSL connection has been closed` | ลืม `?sslmode=require` ท้ายสตริง | เติมต่อท้ายแล้ว Save |
| `Port scan timeout` | แอปไม่ได้ฟังพอร์ตที่ Render กำหนด | ต้องใช้ `Dockerfile.hf` ตัวล่าสุดที่อ่านค่า `PORT` |
| หน้าเว็บขึ้นแต่ข้อมูลไม่มา | `SERVE_WEB` ไม่ได้ตั้ง หรือฐานข้อมูลต่อไม่ติด | ดู Logs ว่ามีบรรทัด `เชื่อมต่อฐานข้อมูลสำเร็จ` ไหม |
| ขึ้น 502 ตอนเปิดครั้งแรก | เซิร์ฟเวอร์กำลังตื่น | รอ 30-50 วินาทีแล้วรีเฟรช |

---

## หลัง deploy เสร็จ ควรทำอีกสองอย่าง

**1. ใส่ลิงก์ไว้ในหน้า GitHub** — กดรูปเฟือง **About** มุมขวาบนของ repo
แล้วใส่ลิงก์ในช่อง **Website** อาจารย์เปิด repo มาจะเห็นปุ่มลิงก์ทันที

**2. เขียนไว้ใน README** — เพิ่มบรรทัดบนสุด

```markdown
> 🌐 **เปิดใช้งานจริงได้ที่** https://bookvice.onrender.com
> (เซิร์ฟเวอร์ฟรีจะหลับเมื่อไม่มีคนใช้ เปิดครั้งแรกอาจรอ 30-50 วินาที)
```

วงเล็บบรรทัดล่างสำคัญ — ถ้าอาจารย์เปิดแล้วช้าโดยไม่รู้สาเหตุ จะเข้าใจผิดว่าเว็บมีปัญหา
