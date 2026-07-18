# วิธีอัป GitHub และส่งงาน — GlowGo

## ขั้นที่ 1: ทดสอบว่าเว็บรันได้ (ก่อนอัป)
เปิดไฟล์ `index.html` ด้วยเบราว์เซอร์ (ดับเบิลคลิก) แล้วลองกดใช้งานตาม flow:
หน้าแรก → เลือกหมวด → เข้าร้าน → จองคิว → เข้าสู่ระบบ → จ่ายมัดจำ → ดูการจอง/แต้ม

> แนะนำรันผ่าน local server เพื่อให้เหมือนจริง: เปิด Terminal ในโฟลเดอร์ `glowgo` แล้วสั่ง
> `python -m http.server 8000` จากนั้นเปิด http://localhost:8000

---

## ขั้นที่ 2: สร้าง repo บน GitHub
1. ไปที่ https://github.com/new
2. ตั้งชื่อ repo เช่น `glowgo-user-journey`
3. เลือก **Public**
4. **อย่า** ติ๊ก "Add a README" (เพราะเรามีไฟล์อยู่แล้ว)
5. กด **Create repository** — คัดลอก URL ที่ได้ เช่น
   `https://github.com/<username>/glowgo-user-journey.git`

---

## ขั้นที่ 3: push โค้ดขึ้น GitHub
เปิด Terminal / Git Bash ในโฟลเดอร์ `glowgo` แล้วสั่งทีละบรรทัด
(แทน `<username>` และชื่อ repo ให้ตรงกับของตัวเอง):

```bash
git init
git add .
git commit -m "GlowGo: แปลง User Journey เป็น source code + docs"
git branch -M main
git remote add origin https://github.com/<username>/glowgo-user-journey.git
git push -u origin main
```

ถ้า push แล้วถามรหัส ให้ใช้ **Personal Access Token** แทนรหัสผ่าน
(GitHub → Settings → Developer settings → Personal access tokens → Generate)

---

## ขั้นที่ 4: ตรวจว่าขึ้นครบ
เปิดหน้า repo บน GitHub ควรเห็น: `index.html`, โฟลเดอร์ `css/ js/ pages/ docs/`, `README.md`
README จะแสดงรายละเอียดโปรเจกต์อัตโนมัติด้านล่างหน้า repo

---

## ขั้นที่ 5: ส่งลิงก์เข้า Google Classroom
1. คัดลอก URL หน้า repo เช่น `https://github.com/<username>/glowgo-user-journey`
2. เปิดงานใน Google Classroom → **เพิ่มไฟล์แนบ → ลิงก์** → วาง URL
3. กด **ส่ง / Turn in**

---

## เช็กลิสต์ตามโจทย์
- [x] แปลง user journey → source code พร้อม DOCS
- [x] จัดโครงสร้างเป็นระบบ + ระบุ tech stack (ดู `docs/`)
- [ ] อัป source code ขึ้น GitHub (Public) — ทำตามขั้น 2-3
- [ ] ส่งลิงก์ GitHub เข้า Google Classroom — ทำตามขั้น 5
