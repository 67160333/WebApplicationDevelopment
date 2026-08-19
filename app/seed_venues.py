"""เติมสนามกีฬาและบริการส่งของด่วน

**ชื่อสนามทั้งหมดในไฟล์นี้เป็นชื่อสมมติ** ไม่ใช่ชื่อธุรกิจที่มีอยู่จริง

แต่ **พิกัด เขต ช่วงราคา และเวลาทำการ อ้างอิงจากสถานที่จริง**
เพื่อให้ทดสอบระบบแผนที่ การคำนวณระยะทาง และการจองข้ามเที่ยงคืน
กับข้อมูลที่สมจริงได้ — เช่น สนามที่เปิดถึงตี 2 หรือเปิด 24 ชั่วโมง

เหตุผลที่ต้องใช้ชื่อสมมติ:
  เว็บนี้เปิดสาธารณะได้ ถ้าใช้ชื่อธุรกิจจริงคู่กับปุ่ม "จองคิว" ที่กดได้
  จะกลายเป็นการแสดงว่าร้านเหล่านั้นรับจองผ่านเรา ทั้งที่เขาไม่เคยตกลงด้วย
  และอาจมีคนหลงจองแล้วเดินทางไปถึงหน้าร้านจริง

ด้วยเหตุผลเดียวกัน ไฟล์นี้จึงไม่ใส่เบอร์โทรและไม่สร้างรีวิวให้สนามเหล่านี้

ราคาที่ใส่เป็น "ราคาต่ำสุดของช่วงที่ประกาศ" เพราะราคาจริงแปรผันตามช่วงเวลา
"""

from datetime import time
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Category, Service, Shop, Staff, User
from app.security import hash_password

# ---------------- หมวดหมู่ใหม่ ----------------
# (slug, ชื่อที่แสดง, คำเรียกสิ่งที่จองได้)
NEW_CATEGORIES: list[tuple[str, str, str]] = [
    ("football", "สนามฟุตบอล", "สนาม"),
    ("badminton", "สนามแบดมินตัน", "คอร์ท"),
    ("delivery", "ส่งของด่วน", "พนักงานส่ง"),
]

# คำเรียกของหมวดเดิม — เดิมทุกหมวดใช้คำว่า "ช่าง" ซึ่งถูกอยู่แล้ว
EXISTING_LABELS = {
    "spa-massage": "ช่าง",
    "nail": "ช่าง",
    "hair": "ช่าง",
    "beauty-clinic": "แพทย์/ผู้ดูแล",
    "tattoo": "ช่างสัก",
}

# ---------------- สนามฟุตบอล ----------------
# (ชื่อ, เขต, ที่อยู่ย่อ, ละติจูด, ลองจิจูด, เปิด, ปิด, ราคาต่ำสุด, จำนวนสนาม)
# พิกัดมาจากหมุด Google Maps ที่แหล่งข้อมูลอ้างอิงไว้
FOOTBALL: list[tuple] = [
    ("สนามฟุตบอล ทองหล่อ อารีนา", "วัฒนา", "ซอยทองหล่อ 10 ถนนสุขุมวิท 55",
     13.731724, 100.584855, time(9, 0), time(0, 0), 1500, 3),
    ("สนามเลียบด่วน ฟุตบอลคลับ", "วังทองหลาง", "ถนนประดิษฐ์มนูธรรม (เลียบทางด่วนรามอินทรา)",
     13.794010, 100.611076, time(6, 0), time(2, 0), 750, 3),
    ("สนามรามคำแหง คิกออฟ", "วังทองหลาง", "ซอยรามคำแหง 39 ใกล้แยกเหม่งจ๋าย",
     13.776453, 100.602300, time(0, 0), time(0, 0), 1300, 4),
    ("สนามรัชดา สปอร์ตคลับ", "ห้วยขวาง", "ซอยประชาราษฎร์บำเพ็ญ 18 ย่านรัชดา",
     13.783687, 100.586459, time(10, 0), time(0, 0), 600, 6),
    ("สนามเสือใหญ่ ฟุตบอลพาร์ค", "จตุจักร", "ซอยรัชดาภิเษก 36 (ซอยเสือใหญ่อุทิศ)",
     13.822911, 100.580745, time(8, 0), time(0, 0), 600, 3),
    ("สนามวิภาวดี กรีนฟิลด์", "จตุจักร", "ซอยวิภาวดี 50 ใกล้โรงพยาบาลวิภาวดี",
     13.844313, 100.561619, time(13, 0), time(0, 0), 600, 2),
    ("สนามประดิษฐ์มนูธรรม ยูไนเต็ด", "ลาดพร้าว", "ถนนประดิษฐ์มนูธรรม",
     13.804049, 100.608817, time(8, 30), time(0, 0), 1300, 3),
    ("สนามพระราม 9 สปอร์ติ้ง", "ห้วยขวาง", "ซอยวัดพระราม 9 (ซอย 19)",
     13.758643, 100.592536, time(9, 0), time(2, 0), 700, 2),
    ("สนามประเสริฐมนูกิจ โกลคลับ", "บึงกุ่ม", "ซอยประเสริฐมนูกิจ 24",
     13.822601, 100.628249, time(0, 0), time(0, 0), 600, 3),
]

