# รายการทดสอบรอบแก้บั๊ก + ความลื่นไหล — 19 ส.ค. 2026

รอบนี้แก้ **โค้ดฝั่งเซิร์ฟเวอร์** ด้วย จึงต้อง `--build` ไม่ใช่แค่ `Ctrl+Shift+R`
และเปลี่ยน **ชื่อโฟลเดอร์** จาก `glowgo-fastapi` เป็น `bookvice` เพื่อเก็บกวาดชื่อเก่าให้หมด

---

## 0. คำสั่งที่ต้องรัน

### 0.1 เปลี่ยนชื่อโฟลเดอร์ (ทำครั้งเดียว)

```powershell
cd "C:\Users\Prame\Claude\Projects\WORK WEBSITE UNIVERSITY\glowgo-fastapi"
docker compose down
cd ..
Rename-Item "glowgo-fastapi" "bookvice"
cd bookvice
docker compose up -d --build
```

> Compose ผูกชื่อ project กับชื่อโฟลเดอร์ พอเปลี่ยนชื่อมันจึงมองว่าเป็นโปรเจกต์ใหม่
> **จะสร้าง volume ใหม่ทั้งคู่** ฐานข้อมูลใส่ข้อมูลตัวอย่างเองอัตโนมัติภายในไม่กี่วินาที
> แต่ **รูปที่เคยอัปโหลดเองจะค้างอยู่ใน volume เก่า** ถ้ายังต้องการต้องกู้ก่อนลบ
>
> ชื่อ container ไม่เปลี่ยน เพราะ `docker-compose.yml` กำหนดไว้ตรง ๆ ว่า `bookvice-*`

เก็บกวาดของเก่าหลังยืนยันว่าเว็บใหม่ทำงานปกติแล้ว:

```powershell
docker volume rm glowgo-fastapi_db_data glowgo-fastapi_uploads_data
docker image rm glowgo-fastapi-api
```

### 0.2 รอบถัดไปใช้แค่นี้

```powershell
cd "C:\Users\Prame\Claude\Projects\WORK WEBSITE UNIVERSITY\bookvice"

docker compose up -d --build
docker compose logs api --tail 20
```

ต้องเห็นบรรทัดสุดท้ายว่า

```
Bookvice API พร้อมใช้งานที่ http://localhost:8000/docs
```

> **ทำไมต้อง `--build`** — โฟลเดอร์ `app/` ถูก COPY เข้า image ตอนสร้าง ไม่ได้ bind-mount
> ถ้ารัน `docker compose up -d` เฉย ๆ container จะยังใช้โค้ดชุดเก่าที่มีบั๊กอยู่
> ส่วน `web/` bind-mount อยู่แล้ว แค่ `Ctrl+Shift+R` ที่เบราว์เซอร์ก็พอ

รอบนี้ `app/migrate.py` มีการ **ลบ index เก่าแล้วสร้างใหม่**
(`uq_payment_booking_kind` → `uq_payment_booking_deposit`) ทำงานเองตอน API เริ่ม ไม่ต้องสั่งอะไรเพิ่ม

เลข `?v=` ของ css/js ขยับเป็น `202608252100` แล้ว เบราว์เซอร์จะโหลดชุดใหม่เองแม้กด F5 ธรรมดา

---

## 1. ทดสอบด้วยสคริปต์ (เร็วที่สุด)

เปิด `http://localhost:3000` → กด **F12** → แท็บ **Console** → วางทั้งก้อนแล้ว Enter

