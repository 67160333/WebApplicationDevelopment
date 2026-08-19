"""เติมข้อมูลตัวอย่างให้ระบบดูเหมือนใช้งานจริง

ต่างจาก seed.py ตรงที่ไฟล์นี้ "เติมเพิ่ม" ได้แม้ฐานข้อมูลมีข้อมูลอยู่แล้ว
และตรวจชื่อซ้ำก่อนทุกครั้ง จึงรันกี่รอบก็ไม่เกิดข้อมูลซ้ำ

เหตุผลที่ต้องมี: ระบบที่มีร้าน 3 ร้านและ 0 รีวิว จะดูเหมือนเว็บเปล่า
ดาวสีเทากับข้อความ "0.0 · 0 รีวิว" ทำให้คนไม่เชื่อถือทันที
ข้อมูลชุดนี้ทำให้คะแนน กราฟ และรายงานมีของจริงให้ดู
"""

import random
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Booking, Category, Review, Service, Shop, Staff, User
from app.security import hash_password

# ใช้ค่าคงที่ เพื่อให้รันกี่ครั้งก็ได้ข้อมูลชุดเดิม ไม่สุ่มใหม่ทุกครั้ง
RNG = random.Random(20260817)

# ---------------- ร้านและบริการ ----------------
# (ชื่อร้าน, slug หมวด, เขต, คำอธิบาย, เปิด, ปิด, ผ่านการรับรอง)
SHOPS: list[tuple] = [
    ("บ้านสบาย นวดแผนไทย", "spa-massage", "สาทร",
     "นวดแผนไทยโบราณโดยหมอนวดที่ผ่านการอบรมจากวัดโพธิ์ บรรยากาศเงียบสงบเหมาะกับคนทำงาน",
     time(9, 0), time(21, 0), True),
    ("Aroma House ทองหล่อ", "spa-massage", "วัฒนา",
     "สปาน้ำมันหอมระเหยสไตล์บาหลี ห้องส่วนตัวทุกห้อง มีบริการอบสมุนไพร",
     time(10, 0), time(22, 0), True),
    ("The Nail Bar สยาม", "nail", "ปทุมวัน",
     "ร้านทำเล็บกลางสยาม เน้นงานเพ้นท์ลายและเจลติดทน อุปกรณ์ผ่านการนึ่งฆ่าเชื้อทุกชิ้น",
     time(11, 0), time(20, 0), True),
    ("Pastel Nails อ่อนนุช", "nail", "สวนหลวง",
     "เล็บสีพาสเทลและงานมินิมอล ราคาเป็นกันเอง จองคิวล่วงหน้าได้",
     time(10, 0), time(19, 0), False),
    ("Studio Hair อารีย์", "hair", "พญาไท",
     "ตัด ทำสี ยืดผม โดยช่างที่มีประสบการณ์กว่า 10 ปี ใช้ผลิตภัณฑ์ปลอดแอมโมเนีย",
     time(10, 0), time(20, 0), True),
    ("Hair Room เอกมัย", "hair", "วัฒนา",
     "ร้านทำผมสไตล์เกาหลี ถนัดงานดัดวอลลุ่มและสีโทนธรรมชาติ",
     time(11, 0), time(21, 0), False),
    ("Glow Clinic พระราม 9", "beauty-clinic", "ห้วยขวาง",
     "คลินิกผิวหนังภายใต้การดูแลของแพทย์ มีบริการเลเซอร์และดูแลปัญหาสิว",
     time(10, 0), time(20, 0), True),
    ("Ink & Line Tattoo", "tattoo", "คลองเตย",
     "สตูดิโอสักลายเส้นบางและมินิมอล ใช้เข็มแบบใช้ครั้งเดียวทิ้ง ปรึกษาแบบก่อนได้ฟรี",
     time(12, 0), time(21, 0), False),
]