# บริการของสนามฟุตบอล — (ชื่อ, บวกจากราคาฐาน, นาที)
FOOTBALL_SERVICES: list[tuple[str, int, int]] = [
    ("เช่าสนาม 1 ชั่วโมง", 0, 60),
    ("เช่าสนาม 1 ชั่วโมงครึ่ง", 500, 90),
    ("เช่าสนาม 2 ชั่วโมง", 900, 120),
]

# ---------------- สนามแบดมินตัน ----------------
# (ชื่อ, เขต, ที่อยู่ย่อ, ละติจูด, ลองจิจูด, เปิด, ปิด, ราคาต่อชั่วโมง, จำนวนคอร์ท)
BADMINTON: list[tuple] = [
    ("คอร์ทแบด สยามสแควร์", "ปทุมวัน", "ปทุมวันปริ๊นเซส ชั้น 8 ศูนย์การค้า MBK",
     13.744900, 100.529700, time(10, 0), time(22, 0), 280, 6),
    ("คอร์ทแบด สวนผัก", "ตลิ่งชัน", "ซอยสวนผัก 29",
     13.786900, 100.443800, time(9, 0), time(23, 0), 160, 8),
    ("คอร์ทแบด นวลจันทร์", "บึงกุ่ม", "ซอยนวลจันทร์ 56",
     13.816700, 100.646900, time(9, 0), time(23, 0), 170, 6),
    ("คอร์ทแบด รามอินทรา", "บางเขน", "ซอยรามอินทรา 31",
     13.855800, 100.630600, time(8, 0), time(0, 0), 250, 10),
    ("คอร์ทแบด พหลโยธิน", "จตุจักร", "ใกล้ MRT พหลโยธิน",
     13.813900, 100.560300, time(9, 0), time(23, 0), 180, 8),
]

BADMINTON_SERVICES: list[tuple[str, int, int]] = [
    ("เช่าคอร์ท 1 ชั่วโมง", 1, 60),      # ตัวคูณของราคาต่อชั่วโมง
    ("เช่าคอร์ท 2 ชั่วโมง", 2, 120),
    ("เช่าคอร์ท 3 ชั่วโมง", 3, 180),
]

# ---------------- บริการส่งของด่วน ----------------
# (ชื่อ, เขตที่ตั้งศูนย์, ละติจูด, ลองจิจูด, ค่าเริ่มต้น, ค่าต่อกิโลเมตร, จำนวนคนส่ง)
DELIVERY: list[tuple] = [
    ("Bookvice Express พระราม 9", "ห้วยขวาง", 13.758500, 100.565500, 25, 8, 12),
    ("Bookvice Express อารีย์", "พญาไท", 13.779800, 100.544600, 25, 8, 8),
]

DELIVERY_SERVICES: list[tuple[str, int, int, int, int]] = [
    # (ชื่อ, ค่าเริ่มต้น, ค่าต่อกม., นาทีโดยประมาณ, —)
    ("ส่งเอกสารและของชิ้นเล็ก", 25, 8, 45, 0),
    ("ส่งพัสดุขนาดกลาง", 40, 10, 60, 0),
    ("ส่งของด่วนพิเศษ ภายใน 1 ชั่วโมง", 80, 14, 60, 0),
]


def _venue_owner(db: Session) -> User:
    """บัญชีเจ้าของสำหรับสนามและศูนย์ส่งของ แยกจากเจ้าของร้านความงาม"""
    owner = db.scalar(select(User).where(User.username == "venueowner"))
    if owner is None:
        owner = User(
            username="venueowner",
            email="venue@example.com",
            password_hash=hash_password("Password123"),
            full_name="ผู้ดูแลสนามและศูนย์ส่งของ",
            role="owner",
        )
        db.add(owner)
        db.flush()
    return owner