```js
// ---------- ตั้งต้น ----------
const B = "http://localhost:8000";
const tok = async u => (await (await fetch(B + "/api/auth/login", {
  method: "POST", headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ username: u, password: "Password123" })
})).json()).access_token;

const T = { cust: await tok("mind"), owner: await tok("spaowner"), admin: await tok("admin") };
const J = (t, m, b) => ({
  method: m || "GET",
  headers: { Authorization: "Bearer " + t, "Content-Type": "application/json" },
  ...(b ? { body: JSON.stringify(b) } : {})
});
const get = async (t, p) => (await fetch(B + p, J(t))).json();
const raw = (t, p, m, b) => fetch(B + p, J(t, m, b));

const ok = [], fail = [];
const check = (name, pass, detail = "") => (pass ? ok : fail).push(name + (detail ? ` — ${detail}` : ""));

// ---------- ก. ระบบยังทำงานปกติ (กันของเดิมพัง) ----------
const shops = (await get(T.cust, "/api/shops?limit=100")).items;
check("จำนวนร้านยังเป็น 27", shops.length === 27, `พบ ${shops.length} ร้าน`);
check("ไม่มีชื่อร้านที่ยังเป็น GlowGo", !shops.some(s => /glowgo/i.test(s.name)));

const spec = await (await fetch(B + "/openapi.json")).json();
let core = 0;
for (const [p, ops] of Object.entries(spec.paths))
  for (const m of ["get", "post", "put", "patch", "delete"])
    if (ops[m] && p.startsWith("/api/")) core++;
check("endpoint หลักครบ 56 เส้น", core === 56, `${core} เส้น`);

// tag ใน Swagger ต้องไม่มีเลขหมวดซ้ำ
const tags = [...new Set(Object.values(spec.paths).flatMap(o =>
  Object.values(o).flatMap(x => x.tags || [])))];
const nums = tags.map(t => t.split(".")[0]);
check("เลขหมวดใน Swagger ไม่ซ้ำกัน", new Set(nums).size === nums.length, tags.join(" | "));

// ---------- ข. บั๊กความปลอดภัยที่แก้รอบนี้ ----------
// 1) ผู้ใช้ทั่วไปต้องดูโปรไฟล์คนอื่นไม่ได้ (IDOR)
const me = await get(T.cust, "/api/users/me");
const other = shops[0].owner_id;
check("ดูโปรไฟล์คนอื่นไม่ได้ (ต้องได้ 403)",
      (await raw(T.cust, `/api/users/${other}`)).status === 403);
check("ดูโปรไฟล์ตัวเองได้", (await raw(T.cust, `/api/users/${me.id}`)).status === 200);
check("แอดมินยังดูได้ทุกคน", (await raw(T.admin, `/api/users/${other}`)).status === 200);

// 2) token พังต้องได้ 401 ไม่ใช่ 500
for (const bad of ["abc", "a.b.c", btoa("{}") + ".x.y"]) {
  const r = await fetch(B + "/api/users/me", { headers: { Authorization: "Bearer " + bad } });
  check(`token พัง "${bad.slice(0, 8)}" ได้ 401 ไม่ใช่ 500`, r.status === 401, `ได้ ${r.status}`);
}

// ---------- ค. บั๊กระบบจองที่แก้รอบนี้ ----------
// 3) ร้านเปิด 24 ชม. — คิวช่วงดึกต้องไม่วนกลับ
const venue = shops.find(s => s.category_slug === "football");
const vd = await get(T.cust, `/api/shops/${venue.id}`);
const svc = vd.services.find(x => x.is_active && x.booking_mode === "scheduled");
const day = new Date(Date.now() + 3 * 86400000).toISOString().slice(0, 10);
const av = await get(T.cust, `/api/services/${svc.id}/availability?date=${day}`);
check("สนามกีฬามีช่องเวลาให้จอง", av.slots.length > 0, `ว่าง ${av.available_count}/${av.slots.length}`);
check("ไม่มีช่องไหนจบที่ 00:00 (เวลาไม่วนกลับ)", !av.slots.some(s => s.end_time === "00:00:00"),
      av.slots.map(s => s.end_time).slice(-2).join(", "));

// 4) จองแล้วช่องเดิมต้องหายไปจากรายการว่าง
const free = av.slots.find(s => s.available);
let madeId = null;
if (free) {
  const r = await raw(T.cust, "/api/bookings", "POST",
    { service_id: svc.id, booking_date: day, booking_time: free.time });
  const bk = await r.json();
  if (r.ok) {
    madeId = bk.id;
    check("รหัสคิวอยู่ในรูปแบบใหม่ (กันรหัสซ้ำ)",
          /^BK\d{8}[0-9A-F]{6}$/.test(bk.booking_code), bk.booking_code);
    check("เวลาจบไม่วนกลับเป็น 00:xx", bk.end_time > bk.booking_time,
          `${bk.booking_time} → ${bk.end_time}`);
    const av2 = await get(T.cust, `/api/services/${svc.id}/availability?date=${day}`);
    check("ช่องที่เพิ่งจองหายจากรายการว่าง",
          av2.slots.find(s => s.time === free.time)?.available === false);
    const dup = await raw(T.cust, "/api/bookings", "POST",
      { service_id: svc.id, booking_date: day, booking_time: free.time });
    check("จองซ้ำช่องเดิมได้ 409", dup.status === 409, `ได้ ${dup.status}`);
  } else {
    check("จองสำเร็จ", false, `ได้ ${r.status} — ${JSON.stringify(bk).slice(0, 120)}`);
  }
}

// 5) เลื่อนนัดต้องคืนช่องเดิมและไม่ไปลบคิวคนอื่น
if (madeId) {
  const target = (await get(T.cust, `/api/services/${svc.id}/availability?date=${day}`))
    .slots.find(s => s.available && s.time !== free.time);
  if (target) {
    const rs = await raw(T.cust, `/api/bookings/${madeId}/reschedule`, "PATCH",
      { booking_date: day, booking_time: target.time });
    check("เลื่อนนัดสำเร็จ", rs.ok, `ได้ ${rs.status}`);
    const av3 = await get(T.cust, `/api/services/${svc.id}/availability?date=${day}`);
    check("ช่องเดิมกลับมาว่างหลังเลื่อน",
          av3.slots.find(s => s.time === free.time)?.available === true);
    check("ช่องใหม่ถูกจองแล้ว",
          av3.slots.find(s => s.time === target.time)?.available === false);
  }
  await raw(T.cust, `/api/bookings/${madeId}`, "DELETE"); // เก็บกวาด
}

// ---------- ง. เงินและรายงาน ----------
const ownerMe = await get(T.owner, "/api/users/me");
const shop = shops.find(s => s.owner_id === ownerMe.id);
if (shop) {
  const rev = await get(T.owner, `/api/shops/${shop.id}/revenue`);
  const recv = Number(rev.received), ref = Number(rev.refunded), net = Number(rev.net);
  check("รายรับ = สุทธิ + คืนเงิน (ไม่หักซ้ำ)", Math.abs(recv - (net + ref)) < 0.01,
        `รับ ${recv} · คืน ${ref} · สุทธิ ${net}`);
}

// ---------- สรุป ----------
console.log("%cผ่าน " + ok.length, "color:#1d7a52;font-weight:700");
ok.forEach(x => console.log("  ✓ " + x));
if (fail.length) {
  console.log("%cไม่ผ่าน " + fail.length, "color:#b3352f;font-weight:700");
  fail.forEach(x => console.log("  ✗ " + x));
} else {
  console.log("%cครบทุกข้อ", "color:#1d7a52");
}
```

