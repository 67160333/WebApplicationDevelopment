"""ปรับโครงสร้างตารางให้ทันสมัยโดยไม่ลบข้อมูลเดิม

`Base.metadata.create_all()` สร้างได้เฉพาะ "ตารางใหม่" เท่านั้น
ถ้าเราเพิ่มคอลัมน์ในตารางที่มีอยู่แล้ว มันจะไม่ทำอะไรเลย
ไฟล์นี้จึงเติมคอลัมน์และเงื่อนไขที่ขาดให้เอง

ทุกคำสั่งเขียนแบบ "รันซ้ำกี่รอบก็ได้ผลเหมือนเดิม" (idempotent)
จึงปลอดภัยที่จะให้ทำงานทุกครั้งที่ระบบเริ่มต้น
"""

from sqlalchemy import text
from sqlalchemy.engine import Engine

# ---------- คอลัมน์ที่ต้องมี : (ตาราง, ชื่อคอลัมน์, ชนิดข้อมูลและค่าเริ่มต้น) ----------
COLUMNS: list[tuple[str, str, str]] = [
    # ตารางเวลาทำงานและคะแนนของช่าง
    ("staff", "work_days",  "VARCHAR(20)"),
    ("staff", "work_start", "TIME"),
    ("staff", "work_end",   "TIME"),
    ("staff", "rating_avg", "NUMERIC(3,2) NOT NULL DEFAULT 0.00"),
    ("staff", "rating_count", "INTEGER NOT NULL DEFAULT 0"),
    # รีวิวที่ครอบคลุมมากขึ้น
    ("reviews", "service_id",         "INTEGER"),
    ("reviews", "staff_id",           "INTEGER"),
    ("reviews", "staff_rating",       "INTEGER"),
    ("reviews", "rating_cleanliness", "INTEGER"),
    ("reviews", "rating_punctuality", "INTEGER"),
    ("reviews", "rating_value",       "INTEGER"),
    ("reviews", "reply",              "VARCHAR(1000)"),
    ("reviews", "replied_at",         "TIMESTAMPTZ"),
    # ลูกค้าที่ไม่มีบัญชี — เจ้าของร้านจองแทนให้
    ("bookings", "guest_name",  "VARCHAR(150)"),
    ("bookings", "guest_phone", "VARCHAR(20)"),
    # พิกัดร้านสำหรับแผนที่และการหาร้านใกล้ฉัน
    ("shops", "latitude",  "NUMERIC(9,6)"),
    ("shops", "longitude", "NUMERIC(9,6)"),
    # คำเรียกทรัพยากรที่จองได้ ต่างกันตามหมวด (ช่าง / คอร์ท / สนาม / พนักงานส่ง)
    ("categories", "resource_label", "VARCHAR(30) NOT NULL DEFAULT 'ช่าง'"),
    # บริการแบบเรียกใช้ทันที ไม่ต้องเลือกวันเวลา
    ("services", "booking_mode", "VARCHAR(10) NOT NULL DEFAULT 'scheduled'"),
    ("services", "price_per_km", "NUMERIC(10,2) NOT NULL DEFAULT 0.00"),
    # ที่อยู่รับ-ส่ง สำหรับบริการส่งของด่วน
    ("bookings", "pickup_address",  "VARCHAR(300)"),
    ("bookings", "dropoff_address", "VARCHAR(300)"),
    ("bookings", "distance_km",     "NUMERIC(6,2)"),
    # ล็อกช่องเวลาเมื่อจ่ายเงินแล้วเท่านั้น (ดูคำอธิบายเต็มใน models.py)
    ("bookings", "holds_slot",       "BOOLEAN NOT NULL DEFAULT FALSE"),
    ("bookings", "cancelled_by",     "VARCHAR(20)"),
    ("bookings", "cancellation_fee", "NUMERIC(10,2) NOT NULL DEFAULT 0.00"),
    # ---------- ก๊วน : เปิดรับคนไปด้วยกัน ----------
    # ค่าเริ่มต้น 0 แปลว่าคิวเก่าทั้งหมดไม่ได้เปิดก๊วน ซึ่งถูกต้องอยู่แล้ว
    # ไม่ต้องเติมย้อนหลังเหมือนตอนเพิ่ม holds_slot
    ("bookings", "open_slots",  "INTEGER NOT NULL DEFAULT 0"),
    ("bookings", "share_price", "NUMERIC(10,2) NOT NULL DEFAULT 0.00"),
    ("bookings", "match_note",  "VARCHAR(300)"),
    # กลุ่มใหญ่ของหมวด ใช้แยกทางเข้าในหน้าเว็บ — seed เป็นคนเติมค่าจริงให้
    ("categories", "group_key", "VARCHAR(10) NOT NULL DEFAULT 'care'"),
]

