"""เฝ้าช่องเวลาที่เต็ม — แจ้งเตือนเมื่อมีคนยกเลิก

ปัญหาที่แก้
--------------------------------------------------------------------------
สนามดังคืนวันศุกร์เต็มตลอด ผู้ใช้เปิดมาเห็นว่าเต็มแล้วก็ปิดเว็บไป
**ทั้งที่ระบบรู้อยู่แล้วว่าเขาอยากได้ช่องไหน**

นี่คือตัวอย่างของแกนคิดหลักของโปรเจกต์ — การจองมี "ก่อน" ที่ไม่มีใครดูแล
คู่แข่งจบที่ "ช่องนี้เต็ม" แล้วปล่อยผู้ใช้ไป ส่วนเราเก็บความต้องการไว้แล้วตามให้

เชื่อมกับกติกาที่มีอยู่แล้วยังไง
--------------------------------------------------------------------------
กติกาค่าปรับยกเลิกทำให้เรารู้ทันทีที่มีคนปล่อยช่องคืน (`_apply_cancellation`)
`notify_slot_free()` ถูกเรียกจากตรงนั้น — **การยกเลิกจึงไม่ใช่แค่การคืนช่อง
แต่เป็นการส่งต่อโอกาสให้คนที่รออยู่จริง**

ทำไมเก็บเป็น "ช่วงเวลา" ไม่ใช่ "จุดเวลา"
--------------------------------------------------------------------------
คนที่อยากเตะบอลคืนวันศุกร์ยอมรับได้ทั้งสามทุ่มและสี่ทุ่ม
ถ้าให้เลือกจุดเดียวจะพลาดโอกาสที่เขาก็โอเคไปเยอะมาก
"""

from datetime import date as date_cls, datetime, time as time_cls, timezone

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Booking, Service, Shop, SlotWatch, Staff, User
from app.schemas import Message, SlotWatchCreate, SlotWatchOut
from app.routers.notifications import notify
from app.security import get_current_user

router = APIRouter(prefix="/api", tags=["12. เฝ้าช่องเวลาที่เต็ม"])

# เฝ้าได้มากสุดกี่รายการต่อคน — กันคนกดเฝ้ารัวจนกลายเป็นสแปมแจ้งเตือน
MAX_ACTIVE_WATCHES = 20


def _to_out(db: Session, row: SlotWatch) -> SlotWatchOut:
    shop = db.get(Shop, row.shop_id)
    service = db.get(Service, row.service_id)
    member = db.get(Staff, row.staff_id) if row.staff_id else None
    out = SlotWatchOut.model_validate(row)
    out.shop_name = shop.name if shop else "—"
    out.service_name = service.name if service else "—"
    out.staff_name = member.name if member else None
    return out


@router.post(
    "/watches",
    response_model=SlotWatchOut,
    status_code=status.HTTP_201_CREATED,
    summary="ขอให้แจ้งเตือนเมื่อช่วงเวลานี้ว่าง",
    description=(
        "ใช้ตอนที่ช่องเวลาที่อยากได้เต็มแล้ว\n\n"
        "เมื่อมีคนยกเลิกคิวที่คาบเกี่ยวกับช่วงที่ระบุ ระบบจะส่งการแจ้งเตือนให้ทันที"
    ),
)
def create_watch(
    payload: SlotWatchCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from app.routers.bookings import _assert_within_window, now_local

    service = db.get(Service, payload.service_id)
    if service is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "ไม่พบบริการนี้")
    if service.booking_mode == "instant":
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "บริการนี้เรียกใช้ได้ทันทีอยู่แล้ว ไม่มีช่องเวลาให้เฝ้า",
        )
    if payload.from_time >= payload.to_time:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "เวลาเริ่มต้องมาก่อนเวลาสิ้นสุด")
    if payload.watch_date < now_local().date():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "เฝ้าวันที่ผ่านไปแล้วไม่ได้")

    # ใช้เพดานวันจองชุดเดียวกับการจองจริง ไม่งั้นจะเฝ้าวันที่จองไม่ได้อยู่ดี
    _assert_within_window(payload.watch_date)

    if payload.staff_id is not None:
        member = db.get(Staff, payload.staff_id)
        if member is None or member.shop_id != service.shop_id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "ไม่พบผู้ให้บริการนี้ในร้าน")

    active = db.scalars(
        select(SlotWatch).where(
            SlotWatch.user_id == current_user.id, SlotWatch.status == "active"
        )
    ).all()
    if len(active) >= MAX_ACTIVE_WATCHES:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"เฝ้าไว้ได้สูงสุด {MAX_ACTIVE_WATCHES} รายการ กรุณายกเลิกรายการเก่าก่อน",
        )

    row = SlotWatch(
        user_id=current_user.id,
        shop_id=service.shop_id,
        service_id=service.id,
        staff_id=payload.staff_id,
        watch_date=payload.watch_date,
        from_time=payload.from_time,
        to_time=payload.to_time,
    )
    db.add(row)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "คุณเฝ้าช่วงเวลานี้ไว้แล้ว")
    db.refresh(row)
    return _to_out(db, row)


