"""ก๊วน — หาคนไปเล่นกีฬาด้วยกัน

ปัญหาที่แก้
--------------------------------------------------------------------------
หมวดกีฬาต่างจากหมวดอื่นอย่างสิ้นเชิงตรงที่ **ต้องมีคนครบก่อนถึงจะใช้บริการได้**

ร้านทำผมจองคนเดียวก็ตัดผมได้ แต่สนามฟุตบอลต้องมี 10-22 คน
คนที่อยากเตะบอลแต่ไม่มีเพื่อนไปด้วย กดจองสนามไปก็เปล่าประโยชน์
ปุ่ม "จองคิว" จึงแก้ปัญหาผิดข้อสำหรับหมวดนี้ — ปัญหาจริงคือ **"ไม่มีคนไปด้วย"**

คนไทยแก้กันเองมานานแล้วด้วยการ "เปิดก๊วน" คนหนึ่งจองสนามไว้ก่อน
แล้วประกาศหาคนมาเติมให้ครบ หารค่าสนามกัน ระบบนี้ย้ายพฤติกรรมนั้นมาไว้บนเว็บ

หลักการออกแบบที่ยึดไว้
--------------------------------------------------------------------------
**เจ้าของก๊วนยังเป็นเจ้าของคิวคนเดียวเหมือนเดิม**
คนที่เข้าร่วมไม่ได้ถือสิทธิ์ในคิวนั้น แค่ลงชื่อว่าจะไปด้วย
ทำแบบนี้เพื่อไม่ให้กติกาการล็อกช่องเวลาและค่าปรับยกเลิกที่ทำไว้แล้วรวนทั้งระบบ

**ระบบไม่เก็บเงินแทน** `share_price` เป็นตัวเลขที่ตกลงกันเอง
เพราะการโอนเงินระหว่างผู้ใช้ด้วยกันเป็นเรื่องที่ต้องมีใบอนุญาต ไม่ใช่สิ่งที่โปรเจกต์นี้ทำได้จริง
เขียนไว้ตรงนี้เพื่อไม่ให้ใครมาต่อยอดผิดทาง
"""

from datetime import date as date_cls

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Booking, Category, MatchJoin, Service, Shop, Staff, User
from app.schemas import MatchJoinOut, MatchOpen, MatchOut, Message
from app.routers.notifications import notify
from app.security import get_current_user

router = APIRouter(prefix="/api", tags=["10. ก๊วน (หาคนไปด้วยกัน)"])

# หมวดที่เปิดก๊วนได้ — ต้องเป็นกิจกรรมที่ "ยิ่งคนเยอะยิ่งเล่นได้"
# ร้านทำผมเปิดก๊วนไม่ได้เพราะช่างตัดให้ทีละคนอยู่แล้ว ไม่ได้ประหยัดอะไร
TEAM_CATEGORIES = {"football", "badminton", "karaoke"}


def _short_name(full: str | None) -> str:
    """ย่อนามสกุลเหลือตัวอักษรเดียว — กติกาเดียวกับที่ใช้กับรีวิว

    ก๊วนเป็นข้อมูลที่คนแปลกหน้าเห็นได้ จึงต้องไม่เปิดเผยนามสกุลเต็ม
    """
    if not full:
        return "ผู้ใช้"
    parts = full.strip().split()
    return parts[0] if len(parts) == 1 else f"{parts[0]} {parts[1][0]}."


def _joined_count(db: Session, booking_id: int) -> int:
    """นับคนที่ยังอยู่ในก๊วน — คนที่ถอนตัวแล้วไม่นับ"""
    return db.scalar(
        select(func.count()).select_from(MatchJoin).where(
            MatchJoin.booking_id == booking_id,
            MatchJoin.status != "left",
        )
    ) or 0


def _get_booking(db: Session, booking_id: int) -> Booking:
    booking = db.get(Booking, booking_id)
    if booking is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "ไม่พบการจองนี้")
    return booking


def _to_match(db: Session, booking: Booking, me: User | None = None,
              distance: float | None = None) -> MatchOut:
    shop = db.get(Shop, booking.shop_id)
    cat = db.get(Category, shop.category_id) if shop else None
    service = db.get(Service, booking.service_id)
    resource = db.get(Staff, booking.staff_id) if booking.staff_id else None
    host = db.get(User, booking.user_id) if booking.user_id else None

    joined = _joined_count(db, booking.id)
    mine = False
    if me is not None:
        mine = db.scalar(
            select(func.count()).select_from(MatchJoin).where(
                MatchJoin.booking_id == booking.id,
                MatchJoin.user_id == me.id,
                MatchJoin.status != "left",
            )
        ) or 0
        mine = bool(mine)

    return MatchOut(
        booking_id=booking.id,
        shop_id=booking.shop_id,
        shop_name=shop.name if shop else "—",
        shop_district=shop.district if shop else None,
        category_slug=cat.slug if cat else None,
        service_name=service.name if service else "—",
        resource_name=resource.name if resource else None,
        booking_date=booking.booking_date,
        booking_time=booking.booking_time,
        end_time=booking.end_time,
        host_name=_short_name(host.full_name if host else None),
        open_slots=booking.open_slots,
        joined_count=joined,
        slots_left=max(booking.open_slots - joined, 0),
        share_price=booking.share_price,
        match_note=booking.match_note,
        distance_km=distance,
        joined_by_me=mine,
    )


