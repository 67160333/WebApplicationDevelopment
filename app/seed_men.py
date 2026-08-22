"""เติมหมวดบริการที่เจาะกลุ่มผู้ชาย 4 หมวด

**ชื่อร้านทุกแห่งในไฟล์นี้เป็นชื่อสมมติ** เหตุผลเดียวกับ `seed_venues.py` คือ
เว็บนี้เปิดสาธารณะได้ ถ้าใช้ชื่อธุรกิจจริงคู่กับปุ่ม "จองคิว" ที่กดได้
จะกลายเป็นการอ้างว่าร้านเหล่านั้นรับจองผ่านเรา ทั้งที่เขาไม่เคยตกลงด้วย
ด้วยเหตุผลเดียวกัน ไฟล์นี้จึงไม่ใส่เบอร์โทรและไม่สร้างรีวิวปลอม

--------------------------------------------------------------------------
ทำไมต้องเป็น 4 หมวดนี้ — แต่ละหมวดพิสูจน์คนละเรื่อง
--------------------------------------------------------------------------

1. คลินิกสุขภาพเพศชาย (`mens-clinic`)
   หมวดที่ "การจองออนไลน์" คือคุณค่าในตัวมันเอง ไม่ใช่แค่ความสะดวก
   ผู้ชายไม่อยากโทรไปบอกพนักงานรับสายว่ามีปัญหาผมร่วงหรืออยากตรวจฮอร์โมน
   การกดจองเงียบ ๆ โดยไม่ต้องคุยกับใครคือเหตุผลเดียวที่คนยอมใช้ระบบ
   ระบบรองรับอยู่แล้วโดยไม่ได้ตั้งใจ — `_short_name()` ย่อนามสกุลในรีวิว
   และจองแบบ guest ได้โดยไม่ต้องเปิดเผยตัวตนเต็ม

2. ช่างตัดผมนอกสถานที่ (`mobile-barber`)
   **หมวดที่สองที่ใช้ `booking_mode="instant"`**
   ก่อนหน้านี้มีแค่ "ส่งของด่วน" หมวดเดียวที่ใช้โหมดนี้ ซึ่งทำให้โหมดนี้
   ดูเหมือนทางแยกที่เขียนขึ้นเฉพาะกิจเพื่อรองรับส่งของ พอมีหมวดที่สอง
   ที่ใช้โค้ดชุดเดียวกันโดยเปลี่ยนแค่ราคาและค่าต่อกิโลเมตร
   มันจึงกลายเป็นความสามารถของระบบจริง ไม่ใช่การปะ

3. ติดฟิล์มและเคลือบแก้วรถ (`car-care`)
   **รูปร่างการจองที่ระบบยังไม่เคยเจอ — งานยาว 4 ถึง 8 ชั่วโมง**
   ทุกการจองเดิมยาว 60–180 นาที ซึ่งแทบไม่มีทางชนกับเวลาปิดร้าน
   งานเคลือบแก้ว 480 นาทีบังคับให้ `_fits_window()` ทำงานจริง
   ร้านเปิด 08:00–18:00 แปลว่างาน 8 ชั่วโมงเริ่มได้เฉพาะ 08:00–10:00 เท่านั้น

4. ห้องคาราโอเกะ (`karaoke`)
   เปิด 14:00–02:00 คือ **คร่อมเที่ยงคืน** ซึ่งเป็นเคสที่เคยทำให้ระบบพัง
   (ดูบั๊ก #1 ใน PROJECT_CONTEXT) การเพิ่มหมวดนี้คือการยืนยันซ้ำว่า
   `_windows_for()` ที่คืนค่าเป็นรายการช่วงเวลาทำงานถูกต้องจริง

--------------------------------------------------------------------------
กับดักที่ต้องรู้ก่อนแก้ไฟล์นี้
--------------------------------------------------------------------------

ฟังก์ชันข้างล่างตรวจข้อมูลซ้ำ **จากชื่อร้าน** เหมือน `seed_venues()`
**ห้ามแก้ชื่อร้านที่มีอยู่แล้วในไฟล์นี้** เพราะพอรีสตาร์ต ระบบจะมองว่า
เป็นร้านใหม่แล้วสร้างซ้ำทั้งชุด (โปรเจกต์นี้เคยพลาดมาแล้ว 2 ครั้ง)
ถ้าต้องเปลี่ยนชื่อจริง ๆ ให้เปลี่ยนผ่าน `PUT /api/shops/{id}` ด้วยบัญชี admin

เพิ่มหมวดใหม่แล้ว **ต้องไปเพิ่มไอคอนใน `web/js/ui.js`** ทั้ง `ICON`
และ `CATEGORY_ICON` ไม่งั้นการ์ดหมวดในหน้าแรกจะโล่ง
"""

