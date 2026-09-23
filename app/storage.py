"""จัดการไฟล์รูปที่ผู้ใช้อัปโหลด

หลักการสำคัญด้านความปลอดภัย
---------------------------
1. **ไม่เชื่อชื่อไฟล์ที่ส่งมา** — ตั้งชื่อใหม่เป็นสุ่มทั้งหมด
   ถ้าเอาชื่อเดิมมาใช้ ผู้ไม่หวังดีส่ง `../../etc/passwd` หรือ `evil.php` เข้ามาได้

2. **ไม่เชื่อ Content-Type ที่ส่งมา** — ตรวจจาก "ไบต์จริง" ต้นไฟล์ (magic bytes)
   เพราะ header ปลอมได้ง่ายมาก แค่แก้ค่าในคำขอ

3. **เข้ารหัสรูปใหม่เสมอ** — ไม่บันทึกไบต์ที่ได้รับลงดิสก์ตรง ๆ
   ไฟล์รูปแนบสคริปต์ต่อท้ายได้ (polyglot file) การอ่านเข้า Pillow แล้วเซฟใหม่
   จะเหลือแต่ข้อมูลภาพจริง ส่วนที่แอบแนบมาหายไปพร้อมกับ EXIF (ซึ่งมีพิกัด GPS ติดมาด้วย)

4. **จำกัดขนาดก่อนอ่าน** — กันไฟล์ยักษ์และ decompression bomb
   (รูปเล็ก ๆ ที่พอคลายออกแล้วกินแรมหลายกิกะไบต์)
"""

from __future__ import annotations

import secrets
from io import BytesIO

from PIL import Image, UnidentifiedImageError

# ไฟล์นี้ไม่แตะดิสก์แล้ว — ไบต์ของรูปถูกส่งกลับให้ผู้เรียกไปเก็บในฐานข้อมูล
# เหตุผลเต็มอยู่ใน docstring ของ ShopImage ใน models.py
#   สรุปสั้น ๆ: โฮสต์ฟรีไม่มีดิสก์ถาวร ไฟล์หายทุกครั้งที่เครื่องหลับแล้วตื่น

MAX_UPLOAD_BYTES = 5 * 1024 * 1024      # 5 MB ต่อไฟล์
MAX_IMAGES_PER_SHOP = 8
MAX_SIDE = 1600                          # ด้านยาวสุดหลังย่อ
COVER_MIN_SIDE = 400                     # รูปเล็กกว่านี้เอาไปทำปกแล้วแตก

# ลายเซ็นไบต์ต้นไฟล์ของชนิดรูปที่ยอมรับ
_MAGIC: list[tuple[bytes, str]] = [
    (b"\xff\xd8\xff", "JPEG"),
    (b"\x89PNG\r\n\x1a\n", "PNG"),
    (b"GIF87a", "GIF"),
    (b"GIF89a", "GIF"),
]

# Pillow ปฏิเสธรูปที่มีจำนวนพิกเซลเกินค่านี้เอง กัน decompression bomb
Image.MAX_IMAGE_PIXELS = 50_000_000


class UploadError(ValueError):
    """ไฟล์ที่อัปโหลดใช้ไม่ได้ — ข้อความในนี้ส่งให้ผู้ใช้อ่านได้เลย"""


def _sniff(raw: bytes) -> str:
    """เดาชนิดรูปจากไบต์จริงต้นไฟล์ ไม่ใช่จากนามสกุลหรือ Content-Type"""
    for signature, kind in _MAGIC:
        if raw.startswith(signature):
            return kind
    # WebP เช็คยากกว่าเพื่อน เพราะ 4 ไบต์แรกเป็น "RIFF" แล้วขนาดไฟล์ แล้วค่อย "WEBP"
    if raw[:4] == b"RIFF" and raw[8:12] == b"WEBP":
        return "WEBP"
    raise UploadError("รองรับเฉพาะไฟล์ภาพ JPG, PNG, WebP และ GIF เท่านั้น")


