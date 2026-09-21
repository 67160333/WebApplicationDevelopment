"""Pydantic models (schemas) — ใช้ตรวจสอบข้อมูลเข้า-ออกอัตโนมัติ

จุดแข็งของ FastAPI: เขียน "รูปร่างของข้อมูล" ครั้งเดียว
ได้ทั้ง validation + เอกสาร Swagger + auto-complete ใน editor
"""

from datetime import date, datetime, time
from decimal import Decimal
from typing import Annotated, Generic, Literal, TypeVar

from pydantic import AfterValidator, BaseModel, ConfigDict, EmailStr, Field, computed_field

# ชื่อสำรองของ datetime.time — ใช้ในคลาสที่มีฟิลด์ชื่อ `time`
# เพราะการประกาศฟิลด์ `time: time` จะบังชื่อเดิมในขอบเขตของคลาสนั้น
TimeStr = time

# ============================================================
# ชนิดข้อมูลที่ใช้ซ้ำ พร้อมกฎการตรวจสอบ
# ============================================================
Username = Annotated[str, Field(min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_]+$")]


def _password_fits_bcrypt(v: str) -> str:
    """กันรหัสผ่านยาวเกินที่ bcrypt รับไหว

    bcrypt อ่านรหัสผ่านได้แค่ **72 ไบต์แรก** ส่วนที่เกินถูกตัดทิ้งเงียบ ๆ
    ไม่มี error ไม่มีคำเตือน — ซึ่งอันตรายมากกับภาษาไทย เพราะตัวอักษรไทย
    ตัวละ 3 ไบต์ใน UTF-8 รหัสผ่านไทย 32 ตัวจึงเท่ากับ 96 ไบต์

    ทดสอบจริงแล้วยืนยันว่าเป็นอย่างนั้น: สมัครด้วยรหัสไทย 32 ตัว
    แล้วล็อกอินด้วย 24 ตัวแรกก็เข้าได้ = อีก 8 ตัวที่เหลือไม่มีผลอะไรเลย
    ผู้ใช้คิดว่าตั้งรหัสยาว 32 ตัว แต่จริง ๆ ระบบจำแค่ 24

    จึงบอกไปตรง ๆ ดีกว่าปล่อยให้เข้าใจผิด
    (อีกทางคือ SHA-256 ก่อนส่งให้ bcrypt แต่จะทำให้รหัสผ่านเดิมทุกบัญชี
     ใช้ไม่ได้ทันที ซึ่งแลกไม่คุ้มกับระบบที่เปิดใช้จริงอยู่แล้ว)
    """
    if len(v.encode("utf-8")) > 72:
        raise ValueError(
            "รหัสผ่านยาวเกินไป (ภาษาไทยได้ไม่เกิน 24 ตัว ภาษาอังกฤษไม่เกิน 72 ตัว)"
        )
    return v


Password = Annotated[
    str, Field(min_length=8, max_length=100), AfterValidator(_password_fits_bcrypt)
]
FullName = Annotated[str, Field(min_length=2, max_length=150)]
Phone = Annotated[str, Field(pattern=r"^[0-9]{9,15}$")]


def _sane_birth_date(v: date) -> date:
    """ปฏิเสธวันเกิดที่เป็นไปไม่ได้

    เคยเจอในระบบจริงว่าคนกรอกปีเป็น พ.ศ. (เช่น 2545) ซึ่งกลายเป็นอนาคต
    หรือพิมพ์ปีผิดจนได้อายุ 300 ปี ถ้าปล่อยผ่าน ด่านตรวจอายุจะคำนวณเพี้ยนตาม
    """
    from datetime import date as _d

    today = _d.today()
    if v > today:
        raise ValueError("วันเกิดต้องไม่ใช่วันในอนาคต (ถ้ากรอกเป็น พ.ศ. ให้เปลี่ยนเป็น ค.ศ.)")
    if today.year - v.year > 120:
        raise ValueError("วันเกิดไม่ถูกต้อง")
    return v


BirthDate = Annotated[date, AfterValidator(_sane_birth_date)]

# วันหยุดประจำสัปดาห์ — เลขวันคั่นจุลภาค 0=อาทิตย์ ถึง 6=เสาร์ เช่น "1,2"
ClosedWeekdays = Annotated[str, Field(pattern=r"^$|^[0-6](,[0-6])*$", max_length=20)]
Rating = Annotated[int, Field(ge=1, le=5, description="คะแนน 1-5")]

# พิกัดภูมิศาสตร์ — จำกัดช่วงให้ถูกต้องตามความเป็นจริง
# ละติจูดเกิน ±90 หรือลองจิจูดเกิน ±180 ไม่มีอยู่จริงบนโลก
Latitude = Annotated[Decimal, Field(ge=-90, le=90, decimal_places=6)]
Longitude = Annotated[Decimal, Field(ge=-180, le=180, decimal_places=6)]


# ============================================================
# Authentication
# ============================================================
class RegisterRequest(BaseModel):
    username: Username = Field(..., description="ชื่อผู้ใช้ (a-z, 0-9, _)", examples=["testuser"])
    email: EmailStr = Field(..., examples=["test@example.com"])
    password: Password = Field(..., description="อย่างน้อย 8 ตัวอักษร", examples=["Password123"])
    full_name: FullName = Field(..., examples=["ทดสอบ ระบบ"])
    phone: Phone | None = Field(None, examples=["0891234567"])
    birth_date: BirthDate | None = Field(
        None, description="วันเกิด — ใช้ตรวจเกณฑ์อายุของบริการบางหมวด", examples=["2000-05-20"]
    )
    role: Literal["customer", "owner"] = Field("customer", description="สมัครเป็นลูกค้าหรือเจ้าของร้าน")


class LoginRequest(BaseModel):
    username: str = Field(..., description="ใส่ username หรือ email ก็ได้", examples=["mind"])
    password: str = Field(..., examples=["Password123"])


class ForgotPasswordRequest(BaseModel):
    email: EmailStr = Field(..., description="อีเมลที่ใช้สมัคร", examples=["test@example.com"])


class ResetPasswordRequest(BaseModel):
    token: str = Field(..., min_length=20, max_length=200, description="โทเคนจากลิงก์ในอีเมล")
    new_password: Password = Field(..., description="รหัสผ่านใหม่ อย่างน้อย 8 ตัวอักษร")


class ChangePasswordRequest(BaseModel):
    old_password: str = Field(..., description="รหัสผ่านเดิม")
    new_password: Password = Field(..., description="รหัสผ่านใหม่ อย่างน้อย 8 ตัวอักษร")


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: EmailStr
    full_name: str
    phone: str | None = None
    birth_date: date | None = None
    role: str
    is_active: bool
    created_at: datetime

    @computed_field
    @property
    def age(self) -> int | None:
        """อายุเต็มปี — คำนวณสดทุกครั้ง ไม่เก็บลงฐานข้อมูล

        ถ้าเก็บเป็นตัวเลข พอถึงวันเกิดจริงก็ต้องมีใครมาไล่บวกให้ ซึ่งไม่มีทางทำได้
        """
        if self.birth_date is None:
            return None
        from datetime import date as _d

        t = _d.today()
        return t.year - self.birth_date.year - (
            (t.month, t.day) < (self.birth_date.month, self.birth_date.day)
        )


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class UserUpdate(BaseModel):
    """ทุก field เป็น optional — ส่งมาเฉพาะที่ต้องการแก้"""

    full_name: FullName | None = None
    email: EmailStr | None = None
    phone: Phone | None = None
    birth_date: BirthDate | None = None
    role: Literal["customer", "owner", "admin"] | None = Field(None, description="เฉพาะ admin")
    is_active: bool | None = Field(None, description="เฉพาะ admin")


class UsernameAvailable(BaseModel):
    username: str
    available: bool


# ============================================================
# Category / Shop / Service
# ============================================================
class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
    resource_label: str = Field(
        "ช่าง", description="คำเรียกทรัพยากรที่จองได้ในหมวดนี้ เช่น ช่าง / คอร์ท / สนาม"
    )
    group_key: str = Field(
        "care",
        description=(
            "กลุ่มใหญ่ที่ใช้แยกทางเข้าในหน้าเว็บ — "
            "care = ไปที่ร้าน · play = จองสถานที่ไปเป็นกลุ่ม · "
            "auto = ฝากของไว้แล้วรอ · come = เรียกมาหาถึงที่"
        ),
    )


class ShopCreate(BaseModel):
    category_id: int = Field(..., ge=1)
    name: str = Field(..., min_length=2, max_length=150, examples=["Serene Spa อารีย์"])
    description: str | None = Field(None, max_length=1000)
    address: str | None = Field(None, max_length=255)
    district: str | None = Field(None, max_length=100, examples=["พญาไท"])
    province: str = Field("กรุงเทพมหานคร", max_length=100)
    phone: Phone | None = None
    latitude: Latitude | None = Field(None, examples=[13.779800])
    longitude: Longitude | None = Field(None, examples=[100.544600])
    open_time: time = Field(time(10, 0), examples=["10:00:00"])
    close_time: time = Field(time(20, 0), examples=["20:00:00"])
    closed_weekdays: ClosedWeekdays | None = Field(
        None, description="วันหยุดประจำสัปดาห์ 0=อาทิตย์ ถึง 6=เสาร์ เช่น \"1\" คือหยุดทุกวันจันทร์"
    )


class ShopUpdate(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=150)
    description: str | None = Field(None, max_length=1000)
    address: str | None = Field(None, max_length=255)
    district: str | None = Field(None, max_length=100)
    province: str | None = Field(None, max_length=100)
    phone: Phone | None = None
    latitude: Latitude | None = None
    longitude: Longitude | None = None
    open_time: time | None = None
    close_time: time | None = None
    closed_weekdays: ClosedWeekdays | None = Field(
        None, description="วันหยุดประจำสัปดาห์ — ส่งสตริงว่างเพื่อยกเลิกวันหยุด"
    )
    is_active: bool | None = None
    is_certified: bool | None = Field(None, description="เฉพาะ admin")


class ShopOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    owner_id: int
    category_id: int
    name: str
    description: str | None = None
    address: str | None = None
    district: str | None = None
    province: str
    phone: str | None = None
    latitude: Decimal | None = None
    longitude: Decimal | None = None
    open_time: time
    close_time: time
    closed_weekdays: str | None = None
    is_certified: bool
    rating_avg: Decimal
    rating_count: int
    is_active: bool

    # ---- ฟิลด์ที่คำนวณเพิ่ม ไม่ได้อยู่ในตาราง shops ----
    cover_url: str | None = Field(
        None, description="ที่อยู่รูปปกของร้าน ถ้ายังไม่มีรูปจะเป็น null"
    )
    distance_km: float | None = Field(
        None, description="ระยะทางจากตำแหน่งที่ค้นหา (กิโลเมตร) มีเฉพาะตอนค้นหาแบบใกล้ฉัน"
    )
    resource_label: str = Field(
        "ช่าง", description="คำเรียกสิ่งที่จองได้ในร้านนี้ เช่น ช่าง / คอร์ท / สนาม"
    )
    category_slug: str | None = Field(None, description="รหัสหมวดหมู่ เช่น football, delivery")
    group_key: str = Field("care", description="กลุ่มใหญ่ของหมวด — ดู CategoryOut.group_key")

    # ---- ตัวเลขสรุป ใช้วาดการ์ดในหน้ารายการโดยไม่ต้องยิงถามทีละร้าน ----
    price_from: float | None = Field(None, description="ราคาถูกที่สุดของร้านนี้")
    duration_max: int | None = Field(
        None, description="บริการที่ใช้เวลานานที่สุด (นาที) — ใช้เตือนงานยาวอย่างเคลือบแก้วรถ"
    )
    service_count: int = Field(0, description="จำนวนบริการที่เปิดอยู่")
    resource_count: int = Field(
        0, description="จำนวนสิ่งที่จองได้ — ช่างกี่คน สนามกี่สนาม ห้องกี่ห้อง"
    )


class ServiceCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=150, examples=["นวดแผนไทย 60 นาที"])
    description: str | None = Field(None, max_length=1000)
    price: Decimal = Field(..., ge=0, le=1_000_000, examples=[500.00])
    duration_minutes: int = Field(60, ge=15, le=600, description="ความยาวบริการ 15-600 นาที")
    booking_mode: Literal["scheduled", "instant"] = Field(
        "scheduled",
        description="scheduled = เลือกวันเวลาจากปฏิทิน · instant = เรียกใช้ทันที ไม่มีปฏิทิน",
    )
    price_per_km: Decimal = Field(
        Decimal("0.00"), ge=0, le=1000, description="ค่าบริการต่อกิโลเมตร (เฉพาะบริการเรียกทันที)"
    )


