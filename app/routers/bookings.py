"""4) Bookings & Reviews — การจองคิวและรีวิว"""

import secrets
from datetime import date as date_cls
from datetime import datetime, time as time_cls, timedelta, timezone
from zoneinfo import ZoneInfo
from decimal import ROUND_HALF_UP, Decimal

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Booking, Payment, Review, Service, Shop, ShopClosure, Staff, User
from app.schemas import (
    AspectAverages,
    AvailabilityOut,
    BookingCreate,
    BookingOut,
    BookingReschedule,
    BookingStatusUpdate,
    InstantBookingCreate,
    Message,
    Page,
    ReviewCreate,
    ReviewOut,
    ReviewReply,
    ReviewSummary,
    Slot,
)
from app.routers.notifications import notify
from app.security import get_current_user

router = APIRouter(prefix="/api", tags=["4. Bookings & Reviews"])

# ระยะห่างระหว่างช่องเวลาที่เปิดให้เลือก (นาที)
SLOT_STEP_MINUTES = 30

# จองล่วงหน้าได้ไกลสุดกี่วัน
#
# ของเดิมตรวจแค่ "ห้ามจองย้อนหลัง" แต่ไม่มีขอบบน ทดสอบแล้วจองล่วงหน้าได้ถึง
# สองหมื่นวัน (ราว 55 ปี) ซึ่งเป็นไปไม่ได้ในทางธุรกิจ และสร้างปัญหาจริงคือ
#   - ร้านเห็นคิวปี 2080 ค้างในระบบ ลบก็ไม่กล้า ปล่อยไว้ก็รก
#   - ช่องเวลาถูกจองล็อกไว้ล่วงหน้าโดยที่ไม่มีทางรู้ว่าร้านยังเปิดอยู่ไหม
#   - เป็นช่องให้ยิงจองรัว ๆ จนตารางเต็มไปหมด
#
# 90 วันเป็นค่าที่ร้านบริการนัดหมายส่วนใหญ่ใช้กัน และครอบคลุมการวางแผนล่วงหน้า
# ตามปกติของลูกค้า (นัดทำผมก่อนงานแต่ง จองสนามประจำเดือนหน้า)
MAX_ADVANCE_DAYS = 90

# เขตเวลาของร้านทุกร้าน — ผูกไว้ในโค้ด ไม่ฝากไว้กับ TZ ของ container
#
# เวลาเปิด-ปิดร้านและ booking_time เก็บเป็นเวลาไทยล้วน ไม่มีเขตเวลาติดมา
# ถ้าเทียบกับ datetime.now() เฉย ๆ จะได้เวลาของเครื่องที่รัน
# ในเครื่องไม่มีปัญหาเพราะ docker-compose ตั้ง TZ=Asia/Bangkok ไว้
# แต่บนโฮสต์ฟรีอย่าง Hugging Face ที่เป็น UTC จะเพี้ยนไป 7 ชั่วโมงทันที
# อาการคือกดเรียกบริการด่วนตอนสิบเอ็ดโมงแล้วถูกตอบว่า "อยู่นอกเวลาให้บริการ"
SHOP_TZ = ZoneInfo("Asia/Bangkok")


def now_local() -> datetime:
    """เวลาปัจจุบันตามเขตเวลาของร้าน (ตัดเขตเวลาออกเพื่อเทียบกับ Date/Time ในฐานข้อมูล)"""
    return datetime.now(SHOP_TZ).replace(tzinfo=None)


def _assert_within_window(on_date: date_cls) -> None:
    """วันที่จองต้องอยู่ในช่วงที่ระบบรับได้ — ไม่ย้อนหลัง และไม่ไกลเกินเพดาน

    แยกออกมาเป็นฟังก์ชันเดียวเพื่อให้ทั้งการจองใหม่ การเลื่อนนัด และหน้าดูคิวว่าง
    ใช้เกณฑ์ชุดเดียวกัน ถ้าเขียนแยกกันสามที่ วันหนึ่งจะหลุดไม่ตรงกันแน่นอน
    """
    today = now_local().date()
    if on_date < today:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="เลือกวันที่ผ่านไปแล้วไม่ได้",
        )
    limit = today + timedelta(days=MAX_ADVANCE_DAYS)
    if on_date > limit:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"จองล่วงหน้าได้ไม่เกิน {MAX_ADVANCE_DAYS} วัน "
                f"(ถึงวันที่ {limit.strftime('%d/%m/%Y')})"
            ),
        )


def _generate_booking_code() -> str:
    """สร้างรหัสการจอง เช่น BK20260915A3F19C

    ของเดิมใช้ random.randint(100, 999) ซึ่งมีแค่ 900 ค่าต่อวัน
    แต่คอลัมน์นี้เป็น unique พอมีคิวเกินสามสิบกว่ารายการต่อวัน โอกาสชนก็สูงแล้ว
    (ปัญหาวันเกิด) เวลาชนจะไปโผล่เป็น IntegrityError ที่ถูกตีความผิดว่าคิวชนกัน
    ลูกค้าจึงเห็นข้อความ "ช่วงเวลานี้เพิ่งถูกจองไป" ทั้งที่ช่องเวลาว่าง
    """
    today = now_local().strftime("%Y%m%d")
    return f"BK{today}{secrets.token_hex(3).upper()}"


def _slot_conflict(exc: IntegrityError) -> bool:
    """IntegrityError นี้เกิดจากคิวชนกันจริง ไม่ใช่รหัสการจองซ้ำ"""
    text_of = str(getattr(exc, "orig", exc))
    # PostgreSQL ใส่ชื่อ index มาในข้อความ (เช็กชื่อเดิมด้วย เผื่อยังไม่ได้ปรับโครงสร้าง)
    if "uq_booking_held_slot" in text_of or "uq_booking_active_slot" in text_of:
        return True
    # SQLite ไม่บอกชื่อ index บอกแค่รายชื่อคอลัมน์ — ชุดทดสอบรันบน SQLite
    # ถ้าไม่ดักตรงนี้ การทดสอบจะเห็น 500 ทั้งที่ของจริงบน PostgreSQL คืน 409
    return "bookings.booking_time" in text_of and "bookings.shop_id" in text_of


def _paid_total(db: Session, booking_id: int) -> Decimal:
    """รวมเงินที่ลูกค้าจ่ายมาแล้วจริงของคิวนี้ (ไม่นับรายการที่คืนไปแล้ว)"""
    total = db.scalar(
        select(func.coalesce(func.sum(Payment.amount), 0)).where(
            Payment.booking_id == booking_id, Payment.status == "paid"
        )
    )
    return Decimal(total or 0)


def _apply_cancellation(db: Session, booking: Booking, by: str) -> tuple[Decimal, Decimal]:
    """ปรับสถานะคิวเป็นยกเลิก คิดค่าปรับ แล้วคืนค่า (ยอดที่ถูกหัก, ยอดที่ต้องคืน)

    **กติกาค่าปรับ** — ลูกค้ายกเลิกเองจะไม่ได้เงินมัดจำคืน (มัดจำ = 20% ของค่าบริการ)
    เหตุผลคือร้านกันเวลาไว้ให้แล้วและปฏิเสธลูกค้าคนอื่นไปแล้ว การยกเลิกกระชั้น
    ทำให้ช่องเวลานั้นขายไม่ทัน ค่ามัดจำจึงเป็นค่าชดเชยของฝั่งร้าน

    ถ้าร้านเป็นฝ่ายยกเลิกเอง ลูกค้าไม่ผิด จึงไม่หักอะไรเลย ต้องคืนเต็มจำนวน

    หักได้ไม่เกินเงินที่จ่ายมาจริง — คิวที่ยังไม่จ่ายจะถูกหัก 0 บาท
    ซึ่งสอดคล้องกับกติกาการล็อกช่องเวลาพอดี: ไม่จ่าย = ไม่ได้กันเวลาให้ใคร
    = ยกเลิกแล้วไม่มีใครเสียหาย
    """
    paid = _paid_total(db, booking.id)
    fee = min(paid, Decimal(booking.deposit_amount)) if by == "customer" else Decimal("0.00")

    booking.status = "cancelled"
    booking.cancelled_by = by
    booking.cancellation_fee = fee
    # ปล่อยช่องเวลาคืนทันที ให้ลูกค้าคนอื่นจองต่อได้
    booking.holds_slot = False
    return fee, paid - fee


