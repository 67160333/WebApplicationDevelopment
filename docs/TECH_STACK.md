# Tech Stack — GlowGo

## ภาพรวม
โปรเจกต์ใช้เทคโนโลยีเว็บพื้นฐาน (HTML/CSS/JS ล้วน) โดยตั้งใจให้ **ไม่มี dependency ภายนอกและไม่ต้อง build** เพื่อให้เข้าใจง่าย รันได้ทุกเครื่อง และโฟกัสที่การแปลง User Journey เป็นระบบจริง

| ชั้น | เทคโนโลยี | หน้าที่ |
|---|---|---|
| โครงสร้าง | HTML5 | โครงหน้าเว็บแบบ multi-page |
| การนำเสนอ | CSS3 | design system, layout, responsive |
| ตรรกะ | JavaScript (ES6+) | การโต้ตอบ, กรองข้อมูล, จองคิว, จัดการสถานะ |
| เก็บสถานะ | Web Storage API (localStorage) | จำลอง session/ฐานข้อมูลฝั่ง client |

---

## เหตุผลการเลือก

### HTML5 (multi-page)
แต่ละขั้นของ journey = 1 หน้า ทำให้ URL สื่อความหมาย แชร์ลิงก์ตรงหน้าได้ และแมปกับ journey map ได้ตรงตัว

### CSS3 ล้วน (ไม่ใช้ framework)
- ใช้ **CSS Variables** ทำ design token (สี, รัศมี, เงา) — โทนชมพู `#C2185B` ตาม journey map
- ใช้ **Flexbox / Grid** จัด layout ที่ responsive
- ไม่พึ่ง Bootstrap/Tailwind เพื่อลดขนาดและแสดงความเข้าใจ CSS พื้นฐาน

### Vanilla JavaScript (ES6+)
- โมดูลแยกตามหน้า (`search.js`, `booking.js`, ...) + โมดูลกลาง (`app.js`, `data.js`)
- ใช้ฟีเจอร์สมัยใหม่: arrow functions, template literals, destructuring, `URLSearchParams`, `Array` methods
- ไม่ใช้ React/Vue เพื่อเลี่ยง build step และให้เห็นกลไกพื้นฐาน (DOM, event, state)

### localStorage
จำลองระบบหลังบ้าน: เก็บผู้ใช้ที่ล็อกอิน, รายการจอง และแต้มสะสม ให้ข้อมูลคงอยู่แม้รีเฟรช

---

## แนวทางต่อยอดสู่ production
ถ้าจะพัฒนาเป็นระบบจริง แนะนำ upgrade เป็น:

| ส่วน | ปัจจุบัน (เรียน) | Production ที่แนะนำ |
|---|---|---|
| Frontend | HTML/CSS/JS ล้วน | React / Next.js + TypeScript |
| State | localStorage | React Query + backend session |
| Backend | ไม่มี (mock) | Node.js + Express / NestJS |
| Database | `data.js` | PostgreSQL / MongoDB |
| Auth | mock login | OAuth (Google/LINE Login) + JWT |
| ชำระเงิน | mock | Omise / Stripe / PromptPay API |
| แจ้งเตือน | — | LINE Messaging API / Web Push |
| Deploy | เปิดไฟล์ตรง | Vercel / Netlify (FE) + Render/Railway (BE) |

---

## เครื่องมือพัฒนา
- **Editor:** VS Code
- **Version control:** Git + GitHub (public repo)
- **รันทดสอบ:** เปิดไฟล์ตรง หรือ `python -m http.server`
