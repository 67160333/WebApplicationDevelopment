"""รูปตัวอย่างของร้านสาธิต — ไฟล์อยู่ใน web/photos/ และถูก commit เข้า repo

ทำไมไม่ใช้ระบบอัปโหลดปกติ
--------------------------------------------------------------------------
Render free tier เก็บไฟล์ที่อัปโหลดไว้ใน /tmp และ **ล้างทิ้งทุกครั้งที่เครื่อง
หลับแล้วตื่น** ซึ่งเกิดขึ้นเมื่อไม่มีคนเข้าเว็บราว 15 นาที
ไม่ใช่แค่ตอน deploy อย่างที่เคยเข้าใจ

ผลคือรูปที่อัปไว้หายภายในไม่กี่ชั่วโมง คนที่เปิดลิงก์มาดูจึงเห็นการ์ดเปล่า
ทุกใบเสมอ ซึ่งเป็นสิ่งที่ทำให้เว็บดูไม่เสร็จมากที่สุด

ทางแก้: เอารูปเข้า repo ให้เป็นส่วนหนึ่งของโค้ด เสิร์ฟเป็นไฟล์นิ่งจาก
`web/photos/` — อยู่ถาวร ไม่ต้องอัปซ้ำ และไม่ต้องพึ่งบริการภายนอก

รูปทั้งหมดอยู่ภายใต้ Pexels License (ใช้ฟรี ไม่ต้องให้เครดิต แก้ไขได้)
ย่อเหลือกว้าง 1100 px แปลงเป็น WebP แล้ว รวมทั้งหมดราว 3.5 MB

ระบบอัปโหลดของเจ้าของร้านยังทำงานเหมือนเดิม รูปสองชนิดอยู่ร่วมกันได้
เพราะ `image_url()` ใน app/storage.py แยกจากรูปแบบของชื่อไฟล์
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Category, Shop, ShopImage

# ไฟล์ที่มีจริงใน web/photos/<slug>/  — สร้างจากสคริปต์ตอนย่อรูป
STOCK_PHOTOS: dict[str, list[str]] = {
    "badminton": ["01.webp", "02.webp", "03.webp", "04.webp", "05.webp", "06.webp"],
    "beauty-clinic": ["01.webp", "02.webp", "03.webp", "04.webp", "05.webp"],
    "car-care": ["01.webp", "02.webp", "03.webp", "04.webp"],
    "delivery": ["01.webp", "02.webp", "03.webp", "04.webp", "05.webp"],
    "football": ["01.webp", "02.webp", "03.webp", "04.webp", "05.webp", "06.webp", "07.webp", "08.webp"],
    "hair": ["01.webp", "02.webp", "03.webp", "04.webp", "05.webp", "06.webp"],
    "karaoke": ["01.webp", "02.webp", "03.webp", "04.webp", "05.webp"],
    "mens-clinic": ["01.webp", "02.webp", "03.webp", "04.webp", "05.webp"],
    "mobile-barber": ["01.webp", "02.webp", "03.webp", "04.webp", "05.webp"],
    "nail": ["01.webp", "02.webp", "03.webp", "04.webp", "05.webp"],
    "spa-massage": ["01.webp", "02.webp", "03.webp", "04.webp", "05.webp", "06.webp"],
    "tattoo": ["01.webp", "02.webp", "03.webp", "04.webp", "05.webp"],
}


def seed_stock_photos(db: Session) -> None:
    """ตั้งรูปปกให้ร้านที่ยังไม่มีรูปที่ใช้งานได้

    **ไม่แตะรูปที่เจ้าของร้านอัปเองและยังอยู่บนดิสก์**
    ลบเฉพาะแถวที่ชี้ไปยังไฟล์ซึ่งหายไปแล้วจริง ๆ (ตรวจจากดิสก์ ไม่ได้เดา)

    ทำสองรอบแยกกันโดยตั้งใจ
    ----------------------------------------------------------------------
    SQLAlchemy flush คำสั่ง INSERT ก่อน DELETE ภายในรอบเดียวกัน
    ถ้าลบรูปปกเก่าแล้วเพิ่มรูปปกใหม่พร้อมกัน จะชนดัชนี `uq_shop_one_cover`
    ที่บังคับว่าร้านหนึ่งมีรูปปกได้รูปเดียว จึงต้อง flush รอบลบให้จบก่อน
    """
    from app.storage import UPLOAD_ROOT

    def file_exists(shop_id: int, filename: str) -> bool:
        """รูปที่มากับโค้ดถือว่ามีเสมอ ส่วนรูปอัปโหลดต้องเช็คดิสก์จริง"""
        if filename.startswith("/"):
            return True
        return (UPLOAD_ROOT / "shops" / str(shop_id) / filename).exists()

    slug_of = {c.id: c.slug for c in db.scalars(select(Category)).all()}
    shops = db.scalars(select(Shop).order_by(Shop.id)).all()

    images_of: dict[int, list[ShopImage]] = {}
    for im in db.scalars(select(ShopImage)).all():
        images_of.setdefault(im.shop_id, []).append(im)

    # ---------- รอบที่ 1: ล้างแถวที่ไฟล์หายไปแล้ว ----------
    cleaned = 0
    for shop in shops:
        for im in images_of.get(shop.id, []):
            if not file_exists(shop.id, im.filename):
                db.delete(im)
                cleaned += 1
    if cleaned:
        db.flush()          # ต้องให้ DELETE ลงฐานข้อมูลก่อน ไม่งั้นดัชนีปกจะชน

    # ---------- รอบที่ 2: เติมรูปให้ร้านที่ไม่เหลืออะไรเลย ----------
    # แจกรูปตามลำดับร้านในหมวด ร้านที่อยู่ติดกันจะได้คนละรูป
    seen: dict[str, int] = {}
    added = 0
    for shop in shops:
        slug = slug_of.get(shop.category_id, "")
        pool = STOCK_PHOTOS.get(slug)
        if not pool:
            continue
        idx = seen.get(slug, 0)
        seen[slug] = idx + 1

        alive = [im for im in images_of.get(shop.id, [])
                 if file_exists(shop.id, im.filename)]
        if alive:
            continue

        db.add(ShopImage(
            shop_id=shop.id,
            filename=f"/photos/{slug}/{pool[idx % len(pool)]}",
            is_cover=True,
            sort_order=0,
        ))
        added += 1

    if added or cleaned:
        db.commit()
        parts = []
        if cleaned:
            parts.append(f"ล้างรูปที่ไฟล์หายไปแล้ว {cleaned} รายการ")
        if added:
            parts.append(f"ตั้งรูปปกจากรูปที่มากับโค้ดให้ร้าน {added} แห่ง")
        print(" · ".join(parts))
