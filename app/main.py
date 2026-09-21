"""Bookvice REST API — แพลตฟอร์มจองบริการสุขภาพและความงาม

รันด้วย:  uvicorn app.main:app --reload
เอกสาร:   http://localhost:8000/docs
"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select

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
    watches,
)
from app.runtime_secret import resolve_jwt_secret
from app.seed import seed_database
from app.seed_extra import backfill_coordinates, enrich_demo_data, seed_closed_weekdays
from app.seed_men import seed_category_groups, seed_men_services
from app.seed_photos import seed_stock_photos
from app.seed_venues import seed_venues
from app.storage import UPLOAD_ROOT, ensure_dirs


@asynccontextmanager
async def lifespan(app: FastAPI):
    """ทำงานตอนเริ่มระบบ: รอฐานข้อมูล → สร้างตาราง → ปรับโครงสร้าง → ใส่ข้อมูลตัวอย่าง"""
    wait_for_db()
    Base.metadata.create_all(bind=engine)
    # create_all สร้างได้แค่ตารางใหม่ ถ้าเพิ่มคอลัมน์ในตารางเดิมต้องเติมเอง
    run_migrations(engine)

    # หากุญแจ JWT ที่คงเดิมข้ามการรีสตาร์ต (รายละเอียดใน runtime_secret.py)
    # ต้องทำหลัง create_all เพราะต้องมีตาราง app_secrets ก่อน
    db = SessionLocal()
    try:
        resolve_jwt_secret(db)
    finally:
        db.close()

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
            # วันหยุดประจำสัปดาห์ — ใส่ให้เฉพาะหมวดที่ร้านจริงมักหยุด
            # ต้องทำหลัง seed ร้านครบทุกชุด ไม่งั้นร้านที่มาทีหลังจะไม่ได้ค่า
            seed_closed_weekdays(db)
            # รูปตัวอย่างที่มากับโค้ด — ต้องทำหลัง seed ร้านครบทุกชุดแล้ว
            seed_stock_photos(db)
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
#
# allow_credentials ต้องเป็น False คู่กับ allow_origins=["*"]
# ------------------------------------------------------------------
# เว็บนี้ส่ง token ผ่านหัวข้อ Authorization ไม่ได้ใช้คุกกี้เลย จึงไม่ต้องการ
# credentials อยู่แล้ว การเปิดไว้ทั้งที่ไม่ได้ใช้มีแต่เสีย เพราะถ้าวันหนึ่ง
# มีใครเพิ่มคุกกี้เข้ามา ทุกเว็บบนอินเทอร์เน็ตจะยิง API นี้แทนผู้ใช้ที่ล็อกอินอยู่ได้
# (มาตรฐาน CORS ห้ามคู่ "*" + credentials อยู่แล้ว เบราว์เซอร์จะบล็อกเอง
#  ค่านี้จึงไม่เคยทำงานจริง แต่เป็นกับดักที่รอคนมาเหยียบ)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
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
app.include_router(watches.router)
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
# แท็กแชร์ลิงก์รายร้าน
# ============================================================
#
# ทำไมต้องทำฝั่งเซิร์ฟเวอร์ ทั้งที่เว็บเราวาดหน้าด้วย JavaScript
# ------------------------------------------------------------------
# บอตที่อ่านลิงก์ (LINE, Facebook, X, Discord, Slack) **ไม่รัน JavaScript**
# มันดึง HTML ดิบมาแล้วอ่านแท็ก <meta> ที่มีอยู่ตอนนั้นเท่านั้น
# ถ้าเราไปเขียน og:image ด้วย JS หลังหน้าโหลดเสร็จ บอตจะไม่มีวันเห็น
#
# ของเดิม shop.html มี og:title ตายตัวว่า "รายละเอียดร้าน — Bookvice"
# ทุกร้านจึงแชร์ออกไปแล้วหน้าตาเหมือนกันหมด ไม่มีรูป ไม่มีชื่อร้าน
#
# ตรงนี้จึงอ่านไฟล์ shop.html แล้วสลับแท็กให้ก่อนส่งออกไป
# ใช้ได้เฉพาะตอน SERVE_WEB (บนเว็บจริง) — ในเครื่อง nginx เสิร์ฟเอง
# ซึ่งไม่เป็นไร เพราะไม่มีใครแชร์ลิงก์ localhost
_OG_CACHE: dict[str, str] = {}


def _shop_share_html(shop_id: int) -> str | None:
    """คืน HTML ของ shop.html ที่สลับแท็กแชร์เป็นข้อมูลร้านนั้นแล้ว"""
    from html import escape

    from app.models import Shop, ShopImage
    from app.storage import image_url

    web_dir = Path(__file__).resolve().parent.parent / "web"
    path = web_dir / "shop.html"
    if not path.is_file():
        return None

    raw = _OG_CACHE.get("shop.html")
    if raw is None:
        raw = path.read_text(encoding="utf-8")
        _OG_CACHE["shop.html"] = raw

    db = SessionLocal()
    try:
        shop = db.get(Shop, shop_id)
        if shop is None:
            return None

        cover = db.scalar(
            select(ShopImage)
            .where(ShopImage.shop_id == shop.id, ShopImage.is_cover.is_(True))
            .limit(1)
        )
        title = f"{shop.name} — จองคิวผ่าน Bookvice"
        where = " · ".join(x for x in [shop.district, shop.province] if x)
        desc = (shop.description or "").strip() or (
            f"ดูช่วงเวลาที่ว่างจริงของ {shop.name}"
            + (f" ({where})" if where else "")
            + " แล้วจองได้ทันที"
        )
        # บอตส่วนใหญ่ตัดคำอธิบายราว 200 ตัวอักษร ตัดมาให้พอดีตั้งแต่ต้นทาง
        desc = desc[:197] + "…" if len(desc) > 200 else desc
    finally:
        db.close()

    img = ""
    if cover is not None:
        url = image_url(shop.id, cover.filename)
        # og:image ต้องเป็น URL เต็มเสมอ บอตไม่เติม domain ให้
        img = url if url.startswith("http") else f"{settings.PUBLIC_BASE_URL}{url}"

    out = raw
    for key, value in (
        ('<meta property="og:title" content="รายละเอียดร้าน — Bookvice" />',
         f'<meta property="og:title" content="{escape(title, quote=True)}" />'),
        ('<title>รายละเอียดร้าน — Bookvice</title>',
         f'<title>{escape(title)}</title>'),
    ):
        out = out.replace(key, value)

    # คำอธิบายกับรูปใส่เพิ่มเข้าไปก่อนปิด </head> ไม่ต้องไปหาแท็กเดิมให้ยุ่ง
    extra = (
        f'<meta property="og:description" content="{escape(desc, quote=True)}" />\n'
        f'<meta name="description" content="{escape(desc, quote=True)}" />\n'
    )
    if img:
        extra += (
            f'<meta property="og:image" content="{escape(img, quote=True)}" />\n'
            f'<meta name="twitter:card" content="summary_large_image" />\n'
        )
    return out.replace("</head>", extra + "</head>", 1)


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

        # ต้องประกาศ "ก่อน" mount StaticFiles ที่ "/" ไม่งั้นจะโดนกลืน
        @app.get("/shop.html", include_in_schema=False)
        def shop_page(id: int | None = None):
            """หน้าร้าน — แทรกแท็กแชร์ของร้านนั้นให้ก่อนส่งออก

            ไม่มี id หรือหาร้านไม่เจอ ก็ส่งไฟล์เดิมไปตามปกติ
            หน้าจะไปเจอ error เองแล้วขึ้นข้อความ "ไม่พบร้าน" ซึ่งถูกต้องอยู่แล้ว
            """
            if id is not None:
                try:
                    html = _shop_share_html(id)
                    if html:
                        return HTMLResponse(html)
                except Exception as exc:
                    # แท็กแชร์เป็นของเสริม ห้ามทำให้หน้าร้านเปิดไม่ได้
                    print(f"สร้างแท็กแชร์ของร้าน {id} ไม่สำเร็จ: {exc}")
            return FileResponse(WEB_DIR / "shop.html")

        # หน้าที่ไม่มีอยู่จริงต้องได้ 404.html ไม่ใช่ข้อความเปล่า ๆ ของเซิร์ฟเวอร์
        @app.exception_handler(404)
        async def not_found(request: Request, exc):
            # คำขอที่เป็น API ต้องได้ JSON เหมือนเดิม ไม่ใช่หน้าเว็บ
            if request.url.path.startswith(("/api", "/docs", "/redoc", "/openapi")):
                return JSONResponse({"detail": "ไม่พบเส้นทางนี้"}, status_code=404)
            page = WEB_DIR / "404.html"
            if page.is_file():
                return HTMLResponse(page.read_text(encoding="utf-8"), status_code=404)
            return JSONResponse({"detail": "ไม่พบหน้านี้"}, status_code=404)

        app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")
        print(f"เสิร์ฟหน้าเว็บจาก {WEB_DIR}")
    else:
        print(f"เปิด SERVE_WEB ไว้แต่ไม่พบโฟลเดอร์ {WEB_DIR}")
