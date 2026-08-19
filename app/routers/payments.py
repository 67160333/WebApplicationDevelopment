"""8) Payments — มัดจำ การชำระเงิน และใบเสร็จ

**ระบบนี้เป็นการจำลอง** ไม่ได้เชื่อมต่อกับธนาคารหรือผู้ให้บริการชำระเงินจริง
ออกแบบให้โครงสร้างข้อมูลเหมือนของจริง เพื่อให้ต่อกับ payment gateway จริงได้
โดยแก้แค่ฟังก์ชัน `_mock_charge` จุดเดียว
"""

import secrets
from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal

from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Booking, Payment, Service, Shop, User
from app.schemas import (
    Message,
    PaymentCreate,
    PaymentOut,
    PaymentSummary,
    ReceiptOut,
)
from app.routers.notifications import notify
from app.security import get_current_user

router = APIRouter(prefix="/api", tags=["8. Payments"])

# สถานะที่ยังจ่ายเงินได้ — ยกเลิกไปแล้วห้ามจ่าย
PAYABLE_STATUSES = ("pending", "confirmed", "completed")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _money(value: Decimal) -> Decimal:
    return Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _mock_charge(method: str) -> str:
    """จำลองการตัดเงิน แล้วคืนเลขอ้างอิงจากผู้ให้บริการ

    ของจริงตรงนี้จะเป็นการเรียก API ของ payment gateway
    (เช่น Omise, 2C2P, GBPrimePay) แล้วรอผลตอบกลับ
    """
    prefix = {"promptpay": "PP", "card": "CD", "cash": "CS"}[method]
    return f"{prefix}{secrets.token_hex(6).upper()}"


def _receipt_no(payment_id: int, when: datetime) -> str:
    """เลขที่ใบเสร็จ RC-YYMM-00042

    ใช้ id ของแถวเป็นตัวเลขท้าย จึงไม่ซ้ำแน่นอนโดยไม่ต้องล็อกตาราง
    (ถ้านับจำนวนแถวแล้ว +1 สองคำขอพร้อมกันจะได้เลขเดียวกัน)
    """
    return f"RC-{when.strftime('%y%m')}-{payment_id:05d}"


def _get_booking(db: Session, booking_id: int) -> Booking:
    booking = db.get(Booking, booking_id)
    if booking is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ไม่พบการจองนี้")
    return booking


def _shop_owner_id(db: Session, booking: Booking) -> int | None:
    shop = db.get(Shop, booking.shop_id)
    return shop.owner_id if shop else None


def _can_view(db: Session, booking: Booking, user: User) -> bool:
    """เจ้าของคิว เจ้าของร้าน และแอดมิน ดูข้อมูลการชำระเงินได้"""
    if user.role == "admin" or booking.user_id == user.id:
        return True
    return _shop_owner_id(db, booking) == user.id


def _paid_rows(db: Session, booking_id: int) -> list[Payment]:
    return list(
        db.scalars(
            select(Payment)
            .where(Payment.booking_id == booking_id, Payment.status == "paid")
            .order_by(Payment.id)
        ).all()
    )


def _summarise(db: Session, booking: Booking) -> PaymentSummary:
    rows = _paid_rows(db, booking.id)
    paid = _money(sum((r.amount for r in rows), Decimal("0")))
    total = _money(booking.total_price)
    deposit = _money(booking.deposit_amount)
    kinds = {r.kind for r in rows}

    # ตัดสินจาก "ยอดเงินที่จ่ายมาแล้วจริง" ไม่ใช่จาก "มีรายการมัดจำอยู่ไหม"
    #
    # ของเดิมดูจาก kinds ทำให้พอร้านคืนเฉพาะมัดจำ (แต่ยอดคงเหลือยังจ่ายอยู่)
    # สถานะกระโดดกลับไปเป็น unpaid ทั้งที่ลูกค้าจ่ายมาแล้วเกือบเต็มจำนวน
    # แล้วพอลูกค้ากดจ่ายยอดที่ระบบบอกว่าค้าง ก็จะโดนปฏิเสธเพราะติด index เดิม
    if total > 0 and paid >= total:
        state = "paid"          # จ่ายครบแล้ว
    elif paid > 0:
        state = "deposit_paid"  # จ่ายมาบางส่วนแล้ว เหลือส่วนที่เหลือจ่ายหน้าร้าน
    else:
        state = "unpaid"        # ยังไม่ได้จ่ายอะไรเลย

    return PaymentSummary(
        booking_id=booking.id,
        booking_code=booking.booking_code,
        total_price=total,
        deposit_amount=deposit,
        paid_amount=paid,
        outstanding=_money(max(total - paid, Decimal("0"))),
        state=state,
        payments=[PaymentOut.model_validate(r) for r in rows],
    )


