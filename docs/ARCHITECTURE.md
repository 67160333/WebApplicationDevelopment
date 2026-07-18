# Architecture — GlowGo

## แนวคิดโดยรวม
เว็บแอปแบบ **Multi-Page Application (MPA)** ที่แต่ละหน้า = 1 ขั้นของ user journey
ไม่มี build step, ไม่มี backend — ใช้ mock data + localStorage จำลองระบบจริง

```
┌─────────────────────────────────────────────────────────┐
│                        Browser                          │
│                                                         │
│   HTML Pages (index, login, search, shop, booking...)   │
│        │                                                │
│        ▼                                                │
│   ┌──────────────┐   โหลดร่วมทุกหน้า                       │
│   │  app.js      │  → navbar, Auth, Store, toast         │
│   │  data.js     │  → mock: SHOPS, CATEGORIES, SLOTS     │
│   └──────┬───────┘                                       │
│          │ ใช้โดย                                         │
│   ┌──────▼───────────────────────────────┐              │
│   │ page scripts: search.js / shop.js /  │              │
│   │ booking.js / account.js              │              │
│   └──────┬───────────────────────────────┘              │
│          │ อ่าน/เขียนสถานะ                                │
│          ▼                                              │
│   ┌────────────────┐                                     │
│   │  localStorage  │  key = "glowgo_state"               │
│   │  { user, bookings[], points, favorites[] }           │
│   └────────────────┘                                     │
└─────────────────────────────────────────────────────────┘
```

---

## โมดูลหลัก

### `data.js` — Data Layer
เก็บ mock data ทั้งหมด: `CATEGORIES`, `ZONES`, `SHOPS` (พร้อม services + reviews), `TIME_SLOTS`
มี helper: `getShopById()`, `getCategoryName()`
> ในระบบจริงชั้นนี้จะถูกแทนด้วยการเรียก REST API

### `app.js` — Core / Shared Layer
- `Store` — อ่าน/เขียน state ใน localStorage (get/set/update)
- `Auth` — mock authentication (login, logout, requireLogin, isLoggedIn)
- `renderNav()` / `renderFooter()` — สร้าง navbar/footer ให้ทุกหน้าเหมือนกัน
- `toast()`, `money()`, `resolvePath()` — utility

### Page Scripts — Presentation/Logic Layer
แต่ละหน้ามีสคริปต์ของตัวเอง เรียกใช้ `data.js` + `app.js`:
- `search.js` — filter/sort/render รายการร้าน
- `shop.js` — render โปรไฟล์ร้าน + รีวิว
- `booking.js` — จัดการ flow การจอง + คำนวณมัดจำ + บันทึกลง Store
- `account.js` — render การจอง + แต้ม + รีวิว + จองซ้ำ

---

## Data Flow ตัวอย่าง: การจอง 1 ครั้ง
1. ผู้ใช้เลือกร้าน → `shop.html?id=s1`
2. กด "จองคิว" → `booking.html?id=s1`
   - `booking.js` เช็ก `Auth.isLoggedIn()`; ถ้ายัง → เด้งไป `login.html?next=...`
3. เลือกบริการ + วัน-เวลา → คำนวณมัดจำ 30%
4. กดยืนยัน → สร้าง object `booking` → `Store` เพิ่มลง `bookings[]` + เพิ่ม `points`
5. เด้งไป `account.html` → `account.js` อ่าน `Store` มาแสดงผล

---

## หลักการออกแบบ
- **Separation of concerns:** data / core / page-logic แยกไฟล์ชัดเจน
- **DRY:** navbar, footer, auth, money format รวมไว้ที่ `app.js` ใช้ซ้ำทุกหน้า
- **Progressive enhancement:** HTML แสดงโครงได้ก่อน JS เติมข้อมูล
- **Journey-driven:** ทุกหน้าโยงกับขั้นของ journey และแก้ pain point ที่ระบุไว้
