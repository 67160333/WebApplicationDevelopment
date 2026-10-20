"""6) Notifications — แจ้งเตือนในเว็บ

ระบบนี้ไม่ส่ง SMS แค่เก็บเหตุการณ์ไว้ในฐานข้อมูล
แล้วให้กระดิ่งบนแถบเมนูมาดึงไปแสดง — พอสำหรับให้ผู้ใช้รู้ว่ามีอะไรเปลี่ยน
โดยไม่ต้องพึ่งบริการภายนอกที่ต้องเสียเงิน
"""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Booking, Notification, Service, Shop, User
from app.schemas import Message, NotificationOut, Page, UnreadCount
from app.security import get_current_user

router = APIRouter(prefix="/api/notifications", tags=["6. Notifications"])


# ---------------- ตัวช่วยที่ router อื่นเรียกใช้ ----------------
# เงื่อนไข "ยังไม่อ่าน" ใช้ร่วมกันทุกจุด
#
# เขียนเป็น is_read = false ให้ตรงกับเงื่อนไขของ partial index ix_notif_unread ทุกตัวอักษร
# ถ้าเขียน .is_(False) จะได้ SQL "is_read IS false" ซึ่งเป็นเงื่อนไขคนละรูปกับของ index
# วัดแล้วใน indexing-lab (labs/04-pitfalls.sql ข้อ 4.4): แบบ IS false PostgreSQL ไม่ใช้ index ตัวนี้
UNREAD = Notification.is_read == False  # noqa: E712


def notify(
    db: Session,
    user_id: int,
    kind: str,
    title: str,
    body: str | None = None,
    link: str | None = "bookings.html",
) -> None:
    """สร้างการแจ้งเตือนหนึ่งรายการ

    ตั้งใจไม่ commit ในนี้ ให้ไปรวมกับ commit ของงานหลัก
    ถ้างานหลักล้มเหลว การแจ้งเตือนก็ต้องไม่ถูกบันทึกด้วย
    """
    db.add(Notification(user_id=user_id, kind=kind, title=title, body=body, link=link))


# ---------------- เตือนนัดล่วงหน้า ----------------
REMIND_BEFORE = timedelta(hours=24)


def send_due_reminders(db: Session, user: User) -> int:
    """สร้างแจ้งเตือน "อีกไม่ถึง 24 ชม. มีนัด" ให้ลูกค้าคนนี้ คิวละครั้งเดียว

    ทำไมไม่ใช้ตัวตั้งเวลา (cron): Render รุ่นฟรีหลับเมื่อไม่มีคนใช้ ตัวตั้งเวลาในแอปจึงไม่ทำงาน
    เลยตรวจตอนลูกค้าเปิดเว็บแทน — ทุกหน้าที่ล็อกอินจะเรียก unread-count อยู่แล้ว
    แนวเดียวกับ escrow.release_due ที่ปล่อยเงินเมื่อมีคนเปิดดู

    ตรวจเฉพาะคิวของคนนี้ วันนี้กับพรุ่งนี้ ใช้ index ix_bookings_user_id จึงเร็ว
    เฉพาะคิวที่ยืนยันแล้ว — คิวที่ยังไม่จ่ายยังไม่ล็อกช่องเวลา เตือนไปอาจโดนคนอื่นตัดหน้า
    """
    from app.routers.bookings import now_local  # import ในฟังก์ชัน กันวนกันระหว่างสองไฟล์

    now = now_local()
    rows = db.scalars(
        select(Booking).where(
            Booking.user_id == user.id,
            Booking.status == "confirmed",
            Booking.reminded_at.is_(None),
            Booking.guest_name.is_(None),
            Booking.booking_date.in_((now.date(), (now + timedelta(days=1)).date())),
        )
    ).all()

    sent = 0
    for b in rows:
        start = datetime.combine(b.booking_date, b.booking_time, tzinfo=now.tzinfo)
        if not (now <= start <= now + REMIND_BEFORE):
            continue
        service = db.get(Service, b.service_id)
        shop = db.get(Shop, b.shop_id)
        when = "วันนี้" if b.booking_date == now.date() else "พรุ่งนี้"
        notify(
            db, user.id, "booking_reminder",
            f"{when} {b.booking_time.strftime('%H:%M')} น. มีนัดที่ {shop.name if shop else 'ร้าน'}",
            f"{service.name if service else 'บริการ'} · รหัส {b.booking_code}",
        )
        b.reminded_at = datetime.now(timezone.utc)
        sent += 1
    if sent:
        db.commit()
    return sent


# ---------------- endpoint ----------------
@router.get("", response_model=Page[NotificationOut], summary="ดูการแจ้งเตือนของฉัน")
def list_notifications(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    unread_only: bool = Query(False, description="เอาเฉพาะที่ยังไม่ได้อ่าน"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    stmt = select(Notification).where(Notification.user_id == current_user.id)
    if unread_only:
        stmt = stmt.where(UNREAD)

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(
        stmt.order_by(Notification.created_at.desc(), Notification.id.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    ).all()

    return Page[NotificationOut](
        items=list(rows),
        page=page,
        limit=limit,
        total=total,
        total_pages=(total + limit - 1) // limit,
    )


@router.get("/unread-count", response_model=UnreadCount, summary="จำนวนที่ยังไม่ได้อ่าน")
def unread_count(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    """ใช้แสดงจุดแดงบนกระดิ่ง และเป็นจังหวะที่ใช้สร้างแจ้งเตือนนัดล่วงหน้า"""
    send_due_reminders(db, current_user)
    n = db.scalar(
        select(func.count(Notification.id)).where(
            Notification.user_id == current_user.id, UNREAD
        )
    )
    return UnreadCount(unread=int(n or 0))


@router.patch("/{notification_id}/read", response_model=NotificationOut, summary="ทำเครื่องหมายว่าอ่านแล้ว")
def mark_read(
    notification_id: int = Path(..., ge=1),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    row = db.get(Notification, notification_id)
    if row is None or row.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ไม่พบการแจ้งเตือนนี้")

    row.is_read = True
    db.commit()
    db.refresh(row)
    return row


@router.post("/read-all", response_model=Message, summary="อ่านทั้งหมดแล้ว")
def mark_all_read(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    db.execute(
        update(Notification)
        .where(Notification.user_id == current_user.id, UNREAD)
        .values(is_read=True)
    )
    db.commit()
    return Message(message="ทำเครื่องหมายว่าอ่านทั้งหมดแล้ว")