def _notify_cancellation(
    db: Session,
    booking: Booking,
    shop: Shop | None,
    by: str,
    fee: Decimal,
    refundable: Decimal,
) -> None:
    """แจ้งเตือนทั้งสองฝ่ายหลังยกเลิกคิว

    รวมไว้ที่เดียวเพราะยกเลิกได้สองทาง (ปุ่มยกเลิก กับการเปลี่ยนสถานะ)
    ถ้าเขียนแยกกัน สองทางจะแจ้งเตือนไม่เหมือนกันเมื่อมีคนไปแก้ทางใดทางหนึ่งทีหลัง
    """
    if shop is None:
        return
    service = db.get(Service, booking.service_id)
    when = f"{booking.booking_date} {shortstr(booking.booking_time)} น. · {booking.booking_code}"

    if by == "customer":
        # ร้านต้องรู้ว่าช่องเวลาหลุดกลับมาแล้ว และมีเงินค้างต้องจัดการไหม
        notify(
            db, shop.owner_id, "booking_cancelled", "ลูกค้ายกเลิกคิว",
            f"{when}" + (f" · หักค่ามัดจำ ฿{fee:,.0f} เข้าร้าน" if fee > 0 else ""),
            "manage.html",
        )
        # เงินส่วนที่เกินค่ามัดจำต้องคืน ถ้าไม่เตือนจะค้างในระบบเงียบ ๆ
        if refundable > 0:
            notify(
                db, shop.owner_id, "refund_pending",
                f"ค้างคืนเงินลูกค้า ฿{refundable:,.0f}",
                f"{booking.booking_code} · กดคืนเงินที่หน้าจัดการร้าน",
                "manage.html",
            )
        if fee > 0:
            # ลูกค้าต้องเห็นเป็นลายลักษณ์อักษรว่าถูกหักเท่าไหร่ ไม่ใช่รู้จากยอดที่หายไป
            notify(
                db, booking.user_id, "booking_cancelled",
                f"ยกเลิกคิวแล้ว · หักค่ามัดจำ ฿{fee:,.0f}",
                f"{service.name if service else ''} · {when}",
            )
    else:
        # ร้านเป็นฝ่ายยกเลิก ลูกค้าไม่ผิด ต้องได้เงินคืนเต็มจำนวน
        notify(
            db, booking.user_id, "booking_cancelled", "ร้านยกเลิกคิวของคุณ",
            f"{service.name if service else ''} · {when}"
            + (f" · ร้านจะคืนเงิน ฿{refundable:,.0f} ให้เต็มจำนวน" if refundable > 0 else ""),
        )
        if refundable > 0:
            notify(
                db, shop.owner_id, "refund_pending",
                f"ต้องคืนเงินลูกค้า ฿{refundable:,.0f}",
                f"{booking.booking_code} · ร้านเป็นฝ่ายยกเลิก ต้องคืนเต็มจำนวน",
                "manage.html",
            )


def _with_payment(db: Session, rows: list[Booking]) -> list[BookingOut]:
    """เติมสถานะการชำระเงินให้รายการจอง

    รวมยอดของทุกคิวในคำสั่งเดียว ถ้าถามทีละคิวจะกลายเป็น N+1 query
    (หน้าการจองแสดง 10 รายการ = ยิงฐานข้อมูล 11 ครั้งแทนที่จะเป็น 2 ครั้ง)
    """
    if not rows:
        return []

    ids = [b.id for b in rows]
    sums = dict(
        db.execute(
            select(Payment.booking_id, func.coalesce(func.sum(Payment.amount), 0))
            .where(Payment.booking_id.in_(ids), Payment.status == "paid")
            .group_by(Payment.booking_id)
        ).all()
    )

    out: list[BookingOut] = []
    for booking in rows:
        paid = Decimal(sums.get(booking.id, 0))
        item = BookingOut.model_validate(booking)
        item.paid_amount = paid
        # ต้องใช้เกณฑ์เดียวกับ _summarise ใน payments.py เป๊ะ ๆ
        # ไม่งั้นหน้ารายการจองกับหน้าชำระเงินจะบอกสถานะไม่ตรงกัน
        if booking.total_price > 0 and paid >= booking.total_price:
            item.payment_state = "paid"
        elif paid > 0:
            item.payment_state = "deposit_paid"
        else:
            item.payment_state = "unpaid"
        out.append(item)
    return out


DAY = 1440   # จำนวนนาทีใน 1 วัน


def _add_minutes(t: time_cls, minutes: int) -> time_cls:
    """บวกนาทีให้กับเวลา

    เดิมโค้ดตรงนี้บีบชั่วโมงไว้ที่ 23 ทำให้บริการที่จบพอดีเที่ยงคืน
    (เช่น 23:00 + 60 นาที) กลายเป็น 23:00 แทนที่จะเป็น 00:00
    ผลคือ end_time เท่ากับ booking_time และระบบมองว่าคิวยาว 0 นาที
    จึงไม่กันคิวถัดไปเลย — จองทับกันได้
    """
    total = (_minutes(t) + minutes) % DAY
    return time_cls(hour=total // 60, minute=total % 60)


def _minutes(t: time_cls) -> int:
    return t.hour * 60 + t.minute


def shortstr(t: time_cls) -> str:
    """แปลงเวลาเป็นข้อความสั้น เช่น 10:00"""
    return t.strftime("%H:%M")


def _shop_capacity(db: Session, shop_id: int, on_date: date_cls | None = None) -> int:
    """จำนวนคิวที่ร้านรับพร้อมกันได้ในวันที่ระบุ

    ต้องนับเฉพาะ "ช่างที่เข้างานวันนั้นจริง" ไม่ใช่ช่างทั้งหมดที่ยังทำงานอยู่กับร้าน

    เดิมนับช่างทุกคนที่ is_active ทำให้เกิดปัญหาจริง:
    คลินิกมีหมอ 2 คน คนหนึ่งเข้าเฉพาะ จ/พ/ศ พอถึงวันอังคารเหลือคนเดียว
    แต่ระบบยังรับ 2 คิวพร้อมกัน ลูกค้าสองคนจะมาเจอกันแล้วมีคนต้องรอ

    ไม่ระบุวัน = นับช่างที่ยังทำงานอยู่ทั้งหมด (ใช้ตอนที่ยังไม่รู้วัน)
    """
    members = db.scalars(
        select(Staff).where(Staff.shop_id == shop_id, Staff.is_active.is_(True))
    ).all()

    # ร้านที่ยังไม่ได้เพิ่มช่างเลย ต้องจองได้ ถือว่ารับได้ 1 คิว
    # ต้องแยกจากกรณี "มีช่างแต่วันนั้นไม่มีใครเข้างาน" ซึ่งต้องได้ 0 คือปิดรับ
    # ของเดิมใช้ max(len, 1) ทำให้สองกรณีนี้ปนกัน คลินิกที่หมอเข้าเฉพาะ จ-ศ
    # จึงยังเปิดให้จองวันอาทิตย์ ลูกค้าไปถึงร้านแล้วไม่มีคนให้บริการ
    if not members:
        return 1
    if on_date is None:
        return len(members)
    return len([m for m in members if _staff_works_on(m, on_date)])


def _busy_intervals(
    db: Session,
    shop_id: int,
    on_date: date_cls,
    staff_id: int | None,
    exclude_booking_id: int | None = None,
) -> list[tuple[int, int]]:
    """คืนช่วงเวลาที่ถูกจองไปแล้วของวันนั้น เป็นหน่วยนาทีจากเที่ยงคืน

    ระบุช่าง  -> นับเฉพาะคิวของช่างคนนั้น (ช่างคนอื่นยังว่าง)
    ไม่ระบุช่าง -> นับคิวทั้งหมดของร้าน แล้วไปเทียบกับจำนวนช่างที่รับได้พร้อมกัน

    **นับเฉพาะคิวที่ล็อกช่องเวลาไว้แล้ว (holds_slot)**
    คิวที่กดจองไว้แต่ยังไม่จ่ายเงินไม่ถือว่ากันเวลา ลูกค้าคนอื่นเลือกเวลาเดียวกันได้
    ใครจ่ายก่อนได้ก่อน — ถ้าไม่ทำแบบนี้ คนที่กดจองทิ้งไว้เฉย ๆ จะล็อกตารางร้าน
    ทั้งวันได้ฟรีโดยที่ร้านไม่ได้อะไรเลย
    """
    stmt = select(Booking).where(
        Booking.shop_id == shop_id,
        Booking.booking_date == on_date,
        Booking.status.in_(["pending", "confirmed"]),
        Booking.holds_slot.is_(True),
    )
    if staff_id:
        stmt = stmt.where(Booking.staff_id == staff_id)
    # ตอนเลื่อนนัดต้องไม่นับคิวของตัวเองเป็นคิวที่ชน
    # ต้องตัดด้วย id เท่านั้น ตัดด้วยค่าเวลาไม่ได้ เพราะคิวของคนอื่นที่บังเอิญ
    # เวลาตรงกันจะถูกตัดทิ้งไปด้วย แล้วระบบจะยอมให้จองทับ
    if exclude_booking_id is not None:
        stmt = stmt.where(Booking.id != exclude_booking_id)

    out: list[tuple[int, int]] = []
    for b in db.scalars(stmt).all():
        start, end = _minutes(b.booking_time), _minutes(b.end_time)
        # คิวที่จบพอดีเที่ยงคืน (เช่น 23:00–00:00) จะได้ end = 0 ซึ่งน้อยกว่า start
        # ถ้าไม่ปรับ ช่วงจะกลายเป็นติดลบและระบบจะมองว่าไม่ทับกับใครเลย
        if end <= start:
            end += DAY
        out.append((start, end))
    return out


def _slot_used(start: int, end: int, busy: list[tuple[int, int]]) -> int:
    """นับว่ามีกี่คิวที่คาบเกี่ยวกับช่วงเวลานี้

    สองช่วงถือว่าทับกันเมื่อ "เริ่มก่อนที่อีกช่วงจะจบ และจบหลังจากที่อีกช่วงเริ่ม"
    การใช้ < และ > (ไม่ใช่ <= >=) ทำให้คิวที่ต่อกันพอดีไม่นับว่าทับ
    เช่นคิวเดิม 09:00-11:00 กับคิวใหม่ 11:00-13:00 จองได้ตามปกติ
    """
    return sum(1 for b_start, b_end in busy if start < b_end and end > b_start)


def _slot_is_taken(
    start: int, end: int, busy: list[tuple[int, int]], capacity: int
) -> bool:
    """ช่องเวลานี้เต็มหรือยัง

    นับจำนวนคิวที่คาบเกี่ยวกับช่วงนี้ ถ้าถึงจำนวนที่ร้านรับได้พร้อมกันแล้วถือว่าเต็ม
    """
    return _slot_used(start, end, busy) >= capacity


def _span_minutes(start_at: time_cls, duration: int) -> tuple[int, int]:
    """ช่วงเวลาของคิวเป็นนาทีจากเที่ยงคืน โดย **ไม่วนกลับ** เมื่อเลยเที่ยงคืน

    ห้ามคำนวณปลายช่วงจาก _minutes(end_time) เด็ดขาด
    เพราะ _add_minutes วน % 1440 คิวที่จบพอดีเที่ยงคืนจะได้ปลายช่วง = 0
    แล้วเงื่อนไข end > b_start ใน _slot_is_taken จะเป็นเท็จเสมอ
    ผลคือคิวช่วงดึกไม่ถูกตรวจการชนเลย จองทับกันได้ไม่จำกัด
    """
    begin = _minutes(start_at)
    return begin, begin + duration


def _assert_free(
    db: Session,
    shop: Shop,
    on_date: date_cls,
    start_at: time_cls,
    duration: int,
    staff_id: int | None,
    exclude_booking_id: int | None = None,
) -> None:
    """ตรวจว่าช่วงเวลานี้ยังว่างจริง ถ้าไม่ว่างโยน 409 พร้อมเหตุผล

    ต้องตรวจ **สองชั้น** เสมอ
      ชั้นที่ 1 ช่างคนที่เลือก ต้องไม่มีคิวคาบเกี่ยว
      ชั้นที่ 2 ทั้งร้าน ต้องไม่เกินจำนวนคนที่เข้างานวันนั้น

    ถ้าตรวจแค่ชั้นเดียวจะรับคิวเกินความจุ เพราะคิวที่ระบุช่างกับคิวที่ไม่ระบุช่าง
    ถูกนับคนละถัง ร้านที่มีช่าง 2 คนจะรับเวลาเดียวกันได้ถึง 4 คิว
    """
    start, end = _span_minutes(start_at, duration)

    if staff_id:
        own = _busy_intervals(db, shop.id, on_date, staff_id, exclude_booking_id)
        if _slot_is_taken(start, end, own, 1):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="ผู้ให้บริการคนนี้มีคิวในช่วงเวลานี้แล้ว กรุณาเลือกช่วงเวลาอื่นหรือเปลี่ยนคน",
            )

    everyone = _busy_intervals(db, shop.id, on_date, None, exclude_booking_id)
    if _slot_is_taken(start, end, everyone, _shop_capacity(db, shop.id, on_date)):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="ช่วงเวลานี้คิวเต็มแล้ว กรุณาเลือกช่วงเวลาอื่น",
        )