class ServiceUpdate(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=150)
    description: str | None = Field(None, max_length=1000)
    price: Decimal | None = Field(None, ge=0, le=1_000_000)
    duration_minutes: int | None = Field(None, ge=15, le=600)
    booking_mode: Literal["scheduled", "instant"] | None = None
    price_per_km: Decimal | None = Field(None, ge=0, le=1000)
    is_active: bool | None = None


class ServiceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    shop_id: int
    name: str
    description: str | None = None
    price: Decimal
    duration_minutes: int
    is_active: bool
    booking_mode: str = "scheduled"
    price_per_km: Decimal = Decimal("0.00")


# ============================================================
# Staff — ช่าง/ผู้ให้บริการ
# ============================================================
WORK_DAYS_PATTERN = r"^[0-6](,[0-6])*$"
WORK_DAYS_DESC = (
    "วันที่ช่างเข้างาน คั่นด้วยจุลภาค 0=อาทิตย์ ถึง 6=เสาร์ "
    "เช่น 1,2,3,4,5 = จันทร์-ศุกร์ · ไม่ระบุ = ทำงานทุกวันที่ร้านเปิด"
)


class StaffCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100, examples=["ช่างมิ้น"])
    position: str | None = Field(None, max_length=100, examples=["ช่างนวดอาวุโส"])
    bio: str | None = Field(None, max_length=500, description="ประสบการณ์หรือความถนัด")
    work_days: str | None = Field(
        None, pattern=WORK_DAYS_PATTERN, description=WORK_DAYS_DESC, examples=["1,2,3,4,5"]
    )
    work_start: TimeStr | None = Field(None, description="เวลาเข้างาน · ไม่ระบุ = ตามเวลาร้านเปิด")
    work_end: TimeStr | None = Field(None, description="เวลาเลิกงาน · ไม่ระบุ = ตามเวลาร้านปิด")