from datetime import time
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Category, Service, Shop, Staff, User
from app.security import hash_password

# ---------------- หมวดหมู่ใหม่ ----------------
# (slug, ชื่อที่แสดง, คำเรียกสิ่งที่จองได้)
MEN_CATEGORIES: list[tuple[str, str, str]] = [
    ("mens-clinic", "คลินิกสุขภาพชาย", "แพทย์"),
    ("mobile-barber", "ตัดผมนอกสถานที่", "ช่าง"),
    ("car-care", "ดูแลรถยนต์", "ช่องบริการ"),
    ("karaoke", "ห้องคาราโอเกะ", "ห้อง"),
]

# ---------------- 1. คลินิกสุขภาพชาย ----------------
# (ชื่อ, เขต, ที่อยู่ย่อ, lat, lng, เปิด, ปิด, จำนวนแพทย์)
MENS_CLINIC: list[tuple] = [
    ("คลินิกสุขภาพชาย วีรกุล", "วัฒนา", "ซอยสุขุมวิท 24 ใกล้ BTS พร้อมพงษ์",
     13.730500, 100.568900, time(10, 0), time(20, 0), 3),
    ("ManCare Clinic รัชดา", "ห้วยขวาง", "ถนนรัชดาภิเษก ใกล้ MRT ห้วยขวาง",
     13.776900, 100.574300, time(11, 0), time(21, 0), 2),
    ("คลินิกผู้ชาย ปิยะเวท สาทร", "สาทร", "ถนนสาทรใต้ ใกล้ BTS ช่องนนทรี",
     13.720400, 100.529600, time(9, 0), time(19, 0), 3),
]

# (ชื่อบริการ, ราคา, นาที, คำอธิบาย)
MENS_CLINIC_SERVICES: list[tuple[str, int, int, str]] = [
    ("ปรึกษาปัญหาผมร่วงและผมบาง", 500, 30,
     "ตรวจหนังศีรษะด้วยกล้องกำลังขยาย พร้อมวางแผนการรักษาเป็นรายบุคคล"),
    ("ตรวจระดับฮอร์โมนเพศชาย", 1800, 45,
     "เจาะเลือดตรวจระดับฮอร์โมน พร้อมพบแพทย์เพื่ออ่านผลและให้คำแนะนำ"),
    ("ตรวจสุขภาพประจำปีสำหรับผู้ชาย", 2500, 60,
     "โปรแกรมตรวจที่ออกแบบตามช่วงอายุ ครอบคลุมรายการที่ผู้ชายควรตรวจ"),
    ("ปรึกษาแพทย์แบบส่วนตัว", 800, 30,
     "ห้องตรวจแยกส่วนตัว ไม่ต้องแจ้งอาการกับพนักงานหน้าเคาน์เตอร์"),
]

# ---------------- 2. ช่างตัดผมนอกสถานที่ ----------------
# (ชื่อ, เขต, lat, lng, จำนวนช่าง)
MOBILE_BARBER: list[tuple] = [
    ("เฟดถึงบ้าน บาร์เบอร์ (ลาดพร้าว)", "ลาดพร้าว", 13.806200, 100.601400, 6),
    ("Cut2U ช่างตัดผมนอกสถานที่ (สาทร)", "สาทร", 13.718900, 100.533700, 5),
]

# (ชื่อบริการ, ค่าเริ่มต้น, ค่าต่อกิโลเมตร, นาที, คำอธิบาย)
MOBILE_BARBER_SERVICES: list[tuple[str, int, int, int, str]] = [
    ("ตัดผมชายถึงที่ (เฟด / รองทรง)", 350, 12, 45,
     "ช่างเดินทางไปตัดให้ถึงบ้านหรือที่ทำงาน พร้อมอุปกรณ์และผ้าคลุมครบชุด"),
    ("ตัดผม + โกนหนวดด้วยมีดโกน", 550, 12, 60,
     "รวมตัดผม แต่งทรงหนวดเครา และโกนด้วยมีดโกนพร้อมผ้าร้อน"),
    ("ตัดผมเด็กถึงบ้าน", 300, 12, 40,
     "สำหรับเด็กที่ไม่ยอมนั่งร้าน ตัดที่บ้านในบรรยากาศที่คุ้นเคย"),
]

