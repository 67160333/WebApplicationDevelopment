"""5) Staff Profiles — โปรไฟล์ช่างและรีวิวของช่างแต่ละคน

แยกออกมาจาก shops.py เพราะฝั่งลูกค้าจะ "เลือกช่างก่อน แล้วค่อยเลือกร้าน" ก็ได้
เช่น เคยทำกับช่างมิ้นแล้วชอบ ก็อยากดูว่าช่างมิ้นว่างวันไหน คะแนนเท่าไร
"""

from datetime import datetime, timezone

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Path,
    Query,
    Response,
    UploadFile,
    status,
)
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session, undefer

from app.database import get_db
from app.models import Booking, Review, Service, Shop, Staff, User
from app.schemas import Page, ReviewOut, StaffAspects, StaffDetail, StaffOut, StaffService
from app.security import require_roles
from app.storage import UploadError, process_shop_image

router = APIRouter(prefix="/api", tags=["5. Staff Profiles"])


def _get_staff_or_404(db: Session, staff_id: int) -> Staff:
    member = db.get(Staff, staff_id)
    if member is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ไม่พบช่างคนนี้")
    return member


# ============================================================
# รูปโปรไฟล์ช่าง
# ============================================================
@router.post(
    "/staff/{staff_id}/photo",
    response_model=StaffOut,
    summary="อัปโหลดรูปโปรไฟล์ช่าง (เจ้าของร้าน)",
    description=(
        "รับไฟล์ JPG / PNG / WebP / GIF ขนาดไม่เกิน 5 MB "
        "ระบบย่อและแปลงเป็น WebP ให้อัตโนมัติ พร้อมลบข้อมูล EXIF "
        "อัปซ้ำได้ รูปเดิมจะถูกแทนที่"
    ),
)
async def upload_staff_photo(
    staff_id: int = Path(..., ge=1),
    file: UploadFile = File(..., description="ไฟล์ภาพ"),
    current_user: User = Depends(require_roles("owner", "admin")),
    db: Session = Depends(get_db),
):
    member = _get_staff_or_404(db, staff_id)
    shop = db.get(Shop, member.shop_id)
    if current_user.role != "admin" and (shop is None or shop.owner_id != current_user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="คุณไม่ใช่เจ้าของร้านนี้")

    raw = await file.read()
    try:
        filename, data, _w, _h = process_shop_image(raw)
    except UploadError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))

    # ช่างมีรูปได้คนละใบ อัปใหม่ = ทับของเดิมไปเลย
    # ชื่อไฟล์เปลี่ยนทุกครั้ง เบราว์เซอร์จึงเห็นเป็นคนละรูปและไม่หยิบของเก่าจากแคช
    member.photo_name = filename
    member.photo = data
    db.commit()
    db.refresh(member)
    return StaffOut.model_validate(member)


@router.delete("/staff/{staff_id}/photo", response_model=StaffOut, summary="ลบรูปโปรไฟล์ช่าง")
def delete_staff_photo(
    staff_id: int = Path(..., ge=1),
    current_user: User = Depends(require_roles("owner", "admin")),
    db: Session = Depends(get_db),
):
    member = _get_staff_or_404(db, staff_id)
    shop = db.get(Shop, member.shop_id)
    if current_user.role != "admin" and (shop is None or shop.owner_id != current_user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="คุณไม่ใช่เจ้าของร้านนี้")

    member.photo_name = None
    member.photo = None
    db.commit()
    db.refresh(member)
    return StaffOut.model_validate(member)


# เส้นทางไฟล์รูป ไม่มี /api นำหน้า ให้เข้าชุดกับรูปร้าน
# ไม่ต้องล็อกอิน เพราะรูปช่างแสดงบนหน้าร้านสาธารณะอยู่แล้ว
files_router = APIRouter(tags=["5. Staff Profiles"])


@files_router.get(
    "/uploads/staff/{staff_id}/{filename}",
    summary="ไฟล์รูปโปรไฟล์ช่าง",
    include_in_schema=False,
    response_class=Response,
)
def serve_staff_photo(
    staff_id: int = Path(..., ge=1),
    filename: str = Path(..., max_length=120),
    db: Session = Depends(get_db),
):
    member = db.scalars(
        select(Staff).where(Staff.id == staff_id).options(undefer(Staff.photo)).limit(1)
    ).first()

    # ต้องเทียบชื่อไฟล์ด้วย ไม่ใช่ดูแค่ staff_id
    # ไม่งั้นพออัปรูปใหม่ URL เก่าจะยังคืนรูปใหม่ ซึ่งทำให้แคชที่ตั้งไว้หนึ่งปีผิดพลาด
    if member is None or not member.photo or member.photo_name != filename:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ไม่พบรูปนี้")

    return Response(
        content=member.photo,
        media_type="image/webp",
        headers={
            "Cache-Control": "public, max-age=31536000, immutable",
            "ETag": f'"{filename}"',
        },
    )