# บริการของแต่ละร้าน — (ชื่อ, ราคา, นาที)
SERVICES: dict[str, list[tuple[str, int, int]]] = {
    "บ้านสบาย นวดแผนไทย": [
        ("นวดแผนไทย 60 นาที", 350, 60),
        ("นวดแผนไทย 120 นาที", 650, 120),
        ("นวดเท้า 45 นาที", 300, 45),
        ("ประคบสมุนไพร 90 นาที", 700, 90),
    ],
    "Aroma House ทองหล่อ": [
        ("นวดน้ำมันอโรมา 60 นาที", 900, 60),
        ("นวดน้ำมันอโรมา 90 นาที", 1300, 90),
        ("สครับผิว + อบสมุนไพร", 1500, 120),
    ],
    "The Nail Bar สยาม": [
        ("ทาสีเจล มือ", 590, 60),
        ("ทาสีเจล เท้า", 690, 75),
        ("ต่อเล็บ PVC", 1400, 120),
        ("เพ้นท์ลายพิเศษ", 900, 90),
    ],
    "Pastel Nails อ่อนนุช": [
        ("ทาสีเจลมือ", 450, 60),
        ("ตะไบ + ทาสีธรรมดา", 250, 45),
        ("ต่อเล็บอะคริลิก", 1100, 120),
    ],
    "Studio Hair อารีย์": [
        ("ตัดผม + สระไดร์", 450, 60),
        ("ทำสีทั้งหัว", 1800, 150),
        ("ยืดผมถาวร", 2500, 180),
        ("ทรีตเมนต์บำรุงผม", 800, 60),
    ],
    "Hair Room เอกมัย": [
        ("ตัดผมชาย", 350, 45),
        ("ดัดวอลลุ่ม", 2200, 150),
        ("ทำสีโทนธรรมชาติ", 1900, 150),
    ],
    "Glow Clinic พระราม 9": [
        ("ปรึกษาแพทย์ + ตรวจผิว", 500, 30),
        ("เลเซอร์หน้าใส", 2500, 60),
        ("กดสิว + ทรีตเมนต์", 1200, 60),
    ],
    "Ink & Line Tattoo": [
        ("สักลายเล็ก (ไม่เกิน 5 ซม.)", 1500, 60),
        ("สักลายกลาง", 3500, 120),
        ("แก้ไข/เติมลายเดิม", 2000, 90),
    ],
}

# ช่างของแต่ละร้าน — (ชื่อ, ตำแหน่ง, ประวัติ, วันทำงาน, เข้างาน, เลิกงาน)
STAFF: dict[str, list[tuple]] = {
    "บ้านสบาย นวดแผนไทย": [
        ("พี่หน่อย", "หมอนวดอาวุโส", "ผ่านการอบรมวัดโพธิ์ ประสบการณ์ 12 ปี ถนัดแก้ออฟฟิศซินโดรม", "1,2,3,4,5", time(9, 0), time(18, 0)),
        ("พี่ตุ๊ก", "หมอนวด", "ถนัดนวดเท้าและกดจุดสะท้อน", None, None, None),
        ("พี่แดง", "หมอนวด", "ถนัดประคบสมุนไพรและนวดคลายกล้ามเนื้อ", "0,5,6", time(12, 0), None),
    ],
    "Aroma House ทองหล่อ": [
        ("ครูเมย์", "นักบำบัดอาวุโส", "เรียนนวดบาหลีจากอูบุด ประสบการณ์ 8 ปี", "2,3,4,5,6", None, None),
        ("ครูฟ้า", "นักบำบัด", "ถนัดนวดผ่อนคลายและสครับผิว", None, time(13, 0), None),
    ],
    "The Nail Bar สยาม": [
        ("ช่างมุก", "ช่างเล็บอาวุโส", "เพ้นท์ลายละเอียด รับงานแต่งงานและงานอีเวนต์", "1,2,3,4,5,6", None, None),
        ("ช่างแป้ง", "ช่างเล็บ", "ถนัดต่อเล็บ PVC และงานหินคริสตัล", None, None, None),
        ("ช่างเบล", "ช่างเล็บ", "ถนัดสีเรียบและทรงธรรมชาติ", "0,4,5,6", None, None),
    ],
    "Pastel Nails อ่อนนุช": [
        ("ช่างนุ่น", "เจ้าของร้าน", "ทำเล็บมา 6 ปี เน้นงานเรียบง่ายและสีพาสเทล", None, None, None),
        ("ช่างพลอย", "ช่างเล็บ", "ถนัดต่อเล็บอะคริลิก", "1,2,3,4,5", None, None),
    ],
    "Studio Hair อารีย์": [
        ("ช่างโอ๊ต", "ช่างผมอาวุโส", "ประสบการณ์ 14 ปี ถนัดตัดทรงสั้นและทำสี", "1,2,3,4,5,6", None, None),
        ("ช่างจูน", "ช่างทำสี", "เชี่ยวชาญสีโทนหม่นและไฮไลต์", None, time(11, 0), None),
        ("ช่างเอก", "ช่างผม", "ถนัดยืดและทรีตเมนต์บำรุงผม", "0,3,4,5,6", None, None),
    ],
    "Hair Room เอกมัย": [
        ("ช่างมิว", "ช่างผม", "เรียนเทคนิคดัดวอลลุ่มจากเกาหลี", None, None, None),
        ("ช่างต้น", "ช่างผมชาย", "ถนัดทรงสกินเฟดและทรงนักเรียน", "1,2,3,4,5", None, None),
    ],
    "Glow Clinic พระราม 9": [
        ("พญ. ณัฐชา", "แพทย์ผิวหนัง", "แพทย์เฉพาะทางผิวหนัง ดูแลปัญหาสิวและรอยดำ", "1,3,5", time(11, 0), time(18, 0)),
        ("พี่แนน", "ผู้ช่วยแพทย์", "ดูแลทรีตเมนต์และให้คำแนะนำหลังทำ", None, None, None),
    ],
    "Ink & Line Tattoo": [
        ("ช่างกร", "ช่างสักอาวุโส", "สักมา 9 ปี ถนัดลายเส้นบางและลายมินิมอล", "2,3,4,5,6", time(12, 0), None),
        ("ช่างบิว", "ช่างสัก", "ถนัดลายดอกไม้และตัวอักษร", None, None, None),
    ],
}

