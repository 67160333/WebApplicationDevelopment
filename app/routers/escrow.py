"""9) Escrow — ระบบพักเงินแบบ Shopee (จำลอง ไม่ได้ตัดหรือโอนเงินจริง)

ปัญหาที่แก้
------------------------------------------------------------------
เดิมเงินที่ลูกค้าจ่ายถือว่าเป็นของร้านทันที ถ้าร้านไม่ให้บริการ ปิดร้านหนี
หรือให้บริการแย่ ลูกค้าต้องไปตามทวงเงินคืนกับร้านเอง ระบบช่วยอะไรไม่ได้

ระบบพักเงินกลับด้าน: เงินอยู่ที่เว็บก่อน ร้านจะได้ก็ต่อเมื่อทำงานเสร็จจริง

ลำดับของเงินหนึ่งก้อน
------------------------------------------------------------------
    ลูกค้าจ่าย ──► พักไว้ที่ระบบ (held)
                     │
                     ├─ ร้านกด "ให้บริการเสร็จ" (ได้หลังถึงเวลานัดเท่านั้น)
                     │     ├─ ลูกค้ากด "ได้รับบริการแล้ว" ──► ปล่อยให้ร้านทันที
                     │     ├─ ลูกค้าไม่กดอะไรภายใน 24 ชม. ──► ปล่อยให้ร้านอัตโนมัติ
                     │     └─ ลูกค้ากด "แจ้งปัญหา" ภายใน 24 ชม. ──► รอผู้ดูแลตัดสิน
                     │                                    ├─ ให้ร้าน  ──► ปล่อย
                     │                                    └─ ให้ลูกค้า ──► คืนเงิน
                     │
                     └─ ยกเลิกก่อนถึงเวลานัด (ดู _apply_cancellation ใน bookings.py)
                           ├─ ร้านยกเลิก  ──► คืนลูกค้าเต็มจำนวนอัตโนมัติ
                           └─ ลูกค้ายกเลิก ──► มัดจำปล่อยให้ร้าน ส่วนอื่นคืนลูกค้า

    ปล่อยแล้ว (released) ──► ร้านกด "โอนเข้าบัญชี" ──► หักค่าธรรมเนียมเว็บ 5% แล้วโอน

ข้อมูลอยู่ที่ไหน
------------------------------------------------------------------
ไม่มีตารางสถานะเงินแยก สถานะของเงินแต่ละก้อนดูจากตาราง payments ตรง ๆ
    status=paid, released_at ว่าง   = พักอยู่
    status=paid, released_at มีค่า  = ปล่อยแล้ว (payout_id ว่าง = ยังไม่โอน)
    status=refunded                 = คืนแล้ว
เงินสดที่ร้านรับเองหน้าร้านถูกปล่อยทันทีตอนบันทึก เพราะอยู่ในมือร้านตั้งแต่แรก
และไม่ถูกนับในยอดโอน (เว็บไม่เคยถือเงินก้อนนั้น)

ทำไมไม่มีงานตั้งเวลาคอยปล่อยเงิน
------------------------------------------------------------------
โฮสต์ฟรีไม่มีระบบรันงานเบื้องหลัง และเครื่องหลับเมื่อไม่มีคนเข้า
จึงใช้วิธี "ตรวจตอนมีคนเปิดดู" แทน — release_due() ถูกเรียกทุกครั้งที่มีคน
เปิดรายการจองหรือกระเป๋าเงินร้าน ผลลัพธ์ที่ผู้ใช้เห็นจึงตรงเสมอ
เพราะไม่มีใครเห็นตัวเลขได้โดยไม่ผ่านจุดที่ตรวจแล้ว

ตรวจเฉพาะคิวที่กำลังเปิดดู ไม่ใช่ทั้งตาราง
------------------------------------------------------------------
รุ่นแรกตรวจทุกคิวในระบบทุกครั้ง วัดใน indexing-lab ที่ข้อมูล 1 ล้านคิวได้ 63-94 ms
ต่อการเปิดหน้าหนึ่งครั้ง และ index ช่วยได้ไม่มาก เพราะคิวที่เสร็จแล้วมีราว 70% ของตาราง
แก้ที่ตัว query แทน: ตรวจแค่คิวในหน้าที่เปิดอยู่ (booking_ids) หรือร้านเดียว (shop_id)
ซึ่งใช้ index ได้เต็มที่ ผลที่ผู้ใช้เห็นเหมือนเดิมทุกอย่าง เพราะคิวที่ไม่ได้เปิดดูก็ไม่มีใครเห็น

ถ้าจะใช้เงินจริง
------------------------------------------------------------------
ต้องใช้ payment gateway ที่ได้รับอนุญาต (เช่น Opn Payments) ให้ถือเงินแทน
แล้วสั่งโอนผ่าน Transfers API ตอน create_payout และต้องปรึกษาเรื่องใบอนุญาต
"รับชำระเงินแทน" ตาม พ.ร.บ.ระบบการชำระเงิน 2560 กับ ธปท. ก่อน
"""