# ============================================================
# ดูสถานะการชำระเงิน
# ============================================================
@router.get(
    "/bookings/{booking_id}/payment",
    response_model=PaymentSummary,
    summary="ดูสถานะการชำระเงินของคิวนี้",
)
def get_payment_status(
    booking_id: int = Path(..., ge=1),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    booking = _get_booking(db, booking_id)
    if not _can_view(db, booking, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="คุณไม่มีสิทธิ์ดูข้อมูลการชำระเงินนี้"
        )
    return _summarise(db, booking)


# ============================================================
# ชำระเงิน
# ============================================================
@router.post(
    "/bookings/{booking_id}/payment",
    response_model=PaymentSummary,
    status_code=status.HTTP_201_CREATED,
    summary="ชำระมัดจำหรือยอดคงเหลือ",
    description=(
        "**เป็นการชำระเงินจำลอง** ระบบไม่ได้ตัดเงินจริง\n\n"
        "- `kind=deposit` ชำระมัดจำ 20% ของค่าบริการ\n"
        "- `kind=balance` ชำระส่วนที่เหลือ\n\n"
        "ลูกค้าชำระเองได้ด้วย `promptpay` หรือ `card` "
        "ส่วน `cash` (เงินสด) ใช้ได้เฉพาะเจ้าของร้านที่กดรับเงินหน้าร้าน"
    ),
)
def pay_booking(
    payload: PaymentCreate,
    booking_id: int = Path(..., ge=1),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    booking = _get_booking(db, booking_id)
    owner_id = _shop_owner_id(db, booking)
    is_owner = owner_id == current_user.id or current_user.role == "admin"
    is_customer = booking.user_id == current_user.id

    if not (is_owner or is_customer):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="คุณไม่มีสิทธิ์ชำระเงินให้คิวนี้"
        )

    # รับเงินสดได้เฉพาะที่ร้าน — ลูกค้ากดเองจากบ้านไม่ได้
    if payload.method == "cash" and not is_owner:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="การชำระด้วยเงินสดต้องให้ทางร้านเป็นผู้บันทึกที่หน้าร้าน",
        )

    if booking.status == "cancelled":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="คิวนี้ถูกยกเลิกไปแล้ว ไม่สามารถชำระเงินได้",
        )
    if booking.status not in PAYABLE_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="สถานะของคิวนี้ยังชำระเงินไม่ได้"
        )

    summary = _summarise(db, booking)

    if payload.kind == "deposit":
        amount = _money(booking.deposit_amount)
        if amount <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="คิวนี้ไม่ต้องชำระมัดจำ"
            )
        if summary.state != "unpaid":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="ชำระมัดจำของคิวนี้ไปแล้ว"
            )
    else:
        amount = summary.outstanding
        if amount <= 0:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="คิวนี้ชำระครบแล้ว ไม่มียอดค้าง"
            )

    payment = Payment(
        booking_id=booking.id,
        kind=payload.kind,
        amount=amount,
        method=payload.method,
        status="paid",
        reference=_mock_charge(payload.method),
        paid_at=_now(),
    )
    db.add(payment)

    try:
        # flush เพื่อให้ได้ id มาสร้างเลขที่ใบเสร็จ ก่อนจะ commit จริง
        db.flush()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="มีการชำระเงินรายการนี้อยู่แล้ว กรุณารีเฟรชหน้าจอ",
        )

    payment.receipt_no = _receipt_no(payment.id, payment.paid_at)

    # ยืนยันคิวให้อัตโนมัติเมื่อจ่ายมัดจำแล้ว — ลูกค้าจ่ายเงินแล้วไม่ควรต้องรอร้านกดอีกที
    if payload.kind == "deposit" and booking.status == "pending":
        booking.status = "confirmed"
        notify(
            db, booking.user_id, "booking_confirmed",
            "ยืนยันคิวเรียบร้อย",
            f"ได้รับมัดจำ ฿{amount:,.0f} แล้ว · {booking.booking_code}",
        )

    if owner_id is not None and not is_owner:
        service = db.get(Service, booking.service_id)
        notify(
            db, owner_id, "payment_received",
            f"ได้รับเงิน ฿{amount:,.0f}",
            f"{service.name if service else 'บริการ'} · {booking.booking_code}",
            "manage.html",
        )

    db.commit()
    db.refresh(booking)
    return _summarise(db, booking)