class StaffUpdate(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=100)
    position: str | None = Field(None, max_length=100)
    bio: str | None = Field(None, max_length=500)
    is_active: bool | None = None
    work_days: str | None = Field(None, pattern=WORK_DAYS_PATTERN, description=WORK_DAYS_DESC)
    work_start: TimeStr | None = None
    work_end: TimeStr | None = None


class StaffOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    shop_id: int
    name: str
    position: str | None = None
    bio: str | None = None
    is_active: bool
    work_days: str | None = None
    work_start: TimeStr | None = None
    work_end: TimeStr | None = None
    rating_avg: Decimal = Decimal("0.00")
    rating_count: int = 0


class StaffDetail(StaffOut):
    """โปรไฟล์ช่าง พร้อมชื่อร้านและสถิติการทำงาน"""

    shop_name: str
    jobs_done: int = Field(0, description="จำนวนงานที่ให้บริการเสร็จแล้ว")


class ShopDetail(ShopOut):
    """รายละเอียดร้าน พร้อมบริการและช่างทั้งหมด"""

    services: list[ServiceOut] = []
    staff: list[StaffOut] = []
    images: list["ShopImageOut"] = []


# ============================================================
# Booking / Review
# ============================================================
class BookingCreate(BaseModel):
    service_id: int = Field(..., ge=1)
    # เจ้าของร้านจองแทนลูกค้าที่ไม่มีบัญชี (walk-in / โทรมาจอง)
    # ลูกค้าทั่วไปส่งมาก็ไม่มีผล ระบบจะยึดชื่อจากบัญชีที่ล็อกอินอยู่
    guest_name: str | None = Field(
        None, min_length=2, max_length=150,
        description="ชื่อลูกค้าที่ไม่มีบัญชี (เฉพาะเจ้าของร้านเท่านั้นที่ใช้ได้)",
    )
    guest_phone: str | None = Field(None, pattern=r"^[0-9]{9,15}$", description="เบอร์ติดต่อลูกค้า")
    booking_date: date = Field(..., description="รูปแบบ YYYY-MM-DD", examples=["2026-09-15"])
    booking_time: time = Field(..., description="รูปแบบ HH:MM", examples=["14:00:00"])
    staff_id: int | None = Field(None, ge=1, description="ช่างที่ต้องการ (ไม่ระบุ = ร้านจัดให้)")
    note: str | None = Field(None, max_length=500, examples=["ขอห้องส่วนตัว"])
    requirements: str | None = Field(
        None, max_length=1000,
        description="ความต้องการเฉพาะ เช่น ความยาว สี แบบที่อยากได้",
        examples=["อยากได้สีน้ำตาลอ่อน ไม่เอาสว่างมาก"],
    )
    reference_url: str | None = Field(
        None, max_length=500, description="ลิงก์รูปตัวอย่างที่อยากได้"
    )
    health_note: str | None = Field(
        None, max_length=500,
        description="ข้อมูลสุขภาพที่ร้านควรทราบ เช่น แพ้สารเคมี ตั้งครรภ์",
        examples=["แพ้น้ำหอม"],
    )


