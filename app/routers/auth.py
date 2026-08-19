"""1) Authentication — สมัครสมาชิก / เข้าสู่ระบบ / ออกจากระบบ / เปลี่ยนรหัสผ่าน"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import TokenBlacklist, User
from app.schemas import (
    ChangePasswordRequest,
    LoginRequest,
    Message,
    RegisterRequest,
    TokenResponse,
)
from app.security import (
    create_access_token,
    decode_token,
    get_current_user,
    hash_password,
    verify_password,
)

router = APIRouter(prefix="/api/auth", tags=["1. Authentication"])


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="สมัครสมาชิก",
)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    """สร้างบัญชีผู้ใช้ใหม่ แล้วคืน token ให้ใช้งานได้ทันที"""
    exists = db.scalar(
        select(User).where(or_(User.username == payload.username, User.email == payload.email))
    )
    if exists is not None:
        field = "ชื่อผู้ใช้" if exists.username == payload.username else "อีเมล"
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"{field}นี้ถูกใช้แล้ว")

    user = User(
        username=payload.username,
        email=payload.email,
        password_hash=hash_password(payload.password),
        full_name=payload.full_name,
        phone=payload.phone,
        role=payload.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return TokenResponse(access_token=create_access_token(user), user=user)


@router.post("/login", response_model=TokenResponse, summary="เข้าสู่ระบบ")
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    """เข้าสู่ระบบด้วย username หรือ email ก็ได้"""
    user = db.scalar(
        select(User).where(or_(User.username == payload.username, User.email == payload.username))
    )
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง",
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="บัญชีนี้ถูกระงับการใช้งาน")

    return TokenResponse(access_token=create_access_token(user), user=user)


@router.post("/logout", response_model=Message, summary="ออกจากระบบ")
def logout(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """เก็บ token ปัจจุบันเข้า blacklist ทำให้นำกลับมาใช้ไม่ได้อีก"""
    token = current_user._token  # type: ignore[attr-defined]
    payload = decode_token(token)

    db.add(
        TokenBlacklist(
            token=token,
            user_id=current_user.id,
            expires_at=datetime.fromtimestamp(payload["exp"], tz=timezone.utc),
        )
    )
    # ลบ token ที่หมดอายุแล้วทิ้ง ไม่ให้ตารางบวม
    db.query(TokenBlacklist).filter(
        TokenBlacklist.expires_at < datetime.now(timezone.utc)
    ).delete()
    db.commit()

    return Message(message="ออกจากระบบสำเร็จ")


@router.post("/change-password", response_model=Message, summary="เปลี่ยนรหัสผ่าน")
def change_password(
    payload: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """เปลี่ยนรหัสผ่าน แล้วยกเลิก token เดิมเพื่อความปลอดภัย"""
    if not verify_password(payload.old_password, current_user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="รหัสผ่านเดิมไม่ถูกต้อง")
    if payload.old_password == payload.new_password:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="รหัสผ่านใหม่ต้องไม่ซ้ำกับรหัสเดิม",
        )

    current_user.password_hash = hash_password(payload.new_password)

    token = current_user._token  # type: ignore[attr-defined]
    db.add(
        TokenBlacklist(
            token=token,
            user_id=current_user.id,
            expires_at=datetime.fromtimestamp(decode_token(token)["exp"], tz=timezone.utc),
        )
    )
    db.commit()

    return Message(message="เปลี่ยนรหัสผ่านสำเร็จ กรุณาเข้าสู่ระบบใหม่")
