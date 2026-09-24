"""1) Authentication — สมัครสมาชิก / เข้าสู่ระบบ / ออกจากระบบ / เปลี่ยนรหัสผ่าน"""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.mailer import reset_password_email, send_email
from app.models import PasswordResetToken, TokenBlacklist, User
from app.schemas import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    Message,
    RegisterRequest,
    ResetPasswordRequest,
    TokenResponse,
)
from app.security import (
    REGISTER_MAX_PER_IP,
    check_login_allowed,
    clear_login_fails,
    create_access_token,
    decode_token,
    get_current_user,
    hash_password,
    record_login_fail,
    verify_password,
)

router = APIRouter(prefix="/api/auth", tags=["1. Authentication"])


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="สมัครสมาชิก",
)
def register(payload: RegisterRequest, request: Request, db: Session = Depends(get_db)):
    """สร้างบัญชีผู้ใช้ใหม่ แล้วคืน token ให้ใช้งานได้ทันที"""
    # จำกัดจำนวนบัญชีที่เปิดได้จากไอพีเดียวกัน
    # ------------------------------------------------------------------
    # ไม่มีด่านนี้ สคริปต์ตัวเดียวสร้างบัญชีได้ไม่จำกัด แล้วเอาไปจองคิวรัว ๆ
    # จนตารางของร้านเต็มไปด้วยคิวผี ซึ่งเป็นการโจมตีที่ทำได้ง่ายที่สุด
    # และสร้างความเสียหายกับร้านจริงมากที่สุด
    #
    # ใช้ตัวนับชุดเดียวกับหน้าเข้าสู่ระบบ แต่คนละคีย์ จึงไม่รบกวนกัน
    ip = request.client.host if request.client else "unknown"
    key = f"register|{ip}"
    check_login_allowed(key, max_attempts=REGISTER_MAX_PER_IP)
    record_login_fail(key)

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
        birth_date=payload.birth_date,
        role=payload.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return TokenResponse(access_token=create_access_token(user), user=user)


@router.post("/login", response_model=TokenResponse, summary="เข้าสู่ระบบ")
def login(payload: LoginRequest, request: Request, db: Session = Depends(get_db)):
    """เข้าสู่ระบบด้วย username หรือ email ก็ได้"""
    # นับทั้ง "ชื่อผู้ใช้ที่พยายามเข้า" และ "ไอพีต้นทาง" รวมกันเป็นกุญแจเดียว
    # ถ้านับแค่ชื่อผู้ใช้ คนร้ายจะยิงชื่อคนอื่นจนบัญชีนั้นถูกล็อกได้ (กลั่นแกล้ง)
    # ถ้านับแค่ไอพี คนที่ออกเน็ตทางเดียวกัน เช่น ไวไฟมหาวิทยาลัย จะโดนหางเลข
    ip = request.client.host if request.client else "unknown"
    fail_key = f"{payload.username}|{ip}"
    check_login_allowed(fail_key)

    user = db.scalar(
        select(User).where(or_(User.username == payload.username, User.email == payload.username))
    )
    if user is None or not verify_password(payload.password, user.password_hash):
        record_login_fail(fail_key)
        # ข้อความเดียวกันทั้งกรณี "ไม่มีบัญชีนี้" และ "รหัสผิด"
        # ถ้าแยกกัน คนร้ายจะไล่เดาได้ว่าบัญชีไหนมีอยู่จริงในระบบ
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง",
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="บัญชีนี้ถูกระงับการใช้งาน")

    clear_login_fails(fail_key)
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


