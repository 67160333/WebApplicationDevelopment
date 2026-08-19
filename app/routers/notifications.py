"""6) Notifications — แจ้งเตือนในเว็บ

ระบบนี้ไม่ส่งอีเมลหรือ SMS แค่เก็บเหตุการณ์ไว้ในฐานข้อมูล
แล้วให้กระดิ่งบนแถบเมนูมาดึงไปแสดง — พอสำหรับให้ผู้ใช้รู้ว่ามีอะไรเปลี่ยน
โดยไม่ต้องพึ่งบริการภายนอกที่ต้องเสียเงิน
"""

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Notification, User
from app.schemas import Message, NotificationOut, Page, UnreadCount
from app.security import get_current_user

router = APIRouter(prefix="/api/notifications", tags=["6. Notifications"])


# ---------------- ตัวช่วยที่ router อื่นเรียกใช้ ----------------
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
        stmt = stmt.where(Notification.is_read.is_(False))

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
    """ใช้แสดงจุดแดงบนกระดิ่ง — ตอบเร็วเพราะนับอย่างเดียว"""
    n = db.scalar(
        select(func.count(Notification.id)).where(
            Notification.user_id == current_user.id, Notification.is_read.is_(False)
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
        .where(Notification.user_id == current_user.id, Notification.is_read.is_(False))
        .values(is_read=True)
    )
    db.commit()
    return Message(message="ทำเครื่องหมายว่าอ่านทั้งหมดแล้ว")
