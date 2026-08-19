"""3) Shops & Services — หมวดหมู่ ร้าน และบริการของร้าน"""

from decimal import Decimal

from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models import Category, Service, Shop, ShopClosure, ShopImage, Staff, User
from app.schemas import (
    CategoryOut,
    Message,
    Page,
    ServiceCreate,
    ServiceOut,
    ServiceUpdate,
    ShopCreate,
    ShopDetail,
    ShopImageOut,
    ShopOut,
    ShopUpdate,
    ClosureCreate,
    ClosureOut,
    StaffCreate,
    StaffOut,
    StaffUpdate,
)
from app.security import require_roles
from app.storage import delete_shop_folder

router = APIRouter(prefix="/api", tags=["3. Shops & Services"])

# รัศมีเฉลี่ยของโลกเป็นกิโลเมตร ใช้ในสูตร haversine
EARTH_RADIUS_KM = 6371.0


def _get_shop_or_404(db: Session, shop_id: int) -> Shop:
    shop = db.get(Shop, shop_id)
    if shop is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ไม่พบร้านนี้")
    return shop


def _cover_map(db: Session, shop_ids: list[int]) -> dict[int, str]:
    """ดึงรูปปกของหลายร้านในคำสั่งเดียว

    ถ้าวนดึงทีละร้านจะกลายเป็น N+1 query — หน้าค้นหาที่แสดง 12 ร้าน
    จะยิงฐานข้อมูล 13 ครั้งแทนที่จะเป็น 2 ครั้ง
    """
    if not shop_ids:
        return {}
    rows = db.execute(
        select(ShopImage.shop_id, ShopImage.filename).where(
            ShopImage.shop_id.in_(shop_ids), ShopImage.is_cover.is_(True)
        )
    ).all()
    return {sid: f"/uploads/shops/{sid}/{fn}" for sid, fn in rows}


def _label_map(db: Session) -> dict[int, tuple[str, str]]:
    """หมวดหมู่ทั้งหมด -> (คำเรียกทรัพยากร, slug) — ดึงทีเดียวแล้วใช้ซ้ำ"""
    return {
        c.id: (c.resource_label or "ช่าง", c.slug)
        for c in db.scalars(select(Category)).all()
    }


def _to_out(
    db: Session, rows: list[Shop], distances: dict[int, float] | None = None
) -> list[ShopOut]:
    """แปลง Shop เป็น ShopOut พร้อมเติมรูปปก ระยะทาง และคำเรียกทรัพยากร"""
    covers = _cover_map(db, [s.id for s in rows])
    labels = _label_map(db)
    out: list[ShopOut] = []
    for shop in rows:
        item = ShopOut.model_validate(shop)
        item.cover_url = covers.get(shop.id)
        item.resource_label, item.category_slug = labels.get(shop.category_id, ("ช่าง", None))
        if distances is not None:
            item.distance_km = distances.get(shop.id)
        out.append(item)
    return out


def _distance_km(lat: float, lng: float):
    """นิพจน์ SQL คำนวณระยะทางบนผิวโลกด้วยสูตร haversine

    ให้ฐานข้อมูลคำนวณและเรียงลำดับให้ จะได้ไม่ต้องดึงร้านทั้งหมดมาคำนวณในโค้ด

    หมายเหตุสำคัญ: ต้องบีบค่าที่ส่งเข้า acos ให้อยู่ในช่วง -1 ถึง 1 ก่อน
    เพราะความคลาดเคลื่อนของทศนิยมอาจทำให้ได้ 1.0000000002
    แล้ว acos จะโยน error ทันที (เจอบ่อยตอนพิกัดตรงกันเป๊ะ)
    """
    lat_rad = func.radians(lat)
    shop_lat = func.radians(Shop.latitude)
    shop_lng = func.radians(Shop.longitude)
    cosine = (
        func.cos(lat_rad) * func.cos(shop_lat) * func.cos(shop_lng - func.radians(lng))
        + func.sin(lat_rad) * func.sin(shop_lat)
    )
    return EARTH_RADIUS_KM * func.acos(func.least(1.0, func.greatest(-1.0, cosine)))