# ---------------- 3. ดูแลรถยนต์ ----------------
# (ชื่อ, เขต, ที่อยู่ย่อ, lat, lng, เปิด, ปิด, จำนวนช่องบริการ)
CAR_CARE: list[tuple] = [
    ("ออโต้ดีเทล การาจ รามอินทรา", "บางเขน", "ถนนรามอินทรา ใกล้แยกวัชรพล",
     13.861200, 100.643800, time(8, 0), time(18, 0), 4),
    ("ฟิล์มโปร ออโต้สตูดิโอ บางนา", "บางนา", "ถนนบางนา-ตราด กม.3",
     13.669700, 100.628400, time(8, 0), time(18, 0), 3),
    ("คาร์แคร์ พระราม 3 ดีเทลลิ่ง", "ยานนาวา", "ถนนพระรามที่ 3 ใกล้เซ็นทรัลพระราม 3",
     13.687500, 100.542900, time(8, 30), time(18, 30), 3),
]

# (ชื่อบริการ, ราคา, นาที, คำอธิบาย)
# หมายเหตุ: งาน 480 นาทีคือเหตุผลที่หมวดนี้ถูกเพิ่มเข้ามา — ดูหัวข้อ 3 ด้านบน
CAR_CARE_SERVICES: list[tuple[str, int, int, str]] = [
    ("ล้าง ดูดฝุ่น เคลือบสีพื้นฐาน", 890, 90,
     "ล้างภายนอก ดูดฝุ่นภายใน และเคลือบสีแบบใช้ได้ราว 1 เดือน"),
    ("ติดฟิล์มกรองแสงรอบคัน", 4500, 240,
     "ฟิล์มกันความร้อนรอบคัน รับประกันฟิล์ม 5 ปี ใช้เวลาราวครึ่งวัน"),
    ("ขัดลบรอย + เคลือบสี", 3500, 300,
     "ขัดลบรอยขนแมวและคราบฝังแน่น แล้วเคลือบสีทับทั้งคัน"),
    ("เคลือบแก้ว 9H ทั้งคัน", 8900, 480,
     "เคลือบแก้วความแข็ง 9H ต้องใช้เวลาทั้งวัน รับรถคืนตอนเย็น"),
]

# ---------------- 4. ห้องคาราโอเกะ ----------------
# (ชื่อ, เขต, ที่อยู่ย่อ, lat, lng, เปิด, ปิด, ราคาต่อชั่วโมง, จำนวนห้อง)
# เปิด 14:00 ปิด 02:00 = คร่อมเที่ยงคืน — เคสที่เคยทำให้ระบบพังทั้งวัน
KARAOKE: list[tuple] = [
    ("ซาวด์บ็อกซ์ คาราโอเกะ ทองหล่อ", "วัฒนา", "ซอยทองหล่อ 13",
     13.735800, 100.583200, time(14, 0), time(2, 0), 350, 8),
    ("Echo Room คาราโอเกะ รัชดา", "ห้วยขวาง", "ถนนรัชดาภิเษก ใกล้เอสพลานาด",
     13.766400, 100.573800, time(15, 0), time(2, 0), 300, 10),
    ("ไมค์ทอง คาราโอเกะ ลาดพร้าว", "จตุจักร", "ถนนลาดพร้าว ใกล้ MRT ลาดพร้าว",
     13.806900, 100.574600, time(16, 0), time(1, 0), 250, 6),
]

# (ชื่อบริการ, จำนวนชั่วโมง, นาที)
KARAOKE_SERVICES: list[tuple[str, int, int]] = [
    ("จองห้อง 1 ชั่วโมง", 1, 60),
    ("จองห้อง 2 ชั่วโมง", 2, 120),
    ("จองห้อง 3 ชั่วโมง", 3, 180),
]

# ขนาดห้องคาราโอเกะ — วนใช้ตามจำนวนห้องของแต่ละร้าน
ROOM_SIZES = ["ห้องเล็ก 2-4 คน", "ห้องกลาง 5-8 คน", "ห้องใหญ่ 9-15 คน"]


def _men_owner(db: Session) -> User:
    """บัญชีเจ้าของสำหรับหมวดกลุ่มผู้ชาย แยกจากเจ้าของร้านความงามและสนามกีฬา

    แยกบัญชีเพราะต้องใช้ทดสอบว่าเจ้าของร้านคนหนึ่งแก้ข้อมูลร้านของคนอื่นไม่ได้
    ถ้าใช้บัญชีเดียวกันหมด จะทดสอบเรื่องสิทธิ์ข้ามร้านไม่ได้เลย
    """
    owner = db.scalar(select(User).where(User.username == "menowner"))
    if owner is None:
        owner = User(
            username="menowner",
            email="menowner@example.com",
            password_hash=hash_password("Password123"),
            full_name="ผู้ดูแลร้านกลุ่มผู้ชาย",
            role="owner",
        )
        db.add(owner)
        db.flush()
    return owner