class InstantDistanceUpdate(BaseModel):
    """ร้านแก้ระยะทางจริงหลังวิ่งงานเสร็จ

    ระยะทางตอนเรียกงานเป็นตัวเลขที่ลูกค้าพิมพ์เอง จึงเป็นแค่ค่าประมาณ
    ร้านที่วิ่งจริงเท่านั้นที่รู้ระยะจริง — เส้นนี้ให้ร้านกรอกกลับมา
    """

    distance_km: Decimal = Field(
        ..., gt=0, le=200, description="ระยะทางจริงที่วิ่งได้ (กิโลเมตร)", examples=[12.4]
    )
    reason: str | None = Field(
        None, max_length=200, description="เหตุผลที่ปรับ เช่น ปลายทางไกลกว่าที่แจ้ง"
    )


class InstantBookingCreate(BaseModel):
    """เรียกใช้บริการทันที — ไม่มีวันเวลาให้เลือก ระบบใช้เวลาปัจจุบัน"""

    service_id: int = Field(..., ge=1)
    pickup_address: str = Field(
        ..., min_length=5, max_length=300,
        description="ที่อยู่ต้นทางที่ให้ไปรับของ",
        examples=["อาคารเอ ชั้น 3 ซอยสุขุมวิท 21 เขตวัฒนา"],
    )
    dropoff_address: str = Field(
        ..., min_length=5, max_length=300,
        description="ที่อยู่ปลายทาง",
        examples=["คอนโดบี ถนนพระราม 9 เขตห้วยขวาง"],
    )
    distance_km: Decimal = Field(
        ..., gt=0, le=200, description="ระยะทางโดยประมาณเป็นกิโลเมตร", examples=[7.5]
    )
    note: str | None = Field(
        None, max_length=500, description="รายละเอียดของที่ส่ง", examples=["เอกสาร 1 ซอง"]
    )
    guest_name: str | None = Field(None, min_length=2, max_length=150)
    guest_phone: str | None = Field(None, pattern=r"^[0-9]{9,15}$")


class BookingStatusUpdate(BaseModel):
    status: Literal["pending", "confirmed", "completed", "cancelled"]


class BookingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    booking_code: str
    user_id: int
    service_id: int
    shop_id: int
    staff_id: int | None = None
    booking_date: date
    booking_time: time
    end_time: time
    total_price: Decimal
    deposit_amount: Decimal
    status: str
    note: str | None = None
    requirements: str | None = None
    reference_url: str | None = None
    health_note: str | None = None
    guest_name: str | None = None
    guest_phone: str | None = None
    pickup_address: str | None = None
    dropoff_address: str | None = None
    distance_km: Decimal | None = None
    created_at: datetime

    # ---- การล็อกช่องเวลา ----
    holds_slot: bool = Field(
        False,
        description=(
            "คิวนี้กันช่วงเวลาไว้แล้วหรือยัง — เป็น true เมื่อชำระเงินแล้ว "
            "หรือร้านยืนยัน/จองแทนให้ ถ้ายังเป็น false ลูกค้าคนอื่นจองเวลาเดียวกันได้"
        ),
    )

    # ---- การยกเลิก ----
    cancelled_by: str | None = Field(
        None, description="ใครเป็นคนยกเลิก: customer / shop / admin"
    )
    cancellation_fee: Decimal = Field(
        Decimal("0.00"),
        description="ยอดที่ถูกหักตอนยกเลิก (ค่ามัดจำที่จ่ายมาแล้ว) — ลูกค้ายกเลิกเองเท่านั้นที่ถูกหัก",
    )

    # ---- สถานะการชำระเงิน คำนวณจากตาราง payments ----
    # ใส่มาให้พร้อมกับรายการจองเลย หน้าเว็บจะได้ไม่ต้องยิงถามทีละคิว
    payment_state: Literal["unpaid", "deposit_paid", "paid"] = "unpaid"
    paid_amount: Decimal = Decimal("0.00")

    # ---- ก๊วน ----
    open_slots: int = Field(0, description="เปิดรับคนไปด้วยกันทั้งหมดกี่คน (0 = ไม่ได้เปิดก๊วน)")
    share_price: Decimal = Field(Decimal("0.00"), description="ค่าใช้จ่ายต่อคนที่เข้าร่วม")
    match_note: str | None = Field(None, description="ข้อความประกาศหาคน")
    joined_count: int = Field(0, description="ลงชื่อแล้วกี่คน (ไม่นับคนที่ถอนตัว)")


# ============================================================
# ก๊วน — หาคนไปด้วยกัน
# ============================================================
class MatchOpen(BaseModel):
    """เปิดก๊วนจากคิวที่จองไว้แล้ว"""

    open_slots: int = Field(
        ..., ge=1, le=40,
        description="ต้องการคนเพิ่มอีกกี่คน (ไม่นับตัวเอง)", examples=[9],
    )
    share_price: Decimal = Field(
        ..., ge=0, le=100_000,
        description="ค่าใช้จ่ายต่อคน หารกันเอง ระบบไม่ได้เก็บเงินแทน", examples=[120],
    )
    match_note: str | None = Field(
        None, max_length=300, examples=["ขาดอีก 4 คน มือใหม่มาได้ ไม่ซีเรียส"]
    )


class MatchJoinOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    user_name: str = Field("", description="ชื่อผู้เข้าร่วม นามสกุลถูกย่อเหลือตัวอักษรเดียว")
    status: Literal["joined", "paid", "left"]
    share_amount: Decimal
    note: str | None = None
    created_at: datetime


class MatchOut(BaseModel):
    """ก๊วนหนึ่งก๊วน — ใช้ทั้งในหน้ารวมและหน้าสนาม"""

    booking_id: int
    shop_id: int
    shop_name: str
    shop_district: str | None = None
    category_slug: str | None = None
    service_name: str
    resource_name: str | None = Field(None, description="ชื่อสนาม/คอร์ทที่จองไว้")
    booking_date: date
    booking_time: TimeStr
    end_time: TimeStr
    host_name: str = Field("", description="ชื่อคนเปิดก๊วน")
    open_slots: int
    joined_count: int
    slots_left: int = Field(0, description="ยังรับได้อีกกี่คน")
    share_price: Decimal
    match_note: str | None = None
    distance_km: float | None = None
    joined_by_me: bool = Field(False, description="ฉันลงชื่อไว้แล้วหรือยัง")


# ============================================================
# แนะนำสิ่งที่ทำได้ระหว่างรอ
# ============================================================
class GapSuggestion(BaseModel):
    """บริการที่ว่างพอดีกับช่วงเวลาที่ลูกค้าต้องรอ"""

    shop_id: int
    shop_name: str
    category_slug: str | None = None
    resource_label: str = "ช่าง"
    service_id: int
    service_name: str
    price: Decimal
    duration_minutes: int
    distance_km: float
    travel_minutes: int = Field(..., description="เวลาเดินทางโดยประมาณเที่ยวเดียว")
    start_time: TimeStr = Field(..., description="ช่องเวลาที่แนะนำให้จอง")
    end_time: TimeStr