def _work_days(member: Staff) -> set[int] | None:
    """แปลง "1,2,3,4,5" เป็นเซ็ตของเลขวัน · คืน None ถ้าไม่ได้กำหนด (= ทำทุกวัน)

    ใช้เลขแบบเดียวกับ JavaScript: 0=อาทิตย์ ... 6=เสาร์
    """
    if not member.work_days:
        return None
    try:
        return {int(x) for x in member.work_days.split(",") if x.strip() != ""}
    except ValueError:
        return None


def _staff_works_on(member: Staff, on_date: date_cls) -> bool:
    """ช่างคนนี้เข้างานวันนั้นหรือไม่"""
    days = _work_days(member)
    if days is None:
        return True
    # Python: Monday=0..Sunday=6 → แปลงเป็น Sunday=0..Saturday=6
    return ((on_date.weekday() + 1) % 7) in days


def _windows_for(shop: Shop, member: Staff | None) -> list[tuple[int, int]]:
    """ช่วงเวลาที่เปิดให้จองในวันหนึ่ง เป็นนาทีจากเที่ยงคืน

    คืนเป็น "รายการช่วง" ไม่ใช่ช่วงเดียว เพราะร้านที่เปิดคร่อมเที่ยงคืน
    เช่น สนามบอลเปิด 06:00–02:00 ในหนึ่งวันปฏิทินจะมีสองช่วง คือ
    00:00–02:00 (ท้ายรอบของคืนก่อน) และ 06:00–24:00

    เดิมโค้ดคืนค่าเดียวเป็น (360, 120) ซึ่งจุดเริ่มมากกว่าจุดจบ
    ทำให้เงื่อนไข start + duration <= close ไม่เป็นจริงสักครั้ง
    ผลคือสนามที่เปิดถึงตี 2 หรือเปิด 24 ชั่วโมง "จองไม่ได้เลยทั้งวัน"

    ถ้าเลือกช่าง จะตัดให้อยู่ในเวลาทำงานของช่างคนนั้นด้วย
    เช่น ร้านเปิด 10:00–20:00 แต่ช่างเข้า 13:00 → จองได้ตั้งแต่ 13:00
    """
    open_m, close_m = _minutes(shop.open_time), _minutes(shop.close_time)

    if open_m == close_m:
        segments = [(0, DAY)]                    # เปิด-ปิดเวลาเดียวกัน = เปิด 24 ชั่วโมง
    elif open_m < close_m:
        segments = [(open_m, close_m)]           # เวลาทำการปกติภายในวันเดียว
    else:
        segments = [(0, close_m), (open_m, DAY)] # คร่อมเที่ยงคืน แยกเป็นสองช่วง

    if member is None:
        return segments

    lo = _minutes(member.work_start) if member.work_start is not None else 0
    hi = _minutes(member.work_end) if member.work_end is not None else DAY

    # กะของช่างก็แตกเป็นสองช่วงได้เหมือนเวลาเปิดร้าน
    # ของเดิมตีความ hi <= lo ว่า "ทำถึงสิ้นวัน" ซึ่งทำให้ช่างกะดึก 22:00-02:00
    # เสียช่วงเที่ยงคืนถึงตีสองไปทั้งหมด ร้านที่เปิดถึงดึกจึงขายครึ่งกะไม่ได้เลย
    if lo == hi:
        shifts = [(0, DAY)]                      # เข้างานตลอดเวลาที่ร้านเปิด
    elif lo < hi:
        shifts = [(lo, hi)]
    else:
        shifts = [(0, hi), (lo, DAY)]            # กะข้ามคืน

    # ตัดแต่ละช่วงของร้านด้วยแต่ละกะของช่าง แล้วทิ้งช่วงที่ไม่เหลือเวลา
    clipped = {
        (max(seg_s, sh_s), min(seg_e, sh_e))
        for seg_s, seg_e in segments
        for sh_s, sh_e in shifts
    }
    return sorted((s, e) for s, e in clipped if e > s)


def _fits_window(start_at: time_cls, duration: int, windows: list[tuple[int, int]]) -> bool:
    """คิวนี้เริ่มและจบอยู่ในช่วงเปิดทำการช่วงใดช่วงหนึ่งหรือไม่

    ต้องอยู่ใน "ช่วงเดียวกัน" ทั้งเริ่มและจบ ไม่ใช่คร่อมสองช่วง
    เช่น สนามเปิด 00:00–02:00 และ 06:00–24:00 การจอง 01:30 ยาว 2 ชั่วโมง
    จะจบ 03:30 ซึ่งตกอยู่ในเวลาที่สนามปิด จึงต้องถูกปฏิเสธ
    """
    begin = _minutes(start_at)
    finish = begin + duration
    return any(begin >= s and finish <= e for s, e in windows)


