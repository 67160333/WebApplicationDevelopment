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
from pathlib import Path

from PIL import Image, UnidentifiedImageError

from app.config import settings

# โฟลเดอร์เก็บไฟล์จริง — ผูกกับ Docker volume ไว้ ลบคอนเทนเนอร์แล้วรูปไม่หาย
# บนโฮสต์ฟรีที่ไม่มีที่เก็บถาวร ให้ตั้ง UPLOAD_DIR ชี้ไปที่อื่นได้
UPLOAD_ROOT = Path(settings.UPLOAD_DIR)
SHOP_IMAGE_DIR = UPLOAD_ROOT / "shops"

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


def ensure_dirs() -> None:
    """สร้างโฟลเดอร์อัปโหลดถ้ายังไม่มี — เรียกตอนระบบเริ่มทำงาน"""
    SHOP_IMAGE_DIR.mkdir(parents=True, exist_ok=True)


def shop_dir(shop_id: int) -> Path:
    return SHOP_IMAGE_DIR / str(shop_id)


def process_shop_image(raw: bytes, shop_id: int) -> tuple[str, int, int, int]:
    """ตรวจ ย่อ แปลงเป็น WebP แล้วบันทึกลงดิสก์

    คืนค่า (ชื่อไฟล์, กว้าง, สูง, ขนาดไบต์)
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

    target_dir = shop_dir(shop_id)
    target_dir.mkdir(parents=True, exist_ok=True)

    # token_hex(8) ให้ชื่อสุ่ม 16 ตัวอักษร เดาไม่ได้และแทบไม่มีทางชนกัน
    filename = f"{secrets.token_hex(8)}.webp"
    (target_dir / filename).write_bytes(data)

    return filename, img.width, img.height, len(data)


def delete_shop_image(shop_id: int, filename: str) -> None:
    """ลบไฟล์ออกจากดิสก์ — ไม่พังถ้าไฟล์หายไปแล้ว

    ตรวจซ้ำว่าเส้นทางที่จะลบอยู่ในโฟลเดอร์ของร้านนี้จริง ๆ
    กันกรณีชื่อไฟล์ในฐานข้อมูลถูกแก้ให้มี ../ ปนมา
    """
    base = shop_dir(shop_id).resolve()
    target = (base / filename).resolve()
    if not str(target).startswith(str(base)):
        return
    target.unlink(missing_ok=True)


def delete_shop_folder(shop_id: int) -> None:
    """ลบรูปทั้งร้าน — ใช้ตอนลบร้านทิ้ง"""
    folder = shop_dir(shop_id)
    if not folder.is_dir():
        return
    for item in folder.iterdir():
        item.unlink(missing_ok=True)
    folder.rmdir()