import secrets
from datetime import datetime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal

from fastapi import APIRouter, Depends, HTTPException, Path, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Booking, Payment, Payout, Service, Shop, User
from app.routers.notifications import notify
from app.schemas import (
    BankAccountIn,
    BookingOut,
    DisputeCreate,
    DisputeOut,
    DisputeResolve,
    Message,
    PayoutOut,
    UpcomingRelease,
    WalletOut,
)
from app.security import get_current_user, require_roles

router = APIRouter(prefix="/api", tags=["9. Escrow (พักเงิน)"])

# ลูกค้ามีเวลากี่ชั่วโมงหลังร้านปิดงาน ก่อนเงินจะถูกปล่อยให้ร้านเอง
AUTO_RELEASE_HOURS = 24
# ค่าธรรมเนียมที่เว็บหักก่อนโอนให้ร้าน
PLATFORM_FEE_RATE = Decimal("0.05")


# ============================================================
# ตัวช่วยเรื่องเงิน — bookings.py และ payments.py เรียกใช้ด้วย
# ============================================================
def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _aware(dt: datetime | None) -> datetime | None:
    """SQLite (ชุดทดสอบ) คืนเวลาแบบไม่มี timezone ส่วน PostgreSQL คืนแบบมี
    เติม UTC ให้ก่อนเสมอ ไม่งั้นเอามาเทียบกันแล้ว Python โยน TypeError"""
    if dt is not None and dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def money(value) -> Decimal:
    return Decimal(value or 0).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def held_rows(db: Session, booking_id: int) -> list[Payment]:
    """เงินของคิวนี้ที่ยังพักอยู่ที่ระบบ"""
    return list(db.scalars(
        select(Payment).where(
            Payment.booking_id == booking_id,
            Payment.status == "paid",
            Payment.released_at.is_(None),
        )
    ).all())


def release_rows(rows: list[Payment]) -> Decimal:
    """ปล่อยเงินให้ร้าน คืนยอดรวมที่ปล่อย"""
    now = utcnow()
    total = Decimal("0")
    for row in rows:
        if row.status == "paid" and row.released_at is None:
            row.released_at = now
            total += Decimal(row.amount)
    return money(total)


def refund_rows(rows: list[Payment]) -> Decimal:
    """คืนเงินลูกค้า คืนยอดรวมที่คืน"""
    now = utcnow()
    total = Decimal("0")
    for row in rows:
        if row.status == "paid":
            row.status = "refunded"
            row.refunded_at = now
            total += Decimal(row.amount)
    return money(total)


def auto_release_at(booking: Booking) -> datetime | None:
    done = _aware(booking.service_done_at)
    return done + timedelta(hours=AUTO_RELEASE_HOURS) if done else None