def _window_text(segments: list[tuple[int, int]]) -> str:
    """ข้อความบอกช่วงเวลาทำการ ใช้ในข้อความแจ้งเตือนผู้ใช้"""
    def fmt(m: int) -> str:
        m %= DAY
        return f"{m // 60:02d}:{m % 60:02d}"

    if segments == [(0, DAY)]:
        return "ตลอด 24 ชั่วโมง"
    return " และ ".join(f"{fmt(s)}–{fmt(e)}" for s, e in segments)


def _closure_reason(db: Session, shop_id: int, on_date: date_cls) -> str | None:
    """ร้านประกาศปิดวันนั้นไว้หรือไม่ ถ้าปิดคืนเหตุผลกลับไป"""
    row = db.scalar(
        select(ShopClosure).where(
            ShopClosure.shop_id == shop_id, ShopClosure.closed_date == on_date
        )
    )
    if row is None:
        return None
    return f"ร้านปิด{f' — {row.reason}' if row.reason else 'ในวันนี้'}"


def _recalc_shop_rating(db: Session, shop_id: int) -> None:
    """คำนวณคะแนนเฉลี่ยของร้านใหม่จากรีวิวทั้งหมด"""
    shop = db.get(Shop, shop_id)
    if shop is None:
        return
    avg, count = db.execute(
        select(func.avg(Review.rating), func.count(Review.id)).where(Review.shop_id == shop_id)
    ).one()
    shop.rating_avg = Decimal(str(avg or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    shop.rating_count = count or 0


def _recalc_staff_rating(db: Session, staff_id: int) -> None:
    """คำนวณคะแนนเฉลี่ยของช่างใหม่ — นับเฉพาะรีวิวที่ให้ดาวช่างไว้"""
    member = db.get(Staff, staff_id)
    if member is None:
        return
    avg, count = db.execute(
        select(func.avg(Review.staff_rating), func.count(Review.id)).where(
            Review.staff_id == staff_id, Review.staff_rating.isnot(None)
        )
    ).one()
    member.rating_avg = Decimal(str(avg or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    member.rating_count = count or 0


def _short_name(full: str | None) -> str:
    """ย่อชื่อเต็มเป็น "ชื่อจริง อักษรแรกของนามสกุล." เช่น พลอย รัตนา -> พลอย ร."""
    if not full:
        return "ผู้ใช้บริการ"
    parts = full.strip().split()
    if len(parts) == 1:
        return parts[0]
    return f"{parts[0]} {parts[1][0]}."


def _with_names(db: Session, rows: list[Review]) -> list[ReviewOut]:
    """แปลงรีวิวเป็นรูปแบบส่งออก พร้อมเติมชื่อย่อของผู้เขียน

    ดึงชื่อทีเดียวทั้งชุด ไม่ยิงทีละรีวิว (กัน N+1 query)
    """
    if not rows:
        return []
    ids = {r.user_id for r in rows}
    names = dict(db.execute(select(User.id, User.full_name).where(User.id.in_(ids))).all())

    out = []
    for r in rows:
        item = ReviewOut.model_validate(r)
        item.user_name = _short_name(names.get(r.user_id))
        out.append(item)
    return out


def _get_booking_or_404(db: Session, booking_id: int) -> Booking:
    booking = db.get(Booking, booking_id)
    if booking is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ไม่พบการจองนี้")
    return booking


# ---------------- ช่วงเวลาว่าง ----------------
@router.get(
    "/services/{service_id}/availability",
    response_model=AvailabilityOut,
    tags=["4. Bookings & Reviews"],
    summary="ดูช่วงเวลาว่างของบริการในวันที่เลือก",
)
def get_availability(
    service_id: int = Path(..., ge=1),
    booking_date: date_cls = Query(..., alias="date", description="วันที่ต้องการจอง (YYYY-MM-DD)"),
    staff_id: int | None = Query(None, ge=1, description="ระบุช่างเพื่อดูคิวว่างของช่างคนนั้น"),
    db: Session = Depends(get_db),
):
    """คืนช่องเวลาทั้งวันพร้อมบอกว่าช่องไหนว่าง ช่องไหนถูกจองไปแล้ว

    ใช้แสดงผลแบบเลือกที่นั่งโรงหนัง — ลูกค้าเห็นทุกช่องแล้วกดเลือกได้ทันที
    """
    service = db.get(Service, service_id)
    if service is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ไม่พบบริการนี้")

    if service.booking_mode == "instant":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="บริการนี้เป็นแบบเรียกใช้ทันที จึงไม่มีตารางช่องเวลาให้เลือก",
        )

    shop = service.shop
    duration = service.duration_minutes

    # ตรวจว่าช่างที่ระบุอยู่ในร้านนี้จริง
    member: Staff | None = None
    if staff_id is not None:
        member = db.get(Staff, staff_id)
        if member is None or member.shop_id != shop.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ไม่พบช่างคนนี้ในร้าน")

    # ต้องนับทั้งสองชั้นเหมือนตอนสร้างการจอง ไม่งั้นตารางกับหน้าจองจะขัดกัน
    # (เลือกช่าง = คิวของช่างคนนั้น + คิวรวมของร้านต้องยังไม่เต็ม)
    busy_staff = _busy_intervals(db, shop.id, booking_date, staff_id) if staff_id else []
    busy_all = _busy_intervals(db, shop.id, booking_date, None)
    shop_cap = _shop_capacity(db, shop.id, booking_date)

    # ช่วงเวลาที่จองได้ = เวลาร้านเปิด ตัดด้วยเวลาทำงานของช่าง (ถ้าเลือกช่าง)
    windows = _windows_for(shop, member)
    now = now_local()
    is_today = booking_date == now.date()
    now_m = now.hour * 60 + now.minute

    # เหตุผลระดับทั้งวัน — ถ้าติดข้อนี้ ทุกช่องจะจองไม่ได้เหมือนกันหมด
    closed_reason: str | None = _closure_reason(db, shop.id, booking_date)
    if closed_reason:
        pass                                  # ร้านปิดทั้งวัน เหตุผลอื่นไม่ต้องตรวจต่อ
    elif not service.is_active:
        closed_reason = "บริการนี้ปิดให้บริการชั่วคราว"
    elif member is not None and not member.is_active:
        closed_reason = f"{member.name} ไม่รับคิวในช่วงนี้"
    elif member is not None and not _staff_works_on(member, booking_date):
        closed_reason = f"{member.name} หยุดวันนี้"
    elif booking_date < now.date():
        closed_reason = "วันที่ผ่านไปแล้ว"
    elif booking_date > now.date() + timedelta(days=MAX_ADVANCE_DAYS):
        # ต้องบอกด้วยว่าทำไม ไม่ใช่โชว์ช่องเวลาว่างเต็มวันแล้วไปเด้ง error ตอนกดยืนยัน
        closed_reason = f"เปิดให้จองล่วงหน้าได้ไม่เกิน {MAX_ADVANCE_DAYS} วัน"
    elif staff_id is None and shop_cap == 0:
        # มีช่างในระบบ แต่วันนั้นไม่มีใครเข้างานเลย
        closed_reason = "วันนี้ไม่มีผู้ให้บริการเข้างาน"

    # ไล่สร้างช่องเวลาทีละช่วง — ร้านที่เปิดคร่อมเที่ยงคืนจะมีสองช่วงในวันเดียว
    slots: list[Slot] = []
    for seg_start, seg_end in windows:
        start = seg_start
        while start + duration <= seg_end:
            end = start + duration
            reason = closed_reason

            # เหลือรับได้อีกกี่ที่ในช่วงนี้ — ใช้บอกผู้ใช้ว่า "เหลือ 2 คอร์ท"
            #
            # จำเป็นมากสำหรับร้านที่รับได้พร้อมกันหลายที่ เช่นสนามแบดมินตัน 10 คอร์ท
            # ถ้าบอกแค่ว่า "ว่าง" ผู้ใช้จะแยกไม่ออกว่าเหลือคอร์ทเดียวหรือเหลือครบสิบ
            # และจะงงว่าทำไมจองไปแล้วช่องเดิมยังกดได้อยู่ (เพราะยังเหลืออีก 9 คอร์ท)
            used = _slot_used(start, end, busy_all)
            remaining = max(shop_cap - used, 0)

            if reason is None:
                if is_today and start <= now_m:
                    reason = "เวลาผ่านไปแล้ว"
                elif staff_id and _slot_is_taken(start, end, busy_staff, 1):
                    reason = "คิวเต็มแล้ว"
                elif remaining <= 0:
                    reason = "คิวเต็มแล้ว"

            slots.append(
                Slot(
                    # end อาจเท่ากับ 1440 พอดี (จบเที่ยงคืน) ต้องวนกลับเป็น 00:00
                    time=time_cls(start // 60, start % 60),
                    end_time=time_cls((end % DAY) // 60, end % 60),
                    available=reason is None,
                    reason=reason,
                    remaining=0 if reason else remaining,
                    capacity=shop_cap,
                )
            )
            start += SLOT_STEP_MINUTES

    # เรียงตามเวลาอีกครั้ง เพราะช่วงหลังเที่ยงคืนถูกสร้างก่อนช่วงกลางวัน
    slots.sort(key=lambda s: s.time)

    return AvailabilityOut(
        service_id=service.id,
        service_name=service.name,
        duration_minutes=duration,
        booking_date=booking_date,
        staff_id=staff_id,
        staff_name=member.name if member else None,
        open_time=shop.open_time,
        close_time=shop.close_time,
        slots=slots,
        available_count=sum(1 for s in slots if s.available),
        closed_reason=closed_reason,
    )


# ---------------- การจอง ----------------
@router.get("/bookings", response_model=Page[BookingOut], summary="ดูรายการจอง")
def list_bookings(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    booking_status: str | None = Query(
        None, alias="status", pattern="^(pending|confirmed|completed|cancelled)$"
    ),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """ลูกค้าเห็นเฉพาะของตัวเอง · เจ้าของร้านเห็นของร้านตัวเอง · admin เห็นทั้งหมด"""
    stmt = select(Booking)

    if current_user.role == "customer":
        stmt = stmt.where(Booking.user_id == current_user.id)
    elif current_user.role == "owner":
        shop_ids = select(Shop.id).where(Shop.owner_id == current_user.id)
        stmt = stmt.where(Booking.shop_id.in_(shop_ids))

    if booking_status:
        stmt = stmt.where(Booking.status == booking_status)

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(
        stmt.order_by(Booking.booking_date.desc(), Booking.booking_time.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    ).all()

    return Page[BookingOut](
        items=_with_payment(db, list(rows)),
        page=page,
        limit=limit,
        total=total,
        total_pages=(total + limit - 1) // limit,
    )


@router.get("/bookings/{booking_id}", response_model=BookingOut, summary="รายละเอียดการจอง")
def get_booking(
    booking_id: int = Path(..., ge=1),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    booking = _get_booking_or_404(db, booking_id)

    shop = db.get(Shop, booking.shop_id)
    allowed = (
        current_user.role == "admin"
        or booking.user_id == current_user.id
        or (shop is not None and shop.owner_id == current_user.id)
    )
    if not allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="คุณไม่มีสิทธิ์ดูการจองนี้")

    return _with_payment(db, [booking])[0]


@router.post(
    "/bookings/instant",
    response_model=BookingOut,
    status_code=status.HTTP_201_CREATED,
    summary="เรียกใช้บริการทันที (ส่งของด่วน)",
    description=(
        "สำหรับบริการที่ตั้งค่า `booking_mode = instant` เช่น บริการส่งของด่วน\n\n"
        "ต่างจากการจองปกติตรงที่ **ไม่ต้องเลือกวันและเวลา** — ระบบใช้เวลาปัจจุบัน "
        "ยืนยันงานให้ทันที และคิดค่าบริการจากค่าเริ่มต้นบวกค่าระยะทาง\n\n"
        "เนื่องจากเป็นงานที่ออกรถทันที ระบบจึงไม่ตรวจเวลาทำการรายช่อง "
        "แต่ยังตรวจว่าร้านเปิดอยู่จริงในขณะนั้น"
    ),
)
def create_instant_booking(
    payload: InstantBookingCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = db.get(Service, payload.service_id)
    if service is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ไม่พบบริการนี้")
    if service.booking_mode != "instant":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="บริการนี้ต้องจองโดยเลือกวันและเวลา ไม่สามารถเรียกใช้ทันทีได้",
        )
    if not service.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="บริการนี้ปิดให้บริการชั่วคราว"
        )

    shop = service.shop
    now = now_local()

    # ร้านประกาศหยุดวันนี้ไหม
    closed = _closure_reason(db, shop.id, now.date())
    if closed:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=closed)

    # ต้องอยู่ในเวลาทำการ ณ ขณะนี้ — งานด่วนออกรถทันที ถ้าร้านปิดก็รับงานไม่ได้
    windows = _windows_for(shop, None)
    now_m = now.hour * 60 + now.minute
    if not any(s <= now_m < e for s, e in windows):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"ขณะนี้อยู่นอกเวลาให้บริการ ({_window_text(windows)}) กรุณาลองใหม่ในเวลาทำการ",
        )

    # เจ้าของร้านเท่านั้นที่รับงานแทนลูกค้าที่ไม่มีบัญชีได้ (กฎเดียวกับการจองปกติ)
    if payload.guest_name or payload.guest_phone:
        is_owner = shop.owner_id == current_user.id or current_user.role == "admin"
        if not is_owner:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="เฉพาะเจ้าของร้านเท่านั้นที่บันทึกงานแทนลูกค้าได้",
            )
        if not payload.guest_name:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="กรุณาระบุชื่อลูกค้าด้วย ไม่ใช่แค่เบอร์โทร",
            )

    # ค่าบริการ = ค่าเริ่มต้น + (ระยะทาง × ค่าต่อกิโลเมตร)
    distance = Decimal(payload.distance_km).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    total = (service.price + service.price_per_km * distance).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )
    deposit = (total * Decimal("0.2")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    # งานที่รับตอนดึกแล้วจะจบข้ามวัน ให้ตัดปลายไว้ที่สิ้นวัน
    # ระบบทั้งระบบยึดกฎ "หนึ่งการจองจบภายในวันเดียวกัน" ถ้าปล่อยให้ end_time
    # วนกลับไปเป็นเวลาเช้า คิวจะดูเหมือนยาวติดลบ และช่วงที่ล้ำไปวันใหม่จะไม่ถูกกันไว้
    start_at = time_cls(now.hour, now.minute)
    end_at = _add_minutes(start_at, service.duration_minutes)
    if _minutes(end_at) <= _minutes(start_at):
        end_at = time_cls(23, 59)

    booking = Booking(
        booking_code=_generate_booking_code(),
        user_id=current_user.id,
        service_id=service.id,
        shop_id=shop.id,
        staff_id=None,
        booking_date=now.date(),
        booking_time=start_at,
        end_time=end_at,
        total_price=total,
        deposit_amount=deposit,
        # งานด่วนยืนยันทันที ไม่ต้องรอร้านกดรับ ไม่งั้นความ "ด่วน" จะไม่มีความหมาย
        status="confirmed",
        # งานด่วนออกรถทันที พนักงานถูกใช้ไปแล้วจริง จึงล็อกช่องเวลาเลย
        # ไม่ต้องรอชำระเงิน (เก็บเงินปลายทางตอนส่งถึงที่)
        holds_slot=True,
        note=payload.note,
        pickup_address=payload.pickup_address.strip(),
        dropoff_address=payload.dropoff_address.strip(),
        distance_km=distance,
        guest_name=payload.guest_name,
        guest_phone=payload.guest_phone,
    )
    db.add(booking)

    notify(
        db, shop.owner_id, "booking_new",
        f"งานส่งด่วนเข้าใหม่ · {distance} กม.",
        f"รับที่ {payload.pickup_address[:60]}",
        "manage.html",
    )

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT if _slot_conflict(exc) else 500,
            detail="บันทึกงานไม่สำเร็จ กรุณาลองใหม่อีกครั้ง",
        )
    db.refresh(booking)
    return _with_payment(db, [booking])[0]


@router.post(
    "/bookings",
    response_model=BookingOut,
    status_code=status.HTTP_201_CREATED,
    summary="จองคิว",
)
def create_booking(
    payload: BookingCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """จองคิวบริการ — กันจองย้อนหลัง กันเวลานอกเวลาทำการ และกันคิวคาบเกี่ยวกัน

    เจ้าของร้านส่ง guest_name มาด้วยได้ เพื่อจองแทนลูกค้าที่โทรมาหรือเดินเข้าร้าน
    """
    service = db.get(Service, payload.service_id)
    if service is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ไม่พบบริการนี้")
    if not service.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="บริการนี้ปิดให้บริการชั่วคราว"
        )
    # บริการแบบเรียกทันทีไม่มีช่องเวลาให้จอง ต้องไปใช้ /api/bookings/instant
    # ถ้าปล่อยผ่าน ลูกค้าจะจองงานส่งด่วนล่วงหน้าข้ามสัปดาห์ได้ ซึ่งไม่ใช่ความหมายของบริการ
    if service.booking_mode == "instant":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="บริการนี้เป็นแบบเรียกใช้ทันที กรุณาใช้ปุ่มเรียกใช้บริการแทนการเลือกวันเวลา",
        )

    shop = service.shop

    # ร้านประกาศปิดวันนั้นไว้หรือเปล่า
    closed = _closure_reason(db, shop.id, payload.booking_date)
    if closed:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"{closed} กรุณาเลือกวันอื่น",
        )

    # ตรวจว่าช่างที่เลือกอยู่ในร้านนี้และยังเปิดรับงาน
    member: Staff | None = None
    if payload.staff_id is not None:
        member = db.get(Staff, payload.staff_id)
        if member is None or member.shop_id != shop.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ไม่พบช่างคนนี้ในร้าน")
        if not member.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="ช่างคนนี้ไม่รับคิวในขณะนี้"
            )
        # ช่างต้องเข้างานในวันที่ลูกค้าเลือก
        if not _staff_works_on(member, payload.booking_date):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"{member.name} หยุดในวันที่เลือก กรุณาเลือกวันอื่นหรือเปลี่ยนช่าง",
            )

    # วันที่ต้องอยู่ในช่วงที่รับจองได้ (ไม่ย้อนหลัง และไม่เกินเพดานล่วงหน้า)
    _assert_within_window(payload.booking_date)

    # ห้ามจองย้อนหลังในระดับ "เวลา" ด้วย — วันนี้ตอนบ่ายจองรอบเช้าไม่ได้
    booking_dt = datetime.combine(payload.booking_date, payload.booking_time)
    if booking_dt < now_local():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="ไม่สามารถจองย้อนหลังได้ กรุณาเลือกวันเวลาในอนาคต",
        )

    # บริการต้องเริ่มและจบภายในเวลาทำการ (และภายในเวลาทำงานของช่าง ถ้าระบุช่าง)
    end_time = _add_minutes(payload.booking_time, service.duration_minutes)
    windows = _windows_for(shop, member)
    if not _fits_window(payload.booking_time, service.duration_minutes, windows):
        who = f"{member.name} ทำงาน" if member is not None else "ร้านเปิด"
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"บริการนี้ใช้เวลา {service.duration_minutes} นาที "
                f"{who} {_window_text(windows)} "
                "จึงต้องจองให้เสร็จภายในช่วงนี้"
            ),
        )

    # กันคิวคาบเกี่ยว (ไม่ใช่แค่เวลาเริ่มตรงกัน) ทั้งชั้นช่างและชั้นความจุร้าน
    _assert_free(
        db, shop, payload.booking_date, payload.booking_time,
        service.duration_minutes, payload.staff_id,
    )

    # จองแทนลูกค้าที่ไม่มีบัญชี — ทำได้เฉพาะเจ้าของร้านนั้นและผู้ดูแลระบบ
    # ตรวจทั้งชื่อและเบอร์ ไม่งั้นลูกค้าทั่วไปจะแอบยัดเบอร์คนอื่นใส่คิวตัวเองได้
    if payload.guest_name or payload.guest_phone:
        is_owner = shop.owner_id == current_user.id
        if not (is_owner or current_user.role == "admin"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="เฉพาะเจ้าของร้านเท่านั้นที่จองแทนลูกค้าได้",
            )
        if not payload.guest_name:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="กรุณาระบุชื่อลูกค้าด้วย ไม่ใช่แค่เบอร์โทร",
            )

    deposit = (service.price * Decimal("0.2")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    booking = Booking(
        booking_code=_generate_booking_code(),
        user_id=current_user.id,
        guest_name=payload.guest_name,
        guest_phone=payload.guest_phone,
        # คิวที่ร้านกดจองเองถือว่ายืนยันแล้ว ไม่ต้องรอร้านยืนยันซ้ำ
        status="confirmed" if payload.guest_name else "pending",
        # ร้านกดจองแทนลูกค้าหน้าร้าน = ล็อกช่องเวลาทันที เพราะร้านเป็นเจ้าของตาราง
        # และรู้อยู่แล้วว่าลูกค้ามาจริง ส่วนลูกค้าที่จองเองต้องจ่ายก่อนถึงจะล็อกได้
        holds_slot=bool(payload.guest_name),
        service_id=service.id,
        shop_id=shop.id,
        staff_id=payload.staff_id,
        booking_date=payload.booking_date,
        booking_time=payload.booking_time,
        end_time=end_time,
        total_price=service.price,
        deposit_amount=deposit,
        note=payload.note,
        requirements=payload.requirements,
        reference_url=payload.reference_url,
        health_note=payload.health_note,
    )
    db.add(booking)

    # แจ้งเจ้าของร้านว่ามีคิวเข้ามา (ยกเว้นกรณีร้านกดจองเอง จะได้ไม่เตือนตัวเอง)
    if shop.owner_id != current_user.id:
        who = payload.guest_name or current_user.full_name
        notify(
            db, shop.owner_id, "booking_new",
            f"มีคิวใหม่จาก {who}",
            f"{service.name} · {payload.booking_date} {shortstr(payload.booking_time)} น.",
            "manage.html",
        )

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        # แยกให้ออกว่าชนเพราะอะไร ไม่งั้นรหัสการจองซ้ำจะไปขึ้นข้อความว่าคิวชน
        # แล้วลูกค้าจะเปลี่ยนเวลาไปเรื่อย ๆ โดยที่แก้ไม่ตรงจุด
        if _slot_conflict(exc):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="ช่วงเวลานี้เพิ่งถูกจองไป กรุณาเลือกช่วงเวลาอื่น",
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="บันทึกการจองไม่สำเร็จ กรุณาลองใหม่อีกครั้ง",
        )

    db.refresh(booking)
    return _with_payment(db, [booking])[0]