class GapWindow(BaseModel):
    """ช่วงเวลาที่ว่างอันเกิดจากการจองของตัวเอง พร้อมข้อเสนอ"""

    booking_id: int
    mode: Literal["waiting", "after"] = Field(
        ...,
        description=(
            "waiting = ระหว่างรอรับของคืน (เช่นฝากรถไว้) จึงต้องอยู่ใกล้ · "
            "after = ต่อจากคิวที่จบแล้ว เดินทางไกลขึ้นได้"
        ),
    )
    window_start: TimeStr
    window_end: TimeStr
    window_minutes: int
    radius_km: float
    reason: str = Field(..., description="อธิบายให้ผู้ใช้เข้าใจว่าทำไมถึงแนะนำช่วงนี้")
    items: list[GapSuggestion] = []


# ============================================================
# ช่วงเวลาว่าง (Availability)
# ============================================================
class Slot(BaseModel):
    """ช่องเวลาหนึ่งช่อง

    หมายเหตุ: ใช้ TimeStr (alias ของ datetime.time) เป็นชนิดข้อมูล
    เพราะฟิลด์ชื่อ `time` จะบังชื่อ `time` ที่ import มา
    ทำให้ฟิลด์ถัดไปที่ประกาศเป็น `time` ได้ชนิดข้อมูลผิด
    """

    time: TimeStr = Field(..., description="เวลาเริ่มให้บริการ")
    end_time: TimeStr = Field(..., description="เวลาสิ้นสุดโดยประมาณ")
    available: bool = Field(..., description="ว่างให้จองหรือไม่")
    reason: str | None = Field(None, description="เหตุผลที่จองไม่ได้")
    remaining: int = Field(
        0,
        description="จำนวนที่ยังรับได้ในช่วงเวลานี้ (คอร์ท/ช่าง/สนาม ที่ยังว่าง)",
    )
    # ---- คะแนน "ช่องนี้ทำให้ตารางร้านแตกไหม" ----
    # ดูคำอธิบายเต็มใน _score_slots() ที่ bookings.py
    fits_well: bool = Field(
        True,
        description=(
            "จองช่องนี้แล้วร้านยังรับคิวได้เท่าเดิมหรือไม่ "
            "false = จองแล้วทำให้ร้านเสียคิวไปโดยเปล่าประโยชน์"
        ),
    )
    wasted_minutes: int = Field(
        0, description="นาทีที่จะกลายเป็นเวลาตายถ้าจองช่องนี้ (สั้นเกินกว่าจะรับใครได้อีก)"
    )
    capacity: int = Field(
        1,
        description="จำนวนที่รับได้พร้อมกันทั้งหมดของร้านในวันนั้น",
    )


class AvailabilityOut(BaseModel):
    service_id: int
    service_name: str
    duration_minutes: int
    booking_date: date
    staff_id: int | None = None
    staff_name: str | None = None
    open_time: TimeStr
    close_time: TimeStr
    slots: list[Slot]
    available_count: int
    # บอกสาเหตุระดับ "ทั้งวัน" เช่น ช่างคนนี้หยุดวันนี้ หรือร้านปิด
    closed_reason: str | None = Field(
        None, description="ถ้าทั้งวันจองไม่ได้ จะบอกเหตุผลไว้ตรงนี้"
    )


class BookingReschedule(BaseModel):
    """เลื่อนนัด — ส่งเฉพาะสิ่งที่ต้องการเปลี่ยน"""

    booking_date: date = Field(..., description="วันใหม่", examples=["2026-09-20"])
    booking_time: TimeStr = Field(..., description="เวลาใหม่", examples=["15:00:00"])
    staff_id: int | None = Field(None, ge=1, description="เปลี่ยนช่างด้วยได้ · ไม่ส่ง = ไม่ระบุช่าง")


# ============================================================
# วันหยุดพิเศษของร้าน
# ============================================================
class ClosureCreate(BaseModel):
    closed_date: date = Field(..., description="วันที่ร้านปิด", examples=["2026-12-31"])
    reason: str | None = Field(None, max_length=200, examples=["ปิดปรับปรุงร้าน"])


class ClosureOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    shop_id: int
    closed_date: date
    reason: str | None = None


# ============================================================
# การแจ้งเตือน
# ============================================================
class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    kind: str
    title: str
    body: str | None = None
    link: str | None = None
    is_read: bool
    created_at: datetime


class UnreadCount(BaseModel):
    unread: int


class ReviewCreate(BaseModel):
    booking_id: int = Field(..., ge=1)
    rating: Rating = Field(..., description="คะแนนรวมของร้าน")
    staff_rating: Rating | None = Field(None, description="คะแนนของช่างที่ให้บริการ")
    rating_cleanliness: Rating | None = Field(None, description="ความสะอาดของร้าน")
    rating_punctuality: Rating | None = Field(None, description="ตรงต่อเวลา")
    rating_value: Rating | None = Field(None, description="ความคุ้มค่าเมื่อเทียบกับราคา")
    comment: str | None = Field(None, max_length=1000, examples=["บริการดีมาก ร้านสะอาด"])


class ReviewReply(BaseModel):
    """คำตอบกลับจากเจ้าของร้าน"""

    reply: str = Field(..., min_length=1, max_length=1000,
                       examples=["ขอบคุณที่มาใช้บริการนะคะ ไว้มาใหม่ค่ะ"])


class ReviewOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    booking_id: int
    user_id: int
    # ชื่อผู้เขียนรีวิวแบบย่อ เช่น "พลอย ร." — รีวิวที่ไม่มีชื่อคนเขียนดูเหมือนรีวิวปลอม
    # แต่ก็ไม่ควรเปิดนามสกุลเต็มของลูกค้าให้คนทั้งอินเทอร์เน็ตเห็น
    user_name: str | None = None
    shop_id: int
    service_id: int | None = None
    staff_id: int | None = None
    rating: int
    staff_rating: int | None = None
    rating_cleanliness: int | None = None
    rating_punctuality: int | None = None
    rating_value: int | None = None
    comment: str | None = None
    reply: str | None = None
    replied_at: datetime | None = None
    created_at: datetime


class AspectAverages(BaseModel):
    """คะแนนเฉลี่ยแยกตามหัวข้อ — ไม่มีข้อมูลจะเป็น None"""

    staff: float | None = Field(None, description="คะแนนช่างโดยเฉลี่ย")
    cleanliness: float | None = Field(None, description="ความสะอาด")
    punctuality: float | None = Field(None, description="ตรงต่อเวลา")
    value: float | None = Field(None, description="ความคุ้มค่า")


class ReviewSummary(BaseModel):
    """สรุปภาพรวมรีวิวของร้าน ใช้วาดแถบกระจายคะแนนบนหน้าเว็บ"""

    shop_id: int
    total: int = Field(..., description="จำนวนรีวิวทั้งหมด")
    average: float = Field(..., description="คะแนนเฉลี่ยรวม")
    distribution: dict[int, int] = Field(
        ..., description="จำนวนรีวิวของแต่ละดาว เช่น {5: 12, 4: 3, ...}"
    )
    aspects: AspectAverages
    reply_rate: float = Field(..., description="สัดส่วนรีวิวที่ร้านตอบกลับแล้ว (0-1)")


# ============================================================
# รูปภาพของร้าน
# ============================================================
class ImageUpdate(BaseModel):
    caption: str | None = Field(None, max_length=200, examples=["บรรยากาศห้องนวด"])
    is_cover: bool = Field(False, description="ตั้งรูปนี้เป็นรูปปกของร้าน")


class ShopImageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    shop_id: int
    filename: str
    caption: str | None = None
    is_cover: bool
    sort_order: int
    width: int
    height: int
    size_bytes: int
    created_at: datetime

    @computed_field(description="ที่อยู่ไฟล์สำหรับเรียกดูรูป")
    @property
    def url(self) -> str:
        from app.storage import image_url
        return image_url(self.shop_id, self.filename)


# ============================================================
# การชำระเงิน
# ============================================================
class PaymentCreate(BaseModel):
    kind: Literal["deposit", "balance"] = Field(
        "deposit", description="deposit = มัดจำ, balance = ยอดคงเหลือ"
    )
    method: Literal["promptpay", "card", "cash"] = Field(
        "promptpay", description="cash ใช้ได้เฉพาะเจ้าของร้านที่รับเงินหน้าร้าน"
    )


class PaymentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    receipt_no: str | None = None
    booking_id: int
    kind: str
    amount: Decimal
    method: str
    status: str
    reference: str | None = None
    paid_at: datetime
    refunded_at: datetime | None = None


class PaymentSummary(BaseModel):
    """ภาพรวมการชำระเงินของการจองหนึ่งครั้ง"""

    booking_id: int
    booking_code: str
    total_price: Decimal
    deposit_amount: Decimal
    paid_amount: Decimal
    outstanding: Decimal = Field(..., description="ยอดที่ยังค้างชำระ")
    state: Literal["unpaid", "deposit_paid", "paid"]
    payments: list[PaymentOut] = []


class ReceiptOut(BaseModel):
    """ข้อมูลบนใบเสร็จ — รวมทุกอย่างที่ต้องพิมพ์ไว้ในที่เดียว"""

    receipt_no: str
    issued_at: datetime
    status: str
    kind: str
    method: str
    reference: str | None = None
    amount: Decimal

    shop_name: str
    shop_address: str | None = None
    shop_phone: str | None = None

    customer_name: str
    booking_code: str
    booking_date: date
    booking_time: time
    service_name: str
    total_price: Decimal


# ============================================================
# รูปแบบผลลัพธ์แบบแบ่งหน้า (ใช้ร่วมกันทุก endpoint ที่มี pagination)
# ============================================================
T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    items: list[T]
    page: int
    limit: int
    total: int
    total_pages: int


class Message(BaseModel):
    message: str


# ============================================================
# ตารางทรัพยากร × เวลา (ผังแบบเลือกที่นั่งโรงหนัง)
# ============================================================
class ResourceRow(BaseModel):
    """ทรัพยากรหนึ่งชิ้นกับช่องเวลาทั้งวันของมัน"""

    staff_id: int
    name: str
    position: str | None = Field(None, description="ประเภทย่อย เช่น หญ้าเทียม / คอร์ทในร่ม / ห้องเล็ก")
    closed_reason: str | None = Field(None, description="ถ้าทั้งวันจองไม่ได้ บอกเหตุผลไว้ตรงนี้")
    slots: list[Slot] = []
    available_count: int = 0