# ---------------- ข้อความรีวิว แยกตามระดับคะแนน ----------------
COMMENTS: dict[int, list[str]] = {
    5: [
        "บริการดีมากค่ะ พนักงานสุภาพ ร้านสะอาด จะกลับมาใช้บริการอีกแน่นอน",
        "ประทับใจมาก ช่างใส่ใจรายละเอียด ถามความต้องการก่อนเริ่มทุกครั้ง",
        "จองผ่านเว็บสะดวกมาก ไปถึงแล้วได้คิวเลยไม่ต้องรอ",
        "ทำออกมาตรงกับที่คุยไว้เป๊ะ ราคาสมเหตุสมผลกับคุณภาพ",
        "ร้านหาง่าย บรรยากาศดี ช่างฝีมือดีจริง แนะนำเลยครับ",
        "ครั้งที่สามแล้วที่มา ไม่เคยผิดหวังสักครั้ง",
    ],
    4: [
        "โดยรวมดีครับ แต่วันที่ไปคนเยอะหน่อยเลยรอนิดนึง",
        "งานออกมาสวยดี ติดที่ร้านหาที่จอดรถยาก",
        "ช่างทำดีมาก แต่อยากให้มีที่นั่งรอเยอะกว่านี้",
        "พอใจกับผลลัพธ์ ราคาโอเค แต่เสียงจากข้างนอกดังไปหน่อย",
        "บริการดี แต่เริ่มช้ากว่าเวลานัดประมาณ 10 นาที",
    ],
    3: [
        "ก็โอเคตามราคาครับ ไม่ได้ว้าวแต่ก็ไม่แย่",
        "งานใช้ได้ แต่รู้สึกว่ารีบไปหน่อย อาจเพราะคิวแน่น",
        "ผลลัพธ์กลาง ๆ ครับ อยากให้สอบถามความต้องการมากกว่านี้",
    ],
    2: [
        "รอนานกว่าที่นัดไว้เกือบครึ่งชั่วโมง งานพอใช้ได้แต่ไม่ประทับใจ",
        "ไม่ค่อยตรงกับที่คุยไว้ ต้องขอให้แก้อีกรอบ",
    ],
}

REPLIES = [
    "ขอบคุณมากค่ะ ทางร้านดีใจที่ถูกใจ ไว้มาใหม่นะคะ",
    "ขอบคุณสำหรับคำติชมครับ ทางร้านจะนำไปปรับปรุงเรื่องเวลารอให้ดีขึ้น",
    "ขอบคุณที่มาใช้บริการค่ะ จะส่งต่อคำชมให้ช่างนะคะ",
    "ต้องขออภัยด้วยครับ ทางร้านรับไปแก้ไขแล้ว หวังว่าจะได้ดูแลอีกครั้ง",
]

# ลูกค้าเพิ่มเติมสำหรับเป็นเจ้าของรีวิว
EXTRA_USERS = [
    ("ploy_r", "ploy@example.com", "พลอย รัตนา"),
    ("kwan_s", "kwan@example.com", "ขวัญ สุขใจ"),
    ("bee_t", "bee@example.com", "บี ธนกร"),
    ("jane_w", "jane@example.com", "เจน วรรณา"),
    ("nut_p", "nut@example.com", "นัท ปิยะ"),
    ("mook_c", "mook@example.com", "มุก ชนิดา"),
]