def process_shop_image(raw: bytes) -> tuple[str, bytes, int, int]:
    """ตรวจ ย่อ และแปลงเป็น WebP

    คืนค่า (ชื่อไฟล์, ไบต์ของรูป, กว้าง, สูง)
    ผู้เรียกเป็นคนเอาไบต์ไปเก็บ — ฟังก์ชันนี้ไม่แตะที่เก็บข้อมูลเลย
    จึงย้ายไปเก็บที่อื่น (ดิสก์ · S3 · Cloudinary) ได้โดยไม่ต้องแก้ที่นี่
    """
    if not raw:
        raise UploadError("ไฟล์ว่างเปล่า กรุณาเลือกไฟล์ใหม่")
    if len(raw) > MAX_UPLOAD_BYTES:
        mb = len(raw) / 1024 / 1024
        raise UploadError(f"ไฟล์ใหญ่ {mb:.1f} MB เกินขีดจำกัด 5 MB กรุณาย่อรูปก่อน")

    _sniff(raw)   # ไม่ผ่านจะโยน UploadError ออกไปเอง

    # verify() อ่านโครงสร้างไฟล์เพื่อยืนยันว่าเป็นรูปจริง แต่มันทำให้อ็อบเจ็กต์ใช้ต่อไม่ได้
    # จึงต้องเปิดใหม่อีกรอบสำหรับงานประมวลผลจริง
    try:
        Image.open(BytesIO(raw)).verify()
        img = Image.open(BytesIO(raw))
        img.load()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
        raise UploadError("ไฟล์นี้เปิดเป็นรูปภาพไม่ได้ อาจเสียหายหรือไม่ใช่ไฟล์ภาพจริง")

    if img.width < 200 or img.height < 200:
        raise UploadError(
            f"รูปเล็กเกินไป ({img.width}×{img.height} พิกเซล) "
            "ควรมีขนาดอย่างน้อย 200×200 เพื่อให้แสดงผลได้สวย"
        )

    # แปลงเป็น RGB เสมอ — WebP ไม่รับโหมดแปลก ๆ อย่าง P (palette) หรือ CMYK
    # รูปโปร่งใสวางบนพื้นขาวก่อน ไม่งั้นส่วนโปร่งจะกลายเป็นดำ
    if img.mode in ("RGBA", "LA", "P"):
        img = img.convert("RGBA")
        canvas = Image.new("RGB", img.size, (255, 255, 255))
        canvas.paste(img, mask=img.split()[-1])
        img = canvas
    elif img.mode != "RGB":
        img = img.convert("RGB")

    # ย่อให้ด้านยาวสุดไม่เกิน MAX_SIDE — รูปจากมือถือมักใหญ่เกินจำเป็นมาก
    if max(img.size) > MAX_SIDE:
        img.thumbnail((MAX_SIDE, MAX_SIDE), Image.LANCZOS)

    buffer = BytesIO()
    img.save(buffer, format="WEBP", quality=82, method=4)
    data = buffer.getvalue()

    # ชื่อไฟล์ยังต้องมี เพราะใช้ประกอบ URL และให้เบราว์เซอร์รู้ว่าเป็นคนละรูป
    # token_hex(8) ให้ชื่อสุ่ม 16 ตัวอักษร เดาไม่ได้และแทบไม่มีทางชนกัน
    filename = f"{secrets.token_hex(8)}.webp"

    return filename, data, img.width, img.height


# ============================================================
# ที่อยู่รูปสำหรับเรียกดูจากเบราว์เซอร์
# ============================================================
def image_url(shop_id: int, filename: str) -> str:
    """แปลงชื่อไฟล์ในฐานข้อมูลเป็นที่อยู่ที่เบราว์เซอร์เรียกได้

    ระบบมีรูปสองชนิดที่อยู่คนละที่กัน

    1. **รูปที่มากับโค้ด** — `filename` เป็นเส้นทางเต็มขึ้นต้นด้วย `/`
       เช่น `/photos/spa-massage/01.webp` ไฟล์อยู่ใน `web/photos/`
       ซึ่งถูก commit เข้า repo จึงอยู่ถาวร ไม่หายตอน deploy หรือตอนเครื่องรีสตาร์ต

    2. **รูปที่เจ้าของร้านอัปโหลดเอง** — `filename` เป็นชื่อไฟล์ล้วน
       ไบต์ของรูปอยู่ในฐานข้อมูล และเสิร์ฟผ่านเส้นทาง `/uploads/shops/{id}/{ชื่อไฟล์}`

    เส้นทางของชนิดที่ 2 หน้าตาเหมือนไฟล์บนดิสก์ทั้งที่จริงมาจากฐานข้อมูล
    ตั้งใจให้เหมือนเดิม เพราะ URL ชุดนี้ถูกบันทึกไว้ในที่อื่นแล้ว
    (แท็กแชร์ลิงก์ · แคชของเบราว์เซอร์) การเปลี่ยนรูปแบบ URL จะทำให้ของเก่าพัง
    """
    if filename.startswith("/"):
        return filename
    return f"/uploads/shops/{shop_id}/{filename}"
