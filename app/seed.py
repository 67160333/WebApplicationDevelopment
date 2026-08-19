"""ใส่ข้อมูลตัวอย่างลงฐานข้อมูล (ทำงานครั้งแรกครั้งเดียว)

รหัสผ่านของทุกบัญชีคือ Password123
"""

import os
import secrets
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Booking, Category, Review, Service, Shop, Staff, User
from app.security import hash_password

# บัญชีลูกค้าและเจ้าของร้านใช้รหัสนี้ เพื่อให้อาจารย์และผู้ทดสอบเข้าดูระบบได้ทันที
DEMO_PASSWORD = "Password123"


def _admin_password() -> tuple[str, bool]:
    """รหัสผ่านของบัญชีผู้ดูแลระบบ

    บัญชี admin ลบร้าน ลบผู้ใช้ และเปลี่ยนสิทธิ์คนอื่นได้
    ถ้าใช้รหัสเดียวกับบัญชีสาธิตแล้วเอาเว็บขึ้นอินเทอร์เน็ต
    ใครก็ตามที่เห็นหน้าเว็บจะลบข้อมูลทั้งระบบได้ทันที

    จึงอ่านจาก ADMIN_PASSWORD ก่อน ถ้าไม่ได้ตั้งไว้จะสุ่มให้
    แล้วพิมพ์ลง log ครั้งเดียวตอนสร้างบัญชี

    คืนค่า (รหัสผ่าน, สุ่มขึ้นมาเองหรือไม่)
    """
    from_env = os.getenv("ADMIN_PASSWORD", "").strip()
    if from_env:
        return from_env, False
    # รันในเครื่องด้วย compose ให้ใช้รหัสเดิม เพื่อไม่ให้เสียเวลาตอนพัฒนา
    if os.getenv("SERVE_WEB", "false").lower() != "true":
        return DEMO_PASSWORD, False
    return secrets.token_urlsafe(12), True