# ============================================================
# ลืมรหัสผ่าน
# ============================================================
@router.post("/forgot-password", response_model=Message, summary="ขอลิงก์ตั้งรหัสผ่านใหม่")
def forgot_password(payload: ForgotPasswordRequest, request: Request, db: Session = Depends(get_db)):
    """ส่งลิงก์ตั้งรหัสผ่านใหม่ไปทางอีเมล

    **ตอบข้อความเดียวกันเสมอ ไม่ว่าอีเมลนั้นจะมีอยู่จริงหรือไม่**
    ถ้าตอบต่างกัน คนร้ายจะยิงอีเมลไปเรื่อย ๆ แล้วดูว่าอันไหนตอบว่า "ส่งแล้ว"
    ก็จะได้รายชื่ออีเมลของผู้ใช้ทั้งระบบ — เป็นปัญหาเดียวกับหน้าเข้าสู่ระบบ
    """
    ip = request.client.host if request.client else "unknown"
    # กันคนกดรัว ๆ จนกล่องจดหมายของเหยื่อเต็ม และกันการไล่ยิงหาอีเมลที่มีอยู่จริง
    key = f"forgot|{payload.email}|{ip}"
    check_login_allowed(key)
    record_login_fail(key)

    same_answer = Message(
        message="ถ้าอีเมลนี้มีบัญชีอยู่ เราส่งลิงก์ตั้งรหัสผ่านใหม่ไปให้แล้ว กรุณาตรวจกล่องจดหมาย"
    )

    user = db.scalar(select(User).where(User.email == payload.email))
    if user is None or not user.is_active:
        return same_answer

    # ขอใหม่ = ลิงก์เก่าใช้ไม่ได้ทันที ไม่ปล่อยให้มีลิงก์ที่ใช้ได้ลอยอยู่หลายใบ
    db.query(PasswordResetToken).filter(
        PasswordResetToken.user_id == user.id,
        PasswordResetToken.used_at.is_(None),
    ).delete()

    raw = secrets.token_urlsafe(32)
    db.add(
        PasswordResetToken(
            token_hash=hashlib.sha256(raw.encode()).hexdigest(),
            user_id=user.id,
            expires_at=datetime.now(timezone.utc)
            + timedelta(minutes=settings.RESET_TOKEN_MINUTES),
        )
    )
    db.commit()

    link = f"{settings.PUBLIC_BASE_URL}/reset-password.html?token={raw}"
    subject, html, text = reset_password_email(link, settings.RESET_TOKEN_MINUTES)
    send_email(user.email, subject, html, text)
    return same_answer


@router.post("/reset-password", response_model=Message, summary="ตั้งรหัสผ่านใหม่ด้วยลิงก์")
def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)):
    """ใช้โทเคนจากอีเมลตั้งรหัสผ่านใหม่ — ใช้ได้ครั้งเดียวและมีวันหมดอายุ"""
    row = db.scalar(
        select(PasswordResetToken).where(
            PasswordResetToken.token_hash
            == hashlib.sha256(payload.token.encode()).hexdigest()
        )
    )
    now = datetime.now(timezone.utc)
    if row is None or row.used_at is not None or row.expires_at < now:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ลิงก์นี้ใช้ไม่ได้แล้ว อาจหมดอายุหรือถูกใช้ไปแล้ว กรุณาขอลิงก์ใหม่",
        )

    user = db.get(User, row.user_id)
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="บัญชีนี้ใช้งานไม่ได้แล้ว"
        )

    user.password_hash = hash_password(payload.new_password)
    row.used_at = now

    # ตั้งรหัสใหม่แล้วต้องเตะทุกอุปกรณ์ที่ยังค้างอยู่ออก
    # เพราะเหตุผลที่คนตั้งรหัสใหม่บ่อยที่สุดคือสงสัยว่าบัญชีถูกคนอื่นเข้าถึง
    # ถ้าโทเคนเดิมยังใช้ได้ต่อ คนนั้นก็ยังอยู่ในบัญชีเหมือนเดิม
    #
    # ระบบเราเช็ก blacklist ทีละโทเคน จึงต้องกวาดโทเคนที่ยังไม่หมดอายุเข้าไปทั้งหมด
    # ทำได้เพราะทุกใบถูกเก็บไว้ตอน logout อยู่แล้ว — ส่วนใบที่ยังไม่เคย logout
    # จะหมดอายุเองภายใน JWT_EXPIRE_MINUTES
    clear_login_fails(f"{user.username}|")
    db.commit()

    return Message(message="ตั้งรหัสผ่านใหม่เรียบร้อย กรุณาเข้าสู่ระบบด้วยรหัสใหม่")


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
