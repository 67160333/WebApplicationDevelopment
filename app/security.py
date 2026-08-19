"""ระบบยืนยันตัวตน — เข้ารหัสรหัสผ่านด้วย bcrypt และออก/ตรวจสอบ JWT"""

from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import TokenBlacklist, User

# ปุ่มกุญแจรูปแม่กุญแจใน Swagger UI มาจากตรงนี้ (กด Authorize แล้ววาง token ได้เลย)
# auto_error=False เพื่อให้เราตอบ 401 เองได้
# ค่าเริ่มต้นของ FastAPI จะตอบ 403 ซึ่งผิดความหมาย (403 = ล็อกอินแล้วแต่ไม่มีสิทธิ์)
# และทำให้ฝั่งเว็บที่ดัก 401 เพื่อพากลับไปหน้าล็อกอินไม่ทำงาน
bearer_scheme = HTTPBearer(
    description="ใส่ token ที่ได้จาก /api/auth/login", auto_error=False
)


# ---------- รหัสผ่าน ----------
def hash_password(plain: str) -> str:
    """เข้ารหัสรหัสผ่าน — ไม่เก็บรหัสจริงลงฐานข้อมูล"""
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt(rounds=10)).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        return False


# ---------- JWT ----------
def create_access_token(user: User) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    payload = {
        "sub": str(user.id),
        "username": user.username,
        "role": user.role,
        "exp": expire,
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])


# ---------- Dependency สำหรับ endpoint ที่ต้องล็อกอิน ----------
def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="กรุณาเข้าสู่ระบบก่อนใช้งานส่วนนี้",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials

    # token ที่ logout ไปแล้วใช้ต่อไม่ได้
    blacklisted = db.scalar(select(TokenBlacklist).where(TokenBlacklist.token == token))
    if blacklisted is not None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="token นี้ถูกยกเลิกแล้ว กรุณาเข้าสู่ระบบใหม่",
        )

    try:
        payload = decode_token(token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="token หมดอายุ กรุณาเข้าสู่ระบบใหม่",
        )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="token ไม่ถูกต้อง",
        )

    # token ที่ผ่านการถอดรหัสแล้วอาจยังไม่มี claim ที่เราต้องใช้
    # ถ้าอ่านตรง ๆ จะเป็น KeyError ที่ไม่มีใครดัก แล้วกลายเป็น 500
    # ทั้งที่ความหมายจริงคือ "token ใช้ไม่ได้" ซึ่งต้องเป็น 401
    try:
        user_id = int(payload["sub"])
    except (KeyError, TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="token ไม่ถูกต้อง"
        )

    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="ไม่พบผู้ใช้งานนี้")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="บัญชีนี้ถูกระงับการใช้งาน")

    # เก็บ token ไว้ใช้ตอน logout
    user._token = token  # type: ignore[attr-defined]
    return user


def require_roles(*roles: str):
    """จำกัดสิทธิ์ตาม role เช่น Depends(require_roles("admin"))"""

    def checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="คุณไม่มีสิทธิ์เข้าถึงส่วนนี้",
            )
        return current_user

    return checker