def seed_men_services(db: Session) -> None:
    """เติมหมวดและร้านกลุ่มผู้ชาย — รันซ้ำได้ไม่เกิดข้อมูลซ้ำ"""

    # ---------- หมวดหมู่ ----------
    for slug, name, label in MEN_CATEGORIES:
        cat = db.scalar(select(Category).where(Category.slug == slug))
        if cat is None:
            db.add(Category(name=name, slug=slug, resource_label=label))
        elif cat.resource_label != label:
            cat.resource_label = label

    db.flush()
    cats = {c.slug: c for c in db.scalars(select(Category)).all()}
    owner = _men_owner(db)
    added = 0

    # ---------- 1. คลินิกสุขภาพชาย ----------
    for name, district, address, lat, lng, open_t, close_t, doctors in MENS_CLINIC:
        if db.scalar(select(Shop).where(Shop.name == name)):
            continue
        shop = Shop(
            owner_id=owner.id, category_id=cats["mens-clinic"].id, name=name,
            description=(
                "คลินิกที่ให้บริการเฉพาะผู้ชาย ดูแลเรื่องผมร่วง ฮอร์โมน "
                "และสุขภาพทั่วไป จองผ่านระบบได้เลยโดยไม่ต้องโทรแจ้งอาการกับใคร"
            ),
            address=address, district=district,
            latitude=Decimal(f"{lat:.6f}"), longitude=Decimal(f"{lng:.6f}"),
            open_time=open_t, close_time=close_t,
            is_certified=True,
        )
        db.add(shop)
        db.flush()

        for label, price, minutes, detail in MENS_CLINIC_SERVICES:
            db.add(Service(
                shop_id=shop.id, name=label, description=detail,
                price=Decimal(str(price)), duration_minutes=minutes,
            ))
        for i in range(1, doctors + 1):
            db.add(Staff(shop_id=shop.id, name=f"แพทย์ท่านที่ {i}",
                         position="แพทย์เวชปฏิบัติทั่วไป"))
        added += 1

    # ---------- 2. ช่างตัดผมนอกสถานที่ ----------
    for name, district, lat, lng, barbers in MOBILE_BARBER:
        if db.scalar(select(Shop).where(Shop.name == name)):
            continue
        shop = Shop(
            owner_id=owner.id, category_id=cats["mobile-barber"].id, name=name,
            description=(
                "ช่างตัดผมเดินทางไปหาถึงบ้านหรือที่ทำงาน ไม่ต้องนัดล่วงหน้า "
                "กดเรียกแล้วช่างออกเดินทางทันที คิดค่าเดินทางตามระยะทางจริง"
            ),
            address=f"ศูนย์กระจายช่างเขต{district}", district=district,
            latitude=Decimal(f"{lat:.6f}"), longitude=Decimal(f"{lng:.6f}"),
            # เปิด 08:00 ปิดเที่ยงคืนพอดี — งานเรียกใช้ทันทีต้องเช็คว่าร้านเปิดอยู่จริง
            open_time=time(8, 0), close_time=time(0, 0),
        )
        db.add(shop)
        db.flush()

        for label, base_fee, per_km, minutes, detail in MOBILE_BARBER_SERVICES:
            db.add(Service(
                shop_id=shop.id, name=label,
                description=f"{detail} · ค่าเดินทาง {per_km} บาทต่อกิโลเมตร",
                price=Decimal(str(base_fee)),
                price_per_km=Decimal(str(per_km)),
                duration_minutes=minutes,
                # หมวดที่สองที่ใช้โหมดนี้ ต่อจากบริการส่งของด่วน
                booking_mode="instant",
            ))
        for i in range(1, barbers + 1):
            db.add(Staff(shop_id=shop.id, name=f"ช่าง #{i}", position="ช่างตัดผมชาย"))
        added += 1

    # ---------- 3. ดูแลรถยนต์ ----------
    for name, district, address, lat, lng, open_t, close_t, bays in CAR_CARE:
        if db.scalar(select(Shop).where(Shop.name == name)):
            continue
        shop = Shop(
            owner_id=owner.id, category_id=cats["car-care"].id, name=name,
            description=(
                f"ศูนย์ดูแลรถยนต์ {bays} ช่องบริการ ย่าน{district} "
                "รับติดฟิล์ม เคลือบแก้ว ขัดลบรอย และล้างรถ มีที่นั่งรอปรับอากาศ"
            ),
            address=address, district=district,
            latitude=Decimal(f"{lat:.6f}"), longitude=Decimal(f"{lng:.6f}"),
            open_time=open_t, close_time=close_t,
        )
        db.add(shop)
        db.flush()

        for label, price, minutes, detail in CAR_CARE_SERVICES:
            db.add(Service(
                shop_id=shop.id, name=label, description=detail,
                price=Decimal(str(price)), duration_minutes=minutes,
            ))
        # แต่ละช่องยกรถได้หนึ่งคัน จึงเป็นทรัพยากรที่จองแยกกันเหมือนคอร์ทแบด
        for i in range(1, bays + 1):
            db.add(Staff(shop_id=shop.id, name=f"ช่องบริการ {i}",
                         position="ช่องยกรถในร่ม"))
        added += 1

    # ---------- 4. ห้องคาราโอเกะ ----------
    for name, district, address, lat, lng, open_t, close_t, rate, rooms in KARAOKE:
        if db.scalar(select(Shop).where(Shop.name == name)):
            continue
        shop = Shop(
            owner_id=owner.id, category_id=cats["karaoke"].id, name=name,
            description=(
                f"ห้องคาราโอเกะส่วนตัว {rooms} ห้อง ย่าน{district} "
                f"ค่าห้องเริ่มต้น {rate} บาทต่อชั่วโมง เปิดถึงดึก"
            ),
            address=address, district=district,
            latitude=Decimal(f"{lat:.6f}"), longitude=Decimal(f"{lng:.6f}"),
            open_time=open_t, close_time=close_t,
        )
        db.add(shop)
        db.flush()

        for label, hours, minutes in KARAOKE_SERVICES:
            db.add(Service(
                shop_id=shop.id, name=label,
                price=Decimal(str(rate * hours)), duration_minutes=minutes,
            ))
        for i in range(1, rooms + 1):
            db.add(Staff(shop_id=shop.id, name=f"ห้อง {i}",
                         position=ROOM_SIZES[(i - 1) % len(ROOM_SIZES)]))
        added += 1

    db.commit()
    if added:
        print(f"เพิ่มร้านหมวดกลุ่มผู้ชาย {added} แห่ง")


