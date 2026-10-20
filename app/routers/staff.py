"""5) Staff Profiles — โปรไฟล์ช่าง รีวิวของช่าง และบัญชีของตัวช่างเอง

แยกออกมาจาก shops.py เพราะฝั่งลูกค้าจะ "เลือกช่างก่อน แล้วค่อยเลือกร้าน" ก็ได้
เช่น เคยทำกับช่างมิ้นแล้วชอบ ก็อยากดูว่าช่างมิ้นว่างวันไหน คะแนนเท่าไร

บัญชีพนักงาน
------------------------------------------------------------------
เจ้าของร้านผูกโปรไฟล์ช่างเข้ากับบัญชีผู้ใช้ของตัวช่าง (กรอกชื่อผู้ใช้หรืออีเมล)
พอผูกแล้วช่างล็อกอินด้วยบัญชีตัวเองได้ และทำได้ 3 อย่าง
    1. แก้ประวัติ ความถนัด และจำนวนปีประสบการณ์ของตัวเอง
    2. เปลี่ยนรูปโปรไฟล์ของตัวเอง
    3. ดูคิวที่ลูกค้าจองกับตัวเอง (ไม่เห็นเรื่องเงิน)
ส่วนชื่อ ตำแหน่ง และเวลาทำงานยังเป็นเรื่องของร้าน ช่างแก้เองไม่ได้

ไม่ได้เพิ่ม role ใหม่ — ใครจะเป็นช่างดูจาก staff.user_id ล้วน ๆ
ลูกค้าคนหนึ่งจึงเป็นช่างที่ร้านหนึ่งไปพร้อมกับจองบริการร้านอื่นได้ตามปกติ
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

from datetime import date

from sqlalchemy import or_

from app.database import get_db
from app.models import Booking, Category, Review, Service, Shop, Staff, StaffLeave, User
from app.routers.notifications import notify
from app.schemas import (
    Message,
    MyStaffProfile,
    Page,
    ReviewOut,
    ServiceOut,
    StaffAccountOut,
    StaffAspects,
    StaffDetail,
    StaffLeaveCreate,
    StaffLeaveOut,
    StaffLink,
    StaffOut,
    StaffQueueItem,
    StaffSelfUpdate,
    StaffService,
)
from app.security import get_current_user
from app.storage import UploadError, process_shop_image

router = APIRouter(prefix="/api", tags=["5. Staff Profiles"])


def _get_staff_or_404(db: Session, staff_id: int) -> Staff:
    member = db.get(Staff, staff_id)
    if member is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ไม่พบช่างคนนี้")
    return member


def _staff_fields(member: Staff) -> dict:
    """ค่าของทุกช่องใน StaffOut อ่านตรงจากแถวในฐานข้อมูล

    ห้ามใช้ StaffOut.model_validate(member).model_dump() แทน
    เพราะ model_dump ตัดช่องที่ตั้ง exclude=True ทิ้ง (photo_name, user_id)
    พอเอาไปสร้าง StaffDetail ต่อ photo_url จะเป็น null เสมอ ทั้งที่ช่างมีรูป
    — เคยเป็นบักจริง โปรไฟล์ช่างไม่เคยแสดงรูปเลยสักครั้ง
    """
    return {name: getattr(member, name) for name in StaffOut.model_fields}


def _is_shop_owner(db: Session, member: Staff, user: User) -> bool:
    shop = db.get(Shop, member.shop_id)
    return user.role == "admin" or (shop is not None and shop.owner_id == user.id)


def _ensure_shop_owner(db: Session, member: Staff, user: User) -> None:
    if not _is_shop_owner(db, member, user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="คุณไม่ใช่เจ้าของร้านนี้")


def _ensure_can_edit_profile(db: Session, member: Staff, user: User) -> None:
    """แก้โปรไฟล์ได้สามคน: เจ้าของร้าน ผู้ดูแลระบบ และตัวช่างเองที่ผูกบัญชีไว้"""
    if member.user_id == user.id:
        return
    _ensure_shop_owner(db, member, user)


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
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    member = _get_staff_or_404(db, staff_id)
    _ensure_can_edit_profile(db, member, current_user)

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
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    member = _get_staff_or_404(db, staff_id)
    _ensure_can_edit_profile(db, member, current_user)

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
        created = member.created_at
        # PostgreSQL คืนเวลาที่มี timezone แต่ SQLite (ที่ชุดทดสอบใช้) คืนแบบไม่มี
        # เอาเวลาที่มีกับไม่มี timezone มาลบกันตรง ๆ Python จะโยน TypeError ทันที
        # จึงเติม UTC ให้ก่อนถ้ายังไม่มี — ค่าในตารางบันทึกเป็น UTC อยู่แล้ว (ดู now_utc)
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        days = (datetime.now(timezone.utc) - created).days
        months = max(days // 30, 0)

    # บริการของร้านที่จองกับช่างคนนี้ได้ — ให้หน้าโปรไฟล์มีปุ่มจองตรงจากหน้านั้นเลย
    services = []
    label = "ช่าง"
    if shop is not None:
        services = [
            ServiceOut.model_validate(x)
            for x in db.scalars(
                select(Service)
                .where(Service.shop_id == shop.id, Service.is_active.is_(True))
                .order_by(Service.price)
            ).all()
        ]
        category = db.get(Category, shop.category_id) if shop.category_id else None
        label = (category.resource_label if category else None) or "ช่าง"

    return StaffDetail(
        **_staff_fields(member),
        shop_name=shop.name if shop else "-",
        shop_district=shop.district if shop else None,
        shop_province=shop.province if shop else None,
        resource_label=label,
        services=services,
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


# ============================================================
# บัญชีพนักงาน — ฝั่งเจ้าของร้าน
# ============================================================
@router.get(
    "/staff/{staff_id}/account",
    response_model=StaffAccountOut,
    summary="ดูว่าโปรไฟล์ช่างผูกกับบัญชีไหน (เจ้าของร้าน)",
)
def get_staff_account(
    staff_id: int = Path(..., ge=1),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    member = _get_staff_or_404(db, staff_id)
    _ensure_shop_owner(db, member, current_user)
    user = db.get(User, member.user_id) if member.user_id else None
    return StaffAccountOut(
        staff_id=member.id,
        username=user.username if user else None,
        full_name=user.full_name if user else None,
    )


@router.put(
    "/staff/{staff_id}/account",
    response_model=StaffAccountOut,
    summary="ผูกโปรไฟล์ช่างกับบัญชีผู้ใช้ของตัวช่าง (เจ้าของร้าน)",
)
def link_staff_account(
    payload: StaffLink,
    staff_id: int = Path(..., ge=1),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    member = _get_staff_or_404(db, staff_id)
    _ensure_shop_owner(db, member, current_user)

    login = payload.login.strip()
    user = db.scalar(select(User).where(or_(User.username == login, User.email == login)))
    # ข้อความเดียวกันทั้ง "ไม่มีบัญชีนี้" และ "บัญชีถูกระงับ" กันการไล่เดาว่าใครมีบัญชีบ้าง
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="ไม่พบบัญชีนี้ ให้ช่างสมัครสมาชิกก่อน แล้วส่งชื่อผู้ใช้มาให้ร้าน",
        )
    # ผู้ดูแลระบบห้ามเป็นช่าง — บัญชีที่มีสิทธิ์สูงสุดไม่ควรถูกผูกกับร้านใดร้านหนึ่ง
    if user.role == "admin":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ผูกกับบัญชีผู้ดูแลระบบไม่ได้")
    # คนเดียวมีโปรไฟล์ช่างในร้านเดียวกันได้ใบเดียว ไม่งั้นคิวของตัวเองจะแยกเป็นสองชุด
    dup = db.scalar(
        select(Staff.id).where(
            Staff.shop_id == member.shop_id, Staff.user_id == user.id, Staff.id != member.id
        )
    )
    if dup is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="บัญชีนี้ผูกกับช่างอีกคนในร้านนี้อยู่แล้ว",
        )

    member.user_id = user.id
    shop = db.get(Shop, member.shop_id)
    notify(
        db, user.id, "staff_linked",
        f"ร้าน {shop.name if shop else ''} เพิ่มคุณเป็น{member.position or 'ผู้ให้บริการ'}",
        "แก้โปรไฟล์และดูคิวของตัวเองได้ที่หน้าบัญชีของฉัน",
        "profile.html",
    )
    db.commit()
    return StaffAccountOut(staff_id=member.id, username=user.username, full_name=user.full_name)


@router.delete(
    "/staff/{staff_id}/account",
    response_model=Message,
    summary="ยกเลิกการผูกบัญชี (เจ้าของร้าน หรือตัวช่างเอง)",
)
def unlink_staff_account(
    staff_id: int = Path(..., ge=1),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    member = _get_staff_or_404(db, staff_id)
    # ช่างถอนตัวเองได้ — เช่นลาออกแล้วร้านลืมถอดออก ไม่ควรต้องรอร้าน
    if member.user_id != current_user.id:
        _ensure_shop_owner(db, member, current_user)
    if member.user_id is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="โปรไฟล์นี้ยังไม่ได้ผูกบัญชี")
    member.user_id = None
    db.commit()
    return Message(message="ยกเลิกการผูกบัญชีแล้ว")


# ============================================================
# บัญชีพนักงาน — ฝั่งตัวช่างเอง
# ============================================================
def _my_member(db: Session, staff_id: int, user: User) -> Staff:
    member = _get_staff_or_404(db, staff_id)
    if member.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="นี่ไม่ใช่โปรไฟล์ของคุณ")
    return member


@router.get("/me/staff", response_model=list[MyStaffProfile], summary="โปรไฟล์ช่างของฉัน")
def my_staff_profiles(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rows = db.scalars(select(Staff).where(Staff.user_id == current_user.id).order_by(Staff.id)).all()
    out = []
    for m in rows:
        shop = db.get(Shop, m.shop_id)
        out.append(MyStaffProfile(**_staff_fields(m), shop_name=shop.name if shop else "-"))
    return out


@router.put("/me/staff/{staff_id}", response_model=StaffOut, summary="แก้โปรไฟล์ช่างของฉัน")
def update_my_staff_profile(
    payload: StaffSelfUpdate,
    staff_id: int = Path(..., ge=1),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    member = _my_member(db, staff_id, current_user)
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        # ส่งข้อความว่างมา = ต้องการลบช่องนั้นทิ้ง
        if isinstance(value, str):
            value = value.strip() or None
        setattr(member, key, value)
    db.commit()
    db.refresh(member)
    return member


@router.get(
    "/me/staff/{staff_id}/queue",
    response_model=list[StaffQueueItem],
    summary="คิวของฉันที่ยังมาไม่ถึง",
)
def my_staff_queue(
    staff_id: int = Path(..., ge=1),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """คิวที่ลูกค้าเลือกช่างคนนี้ ตั้งแต่วันนี้เป็นต้นไป

    ช่างต้องเห็นสิ่งที่ลูกค้าแจ้ง (ความต้องการ ข้อมูลสุขภาพ) เพื่อเตรียมงานได้ถูก
    แต่ไม่ต้องเห็นเบอร์โทร นามสกุลเต็ม หรือยอดเงิน ซึ่งเป็นเรื่องของร้าน
    """
    member = _my_member(db, staff_id, current_user)
    from app.routers.bookings import _is_demo_email, _short_name
    from app.seed_extra import DEMO_OWNER_USERNAMES

    rows = db.scalars(
        select(Booking)
        .where(
            Booking.staff_id == member.id,
            Booking.booking_date >= date.today(),
            Booking.status.in_(["pending", "confirmed"]),
        )
        .order_by(Booking.booking_date, Booking.booking_time)
        .limit(50)
    ).all()

    # ร้านตัวอย่างประกาศรหัสไว้ให้ทดลอง ใครก็ผูกบัญชีตัวเองเป็นช่างของร้านตัวอย่างได้
    # จึงต้องซ่อนข้อมูลของลูกค้าจริงแบบเดียวกับหน้าจัดการร้าน
    shop = db.get(Shop, member.shop_id)
    owner = db.get(User, shop.owner_id) if shop else None
    demo_shop = owner is not None and owner.username in DEMO_OWNER_USERNAMES

    out = []
    for b in rows:
        customer = db.get(User, b.user_id)
        hide = demo_shop and not _is_demo_email(customer.email if customer else None)
        service = db.get(Service, b.service_id)
        out.append(StaffQueueItem(
            booking_id=b.id,
            booking_code=b.booking_code,
            booking_date=b.booking_date,
            booking_time=b.booking_time,
            end_time=b.end_time,
            status=b.status,
            service_name=service.name if service else "-",
            customer_name=b.guest_name or _short_name(customer.full_name if customer else None),
            requirements=None if hide else b.requirements,
            health_note=None if hide else b.health_note,
            note="ซ่อนข้อมูลลูกค้าจริงจากบัญชีทดลอง" if hide else b.note,
        ))
    return out


# ============================================================
# ปฏิทินช่าง — วันลา / ปิดรับคิวรายวัน
# ============================================================
# ใครแก้ได้: เจ้าของร้าน ผู้ดูแลระบบ และตัวช่างเองที่ผูกบัญชีไว้ (กติกาเดียวกับแก้โปรไฟล์)
# ผลต่อการจอง: bookings._staff_works_on ตรวจตารางนี้ด้วย วันที่ลาจึงปิดเองในทุกหน้า
# ทั้งหน้าดูคิวว่าง การจอง การเลื่อนนัด ผังทรัพยากร และการนับความจุของร้าน
@router.get(
    "/staff/{staff_id}/leaves",
    response_model=list[StaffLeaveOut],
    summary="ดูวันลาของช่าง (เจ้าของร้าน / ตัวช่าง)",
)
def list_staff_leaves(
    staff_id: int = Path(..., ge=1),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """เฉพาะวันนี้เป็นต้นไป — เหตุผลการลาเป็นเรื่องภายในร้าน ลูกค้าไม่ต้องเห็น"""
    member = _get_staff_or_404(db, staff_id)
    _ensure_can_edit_profile(db, member, current_user)
    return list(db.scalars(
        select(StaffLeave)
        .where(StaffLeave.staff_id == staff_id, StaffLeave.leave_date >= date.today())
        .order_by(StaffLeave.leave_date)
    ).all())


@router.post(
    "/staff/{staff_id}/leaves",
    response_model=StaffLeaveOut,
    status_code=status.HTTP_201_CREATED,
    summary="บันทึกวันลาของช่าง",
)
def create_staff_leave(
    payload: StaffLeaveCreate,
    staff_id: int = Path(..., ge=1),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    member = _get_staff_or_404(db, staff_id)
    _ensure_can_edit_profile(db, member, current_user)

    if payload.leave_date < date.today():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="เลือกวันย้อนหลังไม่ได้"
        )
    exists = db.scalar(
        select(StaffLeave.id).where(
            StaffLeave.staff_id == staff_id, StaffLeave.leave_date == payload.leave_date
        )
    )
    if exists is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="บันทึกวันนี้ไว้แล้ว")

    # มีลูกค้าจองช่างคนนี้วันนั้นอยู่แล้ว ห้ามลาทับเงียบ ๆ
    # ไม่งั้นลูกค้ามาถึงร้านแล้วไม่เจอช่าง — ร้านต้องย้ายช่างหรือเลื่อนนัดให้ลูกค้าก่อน
    booked = db.scalar(
        select(func.count(Booking.id)).where(
            Booking.staff_id == staff_id,
            Booking.booking_date == payload.leave_date,
            Booking.status.in_(("pending", "confirmed")),
        )
    ) or 0
    if booked:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"วันนั้นมีลูกค้าจอง{member.name}ไว้ {booked} คิว "
                   "ต้องเลื่อนนัดหรือเปลี่ยนช่างให้ลูกค้าก่อนถึงจะลาได้",
        )

    row = StaffLeave(staff_id=staff_id, leave_date=payload.leave_date, reason=payload.reason)
    db.add(row)

    # ช่างลาเอง ต้องให้เจ้าของร้านรู้ จะได้วางคนแทน
    shop = db.get(Shop, member.shop_id)
    if shop is not None and member.user_id == current_user.id and shop.owner_id != current_user.id:
        notify(
            db, shop.owner_id, "staff_leave",
            f"{member.name} ลางาน {payload.leave_date.strftime('%d/%m/%Y')}",
            payload.reason or "ระบบปิดรับคิวของช่างคนนี้ในวันนั้นแล้ว",
            "manage.html",
        )
    db.commit()
    db.refresh(row)
    return row


@router.delete(
    "/staff/leaves/{leave_id}",
    response_model=Message,
    summary="ยกเลิกวันลา (เปิดรับคิวอีกครั้ง)",
)
def delete_staff_leave(
    leave_id: int = Path(..., ge=1),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    row = db.get(StaffLeave, leave_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ไม่พบรายการนี้")
    member = _get_staff_or_404(db, row.staff_id)
    _ensure_can_edit_profile(db, member, current_user)
    db.delete(row)
    db.commit()
    return Message(message="เปิดรับคิววันนั้นอีกครั้งแล้ว")
