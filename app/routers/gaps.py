"""แนะนำสิ่งที่ทำได้ระหว่างรอ — ใช้ประโยชน์จากการที่ระบบเห็นทุกหมวดพร้อมกัน

ข้อสังเกตที่เป็นจุดเริ่ม
--------------------------------------------------------------------------
**การจองบางอย่างสร้างเวลาว่างขึ้นมาเอง**

เคลือบแก้วรถใช้เวลา 480 นาที ลูกค้าเอารถไปฝากตอน 08:00 ได้คืน 16:00
แปดชั่วโมงนั้นเขา **ติดอยู่แถวนั้นโดยไม่มีรถ** จะกลับบ้านก็ไม่สะดวก
จะไปไหนไกลก็ไม่ได้ เพราะพาหนะของตัวเองอยู่ในร้าน

ระบบรู้ทุกอย่างที่ต้องใช้อยู่แล้ว — รู้ว่าว่างกี่โมงถึงกี่โมง รู้ว่าอยู่พิกัดไหน
และรู้ว่ามีร้านอะไรว่างแถวนั้น แต่ไม่เคยเอามาต่อกัน

ทำไมคู่แข่งทำแบบนี้ไม่ได้
--------------------------------------------------------------------------
- GoWabi เห็นแค่ร้านความงาม ไม่รู้ว่าลูกค้าเอารถไปเคลือบแก้วอยู่
- Matchday เห็นแค่สนามกีฬา ไม่รู้ว่าโลกนี้มีสปา
- Fresha / SimplyBook.me เป็นซอฟต์แวร์ของ **ร้านแต่ละร้าน** — ร้านหนึ่งไม่รู้ด้วยซ้ำว่าร้านอื่นมีอยู่

ต้องเป็นระบบที่เห็นหลายหมวดพร้อมกันเท่านั้นถึงจะทำได้

สองโหมด
--------------------------------------------------------------------------
`waiting`  ฝากของไว้แล้วรอ (ดูแลรถยนต์) — ช่วงว่างคือ *ระหว่าง* คิวนั้นเอง
           ลูกค้าไม่มีรถ จึงต้องอยู่ใกล้มาก รัศมีแคบ

`after`    ไปเองแล้วเสร็จ (สนามบอล ตัดผม) — ช่วงว่างคือ *หลัง* คิวจบ
           ยังมีพาหนะอยู่ เดินทางไกลขึ้นได้ รัศมีกว้างกว่า

ข้อจำกัดที่ต้องรู้
--------------------------------------------------------------------------
**เวลาเดินทางเป็นการประมาณจากระยะทางเส้นตรง ไม่ใช่เส้นทางจริง**
ใช้สูตร 10 นาที + 4 นาทีต่อกิโลเมตร ซึ่งพอไหวกับวินมอเตอร์ไซค์ในกรุงเทพ
แต่ไม่ได้ดูสภาพจราจรจริง ถ้าจะทำให้แม่นต้องต่อ API เส้นทางซึ่งอยู่นอกขอบเขตโปรเจกต์นี้
"""

from datetime import date as date_cls, time as time_cls

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Booking, Category, Service, Shop, User
from app.schemas import GapSuggestion, GapWindow
from app.security import get_current_user

router = APIRouter(prefix="/api", tags=["11. แนะนำระหว่างรอ"])

# หมวดที่ลูกค้า "ฝากของไว้แล้วต้องรอ" — เวลาว่างเกิดขึ้นระหว่างคิว ไม่ใช่หลังคิว
WAITING_CATEGORIES = {"car-care"}

# รัศมีค้นหา (กิโลเมตร)
RADIUS_WAITING = 5.0    # ไม่มีรถ ต้องเดินหรือนั่งวินได้
RADIUS_AFTER = 12.0     # มีพาหนะอยู่ ไปได้ไกลกว่า

# เผื่อเวลาไว้กันพลาด — ไม่แนะนำอะไรที่ทำให้กลับมาไม่ทัน
BUFFER_MINUTES = 20
MIN_WINDOW = 60         # ช่วงว่างสั้นกว่านี้ไม่คุ้มจะไปไหน


def _travel_minutes(km: float) -> int:
    """ประมาณเวลาเดินทางเที่ยวเดียวจากระยะทางเส้นตรง

    10 นาทีคือค่าคงที่ของการเรียกรถและเดินเข้าออก
    4 นาที/กม. มาจากความเร็วเฉลี่ยราว 15 กม./ชม. ซึ่งเป็นความเร็วจริงของ
    มอเตอร์ไซค์ในกรุงเทพช่วงกลางวัน (รถยนต์ช้ากว่านี้อีก)

    ตั้งใจประมาณให้ "แพงไว้ก่อน" เพราะแนะนำแล้วไปไม่ทันแย่กว่าไม่แนะนำเลย
    """
    return int(round(10 + km * 4))


