"""7) Shop Images — รูปภาพหน้าร้านและผลงาน"""

from fastapi import APIRouter, Depends, File, HTTPException, Path, UploadFile, status
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Shop, ShopImage, User
from app.schemas import ImageUpdate, Message, ShopImageOut
from app.security import require_roles
from app.storage import (
    MAX_IMAGES_PER_SHOP,
    MAX_UPLOAD_BYTES,
    UploadError,
    delete_shop_image,
    process_shop_image,
)

router = APIRouter(prefix="/api", tags=["7. Shop Images"])


def _get_shop_or_404(db: Session, shop_id: int) -> Shop:
    shop = db.get(Shop, shop_id)
    if shop is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ไม่พบร้านนี้")
    return shop


def _ensure_owner(shop: Shop, user: User) -> None:
    if user.role != "admin" and shop.owner_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="คุณไม่ใช่เจ้าของร้านนี้"
        )


@router.get(
    "/shops/{shop_id}/images",
    response_model=list[ShopImageOut],
    summary="ดูรูปทั้งหมดของร้าน",
)
def list_images(shop_id: int = Path(..., ge=1), db: Session = Depends(get_db)):
    _get_shop_or_404(db, shop_id)
    rows = db.scalars(
        select(ShopImage)
        .where(ShopImage.shop_id == shop_id)
        .order_by(ShopImage.is_cover.desc(), ShopImage.sort_order, ShopImage.id)
    ).all()
    return [ShopImageOut.model_validate(r) for r in rows]


@router.post(
    "/shops/{shop_id}/images",
    response_model=ShopImageOut,
    status_code=status.HTTP_201_CREATED,
    summary="อัปโหลดรูปร้าน (เจ้าของร้าน)",
    description=(
        f"รับไฟล์ JPG / PNG / WebP / GIF ขนาดไม่เกิน {MAX_UPLOAD_BYTES // 1024 // 1024} MB "
        f"ร้านละไม่เกิน {MAX_IMAGES_PER_SHOP} รูป\n\n"
        "ระบบจะย่อรูปและแปลงเป็น WebP ให้อัตโนมัติ พร้อมลบข้อมูล EXIF "
        "(ซึ่งอาจมีพิกัด GPS ของผู้ถ่ายติดมาด้วย)"
    ),
)
async def upload_image(
    shop_id: int = Path(..., ge=1),
    file: UploadFile = File(..., description="ไฟล์ภาพ"),
    current_user: User = Depends(require_roles("owner", "admin")),
    db: Session = Depends(get_db),
):
    shop = _get_shop_or_404(db, shop_id)
    _ensure_owner(shop, current_user)

    used = db.scalar(
        select(func.count()).select_from(ShopImage).where(ShopImage.shop_id == shop_id)
    ) or 0
    if used >= MAX_IMAGES_PER_SHOP:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"ร้านนี้มีรูปครบ {MAX_IMAGES_PER_SHOP} รูปแล้ว กรุณาลบรูปเก่าก่อน",
        )

    raw = await file.read()
    try:
        filename, width, height, size = process_shop_image(raw, shop_id)
    except UploadError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))

    # รูปแรกของร้านตั้งเป็นปกให้เลย เจ้าของร้านจะได้ไม่ต้องมากดเอง
    image = ShopImage(
        shop_id=shop_id,
        filename=filename,
        is_cover=(used == 0),
        sort_order=used,
        width=width,
        height=height,
        size_bytes=size,
    )
    db.add(image)
    try:
        db.commit()
    except Exception:
        # บันทึกฐานข้อมูลไม่สำเร็จ ต้องเก็บกวาดไฟล์ที่เขียนลงดิสก์ไปแล้วด้วย
        # ไม่งั้นจะเหลือไฟล์ค้างที่ไม่มีใครอ้างถึง กินพื้นที่ไปเรื่อย ๆ
        db.rollback()
        delete_shop_image(shop_id, filename)
        raise
    db.refresh(image)
    return ShopImageOut.model_validate(image)


@router.patch(
    "/shop-images/{image_id}",
    response_model=ShopImageOut,
    summary="แก้ไขคำบรรยายหรือตั้งเป็นรูปปก",
)
def update_image(
    payload: ImageUpdate,
    image_id: int = Path(..., ge=1),
    current_user: User = Depends(require_roles("owner", "admin")),
    db: Session = Depends(get_db),
):
    image = db.get(ShopImage, image_id)
    if image is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ไม่พบรูปนี้")
    _ensure_owner(_get_shop_or_404(db, image.shop_id), current_user)

    if payload.caption is not None:
        image.caption = payload.caption.strip() or None

    if payload.is_cover:
        # ปลดปกเดิมก่อนเสมอ — ฐานข้อมูลมี unique index บังคับว่าร้านหนึ่งมีปกได้รูปเดียว
        # ถ้าตั้งใหม่โดยไม่ปลดเก่า คำสั่งจะถูกปฏิเสธทันที
        db.execute(
            update(ShopImage)
            .where(ShopImage.shop_id == image.shop_id, ShopImage.id != image.id)
            .values(is_cover=False)
        )
        db.flush()
        image.is_cover = True

    db.commit()
    db.refresh(image)
    return ShopImageOut.model_validate(image)


@router.delete("/shop-images/{image_id}", response_model=Message, summary="ลบรูป")
def delete_image(
    image_id: int = Path(..., ge=1),
    current_user: User = Depends(require_roles("owner", "admin")),
    db: Session = Depends(get_db),
):
    image = db.get(ShopImage, image_id)
    if image is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ไม่พบรูปนี้")
    _ensure_owner(_get_shop_or_404(db, image.shop_id), current_user)

    shop_id, filename, was_cover = image.shop_id, image.filename, image.is_cover
    db.delete(image)
    db.flush()

    # ถ้าลบรูปปกไป ให้เลื่อนรูปถัดไปขึ้นมาเป็นปกแทน
    # ไม่งั้นการ์ดร้านจะกลับไปเป็นภาพวาดทั้งที่ยังมีรูปจริงเหลืออยู่
    if was_cover:
        nxt = db.scalars(
            select(ShopImage)
            .where(ShopImage.shop_id == shop_id)
            .order_by(ShopImage.sort_order, ShopImage.id)
            .limit(1)
        ).first()
        if nxt is not None:
            nxt.is_cover = True

    db.commit()
    delete_shop_image(shop_id, filename)
    return Message(message="ลบรูปเรียบร้อย")