def _dispute_open(booking: Booking) -> bool:
    return booking.disputed_at is not None and booking.dispute_result is None


def release_due(
    db: Session,
    *,
    shop_id: int | None = None,
    booking_ids: list[int] | None = None,
) -> int:
    """ปล่อยเงินของงานที่ปิดครบ 24 ชั่วโมงแล้วและไม่มีใครแจ้งปัญหา

    ต้องระบุขอบเขตเสมอ — คิวชุดที่กำลังเปิดดู (booking_ids) หรือร้านเดียว (shop_id)
    ดูเหตุผลที่หัวไฟล์ หัวข้อ "ตรวจเฉพาะคิวที่กำลังเปิดดู"

    คืนจำนวนคิวที่ถูกปล่อยในรอบนี้ เรียกซ้ำกี่ครั้งก็ได้ ไม่ปล่อยซ้ำ
    """
    if shop_id is None and not booking_ids:
        return 0

    stmt = select(Booking).where(
        Booking.status == "completed",
        Booking.service_done_at.isnot(None),
        # ใช้ partial index ix_payments_held — เก็บเฉพาะเงินที่ยังพักอยู่ จึงเล็กมาก
        Booking.id.in_(
            select(Payment.booking_id).where(
                Payment.status == "paid", Payment.released_at.is_(None)
            )
        ),
    )
    if shop_id is not None:
        stmt = stmt.where(Booking.shop_id == shop_id)      # ix_bookings_shop_date
    if booking_ids:
        stmt = stmt.where(Booking.id.in_(booking_ids))     # primary key
    candidates = db.scalars(stmt).all()

    now = utcnow()
    released = 0
    for booking in candidates:
        due = auto_release_at(booking)
        if _dispute_open(booking) or due is None or due > now:
            continue
        amount = release_rows(held_rows(db, booking.id))
        if amount > 0:
            released += 1
            shop = db.get(Shop, booking.shop_id)
            if shop is not None:
                notify(
                    db, shop.owner_id, "escrow_released",
                    f"เงิน ฿{amount:,.0f} เข้ากระเป๋าร้านแล้ว",
                    f"{booking.booking_code} · ครบ {AUTO_RELEASE_HOURS} ชั่วโมงหลังปิดงาน",
                    "manage.html",
                )
    if released:
        db.commit()
    return released


def _booking_or_404(db: Session, booking_id: int) -> Booking:
    booking = db.get(Booking, booking_id)
    if booking is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ไม่พบการจองนี้")
    return booking


def _booking_out(db: Session, booking: Booking) -> BookingOut:
    from app.routers.bookings import _with_payment   # นำเข้าในฟังก์ชันเพื่อเลี่ยง import วนกัน

    return _with_payment(db, [booking])[0]


# ============================================================
# ฝั่งลูกค้า
# ============================================================
@router.post(
    "/bookings/{booking_id}/confirm-service",
    response_model=BookingOut,
    summary="ลูกค้ายืนยันว่าได้รับบริการแล้ว (ปล่อยเงินให้ร้านทันที)",
)
def confirm_service(
    booking_id: int = Path(..., ge=1),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    booking = _booking_or_404(db, booking_id)
    if booking.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="ยืนยันได้เฉพาะเจ้าของคิว")
    if booking.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="ร้านยังไม่ได้กดให้บริการเสร็จ จึงยังยืนยันไม่ได้",
        )
    if _dispute_open(booking):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="คิวนี้แจ้งปัญหาไว้แล้ว รอผู้ดูแลตัดสินก่อน",
        )

    booking.customer_confirmed_at = utcnow()
    amount = release_rows(held_rows(db, booking.id))

    shop = db.get(Shop, booking.shop_id)
    if shop is not None and amount > 0:
        notify(
            db, shop.owner_id, "escrow_released",
            f"ลูกค้ายืนยันแล้ว เงิน ฿{amount:,.0f} เข้ากระเป๋าร้าน",
            booking.booking_code, "manage.html",
        )
    db.commit()
    db.refresh(booking)
    return _booking_out(db, booking)