@router.patch(
    "/bookings/{booking_id}/status",
    response_model=BookingOut,
    summary="เปลี่ยนสถานะการจอง",
)
def update_booking_status(
    payload: BookingStatusUpdate,
    booking_id: int = Path(..., ge=1),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """ลูกค้ายกเลิกได้อย่างเดียว · เจ้าของร้านและ admin เปลี่ยนได้ทุกสถานะ"""
    booking = _get_booking_or_404(db, booking_id)
    shop = db.get(Shop, booking.shop_id)

    is_admin = current_user.role == "admin"
    is_owner = shop is not None and shop.owner_id == current_user.id
    is_customer = booking.user_id == current_user.id

    if not (is_admin or is_owner or is_customer):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="คุณไม่มีสิทธิ์แก้ไขการจองนี้")
    if is_customer and not (is_owner or is_admin) and payload.status != "cancelled":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="ลูกค้าสามารถยกเลิกการจองได้เท่านั้น",
        )
    if booking.status == "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="การจองที่เสร็จสิ้นแล้วไม่สามารถเปลี่ยนสถานะได้",
        )

    # จะ "ล็อกช่องเวลา" ให้คิวนี้ในรอบนี้ไหม
    #
    # ร้านกดยืนยันคิว = ร้านรับปากลูกค้าแล้ว ต้องกันเวลาให้จริงแม้ยังไม่ได้เงิน
    # (เช่นลูกค้าโทรมาคุยแล้วร้านตกลงรับ) ถ้าไม่ล็อก คนอื่นจะแย่งช่องนั้นไปได้
    # ส่วนลูกค้าเองเปลี่ยนสถานะเป็น confirmed ไม่ได้อยู่แล้ว จึงล็อกเองไม่ได้
    will_hold = (
        payload.status in ("pending", "confirmed")
        and not booking.holds_slot
        and (is_owner or is_admin)
        and payload.status == "confirmed"
    )

    # ต้องตรวจว่าช่องเวลายังว่างจริงก่อน "ทุกครั้งที่กำลังจะไปกันเวลาให้ใคร"
    #
    # สองกรณีที่ต้องตรวจ
    #   1. ดึงคิวที่ยกเลิกไปแล้วกลับมา — ระหว่างที่ยกเลิก ช่องนั้นเปิดให้คนอื่นไปแล้ว
    #   2. ร้านกดยืนยันคิวที่ยังไม่จ่าย — ระหว่างรอ อาจมีคนอื่นจ่ายเงินตัดหน้าไปแล้ว
    reviving = booking.status == "cancelled" and payload.status in ("pending", "confirmed")
    if reviving or will_hold:
        service = db.get(Service, booking.service_id)
        if service is not None and shop is not None:
            _assert_free(
                db, shop, booking.booking_date, booking.booking_time,
                service.duration_minutes, booking.staff_id,
                exclude_booking_id=booking.id,
            )

    if payload.status == "cancelled" and booking.status != "cancelled":
        who = "customer" if (is_customer and not is_owner and not is_admin) else (
            "shop" if is_owner else "admin"
        )
        fee, refundable = _apply_cancellation(db, booking, who)
        _notify_cancellation(db, booking, shop, who, fee, refundable)
    else:
        booking.status = payload.status
        if will_hold:
            booking.holds_slot = True

        # แจ้งลูกค้าเมื่อร้านเปลี่ยนสถานะให้ (ถ้าลูกค้าเปลี่ยนเอง ไม่ต้องเตือนตัวเอง)
        if booking.user_id != current_user.id:
            service = db.get(Service, booking.service_id)
            label = {
                "confirmed": "ร้านยืนยันคิวของคุณแล้ว",
                "completed": "ใช้บริการเสร็จแล้ว เขียนรีวิวได้เลย",
                "pending": "คิวของคุณกลับไปสถานะรอยืนยัน",
            }.get(payload.status, "คิวของคุณมีการเปลี่ยนแปลง")
            notify(
                db, booking.user_id, f"booking_{payload.status}", label,
                f"{service.name if service else ''} · {booking.booking_date} "
                f"{shortstr(booking.booking_time)} น. · {booking.booking_code}",
            )

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="ช่วงเวลาเดิมถูกจองไปแล้ว กรุณาใช้การเลื่อนนัดแทน",
        )
    db.refresh(booking)
    return _with_payment(db, [booking])[0]