# ============================================================
# คืนเงิน
# ============================================================
@router.post(
    "/payments/{payment_id}/refund",
    response_model=Message,
    summary="คืนเงิน (เจ้าของร้าน)",
)
def refund_payment(
    payment_id: int = Path(..., ge=1),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    payment = db.get(Payment, payment_id)
    if payment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ไม่พบรายการชำระเงินนี้")

    booking = _get_booking(db, payment.booking_id)
    if _shop_owner_id(db, booking) != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="เฉพาะเจ้าของร้านเท่านั้นที่คืนเงินได้"
        )
    if payment.status == "refunded":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="รายการนี้คืนเงินไปแล้ว"
        )

    payment.status = "refunded"
    payment.refunded_at = _now()

    notify(
        db, booking.user_id, "payment_refunded",
        f"ร้านคืนเงิน ฿{payment.amount:,.0f} แล้ว",
        f"{booking.booking_code} · เงินจะเข้าบัญชีภายใน 3–5 วันทำการ",
    )
    db.commit()
    return Message(message=f"คืนเงิน ฿{payment.amount:,.2f} เรียบร้อย")


# ============================================================
# ใบเสร็จ
# ============================================================
@router.get(
    "/payments/{payment_id}/receipt",
    response_model=ReceiptOut,
    summary="ดึงข้อมูลใบเสร็จ",
)
def get_receipt(
    payment_id: int = Path(..., ge=1),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    payment = db.get(Payment, payment_id)
    if payment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ไม่พบรายการชำระเงินนี้")

    booking = _get_booking(db, payment.booking_id)
    if not _can_view(db, booking, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="คุณไม่มีสิทธิ์ดูใบเสร็จนี้"
        )

    shop = db.get(Shop, booking.shop_id)
    service = db.get(Service, booking.service_id)
    buyer = db.get(User, booking.user_id)

    return ReceiptOut(
        receipt_no=payment.receipt_no or f"RC-{payment.id:05d}",
        issued_at=payment.paid_at,
        status=payment.status,
        kind=payment.kind,
        method=payment.method,
        reference=payment.reference,
        amount=_money(payment.amount),
        shop_name=shop.name if shop else "—",
        shop_address=", ".join(x for x in [shop.address, shop.district, shop.province] if x)
        if shop
        else None,
        shop_phone=shop.phone if shop else None,
        # ลูกค้า walk-in ไม่มีบัญชี ใช้ชื่อที่ร้านกรอกไว้แทน
        customer_name=booking.guest_name or (buyer.full_name if buyer else "ลูกค้า"),
        booking_code=booking.booking_code,
        booking_date=booking.booking_date,
        booking_time=booking.booking_time,
        service_name=service.name if service else "บริการ",
        total_price=_money(booking.total_price),
    )


# ============================================================
# รายรับของร้าน
# ============================================================
@router.get(
    "/shops/{shop_id}/revenue",
    response_model=dict,
    summary="สรุปรายรับที่รับชำระจริง (เจ้าของร้าน)",
)
def shop_revenue(
    shop_id: int = Path(..., ge=1),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    shop = db.get(Shop, shop_id)
    if shop is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ไม่พบร้านนี้")
    if shop.owner_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="คุณไม่ใช่เจ้าของร้านนี้"
        )

    def _total(payment_status: str) -> Decimal:
        return db.scalar(
            select(func.coalesce(func.sum(Payment.amount), 0))
            .join(Booking, Payment.booking_id == Booking.id)
            .where(Booking.shop_id == shop_id, Payment.status == payment_status)
        ) or Decimal("0")

    # _total("paid") นับเฉพาะรายการที่ยังไม่ถูกคืน — รายการที่คืนไปแล้ว
    # เปลี่ยน status เป็น refunded จึงหลุดออกจากยอดนี้ไปเรียบร้อยแล้ว
    # ของเดิมเอา refunded มาลบซ้ำอีกรอบ ยอดสุทธิเลยต่ำกว่าความจริงและติดลบได้
    kept = _total("paid")            # เงินที่ยังอยู่กับร้านจริง
    refunded = _total("refunded")

    by_method = db.execute(
        select(Payment.method, func.count(Payment.id), func.coalesce(func.sum(Payment.amount), 0))
        .join(Booking, Payment.booking_id == Booking.id)
        .where(Booking.shop_id == shop_id, Payment.status == "paid")
        .group_by(Payment.method)
    ).all()

    return {
        "received": float(kept + refunded),   # รับเข้ามาทั้งหมดก่อนหักคืน
        "refunded": float(refunded),
        "net": float(kept),                   # หักคืนแล้วครั้งเดียวพอ
        "by_method": [
            {"method": m, "count": int(c), "amount": float(a)} for m, c, a in by_method
        ],
    }