class ResourceGrid(BaseModel):
    """ตารางทั้งผัง — แถวคือสนาม/คอร์ท/ห้อง คอลัมน์คือเวลา

    มีไว้ให้หน้าเว็บวาดผังแบบเลือกที่นั่งโรงหนังได้ในคำขอเดียว
    ถ้าไม่มี endpoint นี้ หน้าเว็บต้องยิงถามทีละคอร์ท สนามที่มี 10 คอร์ท
    จะกลายเป็น 10 คำขอต่อการเปลี่ยนวันหนึ่งครั้ง
    """

    service_id: int
    service_name: str
    duration_minutes: int
    booking_date: date
    resource_label: str = "ช่าง"
    open_time: TimeStr
    close_time: TimeStr
    times: list[TimeStr] = Field([], description="หัวคอลัมน์ เรียงตามเวลา ใช้ร่วมกันทุกแถว")
    rows: list[ResourceRow] = []


# ============================================================
# เฝ้าช่องเวลาที่เต็ม (waitlist)
# ============================================================
class SlotWatchCreate(BaseModel):
    """ขอให้แจ้งเตือนเมื่อช่วงเวลาที่ต้องการว่าง"""

    service_id: int = Field(..., ge=1)
    staff_id: int | None = Field(None, ge=1, description="เจาะจงคอร์ท/ช่าง หรือเว้นว่าง = อันไหนก็ได้")
    watch_date: date = Field(..., description="วันที่ต้องการ")
    from_time: TimeStr = Field(..., description="ช่วงเวลาที่ยอมรับได้ — เริ่ม", examples=["19:00"])
    to_time: TimeStr = Field(..., description="ช่วงเวลาที่ยอมรับได้ — สิ้นสุด", examples=["22:00"])


class SlotWatchOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    shop_id: int
    shop_name: str = ""
    service_id: int
    service_name: str = ""
    staff_id: int | None = None
    staff_name: str | None = None
    watch_date: date
    from_time: TimeStr
    to_time: TimeStr
    status: Literal["active", "notified", "cancelled"]
    created_at: datetime


# ============================================================
# ประกาศหาคนก่อนจอง (community)
# ============================================================
class MatchRequestCreate(BaseModel):
    """โพสต์หาคนไปเล่นด้วยกัน โดยยังไม่ต้องจองสนาม"""

    sport: Literal["football", "badminton", "karaoke"] = Field(..., examples=["football"])
    district: str | None = Field(None, max_length=100, examples=["ลาดพร้าว"])
    play_date: date = Field(..., description="วันที่อยากเล่น")
    from_time: TimeStr = Field(..., examples=["20:00"])
    to_time: TimeStr = Field(..., examples=["22:00"])
    need_people: int = Field(..., ge=1, le=40, description="ต้องการคนเพิ่มอีกกี่คน", examples=[8])
    note: str | None = Field(None, max_length=300, examples=["มือใหม่มาได้ ไม่ซีเรียส"])


class MatchRequestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    host_name: str = Field("", description="ชื่อคนโพสต์ นามสกุลย่อเหลือตัวอักษรเดียว")
    sport: str
    district: str | None = None
    play_date: date
    from_time: TimeStr
    to_time: TimeStr
    need_people: int
    note: str | None = None
    status: Literal["open", "booked", "closed"]
    booking_id: int | None = None
    created_at: datetime

    interested_count: int = Field(0, description="กดสนใจแล้วกี่คน")
    people_left: int = Field(0, description="ยังขาดอีกกี่คน")
    is_full: bool = Field(False, description="ครบแล้วหรือยัง — ครบแล้วจองสนามได้")
    joined_by_me: bool = False


# ============================================================
# เสนอวันจองรอบถัดไป
# ============================================================
class NextRoundSuggestion(BaseModel):
    """เดารอบถัดไปจากพฤติกรรมการจองที่ผ่านมา

    การจองครั้งนี้บอกใบ้ครั้งหน้าอยู่แล้ว — ตัดผมทุก 3 สัปดาห์
    เตะบอลทุกอังคาร ระบบเห็นรูปแบบนี้ในประวัติของผู้ใช้เอง
    """

    service_id: int
    service_name: str
    shop_id: int
    shop_name: str
    last_booked: date = Field(..., description="ครั้งล่าสุดที่ใช้บริการนี้")
    interval_days: int = Field(..., description="ระยะห่างเฉลี่ยที่ผ่านมา (วัน)")
    times_used: int = Field(..., description="เคยจองบริการนี้มาแล้วกี่ครั้ง")
    suggested_date: date = Field(..., description="วันที่แนะนำสำหรับรอบถัดไป")
    reason: str = Field(..., description="อธิบายให้ผู้ใช้เข้าใจว่าทำไมถึงแนะนำวันนี้")