# ---------------------------------------------------------------- เปิดก๊วน ----
@router.post(
    "/bookings/{booking_id}/open-match",
    response_model=MatchOut,
    summary="เปิดก๊วนจากคิวที่จองไว้แล้ว",
    description=(
        "ประกาศหาคนไปด้วยกัน ใช้ได้เฉพาะหมวดกีฬาและคาราโอเกะ\n\n"
        "**ระบบไม่ได้เก็บเงินแทน** ยอดต่อคนเป็นตัวเลขที่ตกลงกันเอง"
    ),
)
def open_match(
    payload: MatchOpen,
    booking_id: int = Path(..., ge=1),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    booking = _get_booking(db, booking_id)

    if booking.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "เปิดก๊วนได้เฉพาะคิวของตัวเอง")
    if booking.status == "cancelled":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "คิวนี้ถูกยกเลิกไปแล้ว")

    shop = db.get(Shop, booking.shop_id)
    cat = db.get(Category, shop.category_id) if shop else None
    if cat is None or cat.slug not in TEAM_CATEGORIES:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "หมวดนี้เปิดก๊วนไม่ได้ — เปิดได้เฉพาะสนามกีฬาและห้องคาราโอเกะ "
            "ซึ่งเป็นกิจกรรมที่ต้องมีหลายคนถึงจะเล่นได้",
        )

    # คิวที่ยังไม่ล็อกเวลาเปิดก๊วนไม่ได้ ไม่งั้นจะมีคนมาลงชื่อกับคิวที่หลุดไปแล้ว
    if not booking.holds_slot:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "ต้องชำระมัดจำให้ช่องเวลาถูกล็อกก่อน ถึงจะเปิดก๊วนได้ "
            "ไม่งั้นคนที่มาลงชื่ออาจเสียเที่ยวถ้าคิวถูกคนอื่นตัดหน้า",
        )

    joined = _joined_count(db, booking.id)
    if payload.open_slots < joined:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"ตอนนี้มีคนลงชื่อไว้แล้ว {joined} คน ตั้งจำนวนน้อยกว่านี้ไม่ได้",
        )

    booking.open_slots = payload.open_slots
    booking.share_price = payload.share_price
    booking.match_note = payload.match_note
    db.commit()
    db.refresh(booking)
    return _to_match(db, booking, current_user)


@router.delete(
    "/bookings/{booking_id}/open-match",
    response_model=Message,
    summary="ปิดก๊วน (ไม่รับคนเพิ่มแล้ว)",
)
def close_match(
    booking_id: int = Path(..., ge=1),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    booking = _get_booking(db, booking_id)
    if booking.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "ปิดก๊วนได้เฉพาะคิวของตัวเอง")

    booking.open_slots = 0
    booking.match_note = None
    # ไม่ลบคนที่ลงชื่อไว้ เพราะเขายังไปตามนัดอยู่ แค่ไม่รับคนเพิ่มแล้ว
    db.commit()
    return Message(message="ปิดรับคนเพิ่มแล้ว คนที่ลงชื่อไว้ยังอยู่ในก๊วนตามเดิม")