@router.get(
    "/bookings/{booking_id}/gap",
    response_model=GapWindow,
    summary="สิ่งที่ทำได้ระหว่างรอคิวนี้",
    description=(
        "หาบริการใกล้เคียงที่ว่างพอดีกับช่วงเวลาที่ลูกค้าต้องรอ\n\n"
        "ใช้ได้ผลชัดที่สุดกับงานที่ใช้เวลานานอย่างเคลือบแก้วรถ 8 ชั่วโมง "
        "ซึ่งลูกค้าต้องฝากรถไว้แล้วไม่มีพาหนะกลับ"
    ),
)
def booking_gap(
    booking_id: int = Path(..., ge=1),
    limit: int = Query(6, ge=1, le=20),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # นำเข้าตรงนี้เพื่อเลี่ยง circular import — bookings.py ไม่ได้อ้างถึงไฟล์นี้
    from app.routers.bookings import (
        SLOT_STEP_MINUTES, _add_minutes, _busy_intervals, _closure_reason,
        _minutes, _shop_capacity, _slot_is_taken, _windows_for,
    )
    from app.routers.shops import _distance_km, _label_map

    booking = db.get(Booking, booking_id)
    if booking is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "ไม่พบการจองนี้")
    if booking.user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "ดูได้เฉพาะคิวของตัวเอง")

    origin = db.get(Shop, booking.shop_id)
    if origin is None or origin.latitude is None or origin.longitude is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "ร้านนี้ยังไม่มีพิกัด จึงหาร้านใกล้เคียงไม่ได้")

    origin_cat = db.get(Category, origin.category_id)
    waiting = bool(origin_cat and origin_cat.slug in WAITING_CATEGORIES)

    # ---------- 1. หาช่วงเวลาว่าง ----------
    if waiting:
        win_start = _minutes(booking.booking_time)
        win_end = _minutes(booking.end_time)
        radius = RADIUS_WAITING
        reason = (
            f"ระหว่างที่รถอยู่ที่ {origin.name} คุณจะไม่มีพาหนะ "
            f"จึงแนะนำเฉพาะร้านในรัศมี {RADIUS_WAITING:.0f} กม."
        )
    else:
        win_start = _minutes(booking.end_time)
        # ปิดหน้าต่างไว้ที่เที่ยงคืน ไม่ลากข้ามวัน เพราะการจองหนึ่งครั้ง
        # ต้องจบในวันปฏิทินเดียวกันตามกติกาที่ตั้งไว้ตั้งแต่แรก
        win_end = 1440
        radius = RADIUS_AFTER
        reason = f"หลังจบคิวที่ {origin.name} เวลา {booking.end_time.strftime('%H:%M')} น."

    window = win_end - win_start
    empty = GapWindow(
        booking_id=booking.id,
        mode="waiting" if waiting else "after",
        window_start=time_cls(win_start // 60 % 24, win_start % 60),
        window_end=time_cls(win_end // 60 % 24, win_end % 60),
        window_minutes=max(window, 0),
        radius_km=radius,
        reason=reason,
        items=[],
    )
    if window < MIN_WINDOW or booking.status == "cancelled":
        return empty

    # ---------- 2. ร้านที่อยู่ในรัศมี ----------
    dist = _distance_km(float(origin.latitude), float(origin.longitude))
    # ใช้ .where() กับนิพจน์ระยะทางตรง ๆ แบบเดียวกับ shops.py
    # (ไม่ใช่ .having() เพราะไม่มีการ group)
    near = db.execute(
        select(Shop, dist.label("d"))
        .where(
            Shop.id != origin.id,
            Shop.is_active.is_(True),
            Shop.latitude.is_not(None),
            Shop.longitude.is_not(None),
            dist <= radius,
        )
        .order_by(dist)
        .limit(40)
    ).all()
    if not near:
        return empty

    labels = _label_map(db)
    on_date: date_cls = booking.booking_date
    out: list[GapSuggestion] = []

    for shop, km in near:
        km = float(km)
        travel = _travel_minutes(km)
        # ต้องเผื่อเวลาไป-กลับ ไม่ใช่แค่ขาไป
        overhead = travel * 2 + BUFFER_MINUTES
        usable = window - overhead
        if usable <= 0:
            continue
        if _closure_reason(db, shop.id, on_date):
            continue

        shop_windows = _windows_for(shop, None)
        capacity = _shop_capacity(db, shop.id, on_date)
        if capacity <= 0:
            continue
        busy = _busy_intervals(db, shop.id, on_date, None)

        services = db.scalars(
            select(Service).where(
                Service.shop_id == shop.id,
                Service.is_active.is_(True),
                Service.booking_mode == "scheduled",
                Service.duration_minutes <= usable,
            ).order_by(Service.duration_minutes)
        ).all()

        for sv in services:
            dur = sv.duration_minutes
            earliest = win_start + travel + BUFFER_MINUTES // 2
            latest = win_end - travel - BUFFER_MINUTES // 2 - dur
            # ปัดขึ้นให้ตรงกับตารางช่องเวลา ไม่งั้นจะแนะนำเวลาที่จองไม่ได้จริง
            start = ((earliest + SLOT_STEP_MINUTES - 1) // SLOT_STEP_MINUTES) * SLOT_STEP_MINUTES
            found = None
            while start <= latest:
                end = start + dur
                inside = any(s <= start and end <= e for s, e in shop_windows)
                if inside and not _slot_is_taken(start, end, busy, capacity):
                    found = start
                    break
                start += SLOT_STEP_MINUTES
            if found is None:
                continue

            label, slug = labels.get(shop.category_id, ("ช่าง", None))
            out.append(GapSuggestion(
                shop_id=shop.id,
                shop_name=shop.name,
                category_slug=slug,
                resource_label=label,
                service_id=sv.id,
                service_name=sv.name,
                price=sv.price,
                duration_minutes=dur,
                distance_km=round(km, 2),
                travel_minutes=travel,
                start_time=time_cls(found // 60 % 24, found % 60),
                end_time=_add_minutes(time_cls(found // 60 % 24, found % 60), dur),
            ))
            # ร้านละหนึ่งข้อเสนอพอ ไม่งั้นร้านเดียวจะยึดรายการทั้งหมด
            break

        if len(out) >= limit:
            break

    empty.items = out[:limit]
    return empty
