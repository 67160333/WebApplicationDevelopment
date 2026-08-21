# วิธีอัปโปรเจกต์ Bookvice ขึ้น GitHub repo เดิม

repo ปลายทาง: **https://github.com/67160333/WebApplicationDevelopment**

repo นี้ตอนนี้เก็บงานเก่า (GlowGo — แปลง User Journey เป็นหน้าเว็บ static) อยู่ 1 commit
ซึ่งเป็น **โปรเจกต์เดียวกันนี่แหละ แค่เป็นรุ่นเก่ามาก** เก็บไว้คู่กันจะทำให้อาจารย์สับสนว่าอันไหนคืองานจริง
แผนคือ **ลบไฟล์เก่าออกจากหน้า repo แล้วเอาโปรเจกต์ใหม่ไว้แทน**

> **ของเก่าไม่ได้หายไปไหน** — Git เก็บทุก commit ไว้เสมอ
> commit เดิม (`707bb7e`) ยังเปิดดูได้ตลอดที่แท็บ **Insights → Network** หรือกดที่ "2 Commits"
> ถ้าอยากย้อนกลับไปดูไฟล์เก่าเมื่อไหร่ก็สั่ง `git checkout 707bb7e` ได้
> การ "ลบ" ในที่นี้คือลบออกจาก **หน้าปัจจุบัน** ของ repo เท่านั้น

> ผมรันคำสั่งพวกนี้แทนคุณไม่ได้ เพราะขั้นตอน `git push` ต้องล็อกอิน GitHub ด้วยบัญชีคุณเอง
> คัดลอกทีละก้อนไปวางใน PowerShell ได้เลย

---

## ก่อนเริ่ม — เช็กว่ามี Git ไหม

```powershell
git --version
```

- ขึ้นเลขเวอร์ชัน = พร้อมแล้ว ข้ามไปขั้นที่ 1
- ขึ้นว่าไม่รู้จักคำสั่ง = ยังไม่ได้ติดตั้ง โหลดที่ https://git-scm.com/download/win แล้วกด Next รวดเดียวจนจบ จากนั้น **ปิด PowerShell แล้วเปิดใหม่**

ถ้าเพิ่งติดตั้ง Git ครั้งแรก ตั้งชื่อกับอีเมลก่อน (จะไปแสดงเป็นชื่อคนคอมมิต)

```powershell
git config --global user.name "Prame"
git config --global user.email "ttmttsbaris@gmail.com"
```

---

## ขั้นที่ 1 — ดึง repo เดิมลงมา

```powershell
cd "C:\Users\Prame\Claude\Projects\WORK WEBSITE UNIVERSITY"
git clone https://github.com/67160333/WebApplicationDevelopment.git repo-upload
cd repo-upload
```

ตอนนี้จะได้โฟลเดอร์ `repo-upload` ที่มีงานเก่าอยู่ข้างใน

---

## ขั้นที่ 2 — ล้างไฟล์เก่าออก

```powershell
Get-ChildItem -Force | Where-Object { $_.Name -ne '.git' } | Remove-Item -Recurse -Force
```

บรรทัดนี้ลบทุกอย่างในโฟลเดอร์ **ยกเว้น `.git`** ซึ่งเป็นที่เก็บประวัติทั้งหมด
ห้ามลบ `.git` เด็ดขาด ไม่งั้นจะกลายเป็นโฟลเดอร์ธรรมดาที่ push ไม่ได้

เช็กว่าเหลือแต่ `.git` จริง

```powershell
Get-ChildItem -Force
```

ต้องเห็นบรรทัดเดียวคือ `.git`

> ลบตรงนี้ปลอดภัย เพราะเป็นแค่สำเนาที่เพิ่ง clone ลงมาเมื่อกี้
> ของจริงยังอยู่บน GitHub และในประวัติ Git ครบทุกไฟล์

---

## ขั้นที่ 3 — คัดลอกโปรเจกต์ใหม่เข้ามา

```powershell
robocopy "..\bookvice" . /E /XD .git __pycache__ /XF .env
```

> **robocopy จะขึ้นตัวเลขสรุปตอนจบ ไม่ใช่ error** เลข 0-7 ถือว่าสำเร็จทั้งหมด
> `/XD` = ไม่เอาโฟลเดอร์ `.git` กับ `__pycache__` · `/XF .env` = **ไม่เอาไฟล์ `.env`**

**ทำไมต้องกัน `.env`** — ในนั้นมีรหัสผ่านฐานข้อมูลและ `JWT_SECRET` ถ้าหลุดขึ้น GitHub
คนอื่นปลอมเป็นผู้ใช้คนไหนก็ได้ในระบบ ไฟล์ `.gitignore` กันไว้อีกชั้นแล้ว แต่กันสองชั้นปลอดภัยกว่า
ส่วน `.env.example` ที่ไม่มีรหัสจริงจะขึ้นไปด้วย ซึ่งถูกต้อง — คนโหลดไปใช้จะได้รู้ว่าต้องตั้งค่าอะไรบ้าง