# ---------- กุญแจนอกและดัชนี : (ชื่อ, คำสั่งสร้าง) ----------
CONSTRAINTS: list[tuple[str, str]] = [
    (
        "fk_reviews_service",
        "ALTER TABLE reviews ADD CONSTRAINT fk_reviews_service "
        "FOREIGN KEY (service_id) REFERENCES services(id) ON DELETE SET NULL",
    ),
    (
        "fk_reviews_staff",
        "ALTER TABLE reviews ADD CONSTRAINT fk_reviews_staff "
        "FOREIGN KEY (staff_id) REFERENCES staff(id) ON DELETE SET NULL",
    ),
    (
        "ck_reviews_staff_rating",
        "ALTER TABLE reviews ADD CONSTRAINT ck_reviews_staff_rating "
        "CHECK (staff_rating IS NULL OR staff_rating BETWEEN 1 AND 5)",
    ),
    (
        "ck_reviews_cleanliness",
        "ALTER TABLE reviews ADD CONSTRAINT ck_reviews_cleanliness "
        "CHECK (rating_cleanliness IS NULL OR rating_cleanliness BETWEEN 1 AND 5)",
    ),
    (
        "ck_reviews_punctuality",
        "ALTER TABLE reviews ADD CONSTRAINT ck_reviews_punctuality "
        "CHECK (rating_punctuality IS NULL OR rating_punctuality BETWEEN 1 AND 5)",
    ),
    (
        "ck_reviews_value",
        "ALTER TABLE reviews ADD CONSTRAINT ck_reviews_value "
        "CHECK (rating_value IS NULL OR rating_value BETWEEN 1 AND 5)",
    ),
    (
        "ck_services_mode",
        "ALTER TABLE services ADD CONSTRAINT ck_services_mode "
        "CHECK (booking_mode IN ('scheduled','instant'))",
    ),
]

# ---------- เงื่อนไขที่ต้อง "สร้างใหม่" เพราะของเดิมตั้งค่าผิด ----------
# (ชื่อเงื่อนไข, คำสั่งลบของเดิม, คำสั่งสร้างใหม่)
RECREATE: list[tuple[str, str, str]] = [
    (
        # เดิม bookings.service_id ไม่มี ON DELETE ทำให้ลบร้านที่มีคิวไม่ได้
        # ต้องหาชื่อ constraint จริงก่อน เพราะ PostgreSQL ตั้งชื่อให้เอง
        "bookings_service_id_fkey",
        "ALTER TABLE bookings DROP CONSTRAINT IF EXISTS bookings_service_id_fkey",
        "ALTER TABLE bookings ADD CONSTRAINT bookings_service_id_fkey "
        "FOREIGN KEY (service_id) REFERENCES services(id) ON DELETE CASCADE",
    ),
]

# ---------- ดัชนีที่ต้องถอดทิ้งเพราะเปลี่ยนกติกา ----------
DROP_INDEXES: list[str] = [
    # เดิมล็อกไม่ให้จ่ายซ้ำ "ทุกชนิด" ทำให้ยอดคงเหลือจ่ายเก็บตกรอบสองไม่ได้
    # ตัวใหม่ (uq_payment_booking_deposit) ล็อกเฉพาะมัดจำ
    "DROP INDEX IF EXISTS uq_payment_booking_kind",
    # เดิมกันคิวซ้ำเวลาโดยดูแค่สถานะ ทำให้คิวที่ยังไม่จ่ายก็กันเวลาไว้ด้วย
    # ตัวใหม่ (uq_booking_held_slot) กันเฉพาะคิวที่ล็อกช่องเวลาแล้ว
    "DROP INDEX IF EXISTS uq_booking_active_slot",
]

