# รายการรูปที่ต้องหา — เตรียมครั้งเดียวจบ

> เป้าหมาย: **หมวดละ 5 รูป รวม 60 รูป** ครอบคลุมร้านทั้ง 38 แห่ง
> สคริปต์จะแจกจ่ายให้เอง โดยหมุนลำดับไม่ให้ร้านข้าง ๆ กันได้รูปชุดเดียวกัน

---

## ⚡ ทางลัด — ไม่ต้องหารูปเองแล้ว

คัดรูปจาก Pexels ไว้ให้ครบทั้ง 12 หมวดแล้ว รายชื่ออยู่ใน **`tools/photo_urls.txt`**
สั่งคำสั่งเดียว สคริปต์จะโหลดรูปแล้วอัปเข้าร้านให้ครบทั้ง 38 แห่ง

```powershell
cd "C:\Users\Prame\Claude\Projects\WORK WEBSITE UNIVERSITY\bookvice"
python tools\upload_photos.py --fetch
```

รูปทุกรูปอยู่ภายใต้ [Pexels License](https://www.pexels.com/license/) — ใช้ฟรี ไม่ต้องให้เครดิต

> **รายการนี้คัดจากคำบรรยายภาพ ไม่ได้เปิดดูภาพจริงทีละรูป**
> บางรูปอาจเป็นภาพโคลสอัพแทนที่จะเป็นภาพบรรยากาศร้าน
> เปิดลิงก์ใน `photo_urls.txt` ดูก่อนได้ ไม่ชอบอันไหนใส่ `#` หน้าบรรทัดนั้นเพื่อข้าม

ส่วนด้านล่างนี้เก็บไว้เผื่ออยากหารูปเพิ่มเอง

---

## ใช้เว็บไหน

| เว็บ | สัญญาอนุญาต | ทำไมแนะนำ |
|---|---|---|
| **[Pexels](https://www.pexels.com/)** | ใช้ฟรี ไม่ต้องให้เครดิต แก้ไขได้ | ค้นง่าย โหลดเร็ว รูปแนวธุรกิจเยอะ |
| **[Unsplash](https://unsplash.com/)** | ใช้ฟรี ไม่ต้องให้เครดิต | คุณภาพสูง แต่แนวศิลป์กว่า |

> **อย่าเซฟรูปจาก Google Images** — ส่วนใหญ่มีลิขสิทธิ์
> เว็บนี้เปิดสาธารณะอยู่ ถ้าใช้รูปมีลิขสิทธิ์คู่กับปุ่มจองที่กดได้ จะเป็นปัญหาจริง

---

## เลือกรูปยังไงให้ดูเป็นเว็บจอง ไม่ใช่คลังภาพ

| ✅ เอา | ❌ เลี่ยง |
|---|---|
| **ภาพแนวนอน** อัตราส่วนราว 3:2 หรือ 16:9 | ภาพแนวตั้ง — การ์ดจะครอปหัวคนหาย |
| ภาพ**สถานที่จริง** เห็นบรรยากาศร้าน | ภาพโคลสอัพมือหรือของชิ้นเดียว |
| แสงธรรมชาติ โทนสงบ | ฟิลเตอร์จัดจ้าน สีสะท้อนแรง |
| ไม่มีข้อความหรือโลโก้ในภาพ | ภาพมีตัวหนังสือภาษาต่างประเทศ |
| ขนาดกลาง ๆ พอ (ราว 1200–1600 px) | ภาพ 6000 px — ระบบย่อให้อยู่แล้ว แต่อัปช้า |

ระบบจะ**ย่อให้ด้านยาวสุดไม่เกิน 1600 px และแปลงเป็น WebP ให้อัตโนมัติ**
พร้อมลบข้อมูล EXIF (ซึ่งอาจมีพิกัด GPS ติดมา) — ไม่ต้องแต่งรูปเองก่อนอัป

**ขนาดไฟล์ไม่เกิน 5 MB ต่อรูป · ร้านละไม่เกิน 8 รูป**

---

## รายการทีละหมวด

วางรูปลงโฟลเดอร์ตามชื่อในคอลัมน์แรก — โฟลเดอร์สร้างรอไว้ให้แล้วที่ `tools/photos/`

### กลุ่มความงาม (11 ร้าน)

| โฟลเดอร์ | ร้าน | คำค้นที่แนะนำ | ลิงก์ |
|---|:--:|---|---|
| `spa-massage/` | 3 | `thai spa interior` · `massage room candle` | [ค้นบน Pexels](https://www.pexels.com/search/thai%20spa%20interior/) |
| `nail/` | 3 | `nail salon interior` · `manicure studio` | [ค้นบน Pexels](https://www.pexels.com/search/nail%20salon%20interior/) |
| `hair/` | 2 | `hair salon interior` · `hairdresser studio` | [ค้นบน Pexels](https://www.pexels.com/search/hair%20salon%20interior/) |
| `beauty-clinic/` | 2 | `aesthetic clinic interior` · `dermatology clinic` | [ค้นบน Pexels](https://www.pexels.com/search/aesthetic%20clinic/) |
| `tattoo/` | 1 | `tattoo studio interior` | [ค้นบน Pexels](https://www.pexels.com/search/tattoo%20studio/) |

### กลุ่มกีฬาและบริการ (16 ร้าน)

| โฟลเดอร์ | ร้าน | คำค้นที่แนะนำ | ลิงก์ |
|---|:--:|---|---|
| `football/` | 9 | `futsal court night` · `artificial turf football pitch` | [ค้นบน Pexels](https://www.pexels.com/search/futsal%20court/) |
| `badminton/` | 5 | `badminton court indoor` | [ค้นบน Pexels](https://www.pexels.com/search/badminton%20court/) |
| `delivery/` | 2 | `delivery rider motorcycle city` | [ค้นบน Pexels](https://www.pexels.com/search/delivery%20rider/) |

> **`football/` ต้องการรูปเยอะสุด** เพราะมี 9 สนาม — ใส่สัก **6–8 รูป** จะดูหลากหลายกว่า

### กลุ่มผู้ชาย — หมวดใหม่ (11 ร้าน)

| โฟลเดอร์ | ร้าน | คำค้นที่แนะนำ | ลิงก์ |
|---|:--:|---|---|
| `mens-clinic/` | 3 | `modern medical clinic interior` · `doctor consultation room` | [ค้นบน Pexels](https://www.pexels.com/search/medical%20clinic%20interior/) |
| `mobile-barber/` | 2 | `barber cutting hair` · `barbershop tools` | [ค้นบน Pexels](https://www.pexels.com/search/barber/) |
| `car-care/` | 3 | `car detailing garage` · `car wash service` | [ค้นบน Pexels](https://www.pexels.com/search/car%20detailing/) |
| `karaoke/` | 3 | `karaoke room` · `private karaoke lounge` | [ค้นบน Pexels](https://www.pexels.com/search/karaoke/) |

> **`mens-clinic/` เลือกให้ระวัง** — เอาภาพห้องตรวจหรือเคาน์เตอร์ที่ดูสะอาดและเป็นมืออาชีพ
> **อย่าเอาภาพคนไข้หน้าตาเป็นทุกข์หรือภาพเชิงการแพทย์ที่ดูน่ากลัว**
> หมวดนี้ขายความเป็นส่วนตัวและความสบายใจ ไม่ใช่ขายโรค

---

## อัปโหลด

เมื่อรูปครบแล้ว รันจากโฟลเดอร์โปรเจกต์

```powershell
cd "C:\Users\Prame\Claude\Projects\WORK WEBSITE UNIVERSITY\bookvice"
python tools\upload_photos.py --dry-run
```

`--dry-run` จะบอกว่าร้านไหนจะได้รูปอะไรบ้าง **แต่ยังไม่อัปจริง** ดูให้พอใจแล้วค่อยรันจริง

```powershell
python tools\upload_photos.py
```

### ถ้าเครื่องไม่มี Python

รันผ่าน container แทน ได้ผลเหมือนกัน

```powershell
docker compose cp tools bookvice-api:/app/tools
docker compose exec api python /app/tools/upload_photos.py
```

### อัปขึ้นเว็บจริงบน Render

```powershell
python tools\upload_photos.py --base https://bookvice.onrender.com --password <รหัส ADMIN_PASSWORD>
```

> ⚠️ **บน Render รูปเก็บใน `/tmp` ซึ่งหายทุกครั้งที่ deploy ใหม่** ต้องอัปซ้ำทุกครั้ง
> และตอนนี้ยังไม่มี `ADMIN_PASSWORD` ใน Environment ต้องไปเพิ่มก่อน

---

## หลังอัปเสร็จ

รูปแรกของแต่ละร้านจะถูกตั้งเป็น**รูปปก**ให้อัตโนมัติ — การ์ดในหน้าแรกและหน้าค้นหาจะเปลี่ยนจาก
ภาพไล่สีที่วาดด้วยโค้ด เป็นรูปจริงทันทีโดยไม่ต้องแก้อะไรเพิ่ม

**แล้วค่อยบอกผมทำฟีเจอร์เลื่อนรูปตอนวางเมาส์** — ตอนนั้นถึงจะเห็นผลจริง
