"""ค่าตั้งค่าของระบบ อ่านจาก environment variable ที่ docker-compose ส่งเข้ามา"""

import os
import secrets


class Settings:
    # ที่อยู่ฐานข้อมูล — ใน Docker จะชี้ไปที่ service ชื่อ db
    #
    # ค่าสำรองข้างล่างใช้เฉพาะตอนรัน uvicorn นอก Docker โดยต่อกับ service db
    # ที่เปิดไว้ที่พอร์ต 5433 จึงต้อง **ตรงกับ DB_NAME / DB_USER / DB_PASSWORD ใน .env**
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg2://bookvice_user:bookvice_pass123@localhost:5433/bookvice",
    )

    # ค่าสำหรับสร้าง/ตรวจสอบ JWT token
    #
    # **ห้ามมีค่าสำรองที่เดาได้** — นี่คือกุญแจที่ใช้เซ็น token ทุกใบ
    # ของเดิมใช้ค่าคงที่ "dev_secret_key_please_change" ซึ่งอยู่ในโค้ดบน GitHub
    # ถ้าเครื่องที่ deploy ลืมตั้ง JWT_SECRET ใครก็ตามที่เปิดซอร์สดูจะเซ็น token
    # ของตัวเองเป็น role: admin แล้วเข้าหลังบ้านได้ทันที โดยไม่ต้องรู้รหัสผ่านใคร
    #
    # เปลี่ยนเป็นสุ่มใหม่ทุกครั้งที่เริ่มระบบแทน ผลที่ตามมาคือถ้าลืมตั้งจริง ๆ
    # ทุกคนจะถูกเด้งออกตอนรีสตาร์ต ซึ่งน่ารำคาญแต่ไม่อันตราย
    # — เลือกทางที่ "พังแบบปลอดภัย" ดีกว่า "ทำงานต่อได้แต่ใครก็เข้ามาได้"
    JWT_SECRET: str = os.getenv("JWT_SECRET") or secrets.token_urlsafe(48)
    JWT_SECRET_IS_RANDOM: bool = not os.getenv("JWT_SECRET")
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = int(os.getenv("JWT_EXPIRE_MINUTES", "1440"))

    # ใส่ข้อมูลตัวอย่างตอนเริ่มระบบหรือไม่
    SEED_ON_START: bool = os.getenv("SEED_ON_START", "true").lower() == "true"

    # ให้ FastAPI เสิร์ฟหน้าเว็บเองด้วยหรือไม่
    #
    # ในเครื่อง: false — nginx เสิร์ฟหน้าเว็บที่พอร์ต 3000 แยกจาก API ที่ 8000
    #            (ตามที่โจทย์กำหนดให้ใช้ Docker Compose หลาย service)
    # บนโฮสต์ฟรีอย่าง Hugging Face: true — เปิดได้พอร์ตเดียวและรันได้ container เดียว
    #            จึงต้องให้ FastAPI เสิร์ฟทั้งสองอย่างจากที่เดียวกัน
    SERVE_WEB: bool = os.getenv("SERVE_WEB", "false").lower() == "true"

    # ---------- อีเมล ----------
    #
    # ไม่ตั้ง RESEND_API_KEY = ระบบยังทำงานได้ครบ แต่จะพิมพ์อีเมลลง log แทนการส่งจริง
    # ทำให้ทดสอบระบบลืมรหัสผ่านได้ตั้งแต่วันแรกโดยไม่ต้องสมัครบริการภายนอกก่อน
    #
    # MAIL_FROM ต้องเป็นโดเมนที่ยืนยันแล้วใน Resend
    # ถ้ายังไม่มีโดเมนของตัวเอง Resend ให้ใช้ onboarding@resend.dev ได้
    # แต่ส่งได้เฉพาะไปยังอีเมลที่สมัคร Resend ไว้เท่านั้น
    RESEND_API_KEY: str = os.getenv("RESEND_API_KEY", "")
    MAIL_FROM: str = os.getenv("MAIL_FROM", "Bookvice <onboarding@resend.dev>")

    # ลิงก์ตั้งรหัสผ่านใหม่มีอายุสั้น — นานไปคือเพิ่มเวลาให้คนที่แอบเห็นอีเมล
    RESET_TOKEN_MINUTES: int = int(os.getenv("RESET_TOKEN_MINUTES", "30"))

    # ที่อยู่เต็มของเว็บจริง — ใช้ประกอบ URL รูปในแท็กแชร์ลิงก์
    #
    # og:image ต้องเป็น URL เต็มเสมอ บอตของ LINE/Facebook ไม่เติม domain ให้
    # ถ้าส่ง "/photos/spa/01.webp" ไป บอตจะหารูปไม่เจอและไม่ขึ้นรูปพรีวิว
    PUBLIC_BASE_URL: str = os.getenv(
        "PUBLIC_BASE_URL", "https://bookvice.onrender.com"
    ).rstrip("/")

    # โฟลเดอร์เก็บรูปที่ผู้ใช้อัปโหลด
    # Hugging Face ให้พื้นที่ถาวรที่ /data (ถ้าซื้อ) แต่ดิสก์หลักหายทุกครั้งที่รีสตาร์ต
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "/app/uploads")


settings = Settings()