@router.patch(
    "/bookings/{booking_id}/reschedule",
    response_model=BookingOut,
    summary="เลื่อนนัด (เปลี่ยนวันเวลาหรือช่าง)",
)
def reschedule_booking(
    payload: BookingReschedule,
    booking_id: int = Path(..., ge=1),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """ย้ายคิวเดิมไปเวลาใหม่ โดยตรวจเงื่อนไขชุดเดียวกับตอนจองครั้งแรก

    ดีกว่าให้ลูกค้ายกเลิกแล้วจองใหม่ เพราะรหัสการจองและข้อมูลที่กรอกไว้ยังอยู่ครบ
    """
    booking = _get_booking_or_404(db, booking_id)
    shop = db.get(Shop, booking.shop_id)

    allowed = (
        current_user.role == "admin"
        or booking.user_id == current_user.id
        or (shop is not None and shop.owner_id == current_user.id)
    )
    if not allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="คุณไม่มีสิทธิ์เลื่อนนัดนี้")
    if booking.status not in ("pending", "confirmed"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="เลื่อนได้เฉพาะคิวที่ยังไม่ถูกยกเลิกและยังไม่ได้ใช้บริการ",
        )

    service = db.get(Service, booking.service_id)
    if service is None or shop is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ไม่พบบริการของการจองนี้")

    # เลื่อนนัดต้องอยู่ในช่วงเดียวกับการจองใหม่ ไม่งั้นจะเลี่ยงเพดานได้
    # ด้วยการจองวันพรุ่งนี้ก่อนแล้วค่อยเลื่อนไปปี 2080
    _assert_within_window(payload.booking_date)

    closed = _closure_reason(db, shop.id, payload.booking_date)
    if closed:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"{closed} กรุณาเลือกวันอื่น"
        )

    member: Staff | None = None
    if payload.staff_id is not None:
        member = db.get(Staff, payload.staff_id)
        if member is None or member.shop_id != shop.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ไม่พบช่างคนนี้ในร้าน")
        if not member.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="ช่างคนนี้ไม่รับคิวในขณะนี้"
            )
        if not _staff_works_on(member, payload.booking_date):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"{member.name} หยุดในวันที่เลือก กรุณาเลือกวันอื่นหรือเปลี่ยนช่าง",
            )

    if datetime.combine(payload.booking_date, payload.booking_time) < now_local():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="เลื่อนไปเวลาที่ผ่านมาแล้วไม่ได้"
        )

    end_time = _add_minutes(payload.booking_time, service.duration_minutes)
    windows = _windows_for(shop, member)
    if not _fits_window(payload.booking_time, service.duration_minutes, windows):
        who = f"{member.name} ทำงาน" if member is not None else "ร้านเปิด"
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"บริการนี้ใช้เวลา {service.duration_minutes} นาที "
                f"{who} {_window_text(windows)} "
                "จึงต้องจองให้เสร็จภายในช่วงนี้"
            ),
        )

    # ตรวจคิวชน โดยไม่นับคิวของตัวเองที่กำลังจะย้ายออกไป
    #
    # ต้องตัดด้วย **id ของการจอง** เท่านั้น
    # ของเดิมตัดด้วยค่าเวลา (busy.remove) ซึ่งพังสองทาง:
    #   - เปลี่ยนช่างพร้อมเปลี่ยนเวลา แล้วช่างคนใหม่บังเอิญมีคิวเวลาเดียวกับคิวเดิมของเรา
    #     คิวของเขาจะถูกตัดทิ้ง ระบบเลยยอมให้จองทับ
    #   - คิวที่จบพอดีเที่ยงคืนจะเทียบไม่ตรง เลื่อนคิวตัวเองแล้วโดนบอกว่าชนกับตัวเอง
    _assert_free(
        db, shop, payload.booking_date, payload.booking_time,
        service.duration_minutes, payload.staff_id,
        exclude_booking_id=booking.id,
    )

    booking.booking_date = payload.booking_date
    booking.booking_time = payload.booking_time
    booking.end_time = end_time
    booking.staff_id = payload.staff_id

    # แจ้งอีกฝ่ายเสมอ ลูกค้าเลื่อนเองร้านต้องรู้ ร้านเลื่อนให้ลูกค้าก็ต้องรู้
    moved = (
        f"{service.name} · {payload.booking_date} {shortstr(payload.booking_time)} น. "
        f"· {booking.booking_code}"
    )
    if booking.user_id == current_user.id:
        notify(db, shop.owner_id, "booking_moved", "ลูกค้าเลื่อนนัด", moved, "manage.html")
    else:
        notify(db, booking.user_id, "booking_moved", "ร้านเลื่อนนัดให้คุณ", moved)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="ช่วงเวลานี้เพิ่งถูกจองไป กรุณาเลือกเวลาอื่น"
        )

    db.refresh(booking)
    return _with_payment(db, [booking])[0]