def seed_database(db: Session) -> None:
    # ถ้ามีข้อมูลอยู่แล้วไม่ต้องใส่ซ้ำ
    if db.scalar(select(User).limit(1)) is not None:
        print("มีข้อมูลอยู่แล้ว ข้ามขั้นตอน seed")
        return

    print("กำลังใส่ข้อมูลตัวอย่าง...")
    pw = hash_password(DEMO_PASSWORD)

    admin_pw, was_random = _admin_password()
    if was_random:
        print("=" * 62)
        print(f"  รหัสผ่านผู้ดูแลระบบ (admin) : {admin_pw}")
        print("  แสดงครั้งเดียวเท่านั้น — บันทึกไว้ หรือตั้ง ADMIN_PASSWORD เอง")
        print("=" * 62)

    # ---------- ผู้ใช้งาน ----------
    # โดเมนต้องเป็นโดเมนปกติ ห้ามใช้ .local / .test / .invalid / .localhost
    # เพราะ UserOut.email เป็น EmailStr ซึ่ง Pydantic ตรวจ "ตอนส่งออก" ด้วย
    # ถ้าโดเมนเป็นชนิดสงวน จะ ValidationError กลายเป็น 500 ทันทีที่ล็อกอินบัญชีนี้
    admin = User(username="admin", email="admin@bookvice.com",
                 password_hash=hash_password(admin_pw),
                 full_name="ผู้ดูแลระบบ", phone="0800000001", role="admin")
    mind = User(username="mind", email="mind@example.com", password_hash=pw,
                full_name="มายด์ ใจดี", phone="0812345678", role="customer")
    nong = User(username="nong", email="nong@example.com", password_hash=pw,
                full_name="น้อง สวยงาม", phone="0823456789", role="customer")
    spa_owner = User(username="spaowner", email="spa@example.com", password_hash=pw,
                     full_name="เจ้าของร้านสปา", phone="0834567890", role="owner")
    nail_owner = User(username="nailowner", email="nail@example.com", password_hash=pw,
                      full_name="เจ้าของร้านเล็บ", phone="0845678901", role="owner")
    db.add_all([admin, mind, nong, spa_owner, nail_owner])
    db.flush()

    # ---------- หมวดหมู่ ----------
    cats = [
        Category(name="สปา & นวด", slug="spa-massage"),
        Category(name="ทำเล็บ", slug="nail"),
        Category(name="ทำผม", slug="hair"),
        Category(name="คลินิกความงาม", slug="beauty-clinic"),
        Category(name="สักลาย", slug="tattoo"),
    ]
    db.add_all(cats)
    db.flush()

    # ---------- ร้าน ----------
    spa = Shop(
        owner_id=spa_owner.id, category_id=cats[0].id, name="Serene Spa อารีย์",
        description="สปาบรรยากาศเงียบสงบ นวดแผนไทยและอโรมา",
        address="123 ถ.พหลโยธิน", district="พญาไท", phone="021111111",
        open_time=time(10, 0), close_time=time(21, 0), is_certified=True,
    )
    nail = Shop(
        owner_id=nail_owner.id, category_id=cats[1].id, name="Nail Studio ทองหล่อ",
        description="ร้านทำเล็บสไตล์มินิมอล อุปกรณ์ผ่านการฆ่าเชื้อ",
        address="456 ซ.ทองหล่อ 10", district="วัฒนา", phone="022222222",
        open_time=time(11, 0), close_time=time(20, 0), is_certified=True,
    )
    clinic = Shop(
        owner_id=spa_owner.id, category_id=cats[3].id, name="GlowUp Clinic สยาม",
        description="คลินิกดูแลผิวหน้า ทีมแพทย์ผู้เชี่ยวชาญ",
        address="789 ถ.พระราม 1", district="ปทุมวัน", phone="023333333",
        open_time=time(10, 0), close_time=time(19, 0),
    )
    db.add_all([spa, nail, clinic])
    db.flush()

    # ---------- บริการ ----------
    thai_massage = Service(shop_id=spa.id, name="นวดแผนไทย 60 นาที",
                           description="นวดคลายกล้ามเนื้อโดยหมอนวดมืออาชีพ",
                           price=Decimal("500.00"), duration_minutes=60)
    aroma = Service(shop_id=spa.id, name="นวดอโรมา 90 นาที",
                    description="นวดน้ำมันหอมระเหย ผ่อนคลายลึก",
                    price=Decimal("1200.00"), duration_minutes=90)
    gel_nail = Service(shop_id=nail.id, name="ทำเล็บเจล มือ",
                       description="ทาสีเจลพร้อมตัดแต่งหนังรอบเล็บ",
                       price=Decimal("690.00"), duration_minutes=90)
    pvc_nail = Service(shop_id=nail.id, name="ต่อเล็บ PVC",
                       description="ต่อเล็บพร้อมเพ้นท์ลายตามแบบ",
                       price=Decimal("1500.00"), duration_minutes=120)
    facial = Service(shop_id=clinic.id, name="ทรีตเมนต์ผิวหน้า",
                     description="ทำความสะอาดผิวหน้าลึก พร้อมมาส์ก",
                     price=Decimal("1800.00"), duration_minutes=60)
    db.add_all([thai_massage, aroma, gel_nail, pvc_nail, facial])
    db.flush()

    # ---------- ช่าง / ผู้ให้บริการ ----------
    # work_days ใช้เลขวันแบบเดียวกับ JavaScript: 0=อาทิตย์ ... 6=เสาร์
    # ไม่ระบุ = ทำงานทุกวันที่ร้านเปิด · ไม่ระบุเวลา = ตามเวลาเปิด-ปิดร้าน
    spa_staff = [
        Staff(shop_id=spa.id, name="ช่างมิ้น", position="นักบำบัดอาวุโส",
              bio="ประสบการณ์นวดแผนไทย 8 ปี ถนัดแก้อาการปวดคอบ่าไหล่",
              work_days="1,2,3,4,5", work_start=time(10, 0), work_end=time(19, 0)),
        Staff(shop_id=spa.id, name="ช่างแนน", position="นักบำบัดอโรมา",
              bio="เชี่ยวชาญนวดน้ำมันหอมระเหยและการผ่อนคลายกล้ามเนื้อ",
              work_days="0,3,4,5,6", work_start=time(13, 0)),
        Staff(shop_id=spa.id, name="ช่างโบว์", position="นักบำบัด",
              bio="ถนัดนวดเท้าและนวดคลายเส้น"),
    ]
    nail_staff = [
        Staff(shop_id=nail.id, name="ช่างเจน", position="ช่างเล็บอาวุโส",
              bio="ถนัดงานเพ้นท์ลายละเอียดและเล็บสไตล์มินิมอล",
              work_days="2,3,4,5,6"),
        Staff(shop_id=nail.id, name="ช่างพลอย", position="ช่างเล็บ",
              bio="ถนัดต่อเล็บ PVC และงานแต่งหิน"),
    ]
    clinic_staff = [
        Staff(shop_id=clinic.id, name="พญ. ศิริพร", position="แพทย์ผิวหนัง",
              bio="แพทย์เฉพาะทางผิวหนัง ดูแลปัญหาสิวและฝ้า",
              work_days="1,3,5", work_start=time(11, 0), work_end=time(18, 0)),
    ]
    db.add_all(spa_staff + nail_staff + clinic_staff)
    db.flush()

    # ---------- การจอง ----------
    today = date.today()
    b1 = Booking(booking_code="BK00000001", user_id=mind.id, service_id=thai_massage.id,
                 shop_id=spa.id, staff_id=spa_staff[0].id,
                 booking_date=today + timedelta(days=7),
                 booking_time=time(14, 0), end_time=time(15, 0),
                 total_price=Decimal("500.00"), deposit_amount=Decimal("100.00"),
                 status="confirmed", note="ขอห้องส่วนตัว",
                 requirements="ขอแรงกลางค่อนไปทางเบา เน้นบ่าและสะบัก",
                 health_note="แพ้น้ำหอมกลิ่นแรง")
    b2 = Booking(booking_code="BK00000002", user_id=mind.id, service_id=gel_nail.id,
                 shop_id=nail.id, staff_id=nail_staff[0].id,
                 booking_date=today + timedelta(days=12),
                 booking_time=time(13, 0), end_time=time(14, 30),
                 total_price=Decimal("690.00"), deposit_amount=Decimal("138.00"),
                 status="pending",
                 requirements="อยากได้สีโทนเบจอมชมพู ทรงสั้นมน")
    # การจองที่ใช้บริการแล้ว ใช้ทดสอบการเขียนรีวิว
    b3 = Booking(booking_code="BK00000003", user_id=nong.id, service_id=aroma.id,
                 shop_id=spa.id, staff_id=spa_staff[1].id,
                 booking_date=today - timedelta(days=14),
                 booking_time=time(16, 0), end_time=time(17, 30),
                 total_price=Decimal("1200.00"), deposit_amount=Decimal("240.00"),
                 status="completed")
    db.add_all([b1, b2, b3])
    db.flush()

    # ---------- รีวิว ----------
    review = Review(booking_id=b3.id, user_id=nong.id, shop_id=spa.id,
                    service_id=aroma.id, staff_id=spa_staff[1].id,
                    rating=5, staff_rating=5,
                    rating_cleanliness=5, rating_punctuality=4, rating_value=4,
                    comment="บริการดีมาก ร้านสะอาด พนักงานสุภาพ จะกลับมาใช้บริการอีกแน่นอน",
                    reply="ขอบคุณมากค่ะ ช่างแนนฝากขอบคุณด้วยนะคะ ไว้มาใหม่ค่ะ",
                    replied_at=datetime.now(timezone.utc))
    db.add(review)

    spa.rating_avg = Decimal("5.00")
    spa.rating_count = 1
    spa_staff[1].rating_avg = Decimal("5.00")
    spa_staff[1].rating_count = 1

    db.commit()
    print(f"ใส่ข้อมูลตัวอย่างเรียบร้อย (รหัสผ่านทุกบัญชี: {DEMO_PASSWORD})")