@router.get(
    "/watches",
    response_model=list[SlotWatchOut],
    summary="รายการที่ฉันเฝ้าไว้",
)
def list_watches(
    only_active: bool = Query(True, description="แสดงเฉพาะที่ยังรออยู่"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    stmt = select(SlotWatch).where(SlotWatch.user_id == current_user.id)
    if only_active:
        stmt = stmt.where(SlotWatch.status == "active")
    rows = db.scalars(stmt.order_by(SlotWatch.watch_date, SlotWatch.from_time)).all()
    return [_to_out(db, r) for r in rows]


@router.delete(
    "/watches/{watch_id}",
    response_model=Message,
    summary="เลิกเฝ้าช่วงเวลานี้",
)
def cancel_watch(
    watch_id: int = Path(..., ge=1),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    row = db.get(SlotWatch, watch_id)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "ไม่พบรายการนี้")
    if row.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "ยกเลิกได้เฉพาะรายการของตัวเอง")

    row.status = "cancelled"
    db.commit()
    return Message(message="เลิกเฝ้าช่วงเวลานี้แล้ว")


# ---------------------------------------------------------------------------
# ตัวเชื่อมกับระบบยกเลิก — ถูกเรียกจาก bookings.py ไม่ใช่ endpoint
# ---------------------------------------------------------------------------
def notify_slot_free(db: Session, booking: Booking) -> int:
    """แจ้งคนที่รอช่วงเวลาที่เพิ่งถูกปล่อยคืน — คืนจำนวนคนที่แจ้งไป

    **ตั้งใจไม่ commit ในนี้** ให้ไปรวมกับ commit ของการยกเลิก
    ถ้าการยกเลิกล้มเหลว การแจ้งเตือนก็ต้องไม่ถูกบันทึกด้วย
    (กติกาเดียวกับ notify() ใน notifications.py)

    เงื่อนไขการจับคู่: ช่วงที่เฝ้าไว้ต้อง **คาบเกี่ยว** กับคิวที่ถูกยกเลิก
    ไม่ใช่ตรงกันเป๊ะ เพราะคนที่รอ 19:00-22:00 ก็ยินดีถ้าช่อง 21:00 ว่าง
    """
    rows = db.scalars(
        select(SlotWatch).where(
            SlotWatch.status == "active",
            SlotWatch.service_id == booking.service_id,
            SlotWatch.watch_date == booking.booking_date,
            # ช่วงทับกัน: เริ่มก่อนที่อีกช่วงจะจบ และจบหลังจากที่อีกช่วงเริ่ม
            SlotWatch.from_time < booking.end_time,
            SlotWatch.to_time > booking.booking_time,
        )
    ).all()

    shop = db.get(Shop, booking.shop_id)
    sent = 0
    for row in rows:
        # คนที่เจาะจงคอร์ท จะได้รับแจ้งเฉพาะตอนคอร์ทนั้นว่างจริง
        if row.staff_id is not None and row.staff_id != booking.staff_id:
            continue
        # ไม่ต้องแจ้งคนที่เป็นเจ้าของคิวที่เพิ่งยกเลิกเอง
        if row.user_id == booking.user_id:
            continue

        notify(
            db, row.user_id, "slot_free",
            "ช่วงเวลาที่คุณรออยู่ว่างแล้ว",
            f"{shop.name if shop else 'ร้าน'} · "
            f"{booking.booking_time.strftime('%H:%M')}–{booking.end_time.strftime('%H:%M')} น. "
            "มีคนยกเลิก รีบจองก่อนถูกคนอื่นตัดหน้า",
            link=f"shop.html?id={booking.shop_id}",
        )
        row.status = "notified"
        row.notified_at = datetime.now(timezone.utc)
        sent += 1
    return sent
