"""จัดการการเชื่อมต่อฐานข้อมูลด้วย SQLAlchemy"""

import time

from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,   # ตรวจ connection ก่อนใช้ กัน connection ที่ตายไปแล้ว
    echo=False,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    """คลาสแม่ของทุก model"""
    pass


def get_db():
    """Dependency ของ FastAPI — เปิด session ให้ endpoint ใช้ แล้วปิดให้อัตโนมัติ"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def wait_for_db(retries: int = 15, delay: int = 2) -> None:
    """รอจนฐานข้อมูลพร้อมใช้งาน (ตอนรันด้วย Docker ฐานข้อมูลอาจบูตช้ากว่า API)"""
    for attempt in range(1, retries + 1):
        try:
            with engine.connect():
                print("เชื่อมต่อฐานข้อมูลสำเร็จ")
                return
        except OperationalError as exc:
            print(f"รอฐานข้อมูล... ({attempt}/{retries}) {exc.__class__.__name__}")
            if attempt == retries:
                raise
            time.sleep(delay)
