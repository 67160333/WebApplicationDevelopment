"""อัปโหลดรูปร้านทีเดียวทั้งเว็บ โดยแยกรูปตามหมวดหมู่

ปัญหาที่สคริปต์นี้แก้
--------------------------------------------------------------------------
ระบบมี 38 ร้าน ถ้าอัปผ่านหน้าเว็บทีละร้าน ร้านละ 4 รูป = กด 152 ครั้ง
สคริปต์นี้ให้เตรียมรูปแค่ **หมวดละ 4-6 รูป** (รวมราว 60 รูป)
แล้วมันจะแจกจ่ายให้ร้านทุกแห่งในหมวดนั้นเอง โดยหมุนลำดับไม่ให้ร้านข้าง ๆ กันได้รูปชุดเดียวกัน

วิธีใช้
--------------------------------------------------------------------------
0. วิธีที่เร็วที่สุด — ให้สคริปต์โหลดรูปให้เอง แล้วอัปต่อในคำสั่งเดียว

       python tools/upload_photos.py --fetch

   รายชื่อรูปอยู่ใน tools/photo_urls.txt (ทุกรูปใช้ Pexels License ใช้ฟรี)

1. หรือจะหารูปเองก็ได้ เอาใส่โฟลเดอร์ตามหมวด

       tools/photos/spa-massage/  ← รูปสปา 4-6 รูป
       tools/photos/football/     ← รูปสนามบอล 4-6 รูป
       ...

2. รันจากโฟลเดอร์โปรเจกต์

       python tools/upload_photos.py

   ถ้าเครื่องไม่มี Python ให้รันผ่าน container แทน

       docker compose cp tools bookvice-api:/app/tools
       docker compose exec api python /app/tools/upload_photos.py

3. อยากอัปขึ้นเว็บจริงบน Render ก็เปลี่ยนปลายทาง

       python tools/upload_photos.py --base https://bookvice.onrender.com --password <รหัสแอดมินบน Render>

   หมายเหตุ: บน Render รูปเก็บใน /tmp ซึ่ง **หายทุกครั้งที่ deploy ใหม่** ต้องอัปซ้ำ

ตัวเลือกอื่น
--------------------------------------------------------------------------
    --per-shop 4      จำนวนรูปต่อร้าน (ไม่เกิน 8 ตามเพดานของระบบ)
    --replace         ลบรูปเดิมทิ้งก่อนอัปใหม่ (ค่าเริ่มต้นคือข้ามร้านที่มีรูปแล้ว)
    --only football   ทำเฉพาะหมวดเดียว
    --dry-run         แสดงว่าจะทำอะไร แต่ไม่อัปจริง

ทำไมไม่ใช้ requests
--------------------------------------------------------------------------
ใช้ urllib จาก standard library ล้วน จะได้รันได้ทันทีทั้งบน Windows และใน container
โดยไม่ต้อง pip install อะไรเพิ่ม — multipart ประกอบเองด้านล่าง
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
PHOTO_ROOT = HERE / "photos"
EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}

# เพดานของระบบ — ดู MAX_IMAGES_PER_SHOP ใน app/storage.py
MAX_PER_SHOP = 8

# ---------------------------------------------------------------------------
# เกณฑ์ขนาดรูป — ทำไมต้องมี
#
# ขนาดรูปตัวอย่างในหน้าผลค้นหาของ Pexels/Unsplash คือราว 500 px
# ถ้าคลิกขวาเซฟจากหน้านั้นเลยจะได้ไฟล์เล็กเกินใช้งาน ต้องกดเข้าหน้ารูปแล้วกดปุ่มดาวน์โหลด
#
# การ์ดร้านกว้างจริงราว 355 px แต่จอโน้ตบุ๊กสมัยนี้ส่วนใหญ่เป็นจอ 2x
# จึงต้องใช้ไฟล์ราว 700 px ขึ้นไปถึงจะไม่เห็นว่าแตก
# ระบบย่อรูปให้อัตโนมัติอยู่แล้ว (MAX_SIDE = 1600) แต่ขยายให้ไม่ได้
# ---------------------------------------------------------------------------
MIN_WIDTH = 700          # ต่ำกว่านี้ถือว่าใช้ไม่ได้
GOOD_WIDTH = 1200        # ถึงเกณฑ์นี้ถือว่าสบายใจ


def _image_size(path: Path):
    """อ่านขนาดรูปโดยไม่ต้องพึ่ง Pillow — อ่านเฉพาะส่วนหัวไฟล์

    เขียนเองเพราะสคริปต์นี้ตั้งใจให้รันได้ทันทีบน Windows โดยไม่ต้อง pip install
    คืน None ถ้าอ่านไม่ออก (จะถือว่าผ่าน ไม่บล็อกผู้ใช้เพราะข้อจำกัดของตัวอ่าน)
    """
    try:
        raw = path.read_bytes()
    except OSError:
        return None

    # PNG: ความกว้าง/สูงอยู่ที่ไบต์ 16-24
    if raw[:8] == b"\x89PNG\r\n\x1a\n":
        return int.from_bytes(raw[16:20], "big"), int.from_bytes(raw[20:24], "big")

    # GIF: little-endian 2 ไบต์ ที่ตำแหน่ง 6
    if raw[:6] in (b"GIF87a", b"GIF89a"):
        return int.from_bytes(raw[6:8], "little"), int.from_bytes(raw[8:10], "little")

    # WebP (VP8X / VP8 / VP8L) — เอาเฉพาะ VP8X ที่อ่านง่าย
    if raw[:4] == b"RIFF" and raw[8:12] == b"WEBP" and raw[12:16] == b"VP8X":
        w = int.from_bytes(raw[24:27], "little") + 1
        h = int.from_bytes(raw[27:30], "little") + 1
        return w, h

    # JPEG: ต้องเดินทีละ marker หา SOF ถึงจะเจอขนาด
    if raw[:2] == b"\xff\xd8":
        i = 2
        while i < len(raw) - 9:
            if raw[i] != 0xFF:
                i += 1
                continue
            marker = raw[i + 1]
            # SOF0-SOF15 คือ marker ที่บอกขนาดจริง (ข้าม SOF4/SOF8/SOF12 ที่ไม่ใช่)
            if 0xC0 <= marker <= 0xCF and marker not in (0xC4, 0xC8, 0xCC):
                h = int.from_bytes(raw[i + 5:i + 7], "big")
                w = int.from_bytes(raw[i + 7:i + 9], "big")
                return w, h
            seg = int.from_bytes(raw[i + 2:i + 4], "big")
            if seg <= 0:
                break
            i += 2 + seg
    return None


def check_photos(pools: dict[str, list[Path]], allow_small: bool):
    """คัดรูปที่เล็กเกินไปออก แล้วรายงานให้เห็นว่าไฟล์ไหนมีปัญหา"""
    clean: dict[str, list[Path]] = {}
    warned = False

    for slug, files in pools.items():
        keep, small, portrait = [], [], []
        for f in files:
            size = _image_size(f)
            if size is None:
                keep.append(f)
                continue
            w, h = size
            if w < MIN_WIDTH and not allow_small:
                small.append((f, w, h))
                continue
            if h > w:
                portrait.append(f.name)
            keep.append(f)

        if small:
            warned = True
            print(f"  [{slug}] ข้ามรูปที่เล็กเกินไป {len(small)} ไฟล์ (ต้องกว้างอย่างน้อย {MIN_WIDTH} px)")
            for f, w, h in small:
                print(f"      ✗ {f.name}  {w}x{h}")
        if portrait:
            warned = True
            print(f"  [{slug}] เตือน: รูปแนวตั้ง {len(portrait)} ไฟล์ จะถูกครอปบนการ์ดแนวนอน")
            for n in portrait:
                print(f"      ! {n}")
        if keep:
            clean[slug] = keep

    if warned:
        print()
        print("  วิธีให้ได้ไฟล์ใหญ่: เปิด pexels.com → ค้นคำ → **คลิกที่รูป** →")
        print("  กดปุ่มเขียว Free Download (เลือก Medium ก็พอ) จะได้ราว 1900 px")
        print(f"  ถ้ายืนยันจะใช้ไฟล์เล็กจริง ๆ ใส่ --allow-small (ภาพจะแตกบนจอความละเอียดสูง)")
        print()
    return clean


URL_LIST = HERE / "photo_urls.txt"


def fetch_photos() -> int:
    """โหลดรูปจากรายชื่อใน photo_urls.txt ลงโฟลเดอร์ตามหมวด

    ทำไมต้องมีขั้นนี้: เครื่องที่เตรียมรายชื่อให้ไม่มีสิทธิ์ออกอินเทอร์เน็ต
    แต่เครื่องที่รันสคริปต์นี้มี — จึงให้ฝั่งนี้เป็นคนโหลดเอง
    รูปทั้งหมดอยู่ภายใต้ Pexels License ใช้ได้ฟรีโดยไม่ต้องให้เครดิต
    """
    if not URL_LIST.exists():
        print(f"ไม่พบไฟล์รายชื่อรูป {URL_LIST}")
        return 0

    slug = None
    got = skipped = failed = 0
    for line in URL_LIST.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]"):
            slug = line[1:-1]
            print(f"\n[{slug}]")
            continue
        if slug is None or not line.startswith("http"):
            continue

        folder = PHOTO_ROOT / slug
        folder.mkdir(parents=True, exist_ok=True)
        # ตั้งชื่อไฟล์จากรหัสรูปของ Pexels เพื่อให้รันซ้ำแล้วรู้ว่าโหลดไปแล้ว
        m = re.search(r"/photos/(\d+)/", line)
        name = f"pexels-{m.group(1)}.jpg" if m else f"{abs(hash(line)) % 10**8}.jpg"
        target = folder / name

        if target.exists() and target.stat().st_size > 10_000:
            print(f"    - {name} มีอยู่แล้ว ข้าม")
            skipped += 1
            continue

        try:
            req = urllib.request.Request(line, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=90) as resp:
                data = resp.read()
            if len(data) < 10_000:
                raise ValueError(f"ไฟล์เล็กผิดปกติ {len(data)} ไบต์")
            target.write_bytes(data)
            size = _image_size(target)
            dim = f"{size[0]}x{size[1]}" if size else "?"
            print(f"    ✓ {name}  {dim}  {len(data)//1024} KB")
            got += 1
        except Exception as exc:
            print(f"    ✗ {name}: {exc}")
            failed += 1

    print(f"\nโหลดใหม่ {got} · มีอยู่แล้ว {skipped} · ล้มเหลว {failed}\n")
    return got + skipped


# ---------------------------------------------------------------- HTTP ----
def _request(url: str, *, method="GET", token=None, data=None, headers=None):
    req = urllib.request.Request(url, data=data, method=method)
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = resp.read()
            return json.loads(body) if body else None
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")[:300]
        raise RuntimeError(f"HTTP {exc.code} จาก {url}\n    {detail}") from None
    except urllib.error.URLError as exc:
        raise RuntimeError(f"ต่อ {url} ไม่ได้ — {exc.reason}") from None


def post_json(base, path, payload, token=None):
    return _request(
        base + path, method="POST", token=token,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )


def upload_file(base: str, path: str, token: str, file_path: Path):
    """ประกอบ multipart/form-data เอง เพราะไม่อยากพึ่ง requests"""
    boundary = f"----bookvice{uuid.uuid4().hex}"
    ctype = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
    body = b"".join([
        f'--{boundary}\r\n'.encode(),
        f'Content-Disposition: form-data; name="file"; filename="{file_path.name}"\r\n'.encode(),
        f"Content-Type: {ctype}\r\n\r\n".encode(),
        file_path.read_bytes(),
        f"\r\n--{boundary}--\r\n".encode(),
    ])
    return _request(
        base + path, method="POST", token=token, data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )


# ---------------------------------------------------------------- main ----
def main() -> int:
    ap = argparse.ArgumentParser(description="อัปโหลดรูปร้านยกโฟลเดอร์")
    ap.add_argument("--base", default="http://localhost:8000", help="ที่อยู่ API")
    ap.add_argument("--user", default="admin")
    ap.add_argument("--password", default="Password123")
    ap.add_argument("--per-shop", type=int, default=4)
    ap.add_argument("--replace", action="store_true", help="ลบรูปเดิมก่อนอัปใหม่")
    ap.add_argument("--only", default=None, help="ทำเฉพาะหมวดนี้ (ใส่ slug)")
    ap.add_argument("--fetch", action="store_true",
                    help="โหลดรูปจาก tools/photo_urls.txt ก่อนอัป")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--allow-small", action="store_true",
                    help=f"ยอมใช้รูปที่กว้างน้อยกว่า {MIN_WIDTH} px (ภาพจะแตก)")
    args = ap.parse_args()

    base = args.base.rstrip("/")
    per_shop = max(1, min(args.per_shop, MAX_PER_SHOP))

    # ---------- โหลดรูปจากรายชื่อก่อน ถ้าสั่ง --fetch ----------
    if args.fetch:
        print("โหลดรูปจาก photo_urls.txt ...")
        fetch_photos()

    # ---------- รวบรวมรูปที่เตรียมไว้ ----------
    pools: dict[str, list[Path]] = {}
    if PHOTO_ROOT.exists():
        for folder in sorted(PHOTO_ROOT.iterdir()):
            if not folder.is_dir():
                continue
            files = sorted(p for p in folder.iterdir() if p.suffix.lower() in EXTS)
            if files:
                pools[folder.name] = files

    if not pools:
        print(f"ยังไม่มีรูปในโฟลเดอร์ {PHOTO_ROOT}")
        print("เอารูปใส่โฟลเดอร์ย่อยตามชื่อหมวดก่อน แล้วรันใหม่")
        print("ดูรายการรูปที่ต้องหาได้ที่ PHOTO_SHOPPING_LIST.md")
        return 1

    print("รูปที่เตรียมไว้:")
    for slug, files in pools.items():
        print(f"  {slug:16s} {len(files)} รูป")
    print()

    # ---------- ตรวจขนาดก่อน จะได้ไม่เสียเวลาอัปรูปที่ใช้ไม่ได้ ----------
    pools = check_photos(pools, args.allow_small)
    if not pools:
        print("ไม่เหลือรูปที่ใช้ได้เลย — โหลดไฟล์ขนาดเต็มมาใหม่แล้วรันอีกครั้ง")
        return 1

    # ---------- เข้าสู่ระบบ ----------
    print(f"เข้าสู่ระบบที่ {base} ด้วยบัญชี {args.user} ...")
    try:
        token = post_json(base, "/api/auth/login",
                          {"username": args.user, "password": args.password})["access_token"]
    except RuntimeError as exc:
        print(f"  เข้าสู่ระบบไม่สำเร็จ: {exc}")
        print("  ถ้าเป็นเว็บบน Render ต้องใส่ --password ให้ตรงกับ ADMIN_PASSWORD")
        return 1
    print("  สำเร็จ\n")

    # ---------- ดึงหมวดและร้าน ----------
    cats = _request(f"{base}/api/categories")
    cat_slug = {c["id"]: c["slug"] for c in cats}

    shops: list[dict] = []
    page = 1
    while True:
        res = _request(f"{base}/api/shops?page={page}&limit=50")
        shops.extend(res["items"])
        if page >= res["total_pages"]:
            break
        page += 1

    # จัดกลุ่มร้านตามหมวด เรียงตาม id ให้ผลลัพธ์คงที่ทุกครั้งที่รัน
    by_cat: dict[str, list[dict]] = {}
    for s in sorted(shops, key=lambda x: x["id"]):
        by_cat.setdefault(cat_slug.get(s["category_id"], "?"), []).append(s)

    ok = skipped = failed = 0

    for slug, shop_list in by_cat.items():
        if args.only and slug != args.only:
            continue
        pool = pools.get(slug)
        if not pool:
            print(f"[ข้าม] หมวด {slug} — ยังไม่มีรูปในโฟลเดอร์ ({len(shop_list)} ร้าน)")
            continue

        print(f"[{slug}] {len(shop_list)} ร้าน · คลังรูป {len(pool)} รูป")
        for idx, shop in enumerate(shop_list):
            sid, name = shop["id"], shop["name"]

            existing = _request(f"{base}/api/shops/{sid}/images")
            if existing and not args.replace:
                print(f"    - {name} — มีรูปแล้ว {len(existing)} รูป ข้าม")
                skipped += 1
                continue

            if existing and args.replace:
                for img in existing:
                    if not args.dry_run:
                        _request(f"{base}/api/shop-images/{img['id']}",
                                 method="DELETE", token=token)

            # หมุนจุดเริ่มตามลำดับร้าน ร้านที่อยู่ติดกันจะได้ไม่ใช้รูปชุดเดียวกันเป๊ะ
            picks = [pool[(idx * per_shop + k) % len(pool)] for k in range(per_shop)]

            if args.dry_run:
                print(f"    - {name} ← {', '.join(p.name for p in picks)}")
                ok += 1
                continue

            done = 0
            for photo in picks:
                try:
                    upload_file(base, f"/api/shops/{sid}/images", token, photo)
                    done += 1
                except RuntimeError as exc:
                    print(f"      ! {photo.name}: {exc}")
                    failed += 1
            # รูปแรกของร้านถูกตั้งเป็นปกให้อัตโนมัติแล้วโดย API
            print(f"    - {name} — อัปสำเร็จ {done} รูป")
            ok += 1
        print()

    print("─" * 50)
    print(f"เสร็จแล้ว · ร้านที่อัป {ok} · ข้าม {skipped} · รูปที่ล้มเหลว {failed}")
    if skipped:
        print("ร้านที่ถูกข้ามคือร้านที่มีรูปอยู่แล้ว — ใส่ --replace ถ้าต้องการเขียนทับ")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
