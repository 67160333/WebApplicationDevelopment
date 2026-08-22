"""ตารางในฐานข้อมูล (SQLAlchemy models) ของระบบ Bookvice"""

from datetime import date, datetime, time, timezone
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Time,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    """ผู้ใช้งานระบบ — role: customer (ลูกค้า) / owner (เจ้าของร้าน) / admin (ผู้ดูแล)"""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(150), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(150))
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    role: Mapped[str] = mapped_column(String(20), default="customer", index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

    shops: Mapped[list["Shop"]] = relationship(back_populates="owner", cascade="all, delete-orphan")
    bookings: Mapped[list["Booking"]] = relationship(back_populates="user", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint("role IN ('customer','owner','admin')", name="ck_users_role"),
    )


class TokenBlacklist(Base):
    """เก็บ token ที่ logout แล้ว เพื่อไม่ให้นำกลับมาใช้ได้อีก"""

    __tablename__ = "token_blacklist"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    token: Mapped[str] = mapped_column(String(512), index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Category(Base):
    """หมวดหมู่บริการ เช่น สปา ทำเล็บ คลินิก"""

    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    # คำเรียก "ทรัพยากรที่จองได้" ของหมวดนี้ — ร้านความงามเรียก "ช่าง"
    # แต่สนามแบดต้องเรียก "คอร์ท" และสนามบอลเรียก "สนาม"
    # เก็บไว้ที่หมวดเพราะทุกร้านในหมวดเดียวกันใช้คำเดียวกันเสมอ
    # ---- กลุ่มใหญ่ที่ใช้แยกทางเข้าในหน้าเว็บ ----
    # แบ่งตาม "รูปแบบการใช้บริการ" ไม่ใช่ตามอุตสาหกรรม เพราะผู้ใช้คิดแบบนั้น
    #   care = ไปที่ร้าน มีคนทำให้ จองคนเดียว
    #   play = จองสถานที่ ไปกันเป็นกลุ่ม เปิดก๊วนได้
    #   auto = ฝากของไว้แล้วรอ งานยาวหลายชั่วโมง
    #   come = ไม่มีปฏิทิน เรียกแล้วมาหาถึงที่ คิดเงินตามระยะทาง
    #
    # เก็บในฐานข้อมูลแทนที่จะ hard-code ในหน้าเว็บ เพราะถ้าเพิ่มหมวดใหม่
    # จะได้ไม่ต้องไปตามแก้หลายไฟล์ (ปัญหาที่เคยเจอกับ TEAM_CATEGORIES)
    # ตั้งชื่อ group_key ไม่ใช่ group เพราะ "group" เป็นคำสงวนของ SQL (GROUP BY)
    # ถ้าใช้ชื่อนั้น คำสั่ง ALTER TABLE ตอน migrate จะพังทันที
    group_key: Mapped[str] = mapped_column(String(10), default="care", index=True)
    resource_label: Mapped[str] = mapped_column(String(30), default="ช่าง")

    shops: Mapped[list["Shop"]] = relationship(back_populates="category")


class Shop(Base):
    """ร้าน / ผู้ให้บริการ"""

    __tablename__ = "shops"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"), index=True)
    name: Mapped[str] = mapped_column(String(150), index=True)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    district: Mapped[str | None] = mapped_column(String(100), index=True, nullable=True)
    province: Mapped[str] = mapped_column(String(100), default="กรุงเทพมหานคร")
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    # พิกัดสำหรับแสดงบนแผนที่และคำนวณระยะทาง
    # Numeric(9,6) พอสำหรับความละเอียดระดับเมตร (ทศนิยม 6 ตำแหน่ง ≈ 0.11 เมตร)
    latitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6), nullable=True)
    longitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6), nullable=True)
    open_time: Mapped[time] = mapped_column(Time, default=time(10, 0))
    close_time: Mapped[time] = mapped_column(Time, default=time(20, 0))
    is_certified: Mapped[bool] = mapped_column(Boolean, default=False)
    rating_avg: Mapped[Decimal] = mapped_column(Numeric(3, 2), default=Decimal("0.00"))
    rating_count: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

    owner: Mapped["User"] = relationship(back_populates="shops")
    category: Mapped["Category"] = relationship(back_populates="shops")
    services: Mapped[list["Service"]] = relationship(back_populates="shop", cascade="all, delete-orphan")
    reviews: Mapped[list["Review"]] = relationship(back_populates="shop", cascade="all, delete-orphan")
    staff_members: Mapped[list["Staff"]] = relationship(back_populates="shop", cascade="all, delete-orphan")
    closures: Mapped[list["ShopClosure"]] = relationship(back_populates="shop", cascade="all, delete-orphan")
    images: Mapped[list["ShopImage"]] = relationship(
        back_populates="shop",
        cascade="all, delete-orphan",
        order_by="ShopImage.sort_order, ShopImage.id",
    )