# ---------------------------------------------------------------------------
# กลุ่มใหญ่ของทุกหมวด — ใช้แยกทางเข้าในหน้าเว็บ
# ---------------------------------------------------------------------------
# แบ่งตาม "รูปแบบการใช้บริการ" ไม่ใช่ตามอุตสาหกรรม เพราะผู้ใช้คิดแบบนั้น
# คนไม่ได้ถามว่า "นี่คืออุตสาหกรรมความงามหรือกีฬา" แต่ถามว่า
# "ฉันต้องไปที่ร้าน หรือเขามาหาฉัน" และ "ไปคนเดียวหรือไปเป็นกลุ่ม"
#
# เดิมหน้าแรกโยนหมวดทั้ง 12 มาเรียงกันเป็นแถวเดียว และหน้าค้นหาเอาสปา
# กับสนามบอลมาปนกันในลิสต์เดียวโดยใช้ตัวกรองชุดเดียวกัน ซึ่งทำให้ผู้ใช้สับสน
CATEGORY_GROUPS: dict[str, str] = {
    # care = ไปที่ร้าน มีคนทำให้ จองคนเดียวก็ใช้ได้
    "spa-massage": "care",
    "nail": "care",
    "hair": "care",
    "beauty-clinic": "care",
    "tattoo": "care",
    "mens-clinic": "care",
    # play = จองสถานที่ ไปกันเป็นกลุ่ม เปิดก๊วนได้
    "football": "play",
    "badminton": "play",
    "karaoke": "play",
    # auto = ฝากของไว้แล้วรอ งานยาวหลายชั่วโมง
    "car-care": "auto",
    # come = ไม่มีปฏิทิน เรียกแล้วมาหาถึงที่ คิดเงินตามระยะทาง
    "delivery": "come",
    "mobile-barber": "come",
}


def seed_category_groups(db: Session) -> None:
    """ตั้งกลุ่มให้ทุกหมวด — รันซ้ำได้ แก้เฉพาะตัวที่ยังไม่ตรง"""
    changed = 0
    for cat in db.scalars(select(Category)).all():
        want = CATEGORY_GROUPS.get(cat.slug, "care")
        if cat.group_key != want:
            cat.group_key = want
            changed += 1
    if changed:
        db.commit()
        print(f"ตั้งกลุ่มให้หมวดหมู่ {changed} รายการ")