def _get_or_create_owner(db: Session) -> User:
    """ใช้เจ้าของร้านเดิมถ้ามี ถ้าไม่มีก็สร้างใหม่"""
    owner = db.scalar(select(User).where(User.username == "demoowner"))
    if owner is None:
        owner = User(
            username="demoowner", email="demoowner@example.com",
            password_hash=hash_password("Password123"),
            full_name="เจ้าของร้านตัวอย่าง", phone="0800000009", role="owner",
        )
        db.add(owner)
        db.flush()
    return owner


def enrich_demo_data(db: Session) -> None:
    """เติมร้าน บริการ ช่าง และรีวิว ให้ระบบมีข้อมูลพอที่จะดูน่าเชื่อถือ"""
    shop_count = db.scalar(select(func.count(Shop.id))) or 0
    if shop_count >= len(SHOPS):
        return   # เติมไปแล้ว ไม่ต้องทำซ้ำ

    cats = {c.slug: c for c in db.scalars(select(Category)).all()}
    if not cats:
        return   # ยังไม่มีหมวดหมู่ แปลว่า seed หลักยังไม่ทำงาน

    owner = _get_or_create_owner(db)

    # ---------- ลูกค้าเพิ่มเติม ----------
    customers = list(db.scalars(select(User).where(User.role == "customer")).all())
    for username, email, full_name in EXTRA_USERS:
        if db.scalar(select(User).where(User.username == username)):
            continue
        u = User(
            username=username, email=email, password_hash=hash_password("Password123"),
            full_name=full_name, role="customer",
        )
        db.add(u)
        db.flush()
        customers.append(u)

    if not customers:
        return

    today = date.today()
    new_reviews = 0

    for name, slug, district, desc, open_t, close_t, certified in SHOPS:
        if db.scalar(select(Shop).where(Shop.name == name)):
            continue   # มีร้านนี้แล้ว

        shop = Shop(
            owner_id=owner.id, category_id=cats[slug].id, name=name, description=desc,
            address=f"ถนนตัวอย่าง เขต{district}", district=district,
            phone=f"02{RNG.randint(1000000, 9999999)}",
            open_time=open_t, close_time=close_t, is_certified=certified,
        )
        db.add(shop)
        db.flush()

        services = []
        for sv_name, price, minutes in SERVICES[name]:
            sv = Service(
                shop_id=shop.id, name=sv_name,
                price=Decimal(str(price)), duration_minutes=minutes,
            )
            db.add(sv)
            services.append(sv)

        staff = []
        for st_name, pos, bio, days, ws, we in STAFF[name]:
            st = Staff(
                shop_id=shop.id, name=st_name, position=pos, bio=bio,
                work_days=days, work_start=ws, work_end=we,
            )
            db.add(st)
            staff.append(st)
        db.flush()

        # ---------- ประวัติการใช้บริการย้อนหลัง 5 เดือน พร้อมรีวิว ----------
        n_reviews = RNG.randint(6, 14)
        for i in range(n_reviews):
            sv = RNG.choice(services)
            st = RNG.choice(staff)
            cust = RNG.choice(customers)
            days_ago = RNG.randint(3, 150)
            when = today - timedelta(days=days_ago)
            hour = RNG.choice([10, 11, 13, 14, 15, 16, 17, 18])
            start = time(hour, RNG.choice([0, 30]))
            end_total = start.hour * 60 + start.minute + sv.duration_minutes

            price = sv.price
            bk = Booking(
                booking_code=f"BKD{shop.id:02d}{i:03d}{RNG.randint(10, 99)}",
                user_id=cust.id, service_id=sv.id, shop_id=shop.id, staff_id=st.id,
                booking_date=when, booking_time=start,
                end_time=time(min(end_total // 60, 23), end_total % 60),
                total_price=price,
                deposit_amount=(price * Decimal("0.2")).quantize(Decimal("0.01")),
                status="completed",
                created_at=datetime.combine(when, time(9, 0), tzinfo=timezone.utc),
            )
            db.add(bk)
            db.flush()

            # ให้คะแนนดีเป็นส่วนใหญ่ แต่มีคะแนนกลางและต่ำปนบ้าง เหมือนร้านจริง
            rating = RNG.choices([5, 4, 3, 2], weights=[58, 27, 10, 5])[0]
            rv = Review(
                booking_id=bk.id, user_id=cust.id, shop_id=shop.id,
                service_id=sv.id, staff_id=st.id,
                rating=rating,
                staff_rating=max(1, min(5, rating + RNG.choice([0, 0, 0, 1, -1]))),
                rating_cleanliness=max(1, min(5, rating + RNG.choice([0, 0, 1]))),
                rating_punctuality=max(1, min(5, rating + RNG.choice([0, 0, -1]))),
                rating_value=max(1, min(5, rating + RNG.choice([0, 0, -1, 1]))),
                comment=RNG.choice(COMMENTS[rating]),
                created_at=datetime.combine(when, time(20, 0), tzinfo=timezone.utc),
            )
            # ร้านตอบกลับประมาณครึ่งหนึ่ง เหมือนร้านที่ดูแลลูกค้าจริง
            if RNG.random() < 0.5:
                rv.reply = RNG.choice(REPLIES)
                rv.replied_at = datetime.combine(when, time(21, 0), tzinfo=timezone.utc)

            db.add(rv)
            new_reviews += 1

    db.flush()

    # ---------- คำนวณคะแนนร้านและช่างใหม่ทั้งหมด ----------
    for shop in db.scalars(select(Shop)).all():
        avg, cnt = db.execute(
            select(func.avg(Review.rating), func.count(Review.id)).where(Review.shop_id == shop.id)
        ).one()
        shop.rating_avg = Decimal(str(round(float(avg or 0), 2)))
        shop.rating_count = int(cnt or 0)

    for member in db.scalars(select(Staff)).all():
        avg, cnt = db.execute(
            select(func.avg(Review.staff_rating), func.count(Review.id)).where(
                Review.staff_id == member.id, Review.staff_rating.isnot(None)
            )
        ).one()
        member.rating_avg = Decimal(str(round(float(avg or 0), 2)))
        member.rating_count = int(cnt or 0)

    db.commit()
    print(f"เติมข้อมูลตัวอย่าง: ร้านใหม่ {len(SHOPS)} ร้าน · รีวิว {new_reviews} รายการ")


# ---------------- พิกัดร้านสำหรับแผนที่ ----------------
# จุดอ้างอิงกลางเขตในกรุงเทพฯ (ละติจูด, ลองจิจูด)
DISTRICT_GEO: dict[str, tuple[float, float]] = {
    "พญาไท":    (13.7800, 100.5420),
    "ปทุมวัน":   (13.7455, 100.5340),
    "วัฒนา":     (13.7350, 100.5820),
    "สาทร":     (13.7180, 100.5290),
    "สวนหลวง":  (13.7290, 100.6440),
    "ห้วยขวาง":  (13.7770, 100.5790),
    "คลองเตย":  (13.7080, 100.5620),
    "บางรัก":    (13.7300, 100.5240),
    "จตุจักร":   (13.8280, 100.5600),
    "ดินแดง":    (13.7690, 100.5530),
}

# ถ้าไม่รู้จักเขตนั้น ใช้อนุสาวรีย์ชัยสมรภูมิเป็นจุดตั้งต้น
DEFAULT_GEO = (13.7650, 100.5380)


def backfill_coordinates(db: Session) -> None:
    """เติมพิกัดให้ร้านที่ยังไม่ได้ปักหมุด

    ทำแยกจากการสร้างร้าน เพราะร้านในฐานข้อมูลถูกสร้างไว้ก่อนที่ระบบจะมีแผนที่
    ฟังก์ชันนี้จึงต้องย้อนไปเติมให้ของเดิมด้วย และข้ามร้านที่มีพิกัดอยู่แล้ว
    (เจ้าของร้านอาจย้ายหมุดเองไปแล้ว — ห้ามเขียนทับ)
    """
    rows = list(db.scalars(select(Shop).where(Shop.latitude.is_(None))).all())
    if not rows:
        return

    for shop in rows:
        base_lat, base_lng = DISTRICT_GEO.get(shop.district or "", DEFAULT_GEO)
        # กระจายหมุดออกจากกันเล็กน้อย ไม่งั้นร้านในเขตเดียวกันจะซ้อนทับกันจนคลิกไม่ได้
        # ใช้ id ของร้านเป็นตัวกำหนด ผลลัพธ์จึงคงที่ทุกครั้งที่รัน
        spread = random.Random(shop.id * 7919)
        lat = base_lat + spread.uniform(-0.012, 0.012)
        lng = base_lng + spread.uniform(-0.012, 0.012)
        shop.latitude = Decimal(f"{lat:.6f}")
        shop.longitude = Decimal(f"{lng:.6f}")

    db.commit()
    print(f"เติมพิกัดให้ร้าน {len(rows)} ร้าน")