def _has_free_slot(db: Session, shop: Shop, on_date: date) -> bool:
    """ร้านนี้ยังมีคิวว่างอย่างน้อย 1 ช่องในวันที่ระบุหรือไม่

    ใช้ตรรกะชุดเดียวกับหน้าจองจริง (ดู bookings.py) เพื่อไม่ให้ผลลัพธ์ขัดกัน
    คืน True ทันทีที่เจอช่องว่างช่องแรก จึงไม่ต้องไล่ทั้งวัน
    """
    # import ในฟังก์ชันเพื่อเลี่ยง circular import ระหว่างสอง router
    from app.routers.bookings import (
        SLOT_STEP_MINUTES,
        _busy_intervals,
        _closure_reason,
        _shop_capacity,
        _slot_is_taken,
        _windows_for,
        now_local,
    )

    if _closure_reason(db, shop.id, on_date):
        return False

    # บริการแบบเรียกใช้ทันที (ส่งของด่วน) ไม่มีตารางช่องเวลา จึงไม่นับในตัวกรองนี้
    services = [sv for sv in shop.services if sv.is_active and sv.booking_mode == "scheduled"]
    if not services:
        return False

    # ใช้บริการที่สั้นที่สุด เพราะถ้าอันสั้นสุดยังไม่ว่าง อันอื่นก็ไม่ว่างแน่
    duration = min(sv.duration_minutes for sv in services)

    now = now_local()
    if on_date < now.date():
        return False

    busy = _busy_intervals(db, shop.id, on_date, None)
    capacity = _shop_capacity(db, shop.id, on_date)
    # วันนั้นไม่มีผู้ให้บริการเข้างานเลย ก็ไม่ต้องไล่ช่องเวลาให้เสียเวลา
    if capacity == 0:
        return False
    now_m = now.hour * 60 + now.minute if on_date == now.date() else -1

    # ต้องใช้ตรรกะช่วงเวลาชุดเดียวกับหน้าจอง ไม่งั้นตัวกรอง "ว่างวันนี้"
    # จะตัดสนามที่เปิดคร่อมเที่ยงคืนหรือเปิด 24 ชั่วโมงทิ้งทั้งที่ยังว่างจริง
    for seg_start, seg_end in _windows_for(shop, None):
        start = seg_start
        while start + duration <= seg_end:
            if start > now_m and not _slot_is_taken(start, start + duration, busy, capacity):
                return True
            start += SLOT_STEP_MINUTES
    return False


def _ensure_owner(shop: Shop, user: User) -> None:
    """ตรวจว่าเป็นเจ้าของร้านจริง (admin ผ่านได้ทุกร้าน)"""
    if shop.owner_id != user.id and user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="คุณไม่ใช่เจ้าของร้านนี้")


# ---------------- หมวดหมู่ ----------------
@router.get("/categories", response_model=list[CategoryOut], summary="ดึงหมวดหมู่บริการทั้งหมด")
def list_categories(db: Session = Depends(get_db)):
    return list(db.scalars(select(Category).order_by(Category.id)).all())