@router.post(
    "/bookings/{booking_id}/dispute",
    response_model=BookingOut,
    summary="ลูกค้าแจ้งปัญหา (พักเงินไว้จนผู้ดูแลตัดสิน)",
)
def open_dispute(
    payload: DisputeCreate,
    booking_id: int = Path(..., ge=1),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    booking = _booking_or_404(db, booking_id)
    if booking.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="แจ้งปัญหาได้เฉพาะเจ้าของคิว")
    if booking.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="แจ้งปัญหาได้หลังร้านกดให้บริการเสร็จ ถ้ายังไม่ได้รับบริการให้ยกเลิกคิวแทน",
        )
    if booking.disputed_at is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="คิวนี้แจ้งปัญหาไปแล้ว")

    # ต้องยังมีเงินพักอยู่ — ปล่อยให้ร้านไปแล้วระบบไม่มีเงินให้คืน
    held = held_rows(db, booking.id)
    due = auto_release_at(booking)
    if not held or (due is not None and due <= utcnow()):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"เลย {AUTO_RELEASE_HOURS} ชั่วโมงหลังปิดงานแล้ว หรือเงินถูกปล่อยให้ร้านไปแล้ว "
                "กรุณาติดต่อร้านโดยตรง"
            ),
        )

    booking.disputed_at = utcnow()
    booking.dispute_note = payload.note.strip()

    amount = money(sum((Decimal(r.amount) for r in held), Decimal("0")))
    shop = db.get(Shop, booking.shop_id)
    if shop is not None:
        notify(
            db, shop.owner_id, "escrow_disputed",
            f"ลูกค้าแจ้งปัญหา · พักเงิน ฿{amount:,.0f} ไว้ก่อน",
            f"{booking.booking_code} · {booking.dispute_note[:80]}", "manage.html",
        )
    for admin_id in db.scalars(select(User.id).where(User.role == "admin")).all():
        notify(
            db, admin_id, "escrow_disputed", "มีเรื่องแจ้งปัญหารอตัดสิน",
            f"{booking.booking_code} · ฿{amount:,.0f}", "admin.html",
        )
    db.commit()
    db.refresh(booking)
    return _booking_out(db, booking)