# ---------------------------------------------------------------- ดูก๊วน ----
@router.get(
    "/matches",
    response_model=list[MatchOut],
    summary="ก๊วนที่กำลังหาคน",
    description=(
        "แสดงเฉพาะก๊วนที่ยังรับคนได้และยังไม่ถึงวันนัด "
        "เรียงตามวันที่ใกล้ที่สุดก่อน"
    ),
)
def list_matches(
    category: str | None = Query(None, description="กรองตามหมวด เช่น football"),
    district: str | None = Query(None, description="กรองตามเขต"),
    on_date: date_cls | None = Query(None, alias="date", description="เฉพาะวันที่ระบุ"),
    shop_id: int | None = Query(None, ge=1, description="เฉพาะสนามนี้"),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    from app.routers.bookings import now_local

    today = now_local().date()
    stmt = (
        select(Booking)
        .join(Shop, Shop.id == Booking.shop_id)
        .join(Category, Category.id == Shop.category_id)
        .where(
            Booking.open_slots > 0,
            Booking.status.in_(["pending", "confirmed"]),
            Booking.booking_date >= today,
        )
    )
    if category:
        stmt = stmt.where(Category.slug == category)
    if district:
        stmt = stmt.where(Shop.district == district)
    if on_date:
        stmt = stmt.where(Booking.booking_date == on_date)
    if shop_id:
        stmt = stmt.where(Booking.shop_id == shop_id)

    rows = db.scalars(
        stmt.order_by(Booking.booking_date, Booking.booking_time).limit(limit * 2)
    ).all()

    # กรองก๊วนที่เต็มแล้วออกในโค้ด เพราะจำนวนคนต้องนับจากอีกตาราง
    out: list[MatchOut] = []
    for b in rows:
        m = _to_match(db, b)
        if m.slots_left > 0:
            out.append(m)
        if len(out) >= limit:
            break
    return out


@router.get(
    "/bookings/{booking_id}/joins",
    response_model=list[MatchJoinOut],
    summary="รายชื่อคนในก๊วน",
)
def list_joins(
    booking_id: int = Path(..., ge=1),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    booking = _get_booking(db, booking_id)
    rows = db.scalars(
        select(MatchJoin)
        .where(MatchJoin.booking_id == booking_id, MatchJoin.status != "left")
        .order_by(MatchJoin.created_at)
    ).all()

    is_host = booking.user_id == current_user.id or current_user.role == "admin"
    out = []
    for r in rows:
        u = db.get(User, r.user_id)
        item = MatchJoinOut.model_validate(r)
        item.user_name = _short_name(u.full_name if u else None)
        # คนนอกเห็นแค่ชื่อกับสถานะ ไม่เห็นข้อความส่วนตัวที่เขียนถึงเจ้าของก๊วน
        if not is_host and r.user_id != current_user.id:
            item.note = None
        out.append(item)
    return out


# ---------------------------------------------------------------- เข้าร่วม ----
@router.post(
    "/bookings/{booking_id}/join",
    response_model=MatchJoinOut,
    status_code=status.HTTP_201_CREATED,
    summary="ขอเข้าร่วมก๊วน",
)
def join_match(
    booking_id: int = Path(..., ge=1),
    note: str | None = Query(None, max_length=200, description="ข้อความถึงเจ้าของก๊วน"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from app.routers.bookings import now_local

    booking = _get_booking(db, booking_id)

    if booking.open_slots <= 0:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "ก๊วนนี้ไม่ได้เปิดรับคนเพิ่ม")
    if booking.status == "cancelled":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "ก๊วนนี้ถูกยกเลิกไปแล้ว")
    if booking.user_id == current_user.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "คุณเป็นเจ้าของก๊วนนี้อยู่แล้ว")
    if booking.booking_date < now_local().date():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "ก๊วนนี้เลยวันนัดไปแล้ว")

    existing = db.scalar(
        select(MatchJoin).where(
            MatchJoin.booking_id == booking_id, MatchJoin.user_id == current_user.id
        )
    )
    if existing is not None and existing.status != "left":
        raise HTTPException(status.HTTP_409_CONFLICT, "คุณลงชื่อในก๊วนนี้ไว้แล้ว")

    if _joined_count(db, booking_id) >= booking.open_slots:
        raise HTTPException(status.HTTP_409_CONFLICT, "ก๊วนนี้เต็มแล้ว")

    if existing is not None:
        # เคยถอนตัวแล้วกลับมาใหม่ — ใช้แถวเดิมเพื่อไม่ให้ชนดัชนี uq_match_join_user
        existing.status = "joined"
        existing.share_amount = booking.share_price
        existing.note = note
        row = existing
    else:
        row = MatchJoin(
            booking_id=booking_id,
            user_id=current_user.id,
            status="joined",
            share_amount=booking.share_price,
            note=note,
        )
        db.add(row)

    db.flush()
    if booking.user_id:
        left = booking.open_slots - _joined_count(db, booking_id)
        notify(
            db, booking.user_id, "match_joined",
            "มีคนเข้าร่วมก๊วนของคุณ",
            f"{_short_name(current_user.full_name)} ลงชื่อไปด้วย "
            + (f"ยังขาดอีก {left} คน" if left > 0 else "ครบแล้ว"),
        )
    db.commit()
    db.refresh(row)

    out = MatchJoinOut.model_validate(row)
    out.user_name = _short_name(current_user.full_name)
    return out


@router.delete(
    "/bookings/{booking_id}/join",
    response_model=Message,
    summary="ถอนตัวจากก๊วน",
)
def leave_match(
    booking_id: int = Path(..., ge=1),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    row = db.scalar(
        select(MatchJoin).where(
            MatchJoin.booking_id == booking_id,
            MatchJoin.user_id == current_user.id,
            MatchJoin.status != "left",
        )
    )
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "คุณไม่ได้อยู่ในก๊วนนี้")

    # เปลี่ยนสถานะแทนการลบ เพื่อเก็บประวัติไว้ว่าเคยเข้าแล้วถอน
    row.status = "left"
    booking = db.get(Booking, booking_id)
    if booking is not None and booking.user_id:
        left = booking.open_slots - _joined_count(db, booking_id)
        notify(
            db, booking.user_id, "match_left",
            "มีคนถอนตัวจากก๊วน",
            f"{_short_name(current_user.full_name)} ถอนตัว ยังขาดอีก {left} คน",
        )
    db.commit()
    return Message(message="ถอนตัวจากก๊วนแล้ว")