def seed_venues(db: Session) -> None:
    """เติมหมวดใหม่ สนามจริง และบริการส่งของ — รันซ้ำได้ไม่เกิดข้อมูลซ้ำ"""

    # ---------- หมวดหมู่ ----------
    for slug, name, label in NEW_CATEGORIES:
        cat = db.scalar(select(Category).where(Category.slug == slug))
        if cat is None:
            db.add(Category(name=name, slug=slug, resource_label=label))
        elif cat.resource_label != label:
            cat.resource_label = label

    # เติมคำเรียกให้หมวดเดิมที่สร้างไว้ก่อนระบบจะมีฟิลด์นี้
    for slug, label in EXISTING_LABELS.items():
        cat = db.scalar(select(Category).where(Category.slug == slug))
        if cat is not None and cat.resource_label != label:
            cat.resource_label = label

    db.flush()
    cats = {c.slug: c for c in db.scalars(select(Category)).all()}
    owner = _venue_owner(db)
    added = 0

    # ---------- สนามฟุตบอล ----------
    for name, district, address, lat, lng, open_t, close_t, base, courts in FOOTBALL:
        if db.scalar(select(Shop).where(Shop.name == name)):
            continue
        shop = Shop(
            owner_id=owner.id, category_id=cats["football"].id, name=name,
            description=(
                f"สนามฟุตบอลหญ้าเทียม {courts} สนาม ย่าน{district} "
                "มีห้องอาบน้ำ ที่จอดรถ และอุปกรณ์ให้เช่า"
            ),
            address=address, district=district,
            latitude=Decimal(f"{lat:.6f}"), longitude=Decimal(f"{lng:.6f}"),
            open_time=open_t, close_time=close_t,
        )
        db.add(shop)
        db.flush()

        for label, extra, minutes in FOOTBALL_SERVICES:
            db.add(Service(
                shop_id=shop.id, name=label,
                price=Decimal(str(base + extra)), duration_minutes=minutes,
            ))
        # แต่ละสนามคือทรัพยากรที่จองแยกกันได้ ใช้ตาราง staff เดิมเก็บ
        for i in range(1, courts + 1):
            db.add(Staff(shop_id=shop.id, name=f"สนาม {i}", position="สนามหญ้าเทียม"))
        added += 1

    # ---------- สนามแบดมินตัน ----------
    for name, district, address, lat, lng, open_t, close_t, rate, courts in BADMINTON:
        if db.scalar(select(Shop).where(Shop.name == name)):
            continue
        shop = Shop(
            owner_id=owner.id, category_id=cats["badminton"].id, name=name,
            description=(
                f"สนามแบดมินตันในร่ม {courts} คอร์ท ย่าน{district} "
                f"ค่าคอร์ทเริ่มต้น {rate} บาทต่อชั่วโมง"
            ),
            address=address, district=district,
            latitude=Decimal(f"{lat:.6f}"), longitude=Decimal(f"{lng:.6f}"),
            open_time=open_t, close_time=close_t,
        )
        db.add(shop)
        db.flush()

        for label, hours, minutes in BADMINTON_SERVICES:
            db.add(Service(
                shop_id=shop.id, name=label,
                price=Decimal(str(rate * hours)), duration_minutes=minutes,
            ))
        for i in range(1, courts + 1):
            db.add(Staff(shop_id=shop.id, name=f"คอร์ท {i}", position="คอร์ทในร่ม"))
        added += 1

    # ---------- ศูนย์ส่งของด่วน ----------
    for name, district, lat, lng, _base, _perkm, riders in DELIVERY:
        if db.scalar(select(Shop).where(Shop.name == name)):
            continue
        shop = Shop(
            owner_id=owner.id, category_id=cats["delivery"].id, name=name,
            description=(
                "บริการรับส่งของด่วนในกรุงเทพฯ เรียกใช้ได้ทันทีไม่ต้องนัดล่วงหน้า "
                "คิดค่าบริการตามระยะทางจริง"
            ),
            address=f"ศูนย์กระจายงานเขต{district}", district=district,
            latitude=Decimal(f"{lat:.6f}"), longitude=Decimal(f"{lng:.6f}"),
            # ศูนย์ส่งของเปิด 24 ชั่วโมง — เปิดและปิดเวลาเดียวกันหมายถึงเปิดตลอด
            open_time=time(0, 0), close_time=time(0, 0),
            is_certified=True,
        )
        db.add(shop)
        db.flush()

        for label, base_fee, per_km, minutes, _ in DELIVERY_SERVICES:
            db.add(Service(
                shop_id=shop.id, name=label,
                description=f"ค่าเริ่มต้น {base_fee} บาท + {per_km} บาทต่อกิโลเมตร",
                price=Decimal(str(base_fee)),
                price_per_km=Decimal(str(per_km)),
                duration_minutes=minutes,
                booking_mode="instant",
            ))
        for i in range(1, riders + 1):
            db.add(Staff(shop_id=shop.id, name=f"พนักงานส่ง #{i}", position="ไรเดอร์"))
        added += 1

    db.commit()
    if added:
        print(f"เพิ่มสนามและศูนย์บริการ {added} แห่ง (ข้อมูลอ้างอิงสถานที่จริง)")