# ============================================================
# ฝั่งผู้ดูแล
# ============================================================
@router.get(
    "/admin/disputes",
    response_model=list[DisputeOut],
    summary="เรื่องแจ้งปัญหาที่ยังไม่ตัดสิน (admin)",
)
def list_disputes(
    _admin: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    rows = db.scalars(
        select(Booking)
        .where(Booking.disputed_at.isnot(None), Booking.dispute_result.is_(None))
        .order_by(Booking.disputed_at)
    ).all()

    out: list[DisputeOut] = []
    for b in rows:
        shop = db.get(Shop, b.shop_id)
        service = db.get(Service, b.service_id)
        customer = db.get(User, b.user_id)
        held = money(sum((Decimal(r.amount) for r in held_rows(db, b.id)), Decimal("0")))
        out.append(DisputeOut(
            booking_id=b.id,
            booking_code=b.booking_code,
            shop_id=b.shop_id,
            shop_name=shop.name if shop else "-",
            customer_name=b.guest_name or (customer.full_name if customer else "-"),
            service_name=service.name if service else "-",
            booking_date=b.booking_date,
            held_amount=held,
            dispute_note=b.dispute_note,
            disputed_at=b.disputed_at,
        ))
    return out


@router.post(
    "/bookings/{booking_id}/resolve-dispute",
    response_model=BookingOut,
    summary="ตัดสินเรื่องแจ้งปัญหา (admin)",
)
def resolve_dispute(
    payload: DisputeResolve,
    booking_id: int = Path(..., ge=1),
    _admin: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    booking = _booking_or_404(db, booking_id)
    if not _dispute_open(booking):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="คิวนี้ไม่มีเรื่องรอตัดสิน")

    rows = held_rows(db, booking.id)
    if payload.decision == "release":
        amount = release_rows(rows)
        to_shop = f"ผู้ดูแลตัดสินให้ร้าน · เงิน ฿{amount:,.0f} เข้ากระเป๋าร้าน"
        to_customer = "ผู้ดูแลตัดสินเรื่องที่คุณแจ้งแล้ว · ปล่อยเงินให้ร้าน"
    else:
        amount = refund_rows(rows)
        to_shop = f"ผู้ดูแลตัดสินคืนเงินลูกค้า ฿{amount:,.0f}"
        to_customer = f"ผู้ดูแลตัดสินคืนเงินให้คุณ ฿{amount:,.0f}"

    booking.dispute_result = payload.decision
    extra = f" · {payload.reason}" if payload.reason else ""
    shop = db.get(Shop, booking.shop_id)
    if shop is not None:
        notify(db, shop.owner_id, "escrow_resolved", to_shop, booking.booking_code + extra, "manage.html")
    notify(db, booking.user_id, "escrow_resolved", to_customer, booking.booking_code + extra)

    db.commit()
    db.refresh(booking)
    return _booking_out(db, booking)


# ============================================================
# ฝั่งร้าน — กระเป๋าเงิน บัญชีรับเงิน และการโอน
# ============================================================
def _owned_shop(db: Session, shop_id: int, user: User) -> Shop:
    shop = db.get(Shop, shop_id)
    if shop is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ไม่พบร้านนี้")
    if shop.owner_id != user.id and user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="คุณไม่ใช่เจ้าของร้านนี้")
    return shop


def _mask_account(no: str | None) -> str | None:
    """เลขบัญชีแสดงแค่ 4 ตัวท้าย เช่น xxx-x-x1234-x ใช้ทั้งบนหน้าเว็บและในประวัติการโอน"""
    if not no:
        return None
    return "•" * max(len(no) - 4, 0) + no[-4:]


def _payable_rows(db: Session, shop_id: int) -> list[Payment]:
    """เงินที่ปล่อยแล้วและยังไม่ได้โอน — ไม่รวมเงินสด (เว็บไม่เคยถือเงินก้อนนั้น)"""
    return list(db.scalars(
        select(Payment)
        .join(Booking, Booking.id == Payment.booking_id)
        .where(
            Booking.shop_id == shop_id,
            Payment.status == "paid",
            Payment.released_at.isnot(None),
            Payment.payout_id.is_(None),
            Payment.method != "cash",
        )
    ).all())