**คัดลอกผลลัพธ์ทั้งหมดส่งกลับมาได้เลย** ถ้ามีข้อไหนไม่ผ่านผมจะแก้ต่อให้

> สคริปต์นี้สร้างคิวจริงหนึ่งรายการแล้วยกเลิกทิ้งเองตอนจบ
> ถ้ารันแล้วค้างกลางทาง อาจมีคิวทดสอบตกค้างในหน้า "การจองของฉัน" — ลบทิ้งได้เลย

---

## 2. ทดสอบด้วยการกดจริง

### 2.1 หน้าจัดการร้าน — แท็บ "บริการของร้าน"

**นี่คือบั๊กที่หนักที่สุดของรอบนี้** แท็บนี้เคยพังทั้งแท็บ (ขึ้นว่างเปล่า)
เพราะมีปุ่มหลงเข้าไปอยู่ผิดตำแหน่งในโค้ด ทำให้ JavaScript หยุดทำงานทั้งหน้า

1. เข้า `http://localhost:3000/manage.html` ด้วยบัญชี `spaowner`
2. กดแท็บ **บริการของร้าน** → ต้องเห็นรายการบริการ ไม่ใช่พื้นที่ว่าง
3. กดครบทั้ง 7 แท็บ (คิว · บริการ · ช่าง · รูปภาพ · วันหยุด · รายงาน · ข้อมูลร้าน) — ห้ามมีแท็บไหนว่าง
4. เปิด Console (F12) ค้างไว้ตลอด — **ต้องไม่มีข้อความสีแดง**

### 2.2 แท็บ "คิวที่จองเข้ามา" — ปุ่มพิมพ์สลิป

ปุ่ม **พิมพ์สลิป** ย้ายมาอยู่ในแถวของแต่ละคิวแล้ว
กดแล้วต้องเปิดหน้าต่างพิมพ์ที่มีรหัสคิวตรงกับแถวที่กด

ในสลิปของสนามกีฬา หัวข้อต้องเขียนว่า **"สนามผู้ให้บริการ"** ไม่ใช่ "ช่าง"
(ร้านสปาจะขึ้นว่า "ช่างผู้ให้บริการ")

### 2.3 หน้าร้าน — จังหวะกำลังโหลด

เปิด `http://localhost:3000/shop.html?id=1` แล้วดูวินาทีแรกที่หน้าเปิด

