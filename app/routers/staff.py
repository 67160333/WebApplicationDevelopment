"""5) Staff Profiles — โปรไฟล์ช่างและรีวิวของช่างแต่ละคน

แยกออกมาจาก shops.py เพราะฝั่งลูกค้าจะ "เลือกช่างก่อน แล้วค่อยเลือกร้าน" ก็ได้
เช่น เคยทำกับช่างมิ้นแล้วชอบ ก็อยากดูว่าช่างมิ้นว่างวันไหน คะแนนเท่าไร
"""

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Booking, Review, Shop, Staff, User
from app.schemas import Page, ReviewOut, StaffDetail, StaffOut

router = APIRouter(prefix="/api", tags=["5. Staff Profiles"])


def _get_staff_or_404(db: Session, staff_id: int) -> Staff:
    member = db.get(Staff, staff_id)
    if member is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ไม่พบช่างคนนี้")
    return member


@router.get(
    "/staff/{staff_id}",
    response_model=StaffDetail,
    summary="ดูโปรไฟล์ช่าง",
)
def get_staff(staff_id: int = Path(..., ge=1), db: Session = Depends(get_db)):
    """คืนข้อมูลช่าง คะแนนเฉลี่ย และจำนวนงานที่ทำเสร็จแล้ว

    ตัวเลข "งานที่ทำเสร็จ" ช่วยให้ลูกค้าตัดสินใจได้ว่าช่างคนนี้มีประสบการณ์แค่ไหน
    """
    member = _get_staff_or_404(db, staff_id)
    shop = db.get(Shop, member.shop_id)

    jobs_done = db.scalar(
        select(func.count(Booking.id)).where(
            Booking.staff_id == staff_id, Booking.status == "completed"
        )
    )

    # สร้างจาก StaffOut ก่อน แล้วค่อยเติมสองฟิลด์ที่ไม่ได้อยู่ในตาราง staff
    # (ถ้าใช้ model_validate ตรง ๆ จะพังเพราะ model ไม่มี shop_name / jobs_done)
    return StaffDetail(
        **StaffOut.model_validate(member).model_dump(),
        shop_name=shop.name if shop else "—",
        jobs_done=int(jobs_done or 0),
    )


@router.get(
    "/staff/{staff_id}/reviews",
    response_model=Page[ReviewOut],
    summary="ดูรีวิวของช่างคนนี้",
)
def list_staff_reviews(
    staff_id: int = Path(..., ge=1),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    sort: str = Query("newest", pattern="^(newest|highest|lowest)$"),
    db: Session = Depends(get_db),
):
    """เอาเฉพาะรีวิวที่ลูกค้าให้ดาวช่างไว้ — รีวิวที่พูดถึงแต่ร้านจะไม่ถูกนับ"""
    _get_staff_or_404(db, staff_id)

    stmt = select(Review).where(Review.staff_id == staff_id, Review.staff_rating.isnot(None))
    order = {
        "newest": Review.created_at.desc(),
        "highest": Review.staff_rating.desc(),
        "lowest": Review.staff_rating.asc(),
    }[sort]

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(
        stmt.order_by(order, Review.id.desc()).offset((page - 1) * limit).limit(limit)
    ).all()

    from app.routers.bookings import _with_names   # ใช้ตัวช่วยเดียวกัน ผลลัพธ์จะได้เหมือนกัน

    return Page[ReviewOut](
        items=_with_names(db, list(rows)),
        page=page,
        limit=limit,
        total=total,
        total_pages=(total + limit - 1) // limit,
    )