@router.delete("/bookings/{booking_id}", response_model=Message, summary="ยกเลิกการจอง")
def cancel_booking(
    booking_id: int = Path(..., ge=1),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    booking = _get_booking_or_404(db, booking_id)
    shop = db.get(Shop, booking.shop_id)

    allowed = (
        current_user.role == "admin"
        or booking.user_id == current_user.id
        or (shop is not None and shop.owner_id == current_user.id)
    )
    if not allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="คุณไม่มีสิทธิ์ยกเลิกการจองนี้")
    if booking.status == "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="การจองที่ใช้บริการแล้วยกเลิกไม่ได้"
        )

    if booking.status == "cancelled":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="การจองนี้ถูกยกเลิกไปแล้ว"
        )

    # ใครเป็นคนกดยกเลิก ตัดสินว่าต้องหักค่ามัดจำหรือไม่
    # ถ้าเจ้าของร้านเป็นคนกด ลูกค้าไม่ผิด จึงไม่หัก แม้เจ้าของร้านจะเป็นลูกค้าคิวนั้นเองก็ตาม
    if shop is not None and shop.owner_id == current_user.id:
        who = "shop"
    elif booking.user_id == current_user.id:
        who = "customer"
    else:
        who = "admin"

    fee, refundable = _apply_cancellation(db, booking, who)
    _notify_cancellation(db, booking, shop, who, fee, refundable)

    db.commit()

    if fee > 0:
        return Message(
            message=(
                f"ยกเลิกการจองแล้ว · หักค่ามัดจำ ฿{fee:,.2f} ตามนโยบายยกเลิก"
                + (f" · ร้านจะคืนส่วนที่เหลือ ฿{refundable:,.2f}" if refundable > 0 else "")
            )
        )
    if refundable > 0:
        return Message(message=f"ยกเลิกการจองแล้ว · ร้านจะคืนเงิน ฿{refundable:,.2f} เต็มจำนวน")
    return Message(message="ยกเลิกการจองสำเร็จ")


