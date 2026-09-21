"""กุญแจสำหรับเซ็น JWT — ต้องเป็นค่าเดิมทุกครั้งที่ระบบเริ่มทำงาน

ปัญหาที่ไฟล์นี้แก้
------------------
กุญแจนี้ใช้เซ็น token ตอนล็อกอิน และใช้ตรวจ token ตอนเรียก API
ถ้ากุญแจเปลี่ยน token ที่ออกไปแล้วจะตรวจไม่ผ่านทันที = ทุกคนหลุดล็อกอิน

โฮสต์ฟรีจะปิดเซิร์ฟเวอร์เมื่อไม่มีคนเข้าราว 15 นาที แล้วเปิดใหม่เมื่อมีคนเข้า
ถ้าสุ่มกุญแจใหม่ทุกครั้งที่เปิด ผู้ใช้จะหลุดล็อกอินวันละหลายรอบ

วิธีแก้
-------
เก็บกุญแจไว้ในฐานข้อมูล (ตาราง app_secrets) ซึ่งข้อมูลไม่หายตอนเซิร์ฟเวอร์ปิด
สุ่มครั้งแรกครั้งเดียว ครั้งต่อ ๆ ไปอ่านค่าเดิมมาใช้

    เริ่มระบบ ──> มีกุญแจในฐานข้อมูลไหม?
                      │
                      ├── มี    ──> เอามาใช้
                      └── ไม่มี ──> สุ่มใหม่ แล้วบันทึกลงฐานข้อมูล

ถ้าตั้ง JWT_SECRET ไว้ใน environment variable ระบบจะใช้ค่านั้นแทน
และไม่ยุ่งกับฐานข้อมูลเลย — ปลอดภัยกว่า เพราะกุญแจอยู่คนละที่กับข้อมูล
"""

import secrets

from sqlalchemy.orm import Session

from app.config import settings
from app.models import AppSecret

SECRET_NAME = "jwt_secret"


def resolve_jwt_secret(db: Session) -> str:
    """หากุญแจที่ควรใช้ แล้วใส่กลับเข้า settings ให้ทั้งระบบใช้ค่าเดียวกัน

    ใส่กลับเข้า settings ได้เพราะ security.py อ่าน settings.JWT_SECRET
    ตอนเรียกใช้ทุกครั้ง ไม่ได้จำค่าไว้ตั้งแต่ตอนเปิดโปรแกรม
    """
    # ตั้ง JWT_SECRET ไว้ใน environment แล้ว — ใช้ค่านั้น จบ
    if not settings.JWT_SECRET_IS_RANDOM:
        return settings.JWT_SECRET

    row = db.get(AppSecret, SECRET_NAME)

    if row is None:
        # ยังไม่เคยมีกุญแจ — สุ่มครั้งแรกและครั้งเดียว
        row = AppSecret(name=SECRET_NAME, value=secrets.token_urlsafe(48))
        db.add(row)
        db.commit()
        print("สร้างกุญแจ JWT เก็บไว้ในฐานข้อมูลแล้ว (ครั้งแรกเท่านั้น)")

    settings.JWT_SECRET = row.value
    return row.value