- ต้องเห็น **โครงร่างสีเทาจาง ๆ** ในตำแหน่งเดียวกับเนื้อหาจริง ไม่ใช่วงกลมหมุนอย่างเดียว
- พอข้อมูลมาถึง เนื้อหาต้องเข้ามาแทนที่ **โดยหน้าไม่กระโดด**
- ลองกด F5 รัว ๆ 5 ครั้ง — ถ้ายังเห็นหน้ากระตุกให้บอกได้ ผมจะวัดซ้ำ

### 2.4 หน้ารีวิว — ปุ่มตอบกลับ

1. เปิดหน้าร้านใด ๆ เลื่อนลงไปที่รีวิว โดยเข้าด้วยบัญชีเจ้าของร้าน
2. กด **ตอบกลับ** หนึ่งครั้ง → ต้องเปิดกล่องพิมพ์ **ครั้งเดียว**
   (ของเดิมกดแล้วเปิดซ้อนกันหลายกล่อง เพราะผูก event ทับกันทุกครั้งที่โหลดรีวิวหน้าใหม่)
3. กด **หน้าถัดไป** ของรีวิวแล้วกดตอบกลับอีกครั้ง → ยังต้องเปิดครั้งเดียวเหมือนเดิม

### 2.4.5 ตัด Tailwind CDN ออกแล้ว — ต้องดูให้ครบทุกหน้า

รอบนี้ตัด `https://cdn.tailwindcss.com` ออกจากทั้ง 10 หน้า แล้วเขียนคลาสที่ใช้จริง 123 ตัว
ลงใน `app.css` เอง หน้าเว็บจึงไม่ต้องรอโหลดอะไรจากอินเทอร์เน็ตอีก

**วิธีตรวจที่ชัดที่สุด — ตัดเน็ตแล้วเปิดเว็บ**

ปิด Wi-Fi (หรือถอดสายแลน) แล้วเปิด `http://localhost:3000` กด `Ctrl+Shift+R`
หน้าเว็บต้องขึ้นสวยเหมือนเดิมทุกประการ ของเดิมจะเละทั้งหน้า

**แล้วไล่ดูให้ครบทั้ง 10 หน้า** ว่าไม่มีอะไรเพี้ยน โดยเฉพาะ

| ดูอะไร | ต้องเป็นแบบไหน |
|---|---|
| ระยะห่างระหว่างกล่อง | เท่าเดิม ไม่ชิดกันหรือห่างผิดปกติ |
| ฟอร์มที่แบ่งสองคอลัมน์ (ละติจูด/ลองจิจูด ในหน้าจัดการร้าน) | ยังเรียงสองคอลัมน์บนจอกว้าง |
| การ์ดร้านในหน้าค้นหา | ยังเรียงเป็นกริดหลายใบต่อแถว |
| ย่อหน้าและรายการ | ไม่มีจุดดำนำหน้า ไม่มีช่องว่างบนล่างโผล่มาเอง |
| ปุ่มทุกปุ่ม | ยังเป็นปุ่มสีน้ำเงินของเรา ไม่ใช่ปุ่มเทาของ Windows |
| ย่อหน้าต่างเบราว์เซอร์ให้แคบ | ยังเปลี่ยนเป็นคอลัมน์เดียวตามปกติ |

ถ้าเจอจุดไหนเพี้ยน **แคปหน้าจอส่งมา** บอกด้วยว่าหน้าไหน ผมจะเติมคลาสที่ขาดให้
(คลาสยูทิลิตี้อยู่ท้ายไฟล์ `web/css/app.css` เพิ่มได้ตรงนั้น)

---

### 2.5 หน้าค้นหา — ค้นแล้วไม่เจอ

`http://localhost:3000/shops.html` → พิมพ์คำที่ไม่มีจริง เช่น `zzzz`
ตัวเลขด้านบนต้องเปลี่ยนเป็น **"ไม่พบร้านที่ตรงกับเงื่อนไข"**
ของเดิมค้างอยู่ที่ "กำลังค้นหา..." ตลอดไป

### 2.6 กระดิ่งแจ้งเตือน

กดกระดิ่งเปิด-ปิดสลับกัน 10 ครั้ง แล้วกดที่พื้นที่ว่างนอกกล่อง
ต้องปิดตามปกติทุกครั้ง (ของเดิมผูก event ซ้อนกันเรื่อย ๆ จนหน้าหน่วงขึ้นทุกครั้งที่กด)

---

## 3. ชุดถดถอย — รันซ้ำเพราะแตะระบบจอง

รอบนี้แก้ `app/routers/bookings.py` มากที่สุดในโปรเจกต์ ต้องตรวจว่าของเดิมยังใช้ได้

