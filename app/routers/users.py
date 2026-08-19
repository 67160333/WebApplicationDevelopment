"""2) User Management — จัดการข้อมูลผู้ใช้"""

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.schemas import Message, Page, UserOut, UsernameAvailable, UserUpdate
from app.security import get_current_user, require_roles

router = APIRouter(prefix="/api/users", tags=["2. User Management"])


@router.get("/me", response_model=UserOut, summary="ดึงข้อมูลตัวเอง")
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.get(
    "/check-username/{name}",
    response_model=UsernameAvailable,
    summary="ตรวจสอบว่าชื่อผู้ใช้ว่างไหม",
)
def check_username(name: str = Path(..., min_length=3, max_length=50), db: Session = Depends(get_db)):
    """ใช้ตอนกรอกฟอร์มสมัคร เพื่อบอกผู้ใช้ทันทีว่าชื่อนี้ใช้ได้หรือไม่"""
    taken = db.scalar(select(User).where(User.username == name))
    return UsernameAvailable(username=name, available=taken is None)


@router.get(
    "",
    response_model=Page[UserOut],
    summary="ดึงข้อมูล user ทั้งหมด (แบ่งหน้า)",
    dependencies=[Depends(require_roles("admin"))],
)
def list_users(
    page: int = Query(1, ge=1, description="หน้าที่ต้องการ"),
    limit: int = Query(10, ge=1, le=100, description="จำนวนต่อหน้า"),
    search: str | None = Query(None, description="ค้นหาจาก username / email / ชื่อ"),
    role: str | None = Query(None, pattern="^(customer|owner|admin)$"),
    db: Session = Depends(get_db),
):
    """เฉพาะผู้ดูแลระบบ (admin) เท่านั้น"""
    stmt = select(User)
    if search:
        kw = f"%{search}%"
        stmt = stmt.where(
            or_(User.username.ilike(kw), User.email.ilike(kw), User.full_name.ilike(kw))
        )
    if role:
        stmt = stmt.where(User.role == role)

    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(
        stmt.order_by(User.id.desc()).offset((page - 1) * limit).limit(limit)
    ).all()

    return Page[UserOut](
        items=list(rows),
        page=page,
        limit=limit,
        total=total,
        total_pages=(total + limit - 1) // limit,
    )


@router.get("/{user_id}", response_model=UserOut, summary="ดึงข้อมูล user รายคน")
def get_user(
    user_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """ดูได้เฉพาะข้อมูลของตัวเอง — admin ดูได้ทุกคน

    เดิมเส้นนี้ขอแค่ "ล็อกอินแล้ว" ไม่ได้เทียบว่าเป็นเจ้าของข้อมูลหรือไม่
    บัญชีลูกค้าบัญชีเดียวจึงไล่ยิง /api/users/1..N ดูดอีเมลกับเบอร์โทร
    ของผู้ใช้ทุกคนในระบบได้ ทำให้ด่านที่ล็อก GET /api/users ไว้ให้ admin
    ไม่มีความหมายเลย
    """
    if user_id != current_user.id and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="คุณดูได้เฉพาะข้อมูลของตัวเองเท่านั้น",
        )

    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ไม่พบผู้ใช้งานนี้")
    return user


@router.put("/{user_id}", response_model=UserOut, summary="แก้ไขข้อมูล user")
def update_user(
    payload: UserUpdate,
    user_id: int = Path(..., ge=1),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """แก้ไขได้เฉพาะข้อมูลของตัวเอง ยกเว้น admin ที่แก้ของใครก็ได้"""
    is_admin = current_user.role == "admin"
    if user_id != current_user.id and not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="คุณแก้ไขได้เฉพาะข้อมูลของตัวเองเท่านั้น",
        )

    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ไม่พบผู้ใช้งานนี้")

    data = payload.model_dump(exclude_unset=True)

    # role และ is_active เปลี่ยนได้เฉพาะ admin
    for admin_only in ("role", "is_active"):
        if admin_only in data and not is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"เฉพาะผู้ดูแลระบบเท่านั้นที่แก้ไข {admin_only} ได้",
            )

    if "email" in data:
        dup = db.scalar(select(User).where(User.email == data["email"], User.id != user_id))
        if dup is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="อีเมลนี้ถูกใช้แล้ว")

    if not data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="ไม่มีข้อมูลที่ต้องการแก้ไข"
        )

    for key, value in data.items():
        setattr(user, key, value)

    db.commit()
    db.refresh(user)
    return user


@router.delete(
    "/{user_id}",
    response_model=Message,
    summary="ลบ user",
)
def delete_user(
    user_id: int = Path(..., ge=1),
    current_user: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    """เฉพาะ admin — และห้ามลบบัญชีของตัวเอง"""
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="ไม่สามารถลบบัญชีของตัวเองได้"
        )

    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ไม่พบผู้ใช้งานนี้")

    db.delete(user)
    db.commit()
    return Message(message="ลบผู้ใช้งานสำเร็จ")
