"""Bookvice REST API — แพลตฟอร์มจองบริการสุขภาพและความงาม

รันด้วย:  uvicorn app.main:app --reload
เอกสาร:   http://localhost:8000/docs
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import Base, SessionLocal, engine, wait_for_db
from app.migrate import run_migrations
from app.routers import (
    aliases,
    auth,
    bookings,
    gaps,
    images,
    matches,
    notifications,
    payments,
    shops,
    staff,
    users,
)
from app.seed import seed_database
from app.seed_extra import backfill_coordinates, enrich_demo_data
from app.seed_men import seed_category_groups, seed_men_services
from app.seed_venues import seed_venues
from app.storage import UPLOAD_ROOT, ensure_dirs


@asynccontextmanager
async def lifespan(app: FastAPI):
    """ทำงานตอนเริ่มระบบ: รอฐานข้อมูล → สร้างตาราง → ปรับโครงสร้าง → ใส่ข้อมูลตัวอย่าง"""
    wait_for_db()
    Base.metadata.create_all(bind=engine)
    # create_all สร้างได้แค่ตารางใหม่ ถ้าเพิ่มคอลัมน์ในตารางเดิมต้องเติมเอง
    run_migrations(engine)
    # โฟลเดอร์เก็บรูปที่ผู้ใช้อัปโหลด ต้องมีก่อนถึงจะ mount ให้เสิร์ฟไฟล์ได้
    ensure_dirs()

    if settings.SEED_ON_START:
        db = SessionLocal()
        try:
            seed_database(db)
            # เติมร้าน ช่าง และรีวิวเพิ่ม ให้ระบบมีข้อมูลพอที่จะดูน่าเชื่อถือ
            enrich_demo_data(db)
            # สนามกีฬาและศูนย์ส่งของ — ใช้ชื่อและพิกัดของสถานที่ที่มีอยู่จริง
            seed_venues(db)
            # หมวดที่เจาะกลุ่มผู้ชาย — คลินิกชาย ตัดผมนอกสถานที่ ดูแลรถ คาราโอเกะ
            seed_men_services(db)
            # จัดหมวดเข้ากลุ่มใหญ่ ใช้แยกทางเข้าในหน้าเว็บ
            seed_category_groups(db)
            # ร้านเก่าถูกสร้างก่อนที่ระบบจะมีแผนที่ จึงต้องย้อนไปเติมพิกัดให้
            backfill_coordinates(db)
        finally:
            db.close()

    print("Bookvice API พร้อมใช้งานที่ http://localhost:8000/docs")
    yield


app = FastAPI(
    title="Bookvice API",
    description=(
        "REST API สำหรับแพลตฟอร์มจองบริการสุขภาพและความงาม "
        "(สปา ทำเล็บ ทำผม คลินิก สักลาย)\n\n"
        "**วิธีทดสอบ:** เรียก `POST /api/auth/login` ด้วย `mind` / `Password123` "
        "แล้วคัดลอก `access_token` ไปกดปุ่ม **Authorize** มุมขวาบน"
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# อนุญาตให้เว็บฝั่ง frontend เรียก API ได้
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# เสิร์ฟรูปที่ผู้ใช้อัปโหลด — ต้องสร้างโฟลเดอร์ก่อน ไม่งั้น StaticFiles จะโยน error ตอนเริ่ม
# check_dir=False บอกให้ข้ามการตรวจตอน mount แล้วไปเช็คตอนมีคนขอไฟล์แทน
# (ตอน import โมดูลนี้ lifespan ยังไม่ทำงาน โฟลเดอร์จึงอาจยังไม่มี)
UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOAD_ROOT, check_dir=False), name="uploads")

# รวม router ทั้งหมดเข้าแอป
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(shops.router)
app.include_router(staff.router)
app.include_router(bookings.router)
app.include_router(notifications.router)
app.include_router(images.router)
app.include_router(payments.router)
app.include_router(matches.router)
app.include_router(gaps.router)
# เส้นทางลัดให้ตรงกับรูปแบบที่โจทย์กำหนด (POST /register, GET /me, ...)
app.include_router(aliases.router)


@app.get("/api", tags=["ทั่วไป"], summary="ข้อมูลระบบ")
def read_root():
    return {
        "message": "Bookvice API — แพลตฟอร์มจองบริการสุขภาพและความงาม",
        "version": "1.0.0",
        "docs": "/docs",
        "redoc": "/redoc",
    }


@app.get("/health", tags=["ทั่วไป"], summary="ตรวจสอบสถานะระบบ")
def health_check():
    return {"status": "ok", "message": "API ทำงานปกติ"}


# ============================================================
# เสิร์ฟหน้าเว็บจาก FastAPI (ใช้เฉพาะตอน deploy ที่เปิดได้พอร์ตเดียว)
# ============================================================
#
# ต้อง mount ตรงนี้เป็นอันสุดท้ายเสมอ เพราะ StaticFiles ที่ path "/"
# จะรับทุกเส้นทางที่เหลือ ถ้า mount ก่อน router จะกลืน /api ไปหมด
#
# ในเครื่องเราไม่เปิดโหมดนี้ — nginx เสิร์ฟหน้าเว็บที่พอร์ต 3000 ตามโจทย์
if settings.SERVE_WEB:
    WEB_DIR = Path(__file__).resolve().parent.parent / "web"
    if WEB_DIR.is_dir():
        app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")
        print(f"เสิร์ฟหน้าเว็บจาก {WEB_DIR}")
    else:
        print(f"เปิด SERVE_WEB ไว้แต่ไม่พบโฟลเดอร์ {WEB_DIR}")