@router.get(
    "/staff/{staff_id}",
    response_model=StaffDetail,
    summary="ดูโปรไฟล์ช่าง",
)
def get_staff(staff_id: int = Path(..., ge=1), db: Session = Depends(get_db)):
    """โปรไฟล์ช่าง พร้อมสถิติที่คำนวณจากงานและรีวิวจริง

    ทำไมต้องคำนวณเอง ไม่ให้เจ้าของร้านกรอก
    ------------------------------------------------------------------
    ช่องให้กรอกเองมักถูกปล่อยว่าง โปรไฟล์ช่างจึงมีแค่ชื่อกับตำแหน่ง
    ซึ่งไม่ช่วยให้ลูกค้าตัดสินใจอะไรได้เลย

    ตัวเลขชุดนี้มาจากตาราง bookings และ reviews โดยตรง เจ้าของร้านไม่ต้องทำอะไร
    โปรไฟล์จึงแน่นขึ้นเองตามการใช้งานจริง และที่สำคัญกว่าคือ **ปลอมไม่ได้**
    ต่างจากข้อความโฆษณาที่ใครก็พิมพ์ได้
    """
    member = _get_staff_or_404(db, staff_id)
    shop = db.get(Shop, member.shop_id)

    jobs_done = int(db.scalar(
        select(func.count(Booking.id)).where(
            Booking.staff_id == staff_id, Booking.status == "completed"
        )
    ) or 0)

    # ---------- บริการที่ช่างคนนี้ทำบ่อยที่สุด ----------
    # ตอบคำถามที่ลูกค้าถามจริง ๆ ว่า "คนนี้ถนัดอะไร"
    # นับจากงานที่ทำเสร็จแล้วเท่านั้น คิวที่จองทิ้งไว้ไม่นับเป็นประสบการณ์
    top_rows = db.execute(
        select(Service.name, func.count(Booking.id).label("n"))
        .join(Booking, Booking.service_id == Service.id)
        .where(Booking.staff_id == staff_id, Booking.status == "completed")
        .group_by(Service.name)
        .order_by(func.count(Booking.id).desc())
        .limit(4)
    ).all()
    top_services = [StaffService(name=name, count=int(n)) for name, n in top_rows]

    # ---------- คะแนนย่อยรายด้านของช่างคนนี้ ----------
    # หน้าร้านมีคะแนนย่อยของ "ทั้งร้าน" อยู่แล้ว แต่ร้านหนึ่งมีช่างหลายคน
    # คะแนนรวมจึงบอกไม่ได้ว่าช่างคนที่กำลังดูอยู่เป็นอย่างไร
    #
    # staff_rating คือคะแนนที่ลูกค้าให้ช่างโดยตรง ส่วนอีกสามด้านเป็นคะแนนของงานครั้งนั้น
    # ซึ่งผูกกับช่างที่ทำงานครั้งนั้นอยู่ดี จึงใช้แทนกันได้
    aspect = db.execute(
        select(
            func.avg(Review.staff_rating),
            func.avg(Review.rating_cleanliness),
            func.avg(Review.rating_punctuality),
            func.avg(Review.rating_value),
        ).where(Review.staff_id == staff_id)
    ).one()

    def _avg(value) -> float | None:
        return round(float(value), 2) if value is not None else None

    aspects = StaffAspects(
        skill=_avg(aspect[0]),
        cleanliness=_avg(aspect[1]),
        punctuality=_avg(aspect[2]),
        value=_avg(aspect[3]),
    )

    # ---------- ลูกค้ากลับมาหาซ้ำกี่เปอร์เซ็นต์ ----------
    # ตัวเลขที่บอกคุณภาพได้ตรงที่สุด — คนพอใจเท่านั้นที่กลับมาหาคนเดิม
    #
    # นับเป็น "ลูกค้าที่มาหาช่างคนนี้ตั้งแต่ 2 ครั้งขึ้นไป หารด้วยลูกค้าทั้งหมด"
    # ไม่นับคิวที่เจ้าของร้านจองแทนให้ (user_id เป็น NULL) เพราะแยกคนไม่ออก
    per_customer = (
        select(Booking.user_id, func.count(Booking.id).label("n"))
        .where(
            Booking.staff_id == staff_id,
            Booking.status == "completed",
            Booking.user_id.isnot(None),
        )
        .group_by(Booking.user_id)
        .subquery()
    )
    counts = db.execute(
        select(
            func.count(),
            func.sum(case((per_customer.c.n > 1, 1), else_=0)),
        ).select_from(per_customer)
    ).one()

    total_customers = int(counts[0] or 0)
    repeat_customers = int(counts[1] or 0)
    # ต่ำกว่า 5 คนยังไม่พอจะสรุปอะไร — 1 ใน 2 คนคือ 50% ซึ่งทำให้เข้าใจผิด
    repeat_rate = (
        round(repeat_customers * 100 / total_customers)
        if total_customers >= 5
        else None
    )

    # ---------- อยู่กับร้านมานานแค่ไหน ----------
    months = None
    if member.created_at is not None:
        days = (datetime.now(timezone.utc) - member.created_at).days
        months = max(days // 30, 0)

    return StaffDetail(
        **StaffOut.model_validate(member).model_dump(),
        shop_name=shop.name if shop else "—",
        jobs_done=jobs_done,
        top_services=top_services,
        aspects=aspects,
        total_customers=total_customers,
        repeat_rate=repeat_rate,
        months_with_shop=months,
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