# ---------------- รีวิว ----------------
@router.get(
    "/shops/{shop_id}/reviews",
    response_model=Page[ReviewOut],
    summary="ดูรีวิวของร้าน (กรองและเรียงลำดับได้)",
)
def list_reviews(
    shop_id: int = Path(..., ge=1),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    staff_id: int | None = Query(None, ge=1, description="ดูเฉพาะรีวิวที่ถึงช่างคนนี้"),
    min_rating: int | None = Query(None, ge=1, le=5, description="คะแนนขั้นต่ำ"),
    with_comment: bool = Query(False, description="เอาเฉพาะรีวิวที่มีข้อความ"),
    sort: str = Query("newest", pattern="^(newest|highest|lowest)$", description="การเรียงลำดับ"),
    db: Session = Depends(get_db),
):
    """ลูกค้ากรองได้ว่าอยากอ่านรีวิวของช่างคนไหน หรือดูเฉพาะรีวิวที่คะแนนต่ำเพื่อดูข้อเสีย"""
    if db.get(Shop, shop_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ไม่พบร้านนี้")

    stmt = select(Review).where(Review.shop_id == shop_id)
    if staff_id is not None:
        stmt = stmt.where(Review.staff_id == staff_id)
    if min_rating is not None:
        stmt = stmt.where(Review.rating >= min_rating)
    if with_comment:
        stmt = stmt.where(Review.comment.isnot(None), Review.comment != "")

    order = {
        "newest": Review.created_at.desc(),
        "highest": Review.rating.desc(),
        "lowest": Review.rating.asc(),
    }[sort]

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(
        stmt.order_by(order, Review.id.desc()).offset((page - 1) * limit).limit(limit)
    ).all()

    return Page[ReviewOut](
        items=_with_names(db, list(rows)),
        page=page,
        limit=limit,
        total=total,
        total_pages=(total + limit - 1) // limit,
    )


@router.get(
    "/shops/{shop_id}/review-summary",
    response_model=ReviewSummary,
    summary="สรุปคะแนนรีวิวของร้าน",
)
def review_summary(shop_id: int = Path(..., ge=1), db: Session = Depends(get_db)):
    """คืนการกระจายของดาว คะแนนเฉลี่ยแยกหัวข้อ และสัดส่วนที่ร้านตอบกลับ

    ใช้วาดแถบสรุปด้านบนรายการรีวิว ให้ลูกค้าเห็นภาพรวมก่อนไล่อ่านทีละรีวิว
    """
    if db.get(Shop, shop_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ไม่พบร้านนี้")

    rows = db.scalars(select(Review).where(Review.shop_id == shop_id)).all()
    total = len(rows)

    distribution = {star: 0 for star in range(1, 6)}
    for r in rows:
        distribution[r.rating] = distribution.get(r.rating, 0) + 1

    def mean(values: list[int]) -> float | None:
        return round(sum(values) / len(values), 2) if values else None

    aspects = AspectAverages(
        staff=mean([r.staff_rating for r in rows if r.staff_rating]),
        cleanliness=mean([r.rating_cleanliness for r in rows if r.rating_cleanliness]),
        punctuality=mean([r.rating_punctuality for r in rows if r.rating_punctuality]),
        value=mean([r.rating_value for r in rows if r.rating_value]),
    )

    replied = sum(1 for r in rows if r.reply)

    return ReviewSummary(
        shop_id=shop_id,
        total=total,
        average=round(sum(r.rating for r in rows) / total, 2) if total else 0.0,
        distribution=distribution,
        aspects=aspects,
        reply_rate=round(replied / total, 2) if total else 0.0,
    )


@router.post(
    "/reviews",
    response_model=ReviewOut,
    status_code=status.HTTP_201_CREATED,
    summary="เขียนรีวิว",
)
def create_review(
    payload: ReviewCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """รีวิวได้เฉพาะการจองของตัวเองที่ใช้บริการเสร็จแล้ว และรีวิวได้ครั้งเดียวต่อการจอง"""
    booking = _get_booking_or_404(db, payload.booking_id)

    if booking.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="คุณรีวิวได้เฉพาะการจองของตัวเอง"
        )
    if booking.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="รีวิวได้เฉพาะการจองที่ใช้บริการเสร็จแล้ว",
        )

    existing = db.scalar(select(Review).where(Review.booking_id == booking.id))
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="การจองนี้ถูกรีวิวไปแล้ว")

    # ให้ดาวช่างได้เฉพาะกรณีที่การจองระบุช่างไว้จริง
    if payload.staff_rating is not None and booking.staff_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="การจองนี้ไม่ได้ระบุช่าง จึงให้คะแนนช่างไม่ได้",
        )

    review = Review(
        booking_id=booking.id,
        user_id=current_user.id,
        shop_id=booking.shop_id,
        service_id=booking.service_id,
        staff_id=booking.staff_id,
        rating=payload.rating,
        staff_rating=payload.staff_rating,
        rating_cleanliness=payload.rating_cleanliness,
        rating_punctuality=payload.rating_punctuality,
        rating_value=payload.rating_value,
        comment=payload.comment,
    )
    db.add(review)
    db.flush()

    _recalc_shop_rating(db, booking.shop_id)
    if booking.staff_id is not None:
        _recalc_staff_rating(db, booking.staff_id)

    db.commit()
    db.refresh(review)
    return review


@router.post(
    "/reviews/{review_id}/reply",
    response_model=ReviewOut,
    summary="เจ้าของร้านตอบกลับรีวิว",
)
def reply_review(
    payload: ReviewReply,
    review_id: int = Path(..., ge=1),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """ตอบกลับได้เฉพาะเจ้าของร้านนั้นหรือผู้ดูแลระบบ · แก้ไขคำตอบเดิมได้"""
    review = db.get(Review, review_id)
    if review is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ไม่พบรีวิวนี้")

    shop = db.get(Shop, review.shop_id)
    allowed = current_user.role == "admin" or (shop is not None and shop.owner_id == current_user.id)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="ตอบกลับได้เฉพาะเจ้าของร้านนี้เท่านั้น"
        )

    review.reply = payload.reply
    review.replied_at = datetime.now(timezone.utc)

    if review.user_id != current_user.id:
        notify(
            db, review.user_id, "review_reply",
            f"{shop.name if shop else 'ร้าน'} ตอบกลับรีวิวของคุณแล้ว",
            payload.reply[:180], f"shop.html?id={review.shop_id}",
        )

    db.commit()
    db.refresh(review)
    return review


@router.delete(
    "/reviews/{review_id}/reply",
    response_model=Message,
    summary="ลบคำตอบกลับของร้าน",
)
def delete_reply(
    review_id: int = Path(..., ge=1),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    review = db.get(Review, review_id)
    if review is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ไม่พบรีวิวนี้")

    shop = db.get(Shop, review.shop_id)
    allowed = current_user.role == "admin" or (shop is not None and shop.owner_id == current_user.id)
    if not allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="คุณไม่มีสิทธิ์ลบคำตอบนี้")

    review.reply = None
    review.replied_at = None
    db.commit()
    return Message(message="ลบคำตอบกลับแล้ว")


@router.delete(
    "/reviews/{review_id}",
    response_model=Message,
    summary="ลบรีวิวของตัวเอง",
    description=(
        "เจ้าของรีวิวลบรีวิวตัวเองได้ และผู้ดูแลระบบลบรีวิวที่ไม่เหมาะสมได้\n\n"
        "**เจ้าของร้านลบไม่ได้** — ถ้าให้ร้านลบรีวิวที่ตัวเองไม่ชอบ "
        "คะแนนในระบบจะเหลือแต่รีวิวดี ซึ่งทำให้ระบบรีวิวไม่มีความหมาย "
        "ร้านตอบกลับรีวิวได้แทน (ดู `POST /api/reviews/{id}/reply`)\n\n"
        "ลบแล้วคะแนนของร้านและของผู้ให้บริการจะถูกคำนวณใหม่ทันที "
        "และการจองนั้นจะกลับมาเขียนรีวิวได้อีกครั้ง"
    ),
)
def delete_review(
    review_id: int = Path(..., ge=1),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    review = db.get(Review, review_id)
    if review is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ไม่พบรีวิวนี้")

    if not (review.user_id == current_user.id or current_user.role == "admin"):
        # แยกข้อความให้เจ้าของร้านเข้าใจว่าทำไมถึงลบไม่ได้ ไม่ใช่แค่บอกว่าไม่มีสิทธิ์
        shop = db.get(Shop, review.shop_id)
        if shop is not None and shop.owner_id == current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="เจ้าของร้านลบรีวิวไม่ได้ แต่ตอบกลับรีวิวเพื่อชี้แจงได้",
            )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="คุณลบได้เฉพาะรีวิวของตัวเอง"
        )

    # จำไว้ก่อนลบ เพราะหลัง commit อ็อบเจ็กต์จะอ่านค่าไม่ได้แล้ว
    shop_id, staff_id = review.shop_id, review.staff_id

    db.delete(review)
    db.flush()

    # คะแนนเป็นค่าที่คำนวณไว้ล่วงหน้าในตาราง ต้องคิดใหม่เองหลังลบ
    # ถ้าไม่ทำ ร้านจะยังโชว์คะแนนเดิมทั้งที่รีวิวหายไปแล้ว
    _recalc_shop_rating(db, shop_id)
    if staff_id:
        _recalc_staff_rating(db, staff_id)

    db.commit()
    return Message(message="ลบรีวิวเรียบร้อยแล้ว")