### เช็กก่อนคอมมิตว่าไม่มีอะไรหลุด

```powershell
git status
git status --short | Select-String "\.env$"
```

บรรทัดที่สอง **ต้องไม่ขึ้นอะไรเลย** ถ้าขึ้นมาแปลว่า `.env` กำลังจะถูกอัป — หยุดแล้วบอกผม

---

## ขั้นที่ 4 — คอมมิตและอัปขึ้น

```powershell
git add -A
git commit -m "Bookvice: REST API + Docker Compose

- FastAPI + PostgreSQL 16 จัดการด้วย Docker Compose 4 container
- 56 เส้นทาง API ครอบคลุมครบตามใบงาน (register/login/logout/change-password,
  me/users/check-username พร้อม pagination)
- หน้าเว็บใช้งานจริงครบ 10 หน้า ไม่พึ่ง CDN ภายนอก
- แทนที่รุ่นเก่า (GlowGo static site) ทั้งหมด — ของเดิมยังดูได้จากประวัติ commit"
git push
```

ตอนกด `git push` เบราว์เซอร์จะเด้งให้ล็อกอิน GitHub — **ล็อกอินด้วยบัญชี `67160333` ของคุณเอง**
ล็อกอินครั้งเดียว ครั้งต่อไปไม่ต้องแล้ว

---

## ขั้นที่ 5 — เช็กผลบนเว็บ

เปิด https://github.com/67160333/WebApplicationDevelopment แล้วดูว่า

- [ ] หน้าแรกขึ้น README ของ **Bookvice** (มีตาราง "ตรวจตามใบงาน — ครบทั้ง 10 เส้นทาง")
- [ ] มีโฟลเดอร์ `app/` และ `web/` — **ไม่มี `css/` `js/` `pages/` `index.html` ของเก่าแล้ว**
- [ ] มีไฟล์ `docker-compose.yml` · `Dockerfile` · `requirements.txt`
- [ ] **ไม่มีไฟล์ `.env`** (ต้องมีแต่ `.env.example`)
- [ ] แถบ Languages เปลี่ยนเป็น Python เป็นหลัก
- [ ] ตรงหัวตารางไฟล์ขึ้นว่า **2 Commits** (commit เก่ายังอยู่)

จากนั้นกดรูปเฟือง **About** มุมขวาบน แล้วใส่คำอธิบายสั้น ๆ เช่น

```
Bookvice — ระบบจองคิวบริการ · FastAPI + PostgreSQL + Docker Compose · 89033167 Web Application Development
```

ช่วยให้อาจารย์เห็นตั้งแต่บรรทัดแรกว่าโปรเจกต์คืออะไร

---

## ขั้นที่ 6 — ลบโฟลเดอร์ชั่วคราวทิ้ง

หลังจากเช็กบนเว็บแล้วว่าขึ้นครบ

```powershell
cd "C:\Users\Prame\Claude\Projects\WORK WEBSITE UNIVERSITY"
Remove-Item repo-upload -Recurse -Force
```

โฟลเดอร์ `bookvice` ที่ใช้พัฒนาอยู่ยังอยู่ครบเหมือนเดิม ไม่ได้ถูกแตะเลย

---

## เรื่องที่ควรแก้บน GitHub ด้วย

README เก่าเขียนว่า **"นางสาวชลณิศ · รหัส 3,68160001"** แต่บัญชี repo คือ `67160333`

พอลบของเก่าออก ชื่อนั้นจะหายไปด้วย และ README ใหม่ **ยังไม่มีหัวข้อผู้จัดทำเลย**
โจทย์เป็นงานกลุ่ม อาจารย์น่าจะอยากเห็นว่าใครทำบ้าง

**บอกผมว่าจะให้ใส่ชื่อใครกับรหัสอะไรบ้าง เดี๋ยวผมเขียนหัวข้อ "ผู้จัดทำ" เพิ่มให้ก่อน push**

---

## ถ้าติดปัญหา

| อาการ | ทำอย่างไร |
|---|---|
| `git: command not found` | ยังไม่ได้ติดตั้ง Git หรือยังไม่ได้ปิด-เปิด PowerShell ใหม่ |
| `Authentication failed` | ล็อกอินผิดบัญชี — สั่ง `git credential-manager delete https://github.com` แล้ว push ใหม่ |
| `Updates were rejected` | มีคนแก้ repo บนเว็บหลังจากคุณ clone — สั่ง `git pull --rebase` แล้ว `git push` อีกครั้ง |
| `fatal: not a git repository` | ยังไม่ได้ `cd repo-upload` |
| ลบไฟล์ผิดโฟลเดอร์ | ถ้าเผลอลบใน `bookvice` แทน `repo-upload` บอกผมทันที ผมมีไฟล์ทุกตัวอยู่ ส่งคืนให้ได้ |

ติดตรงไหนคัดลอกข้อความที่ขึ้นมาส่งให้ผมดูได้เลยครับ