INDEXES: list[str] = [
    "CREATE UNIQUE INDEX IF NOT EXISTS uq_payment_booking_deposit ON payments (booking_id) "
    "WHERE status = 'paid' AND kind = 'deposit'",
    # ด่านสุดท้ายกันสองคนจ่ายช่องเวลาเดียวกันพร้อมกันเป๊ะ ๆ
    "CREATE UNIQUE INDEX IF NOT EXISTS uq_booking_held_slot "
    "ON bookings (shop_id, staff_id, booking_date, booking_time) "
    "WHERE holds_slot AND status IN ('pending','confirmed')",
    "CREATE INDEX IF NOT EXISTS ix_reviews_staff_id ON reviews (staff_id)",
    "CREATE INDEX IF NOT EXISTS ix_reviews_service_id ON reviews (service_id)",
    "CREATE INDEX IF NOT EXISTS ix_notif_user_unread ON notifications (user_id, is_read)",
    # ร้านที่มีพิกัดเท่านั้นที่ต้องใช้ตอนค้นหาร้านใกล้ฉัน จึงทำ partial index ให้เล็กลง
    "CREATE INDEX IF NOT EXISTS ix_shops_geo ON shops (latitude, longitude) "
    "WHERE latitude IS NOT NULL AND longitude IS NOT NULL",
]