@router.get("/shops/{shop_id}/wallet", response_model=WalletOut, summary="กระเป๋าเงินของร้าน")
def get_wallet(
    shop_id: int = Path(..., ge=1),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    shop = _owned_shop(db, shop_id, current_user)
    release_due(db, shop_id=shop.id)

    paid_rows = db.scalars(
        select(Payment)
        .join(Booking, Booking.id == Payment.booking_id)
        .where(Booking.shop_id == shop.id, Payment.status == "paid")
    ).all()
    held = sum((Decimal(p.amount) for p in paid_rows if p.released_at is None), Decimal("0"))
    cash = sum((Decimal(p.amount) for p in paid_rows if p.method == "cash"), Decimal("0"))

    gross = money(sum((Decimal(p.amount) for p in _payable_rows(db, shop.id)), Decimal("0")))
    fee = money(gross * PLATFORM_FEE_RATE)

    payouts = db.scalars(
        select(Payout).where(Payout.shop_id == shop.id).order_by(Payout.id.desc())
    ).all()

    # คิวที่ยังมีเงินพักอยู่ บอกร้านว่าเงินจะเข้าเมื่อไหร่
    upcoming: list[UpcomingRelease] = []
    for b in db.scalars(
        select(Booking).where(
            Booking.shop_id == shop.id,
            Booking.id.in_(
                select(Payment.booking_id).where(
                    Payment.status == "paid", Payment.released_at.is_(None)
                )
            ),
        ).order_by(Booking.booking_date, Booking.booking_time)
    ).all():
        amount = money(sum((Decimal(r.amount) for r in held_rows(db, b.id)), Decimal("0")))
        if _dispute_open(b):
            state, when = "disputed", None
        elif b.status == "completed":
            state, when = "waiting_customer", auto_release_at(b)
        else:
            state, when = "not_done", None
        upcoming.append(UpcomingRelease(
            booking_id=b.id, booking_code=b.booking_code, amount=amount,
            release_at=when, state=state,
        ))

    return WalletOut(
        shop_id=shop.id,
        held=money(held),
        available_gross=gross,
        fee_rate=PLATFORM_FEE_RATE,
        available_fee=fee,
        available_net=gross - fee,
        paid_out_total=money(sum((Decimal(p.net) for p in payouts), Decimal("0"))),
        cash_total=money(cash),
        bank_name=shop.bank_name,
        bank_account_no_masked=_mask_account(shop.bank_account_no),
        bank_account_name=shop.bank_account_name,
        upcoming=upcoming[:20],
        payouts=[PayoutOut.model_validate(p) for p in payouts[:10]],
    )


@router.put("/shops/{shop_id}/bank", response_model=Message, summary="ตั้งบัญชีรับเงินของร้าน")
def set_bank_account(
    payload: BankAccountIn,
    shop_id: int = Path(..., ge=1),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    shop = _owned_shop(db, shop_id, current_user)
    shop.bank_name = payload.bank_name.strip()
    shop.bank_account_no = payload.bank_account_no
    shop.bank_account_name = payload.bank_account_name.strip()
    db.commit()
    return Message(message=f"บันทึกบัญชีรับเงินแล้ว ({shop.bank_name} {_mask_account(shop.bank_account_no)})")


@router.post(
    "/shops/{shop_id}/payouts",
    response_model=PayoutOut,
    status_code=status.HTTP_201_CREATED,
    summary="โอนเงินที่ปล่อยแล้วเข้าบัญชีร้าน (จำลอง)",
)
def create_payout(
    shop_id: int = Path(..., ge=1),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    shop = _owned_shop(db, shop_id, current_user)
    if not (shop.bank_name and shop.bank_account_no and shop.bank_account_name):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="กรุณาตั้งบัญชีรับเงินของร้านก่อน"
        )

    release_due(db, shop_id=shop.id)
    rows = _payable_rows(db, shop.id)
    gross = money(sum((Decimal(r.amount) for r in rows), Decimal("0")))
    if gross <= 0:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="ยังไม่มียอดที่พร้อมโอน")

    fee = money(gross * PLATFORM_FEE_RATE)
    payout = Payout(
        shop_id=shop.id,
        gross=gross,
        fee=fee,
        net=gross - fee,
        account_label=f"{shop.bank_name} {_mask_account(shop.bank_account_no)}",
        # ของจริงตรงนี้คือการเรียก Transfers API ของ payment gateway
        reference=f"TR{secrets.token_hex(6).upper()}",
    )
    db.add(payout)
    db.flush()   # ต้องได้ id ก่อนไปผูกกับรายการเงิน
    for row in rows:
        row.payout_id = payout.id

    notify(
        db, shop.owner_id, "payout_done",
        f"โอนเงิน ฿{payout.net:,.2f} เข้าบัญชีร้านแล้ว",
        f"{payout.account_label} · หักค่าธรรมเนียม ฿{fee:,.2f} · {payout.reference}",
        "manage.html",
    )
    db.commit()
    db.refresh(payout)
    return PayoutOut.model_validate(payout)