| # | ทดสอบ | ผลที่ต้องได้ |
|---|-------|-------------|
| 1 | จองสปา (มีช่าง) โดยเลือกช่างเจาะจง | ช่องที่ช่างคนนั้นไม่ว่าง ต้องกดไม่ได้ |
| 2 | จองสปาโดยไม่เลือกช่าง | ช่องจะเต็มก็ต่อเมื่อ **ช่างทุกคน** ไม่ว่าง |
| 3 | จองสนามฟุตบอลตอน 23:00 | จองได้ และคิวต้องจบภายในวันเดียวกัน |
| 4 | จองบริการส่งถึงที่ (instant) | ไม่มีปฏิทินให้เลือก จองแล้วได้ทันที |
| 5 | เลื่อนนัดไปวันที่ร้านปิด | ต้องถูกปฏิเสธพร้อมบอกเหตุผล |
| 6 | ยกเลิกคิวที่จ่ายมัดจำแล้ว | เจ้าของร้านได้แจ้งเตือน + ขึ้นสถานะรอคืนเงิน |
| 7 | เจ้าของกดคิวที่ยกเลิกแล้วกลับเป็นยืนยัน | ถ้าช่วงเวลานั้นมีคนจองไปแล้ว ต้องถูกปฏิเสธ |
| 8 | วันที่ไม่มีช่างคนไหนเข้างาน | ต้องขึ้นว่า "วันนี้ไม่มีผู้ให้บริการเข้างาน" ไม่ใช่มีช่องว่างเต็มวัน |

---

## 4. สิ่งที่ยังไม่ได้แก้ และเหตุผล

| เรื่อง | สถานะ | เหตุผล |
|-------|-------|--------|
| `JWT_SECRET` อยู่ในไฟล์ที่ commit ได้ | ยังไม่แก้ | เป็นงานส่งอาจารย์ ไม่ได้เปิดใช้จริง แก้ได้ทันทีถ้าต้องการ |
| เปลี่ยนรหัสผ่านแล้ว token เครื่องอื่นยังใช้ได้ | ยังไม่แก้ | ต้องเพิ่มคอลัมน์ในฐานข้อมูล = ต้องสร้าง volume ใหม่อีกรอบ |
| ตรวจขนาดไฟล์อัปโหลดหลังอ่านเข้าหน่วยความจำครบ | ยังไม่แก้ | มีเพดาน 5 MB คุมอยู่แล้ว ความเสี่ยงต่ำ |
| ชื่อร้าน `GlowUp Clinic สยาม` / `Glow Clinic พระราม 9` | **ตั้งใจเก็บไว้** | เป็นชื่อร้านสมมติ ไม่ใช่ชื่อแบรนด์ของระบบ |

---

## 5. ผลตรวจอัตโนมัติที่รันไปแล้ว (ไม่ต้องทำซ้ำ)

| ชุดตรวจ | ผล |
|---------|-----|
| ไวยากรณ์ JavaScript ทุกหน้า + `js/api.js` + `js/ui.js` | ผ่านครบ 12 ไฟล์ |
| ตรรกะระบบจอง 13 ข้อ (ข้ามเที่ยงคืน · กะข้ามคืน · ความจุ 0) | ผ่าน 13 · ไม่ผ่าน 0 |
| เปิดหน้าสาธารณะ 5 หน้าด้วยเบราว์เซอร์จำลอง | ไม่มี error |
| เปิดหน้าที่ต้องล็อกอิน 5 หน้า + กดครบทุกแท็บ | ไม่มี error |
| เนื้อหาค้างมองไม่เห็นหลังเลื่อนสุดหน้า (3 หน้า × หน่วง API 3 แบบ) | ไม่มีค้างสักชิ้น |
| การกระโดดของหน้าตอนโหลด (CLS) ครบทั้ง 10 หน้า | สูงสุด 0.042 — เกณฑ์ "ดี" คือต่ำกว่า 0.1 |
| เนื้อหาล้นจอแนวนอน · รูปที่ไม่ระบุขนาด · งานที่บล็อกเกิน 100ms | 0 ทุกหน้า |

**CLS ก่อน/หลังทั้ง 10 หน้า**

| หน้า | ก่อน | หลัง |
|---|---|---|
| index | 0.1209 | 0.0071 |
| shops | 0.2876 | 0.0013 |
| shop | 0.6992 | 0 |
| promotions | 0.0596 | 0 |
| login · register | 0 | 0 |
| bookings | 0.1004 | 0 |
| manage | 0.0697 | 0.0424 |
| profile | 0.2012 | 0.0048 |
| admin | 0.1677 | 0.0313 |