def run_migrations(engine: Engine) -> None:
    """เติมคอลัมน์ เงื่อนไข และดัชนีที่ยังไม่มีในฐานข้อมูล"""
    added: list[str] = []

    with engine.begin() as conn:
        # 1) คอลัมน์ — PostgreSQL รองรับ IF NOT EXISTS อยู่แล้ว
        for table, column, ddl in COLUMNS:
            exists = conn.scalar(
                text(
                    "SELECT 1 FROM information_schema.columns "
                    "WHERE table_name = :t AND column_name = :c"
                ),
                {"t": table, "c": column},
            )
            if exists:
                continue
            conn.execute(text(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column} {ddl}"))
            added.append(f"{table}.{column}")

        # 2) เงื่อนไข — PostgreSQL ไม่มี ADD CONSTRAINT IF NOT EXISTS จึงต้องเช็กเอง
        for name, ddl in CONSTRAINTS:
            exists = conn.scalar(
                text("SELECT 1 FROM pg_constraint WHERE conname = :n"), {"n": name}
            )
            if exists:
                continue
            conn.execute(text(ddl))
            added.append(name)

        # 2.5) เงื่อนไขที่ต้องสร้างใหม่ให้ถูกต้อง
        for name, drop_sql, create_sql in RECREATE:
            # ตรวจว่าเงื่อนไขเดิมตั้ง ON DELETE ไว้แล้วหรือยัง
            rule = conn.scalar(
                text(
                    "SELECT confdeltype FROM pg_constraint WHERE conname = :n AND contype = 'f'"
                ),
                {"n": name},
            )
            # 'c' = CASCADE · 'a' = NO ACTION (ค่าเริ่มต้นที่ผิด)
            if rule == "c":
                continue
            conn.execute(text(drop_sql))
            conn.execute(text(create_sql))
            added.append(f"{name} (ตั้ง ON DELETE CASCADE)")

        # 3) ดัชนี — ถอดตัวที่เลิกใช้ก่อน แล้วค่อยสร้างชุดปัจจุบัน
        for ddl in DROP_INDEXES:
            conn.execute(text(ddl))
        for ddl in INDEXES:
            conn.execute(text(ddl))

        # 3.2) เติมค่า holds_slot ให้คิวที่มีอยู่ก่อนจะมีคอลัมน์นี้
        #
        # คอลัมน์ใหม่มีค่าเริ่มต้นเป็น FALSE ถ้าไม่เติมย้อนหลัง คิวเก่าทุกคิว
        # จะกลายเป็น "ไม่ล็อกเวลา" ทันทีที่อัปเดต — ตารางร้านที่เคยเต็มจะว่างโล่ง
        # และคิวที่จ่ายเงินมาแล้วจะถูกคนอื่นจองทับได้ ซึ่งเสียหายจริง
        #
        # เกณฑ์: คิวที่ร้านยืนยันแล้ว หรือมีเงินเข้ามาแล้ว = ล็อกไว้
        # เขียนแบบรันซ้ำกี่รอบก็ได้ผลเดิม (แถวที่เป็น TRUE อยู่แล้วไม่ถูกแตะ)
        held = conn.execute(
            text(
                "UPDATE bookings SET holds_slot = TRUE "
                "WHERE holds_slot = FALSE AND status IN ('pending','confirmed') AND ("
                "  status = 'confirmed'"
                "  OR EXISTS (SELECT 1 FROM payments p "
                "             WHERE p.booking_id = bookings.id AND p.status = 'paid')"
                ")"
            )
        ).rowcount
        if held:
            added.append(f"ตั้งค่าล็อกช่องเวลาให้คิวเดิม {held} คิว")

        # 3.5) เก็บชื่อแบรนด์เดิมที่ยังค้างอยู่ใน "ข้อมูล" ไม่ใช่ในโค้ด
        #
        # seed_database() ทำงานครั้งเดียวตอนตารางยังว่าง การแก้ไฟล์ seed
        # จึงไม่ย้อนไปแก้แถวที่สร้างไว้ก่อนหน้า ต้องมาแก้ตรงนี้แทน
        # อีเมลของบัญชี admin แสดงอยู่ในตารางผู้ใช้หน้า admin.html — ผู้ใช้เห็นจริง
        #
        # เขียนแบบมีเงื่อนไขกันชนกับอีเมลที่มีอยู่แล้ว (คอลัมน์นี้ unique)
        # และรันซ้ำกี่รอบก็ไม่เปลี่ยนอะไรเพิ่ม
        # รวมทุกค่าเก่าที่เคยใช้ ไล่แก้ให้เป็นค่าปัจจุบัน
        # `admin@bookvice.local` เคยถูกใช้อยู่ช่วงสั้น ๆ แล้วต้องเลิกใช้
        # เพราะ `.local` เป็นโดเมนชนิดสงวน ทำให้ EmailStr ตรวจไม่ผ่านตอนส่งออก
        # และบัญชี admin ล็อกอินไม่ได้ (ได้ 500)
        ADMIN_EMAIL = "admin@bookvice.com"
        renamed = 0
        for stale in ("admin@glowgo.com", "admin@bookvice.local"):
            renamed += conn.execute(
                text(
                    "UPDATE users SET email = :new WHERE email = :old "
                    "AND NOT EXISTS (SELECT 1 FROM users u2 WHERE u2.email = :new)"
                ),
                {"old": stale, "new": ADMIN_EMAIL},
            ).rowcount

        # ชื่อร้านที่ seed ไว้ก่อนเปลี่ยนแบรนด์
        # ต้องแก้ในฐานข้อมูลเสมอ ไม่งั้น seed_venues() จะมองว่าเป็นร้านใหม่
        # แล้วสร้างซ้ำทั้งชุด (ดูหัวข้อ "กับดักที่ทำให้ข้อมูลซ้ำ" ใน PROJECT_CONTEXT)
        renamed += conn.execute(
            text(
                "UPDATE shops SET name = replace(name, 'GlowGo', 'Bookvice') "
                "WHERE name LIKE '%GlowGo%'"
            )
        ).rowcount

        # 4) เติมข้อมูลย้อนหลังให้รีวิวเก่า ที่ยังไม่รู้ว่าเป็นของบริการ/ช่างไหน
        filled = conn.execute(
            text(
                "UPDATE reviews r SET service_id = b.service_id, staff_id = b.staff_id "
                "FROM bookings b WHERE r.booking_id = b.id AND r.service_id IS NULL"
            )
        ).rowcount

        # 5) คำนวณคะแนนช่างใหม่จากรีวิวที่มีอยู่
        conn.execute(
            text(
                """
                UPDATE staff s SET
                    rating_avg = COALESCE(x.avg_rating, 0),
                    rating_count = COALESCE(x.n, 0)
                FROM (
                    SELECT st.id AS staff_id,
                           ROUND(AVG(r.staff_rating)::numeric, 2) AS avg_rating,
                           COUNT(r.id) AS n
                    FROM staff st
                    LEFT JOIN reviews r
                           ON r.staff_id = st.id AND r.staff_rating IS NOT NULL
                    GROUP BY st.id
                ) x
                WHERE s.id = x.staff_id
                """
            )
        )

    if added:
        print(f"ปรับโครงสร้างฐานข้อมูล: เพิ่ม {', '.join(added)}")
    if filled:
        print(f"ปรับโครงสร้างฐานข้อมูล: เติมข้อมูลย้อนหลังให้รีวิวเก่า {filled} รายการ")
    if renamed:
        print(f"ปรับโครงสร้างฐานข้อมูล: แก้ชื่อแบรนด์เดิมที่ค้างอยู่ในข้อมูล {renamed} แถว")