# ---------------- ร้าน ----------------
@router.get("/shops", response_model=Page[ShopOut], summary="ค้นหาร้าน (แบ่งหน้า + กรอง)")
def list_shops(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    search: str | None = Query(None, description="ค้นหาจากชื่อร้านหรือคำอธิบาย"),
    category_id: int | None = Query(None, ge=1),
    district: str | None = Query(None, description="เขต/อำเภอ"),
    min_rating: float | None = Query(None, ge=0, le=5, description="คะแนนขั้นต่ำ"),
    certified: bool | None = Query(None, description="เฉพาะร้านที่ผ่านการรับรองความสะอาด"),
    available_on: date | None = Query(
        None, description="เอาเฉพาะร้านที่ยังมีคิวว่างในวันนี้ (YYYY-MM-DD)"
    ),
    near_lat: float | None = Query(
        None, ge=-90, le=90, description="ละติจูดของผู้ใช้ — ใส่คู่กับ near_lng เพื่อเรียงตามระยะทาง"
    ),
    near_lng: float | None = Query(None, ge=-180, le=180, description="ลองจิจูดของผู้ใช้"),
    radius_km: float = Query(
        20, gt=0, le=200, description="รัศมีการค้นหาเป็นกิโลเมตร (ใช้เมื่อระบุพิกัด)"
    ),
    db: Session = Depends(get_db),
):
    # พิกัดต้องมาเป็นคู่เสมอ ถ้าส่งมาแค่ตัวเดียวคำนวณระยะทางไม่ได้
    if (near_lat is None) != (near_lng is None):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="กรุณาระบุทั้ง near_lat และ near_lng คู่กัน",
        )

    stmt = select(Shop).where(Shop.is_active.is_(True))

    if search:
        kw = f"%{search}%"
        stmt = stmt.where(or_(Shop.name.ilike(kw), Shop.description.ilike(kw)))
    if category_id:
        stmt = stmt.where(Shop.category_id == category_id)
    if district:
        stmt = stmt.where(Shop.district == district)
    if min_rating is not None:
        stmt = stmt.where(Shop.rating_avg >= Decimal(str(min_rating)))
    if certified:
        stmt = stmt.where(Shop.is_certified.is_(True))

    # ---------- ค้นหาแบบ "ใกล้ฉัน" ----------
    if near_lat is not None and near_lng is not None:
        dist = _distance_km(near_lat, near_lng)
        geo = (
            stmt.add_columns(dist.label("km"))
            # ร้านที่ยังไม่ได้ปักหมุดคำนวณระยะทางไม่ได้ ต้องตัดออกก่อน
            .where(Shop.latitude.is_not(None), Shop.longitude.is_not(None))
            .where(dist <= radius_km)
            .order_by(dist)
        )
        found = db.execute(geo).all()

        # ผู้ใช้เลือก "ใกล้ฉัน" พร้อมกับ "ว่างวันนี้" ได้ ต้องกรองต่อให้ครบทั้งสองเงื่อนไข
        # ถ้าข้ามขั้นนี้ ผลลัพธ์จะรวมร้านที่คิวเต็มแล้วโดยที่ผู้ใช้ไม่รู้ตัว
        if available_on is not None:
            found = [row for row in found if _has_free_slot(db, row[0], available_on)]


        total = len(found)
        window = found[(page - 1) * limit : (page - 1) * limit + limit]
        shops = [row[0] for row in window]
        distances = {row[0].id: round(float(row[1]), 2) for row in window}

        return Page[ShopOut](
            items=_to_out(db, shops, distances),
            page=page,
            limit=limit,
            total=total,
            total_pages=(total + limit - 1) // limit,
        )

    # กรอง "ยังมีคิวว่างวันนี้" — ต้องคำนวณทีละร้าน จึงทำหลังกรองเงื่อนไขอื่นให้เหลือน้อยที่สุดก่อน
    if available_on is not None:
        # selectinload ดึงบริการของทุกร้านในคำสั่งเดียว
        # ถ้าไม่ใส่ _has_free_slot จะ lazy load shop.services ทีละร้าน
        # กลายเป็น N+1 query ที่โตตามจำนวนร้านทั้งระบบ ไม่ใช่ตามจำนวนที่แสดงต่อหน้า
        candidates = list(
            db.scalars(
                stmt.options(selectinload(Shop.services))
                .order_by(Shop.rating_avg.desc(), Shop.id.desc())
            ).all()
        )
        open_shops = [s for s in candidates if _has_free_slot(db, s, available_on)]

        total = len(open_shops)
        rows = open_shops[(page - 1) * limit : (page - 1) * limit + limit]
        return Page[ShopOut](
            items=_to_out(db, list(rows)),
            page=page,
            limit=limit,
            total=total,
            total_pages=(total + limit - 1) // limit,
        )

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(
        stmt.order_by(Shop.rating_avg.desc(), Shop.id.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    ).all()

    return Page[ShopOut](
        items=_to_out(db, list(rows)),
        page=page,
        limit=limit,
        total=total,
        total_pages=(total + limit - 1) // limit,
    )


@router.get("/shops/{shop_id}", response_model=ShopDetail, summary="รายละเอียดร้าน พร้อมบริการและช่าง")
def get_shop(shop_id: int = Path(..., ge=1), db: Session = Depends(get_db)):
    shop = _get_shop_or_404(db, shop_id)
    detail = ShopDetail.model_validate(shop)
    cat = db.get(Category, shop.category_id)
    detail.resource_label = (cat.resource_label if cat else None) or "ช่าง"
    detail.category_slug = cat.slug if cat else None
    detail.services = [ServiceOut.model_validate(s) for s in shop.services if s.is_active]
    detail.staff = [StaffOut.model_validate(st) for st in shop.staff_members if st.is_active]
    # รูปปกมาก่อนเสมอ ที่เหลือเรียงตามลำดับที่เจ้าของร้านจัดไว้
    detail.images = sorted(
        (ShopImageOut.model_validate(im) for im in shop.images),
        key=lambda im: (not im.is_cover, im.sort_order, im.id),
    )
    detail.cover_url = next((im.url for im in detail.images if im.is_cover), None)
    return detail


@router.post(
    "/shops",
    response_model=ShopOut,
    status_code=status.HTTP_201_CREATED,
    summary="สร้างร้านใหม่ (owner/admin)",
)
def create_shop(
    payload: ShopCreate,
    current_user: User = Depends(require_roles("owner", "admin")),
    db: Session = Depends(get_db),
):
    if db.get(Category, payload.category_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ไม่พบหมวดหมู่ที่เลือก")

    shop = Shop(owner_id=current_user.id, **payload.model_dump())
    db.add(shop)
    db.commit()
    db.refresh(shop)
    return shop


@router.put("/shops/{shop_id}", response_model=ShopOut, summary="แก้ไขข้อมูลร้าน")
def update_shop(
    payload: ShopUpdate,
    shop_id: int = Path(..., ge=1),
    current_user: User = Depends(require_roles("owner", "admin")),
    db: Session = Depends(get_db),
):
    shop = _get_shop_or_404(db, shop_id)
    _ensure_owner(shop, current_user)

    data = payload.model_dump(exclude_unset=True)

    # ตรารับรองความสะอาด กำหนดได้เฉพาะ admin
    if "is_certified" in data and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="เฉพาะผู้ดูแลระบบเท่านั้นที่กำหนดการรับรองได้",
        )
    if not data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="ไม่มีข้อมูลที่ต้องการแก้ไข"
        )

    for key, value in data.items():
        setattr(shop, key, value)

    db.commit()
    db.refresh(shop)
    return shop


