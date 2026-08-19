"""ค่าตั้งค่าของระบบ อ่านจาก environment variable ที่ docker-compose ส่งเข้ามา"""

import os


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
    JWT_SECRET: str = os.getenv("JWT_SECRET", "dev_secret_key_please_change")
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

    # โฟลเดอร์เก็บรูปที่ผู้ใช้อัปโหลด
    # Hugging Face ให้พื้นที่ถาวรที่ /data (ถ้าซื้อ) แต่ดิสก์หลักหายทุกครั้งที่รีสตาร์ต
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "/app/uploads")


settings = Settings()