class ShopImage(Base):
    """รูปภาพของร้าน — เก็บเฉพาะ "ชื่อไฟล์" ในฐานข้อมูล

    ตัวไฟล์จริงอยู่บนดิสก์ที่ /app/uploads/shops/{shop_id}/{filename}
    เหตุผลที่ไม่เก็บรูปเป็น binary ลงฐานข้อมูล:
      - ฐานข้อมูลจะบวมเร็วมาก สำรองข้อมูลช้า
      - เสิร์ฟไฟล์ตรงจากดิสก์ให้เบราว์เซอร์แคชได้ ไม่ต้องผ่าน query ทุกครั้ง
    """

    __tablename__ = "shop_images"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    shop_id: Mapped[int] = mapped_column(ForeignKey("shops.id", ondelete="CASCADE"), index=True)
    filename: Mapped[str] = mapped_column(String(120))
    caption: Mapped[str | None] = mapped_column(String(200), nullable=True)
    # รูปปกใช้โชว์บนการ์ดร้านในหน้าค้นหา — มีได้ร้านละ 1 รูป
    is_cover: Mapped[bool] = mapped_column(Boolean, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    width: Mapped[int] = mapped_column(Integer, default=0)
    height: Mapped[int] = mapped_column(Integer, default=0)
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

    shop: Mapped["Shop"] = relationship(back_populates="images")

    __table_args__ = (
        # ชื่อไฟล์ต้องไม่ซ้ำภายในร้านเดียวกัน กันการเขียนทับกันเอง
        Index("uq_shop_image_file", "shop_id", "filename", unique=True),
        # ร้านหนึ่งมีรูปปกได้รูปเดียว บังคับที่ระดับฐานข้อมูลเลย
        # เพราะถ้าปล่อยให้โค้ดคุมอย่างเดียว การกดสองครั้งพร้อมกันอาจได้ปกซ้อนกัน
        Index(
            "uq_shop_one_cover",
            "shop_id",
            unique=True,
            postgresql_where=text("is_cover = true"),
        ),
    )


class Service(Base):
    """บริการที่แต่ละร้านเปิดให้จอง"""

    __tablename__ = "services"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    shop_id: Mapped[int] = mapped_column(ForeignKey("shops.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(150))
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    duration_minutes: Mapped[int] = mapped_column(Integer, default=60)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # วิธีจอง — scheduled คือเลือกวันเวลาจากปฏิทิน (ค่าเริ่มต้น)
    #          instant คือเรียกใช้ทันที ไม่มีปฏิทิน เช่น บริการส่งของด่วน
    booking_mode: Mapped[str] = mapped_column(String(10), default="scheduled")
    # ค่าบริการต่อกิโลเมตร ใช้เฉพาะบริการแบบเรียกทันทีที่คิดตามระยะทาง
    price_per_km: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0.00"))

    shop: Mapped["Shop"] = relationship(back_populates="services")
    # passive_deletes บอก SQLAlchemy ว่า "ไม่ต้องโหลดคิวขึ้นมาแก้เอง"
    # ปล่อยให้ ON DELETE CASCADE ของฐานข้อมูลจัดการ
    # ถ้าไม่ใส่ SQLAlchemy จะสั่ง UPDATE bookings SET service_id = NULL ก่อน แล้วพัง
    bookings: Mapped[list["Booking"]] = relationship(
        back_populates="service", passive_deletes=True
    )

    __table_args__ = (
        CheckConstraint("booking_mode IN ('scheduled','instant')", name="ck_services_mode"),
    )


class Staff(Base):
    """ช่าง / ผู้ให้บริการของแต่ละร้าน — ลูกค้าเลือกได้ตอนจอง"""

    __tablename__ = "staff"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    shop_id: Mapped[int] = mapped_column(ForeignKey("shops.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    position: Mapped[str | None] = mapped_column(String(100), nullable=True)
    bio: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # ---------- ตารางเวลาทำงานของช่างคนนี้ ----------
    # work_days เก็บเลขวันคั่นด้วยจุลภาค 0=อาทิตย์ ... 6=เสาร์ เช่น "1,2,3,4,5" = จันทร์-ศุกร์
    # ว่างไว้ = ทำงานทุกวันที่ร้านเปิด
    work_days: Mapped[str | None] = mapped_column(String(20), nullable=True)
    # เวลาเข้า-ออกงาน ว่างไว้ = ตามเวลาเปิด-ปิดของร้าน
    work_start: Mapped[time | None] = mapped_column(Time, nullable=True)
    work_end: Mapped[time | None] = mapped_column(Time, nullable=True)

    # ---------- คะแนนของช่าง (คำนวณใหม่ทุกครั้งที่มีรีวิว) ----------
    rating_avg: Mapped[Decimal] = mapped_column(Numeric(3, 2), default=Decimal("0.00"))
    rating_count: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

    shop: Mapped["Shop"] = relationship(back_populates="staff_members")
    # เช่นกัน — คอลัมน์ staff_id เป็น ON DELETE SET NULL อยู่แล้ว
    # ให้ฐานข้อมูลเซ็ตเอง คิวเก่าจะกลายเป็น "ไม่ระบุผู้ให้บริการ" แทนที่จะหายไป
    bookings: Mapped[list["Booking"]] = relationship(
        back_populates="staff", passive_deletes=True
    )
    reviews: Mapped[list["Review"]] = relationship(back_populates="staff")


class Notification(Base):
    """แจ้งเตือนในเว็บ — เก็บทุกเหตุการณ์ที่ผู้ใช้ควรรู้ โดยไม่ต้องส่งอีเมลหรือ SMS

    kind ใช้เลือกไอคอนและสีฝั่งหน้าเว็บ:
    booking_confirmed / booking_cancelled / booking_completed
    booking_new (แจ้งเจ้าของร้านว่ามีคิวเข้ามา) / booking_moved / review_reply
    """

    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(40))
    title: Mapped[str] = mapped_column(String(150))
    body: Mapped[str | None] = mapped_column(String(400), nullable=True)
    # ลิงก์ที่จะพาไปเมื่อกดการแจ้งเตือน เช่น bookings.html
    link: Mapped[str | None] = mapped_column(String(200), nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


class ShopClosure(Base):
    """วันที่ร้านปิดเป็นกรณีพิเศษ เช่น วันหยุดยาว ปรับปรุงร้าน

    ต่างจากเวลาเปิด-ปิดประจำวันตรงที่อันนี้เป็น "รายวัน"
    ระบบจะไม่เปิดให้จองในวันที่อยู่ในตารางนี้
    """

    __tablename__ = "shop_closures"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    shop_id: Mapped[int] = mapped_column(ForeignKey("shops.id", ondelete="CASCADE"), index=True)
    closed_date: Mapped[date] = mapped_column(Date, index=True)
    reason: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

    shop: Mapped["Shop"] = relationship(back_populates="closures")

    __table_args__ = (
        # ร้านเดียวกัน วันเดียวกัน บันทึกซ้ำไม่ได้
        Index("uq_closure_shop_date", "shop_id", "closed_date", unique=True),
    )


class Booking(Base):
    """การจองคิว — status: pending / confirmed / completed / cancelled"""

    __tablename__ = "bookings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    booking_code: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    # ต้องมี ondelete="CASCADE" — ถ้าไม่มี ฐานข้อมูลจะห้ามลบบริการที่มีคิวผูกอยู่
    # และ SQLAlchemy จะพยายามเซ็ตคอลัมน์นี้เป็น NULL ทั้งที่ห้ามว่าง ทำให้ลบร้านไม่ได้เลย
    service_id: Mapped[int] = mapped_column(
        ForeignKey("services.id", ondelete="CASCADE"), index=True
    )
    shop_id: Mapped[int] = mapped_column(ForeignKey("shops.id", ondelete="CASCADE"), index=True)
    staff_id: Mapped[int | None] = mapped_column(
        ForeignKey("staff.id", ondelete="SET NULL"), index=True, nullable=True
    )
    booking_date: Mapped[date] = mapped_column(Date, index=True)
    booking_time: Mapped[time] = mapped_column(Time)
    # เวลาสิ้นสุด คำนวณจากระยะเวลาบริการ ใช้ตรวจว่าคิวชนกันไหม
    end_time: Mapped[time] = mapped_column(Time)
    total_price: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    deposit_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0.00"))
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # ความต้องการเฉพาะของลูกค้า เช่น ความยาว/สี/แบบที่อยากได้
    requirements: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    # ลิงก์รูปตัวอย่างที่ลูกค้าอยากได้
    reference_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # ข้อมูลสุขภาพที่ร้านควรรู้ เช่น แพ้สารเคมี ตั้งครรภ์ โรคประจำตัว
    health_note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # ลูกค้าที่ไม่มีบัญชีในระบบ — เจ้าของร้านกดจองแทนให้ (walk-in / โทรมาจอง)
    guest_name: Mapped[str | None] = mapped_column(String(150), nullable=True)
    guest_phone: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # คิวนี้ "ล็อกช่องเวลา" ไว้แล้วหรือยัง
    #
    # กติกา: ช่องเวลาจะปิดไม่ให้คนอื่นจองก็ต่อเมื่อมีการชำระเงินเข้ามาแล้วเท่านั้น
    # คิวที่กดจองไว้เฉย ๆ แต่ยังไม่จ่าย จะไม่กันเวลาให้ใคร ลูกค้าคนอื่นเลือกเวลาเดียวกัน
    # ได้ตามปกติ ใครจ่ายก่อนได้ก่อน
    #
    # ทำไมต้องเป็นคอลัมน์ ไม่คำนวณสด ๆ จากตาราง payments:
    #   1. `_busy_intervals` ถูกเรียกทุกครั้งที่เปิดหน้าจอง ถ้าต้อง join ตารางเงิน
    #      ทุกครั้งจะช้าโดยไม่จำเป็น
    #   2. unique index ระดับฐานข้อมูล (uq_booking_held_slot) อ้างตารางอื่นไม่ได้
    #      ต้องมีคอลัมน์อยู่ในตารางเดียวกันเท่านั้น ซึ่งเป็นด่านสุดท้ายที่กัน
    #      การจองชนกันตอนสองคนกดพร้อมกันเป๊ะ ๆ
    #
    # ตั้งเป็น True เมื่อ: มีการชำระเงิน · ร้านกดจองแทนลูกค้าหน้าร้าน · งานส่งด่วน
    # · ร้านกดยืนยันคิวเอง   ตั้งกลับเป็น False เมื่อคิวถูกยกเลิก
    holds_slot: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # ---- การยกเลิก ----
    # ใครเป็นคนยกเลิก: customer / shop / admin — ใช้ตัดสินว่าต้องหักค่ามัดจำไหม
    cancelled_by: Mapped[str | None] = mapped_column(String(20), nullable=True)
    # ยอดที่ถูกหักจริงตอนยกเลิก (= ค่ามัดจำที่จ่ายมาแล้ว) เก็บไว้เพื่อออกรายงานและ
    # เพื่อให้ร้านรู้ว่าต้องคืนเงินลูกค้าเท่าไหร่กันแน่ = ที่จ่ายมา - ที่ถูกหัก
    cancellation_fee: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), default=Decimal("0.00"), nullable=False
    )

    # ---- ใช้เฉพาะบริการส่งของด่วน ----
    # ---- ก๊วน: เปิดรับคนเพิ่มหรือไม่ ----
    # 0 = ไม่ได้เปิดก๊วน · มากกว่า 0 = ยังรับได้อีกกี่คน
    # เก็บเป็น "จำนวนที่ต้องการทั้งหมด" ไม่ใช่ "ที่เหลือ" เพราะที่เหลือคำนวณจาก
    # จำนวนคนที่ลงชื่อแล้วได้ตลอด ถ้าเก็บสองค่าจะมีโอกาสไม่ตรงกัน
    open_slots: Mapped[int] = mapped_column(Integer, default=0)
    # ราคาที่คนเข้าร่วมต้องจ่ายต่อคน เจ้าของก๊วนกำหนดเอง
    share_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)
    # ข้อความประกาศ เช่น "ขาดอีก 4 คน มือใหม่ก็มาได้"
    match_note: Mapped[str | None] = mapped_column(String(300), nullable=True)

    pickup_address: Mapped[str | None] = mapped_column(String(300), nullable=True)
    dropoff_address: Mapped[str | None] = mapped_column(String(300), nullable=True)
    distance_km: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

    user: Mapped["User"] = relationship(back_populates="bookings")
    service: Mapped["Service"] = relationship(back_populates="bookings")
    staff: Mapped["Staff | None"] = relationship(back_populates="bookings")
    review: Mapped["Review | None"] = relationship(back_populates="booking", cascade="all, delete-orphan")
    joins: Mapped[list["MatchJoin"]] = relationship(
        back_populates="booking", cascade="all, delete-orphan"
    )
    payments: Mapped[list["Payment"]] = relationship(
        back_populates="booking", cascade="all, delete-orphan", order_by="Payment.id"
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('pending','confirmed','completed','cancelled')",
            name="ck_bookings_status",
        ),
        # กันจองซ้ำช่องเวลาเดียวกันของช่างคนเดียวกัน
        #
        # นับเฉพาะคิวที่ "ล็อกช่องเวลาไว้แล้ว" (holds_slot) และยังใช้งานอยู่
        # คิวที่ยังไม่จ่ายจึงซ้ำเวลากันได้หลายคิว ซึ่งเป็นกติกาที่ตั้งใจ —
        # ใครจ่ายก่อนได้ก่อน ส่วนคนที่เหลือจะถูกปฏิเสธตอนกดจ่าย
        #
        # ตัวนี้เป็นด่านสุดท้ายระดับฐานข้อมูล กันกรณีสองคนกดจ่ายพร้อมกันเป๊ะ ๆ
        # จนโค้ดตรวจไม่ทัน ส่วนการชนแบบ "คาบเกี่ยว" (ไม่ใช่เวลาเริ่มตรงกัน)
        # ตรวจในโค้ดด้วย _assert_free
        Index(
            "uq_booking_held_slot",
            "shop_id",
            "staff_id",
            "booking_date",
            "booking_time",
            unique=True,
            postgresql_where=text("holds_slot AND status IN ('pending','confirmed')"),
            # ต้องประกาศเงื่อนไขให้ SQLite ด้วย ไม่งั้นชุดทดสอบ (ซึ่งรันบน SQLite)
            # จะได้ unique index แบบไม่มีเงื่อนไข = ห้ามจองเวลาซ้ำแม้ยังไม่จ่าย
            # ซึ่งตรงข้ามกับกติกาจริง แล้วผลทดสอบจะเชื่อถือไม่ได้
            sqlite_where=text("holds_slot = 1 AND status IN ('pending','confirmed')"),
        ),
    )


class Review(Base):
    """รีวิวหลังใช้บริการ — 1 การจอง รีวิวได้ 1 ครั้ง"""

    __tablename__ = "reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    booking_id: Mapped[int] = mapped_column(
        ForeignKey("bookings.id", ondelete="CASCADE"), unique=True
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    shop_id: Mapped[int] = mapped_column(ForeignKey("shops.id", ondelete="CASCADE"), index=True)

    # บริการและช่างที่รีวิวถึง คัดลอกมาจากการจองตอนสร้างรีวิว
    # เก็บไว้ตรงนี้เพื่อให้กรองรีวิวตามช่างได้เร็ว ไม่ต้อง join ย้อนกลับไปที่ bookings
    service_id: Mapped[int | None] = mapped_column(
        ForeignKey("services.id", ondelete="SET NULL"), index=True, nullable=True
    )
    staff_id: Mapped[int | None] = mapped_column(
        ForeignKey("staff.id", ondelete="SET NULL"), index=True, nullable=True
    )

    rating: Mapped[int] = mapped_column(Integer)              # คะแนนรวมของร้าน
    staff_rating: Mapped[int | None] = mapped_column(Integer, nullable=True)   # คะแนนช่าง
    rating_cleanliness: Mapped[int | None] = mapped_column(Integer, nullable=True)  # ความสะอาด
    rating_punctuality: Mapped[int | None] = mapped_column(Integer, nullable=True)  # ตรงเวลา
    rating_value: Mapped[int | None] = mapped_column(Integer, nullable=True)        # ความคุ้มค่า

    comment: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    # คำตอบกลับจากเจ้าของร้าน
    reply: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    replied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

    booking: Mapped["Booking"] = relationship(back_populates="review")
    shop: Mapped["Shop"] = relationship(back_populates="reviews")
    staff: Mapped["Staff | None"] = relationship(back_populates="reviews")

    __table_args__ = (
        CheckConstraint("rating BETWEEN 1 AND 5", name="ck_reviews_rating"),
        CheckConstraint(
            "staff_rating IS NULL OR staff_rating BETWEEN 1 AND 5",
            name="ck_reviews_staff_rating",
        ),
        CheckConstraint(
            "rating_cleanliness IS NULL OR rating_cleanliness BETWEEN 1 AND 5",
            name="ck_reviews_cleanliness",
        ),
        CheckConstraint(
            "rating_punctuality IS NULL OR rating_punctuality BETWEEN 1 AND 5",
            name="ck_reviews_punctuality",
        ),
        CheckConstraint(
            "rating_value IS NULL OR rating_value BETWEEN 1 AND 5",
            name="ck_reviews_value",
        ),
    )


class Payment(Base):
    """การชำระเงิน — เป็นระบบจำลอง ไม่ได้ตัดเงินจากธนาคารจริง

    kind   : deposit (มัดจำตอนจอง) / balance (ส่วนที่เหลือจ่ายหน้าร้าน)
    method : promptpay (สแกน QR) / cash (เงินสด) / card (บัตร)
    status : paid (ชำระแล้ว) / refunded (คืนเงินแล้ว)

    แยกเป็นตารางของตัวเองแทนที่จะยัดคอลัมน์เพิ่มใน bookings เพราะ
    การจอง 1 ครั้งอาจมีการชำระหลายครั้ง (มัดจำก่อน แล้วจ่ายส่วนที่เหลือทีหลัง)
    และเราต้องเก็บประวัติไว้ออกใบเสร็จย้อนหลังได้
    """

    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # เลขที่ใบเสร็จ รูปแบบ RC-YYMM-00001 สร้างหลังบันทึกเพื่อให้ได้เลขที่ไม่ซ้ำแน่นอน
    receipt_no: Mapped[str | None] = mapped_column(String(24), unique=True, index=True, nullable=True)
    booking_id: Mapped[int] = mapped_column(ForeignKey("bookings.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(10), default="deposit")
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    method: Mapped[str] = mapped_column(String(15), default="promptpay")
    status: Mapped[str] = mapped_column(String(10), default="paid", index=True)
    # อ้างอิงจากผู้ให้บริการชำระเงิน — ระบบจำลองสร้างเลขสุ่มให้ดูเหมือนของจริง
    reference: Mapped[str | None] = mapped_column(String(40), nullable=True)
    paid_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    refunded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    booking: Mapped["Booking"] = relationship(back_populates="payments")

    __table_args__ = (
        CheckConstraint("kind IN ('deposit','balance')", name="ck_payments_kind"),
        CheckConstraint("method IN ('promptpay','cash','card')", name="ck_payments_method"),
        CheckConstraint("status IN ('paid','refunded')", name="ck_payments_status"),
        CheckConstraint("amount > 0", name="ck_payments_amount"),
        # จ่ายมัดจำซ้ำไม่ได้ นับเฉพาะรายการที่ยังไม่ถูกคืนเงิน
        #
        # บังคับเฉพาะ deposit ไม่รวม balance
        # เพราะยอดคงเหลืออาจต้องจ่ายเก็บตกหลายครั้ง เช่นคืนมัดจำไปแล้ว
        # ลูกค้ากลับมาจ่ายส่วนที่ขาดใหม่ ถ้าล็อกไว้ทั้งสองชนิดลูกค้าจะจ่ายต่อไม่ได้เลย
        Index(
            "uq_payment_booking_deposit",
            "booking_id",
            unique=True,
            postgresql_where=text("status = 'paid' AND kind = 'deposit'"),
        ),
    )


class MatchJoin(Base):
    """คนที่ขอเข้าร่วม "ก๊วน" ของการจองหนึ่งครั้ง

    ทำไมต้องมีตารางนี้
    --------------------------------------------------------------------
    หมวดกีฬาต่างจากหมวดอื่นตรงที่ **ต้องมีคนครบก่อนถึงจะใช้บริการได้**
    ร้านทำผมจองคนเดียวก็ใช้ได้ แต่สนามฟุตบอลต้องมี 10-22 คน
    คนที่อยากเตะบอลแต่ไม่มีเพื่อนไปด้วย จองสนามไปก็เปล่าประโยชน์

    คนไทยแก้ปัญหานี้กันเองมานานแล้วด้วยการ "เปิดก๊วน" — คนหนึ่งจองสนามไว้
    แล้วประกาศหาคนมาเติมให้ครบ หารค่าสนามกัน ระบบนี้แค่ย้ายพฤติกรรมนั้นมาไว้บนเว็บ

    ทำไมไม่ใช้ตาราง payments ที่มีอยู่
    --------------------------------------------------------------------
    `payments` ไม่มีคอลัมน์บอกว่าใครเป็นคนจ่าย และมีดัชนีบังคับว่า
    หนึ่งการจองมีมัดจำได้ใบเดียว (`uq_payment_booking_deposit`)
    ซึ่งขัดกับก๊วนที่ต้องมีหลายคนจ่ายคนละส่วน จึงต้องแยกตารางออกมา

    เจ้าของก๊วนยังเป็นเจ้าของการจองคนเดียวเหมือนเดิม
    คนที่เข้าร่วมไม่ได้ถือสิทธิ์ในคิวนั้น แค่ลงชื่อว่าจะไปด้วยและจ่ายส่วนของตัวเอง
    ทำแบบนี้เพื่อไม่ให้กติกาการล็อกช่องเวลาและการยกเลิกที่ทำไว้แล้วรวนทั้งระบบ
    """

    __tablename__ = "match_joins"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    booking_id: Mapped[int] = mapped_column(
        ForeignKey("bookings.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)

    # joined = ลงชื่อแล้วยังไม่จ่าย · paid = จ่ายส่วนของตัวเองแล้ว · left = ถอนตัว
    status: Mapped[str] = mapped_column(String(10), default="joined")
    # ยอดที่ต้องจ่ายต่อคน คัดลอกมาตอนเข้าร่วม ไม่อ้างอิงสด
    # เพราะถ้าเจ้าของก๊วนแก้ราคาทีหลัง คนที่จ่ายไปแล้วต้องไม่โดนเรียกเก็บเพิ่ม
    share_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)
    note: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    booking: Mapped["Booking"] = relationship(back_populates="joins")
    user: Mapped["User"] = relationship()

    __table_args__ = (
        CheckConstraint("status IN ('joined','paid','left')", name="ck_match_joins_status"),
        # คนเดียวลงชื่อก๊วนเดียวกันซ้ำไม่ได้ แต่ถอนตัวแล้วกลับมาใหม่ได้
        # (แถวเดิมถูกเปลี่ยนสถานะเป็น left ไม่ได้ลบทิ้ง จะได้เก็บประวัติไว้)
        Index("uq_match_join_user", "booking_id", "user_id", unique=True),
    )