@router.delete("/shops/{shop_id}", response_model=Message, summary="ลบร้าน")
def delete_shop(
    shop_id: int = Path(..., ge=1),
    current_user: User = Depends(require_roles("owner", "admin")),
    db: Session = Depends(get_db),
):
    shop = _get_shop_or_404(db, shop_id)
    _ensure_owner(shop, current_user)
    db.delete(shop)
    db.commit()
    # ฐานข้อมูลลบแถวรูปให้เองด้วย CASCADE แต่ไฟล์บนดิสก์ต้องเก็บกวาดเอง
    # ทำหลัง commit เพราะถ้าลบไฟล์ก่อนแล้วฐานข้อมูลล้มเหลว รูปจะหายทั้งที่ร้านยังอยู่
    delete_shop_folder(shop_id)
    return Message(message="ลบร้านสำเร็จ")


# ---------------- บริการของร้าน ----------------
@router.get(
    "/shops/{shop_id}/services",
    response_model=list[ServiceOut],
    summary="ดูบริการทั้งหมดของร้าน",
)
def list_services(shop_id: int = Path(..., ge=1), db: Session = Depends(get_db)):
    _get_shop_or_404(db, shop_id)
    return list(
        db.scalars(select(Service).where(Service.shop_id == shop_id).order_by(Service.price)).all()
    )


@router.post(
    "/shops/{shop_id}/services",
    response_model=ServiceOut,
    status_code=status.HTTP_201_CREATED,
    summary="เพิ่มบริการให้ร้าน",
)
def create_service(
    payload: ServiceCreate,
    shop_id: int = Path(..., ge=1),
    current_user: User = Depends(require_roles("owner", "admin")),
    db: Session = Depends(get_db),
):
    shop = _get_shop_or_404(db, shop_id)
    _ensure_owner(shop, current_user)

    service = Service(shop_id=shop_id, **payload.model_dump())
    db.add(service)
    db.commit()
    db.refresh(service)
    return service


@router.put("/services/{service_id}", response_model=ServiceOut, summary="แก้ไขบริการ")
def update_service(
    payload: ServiceUpdate,
    service_id: int = Path(..., ge=1),
    current_user: User = Depends(require_roles("owner", "admin")),
    db: Session = Depends(get_db),
):
    service = db.get(Service, service_id)
    if service is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ไม่พบบริการนี้")
    _ensure_owner(service.shop, current_user)

    data = payload.model_dump(exclude_unset=True)
    if not data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="ไม่มีข้อมูลที่ต้องการแก้ไข"
        )

    for key, value in data.items():
        setattr(service, key, value)

    db.commit()
    db.refresh(service)
    return service


@router.delete("/services/{service_id}", response_model=Message, summary="ลบบริการ")
def delete_service(
    service_id: int = Path(..., ge=1),
    current_user: User = Depends(require_roles("owner", "admin")),
    db: Session = Depends(get_db),
):
    service = db.get(Service, service_id)
    if service is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ไม่พบบริการนี้")
    _ensure_owner(service.shop, current_user)

    db.delete(service)
    db.commit()
    return Message(message="ลบบริการสำเร็จ")


# ---------------- ช่าง / ผู้ให้บริการ ----------------
@router.get(
    "/shops/{shop_id}/staff",
    response_model=list[StaffOut],
    summary="ดูรายชื่อช่างของร้าน",
)
def list_staff(shop_id: int = Path(..., ge=1), db: Session = Depends(get_db)):
    _get_shop_or_404(db, shop_id)
    return list(
        db.scalars(select(Staff).where(Staff.shop_id == shop_id).order_by(Staff.id)).all()
    )


@router.post(
    "/shops/{shop_id}/staff",
    response_model=StaffOut,
    status_code=status.HTTP_201_CREATED,
    summary="เพิ่มช่างเข้าร้าน",
)
def create_staff(
    payload: StaffCreate,
    shop_id: int = Path(..., ge=1),
    current_user: User = Depends(require_roles("owner", "admin")),
    db: Session = Depends(get_db),
):
    shop = _get_shop_or_404(db, shop_id)
    _ensure_owner(shop, current_user)

    member = Staff(shop_id=shop_id, **payload.model_dump())
    db.add(member)
    db.commit()
    db.refresh(member)
    return member


@router.put("/staff/{staff_id}", response_model=StaffOut, summary="แก้ไขข้อมูลช่าง")
def update_staff(
    payload: StaffUpdate,
    staff_id: int = Path(..., ge=1),
    current_user: User = Depends(require_roles("owner", "admin")),
    db: Session = Depends(get_db),
):
    member = db.get(Staff, staff_id)
    if member is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ไม่พบช่างคนนี้")
    _ensure_owner(member.shop, current_user)

    data = payload.model_dump(exclude_unset=True)
    if not data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="ไม่มีข้อมูลที่ต้องการแก้ไข"
        )
    for key, value in data.items():
        setattr(member, key, value)

    db.commit()
    db.refresh(member)
    return member


@router.delete("/staff/{staff_id}", response_model=Message, summary="ลบช่าง")
def delete_staff(
    staff_id: int = Path(..., ge=1),
    current_user: User = Depends(require_roles("owner", "admin")),
    db: Session = Depends(get_db),
):
    member = db.get(Staff, staff_id)
    if member is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ไม่พบช่างคนนี้")
    _ensure_owner(member.shop, current_user)

    db.delete(member)
    db.commit()
    return Message(message="ลบช่างสำเร็จ")


# ---------------- วันหยุดพิเศษของร้าน ----------------
@router.get(
    "/shops/{shop_id}/closures",
    response_model=list[ClosureOut],
    summary="ดูวันที่ร้านปิดเป็นกรณีพิเศษ",
)
def list_closures(shop_id: int = Path(..., ge=1), db: Session = Depends(get_db)):
    """ลูกค้าดูได้ด้วย เพื่อให้หน้าจองรู้ล่วงหน้าว่าวันไหนกดไม่ได้"""
    if db.get(Shop, shop_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ไม่พบร้านนี้")

    # เอาเฉพาะตั้งแต่วันนี้เป็นต้นไป วันหยุดที่ผ่านมาแล้วไม่มีประโยชน์
    rows = db.scalars(
        select(ShopClosure)
        .where(ShopClosure.shop_id == shop_id, ShopClosure.closed_date >= date.today())
        .order_by(ShopClosure.closed_date)
    ).all()
    return list(rows)


@router.post(
    "/shops/{shop_id}/closures",
    response_model=ClosureOut,
    status_code=status.HTTP_201_CREATED,
    summary="ประกาศวันหยุดของร้าน",
)
def create_closure(
    payload: ClosureCreate,
    shop_id: int = Path(..., ge=1),
    current_user: User = Depends(require_roles("owner", "admin")),
    db: Session = Depends(get_db),
):
    """เพิ่มวันที่ร้านปิด — ระบบจะไม่เปิดให้จองในวันนั้นทันที"""
    shop = db.get(Shop, shop_id)
    if shop is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ไม่พบร้านนี้")
    _ensure_owner(shop, current_user)

    if payload.closed_date < date.today():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="เลือกวันย้อนหลังไม่ได้"
        )

    exists = db.scalar(
        select(ShopClosure).where(
            ShopClosure.shop_id == shop_id, ShopClosure.closed_date == payload.closed_date
        )
    )
    if exists is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="บันทึกวันนี้ไว้แล้ว")

    row = ShopClosure(shop_id=shop_id, closed_date=payload.closed_date, reason=payload.reason)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.delete(
    "/closures/{closure_id}",
    response_model=Message,
    summary="ยกเลิกวันหยุดที่ประกาศไว้",
)
def delete_closure(
    closure_id: int = Path(..., ge=1),
    current_user: User = Depends(require_roles("owner", "admin")),
    db: Session = Depends(get_db),
):
    row = db.get(ShopClosure, closure_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ไม่พบรายการนี้")
    _ensure_owner(row.shop, current_user)

    db.delete(row)
    db.commit()
    return Message(message="เปิดรับจองวันดังกล่าวอีกครั้งแล้ว")
