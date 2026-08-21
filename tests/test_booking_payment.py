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

ok = fail = 0


def check(label, got, want):
    global ok, fail
    if got == want:
        ok += 1
        print(f"  ✅ {label}")
    else:
        fail += 1
        print(f"  ❌ {label}  ได้ {got} ควรเป็น {want}")


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

    print("\n" + "=" * 60)
    print(f"สรุป: ผ่าน {ok} · ไม่ผ่าน {fail}")
    print("=" * 60)


try:
    main()
finally:
    os.unlink(DB)
raise SystemExit(1 if fail else 0)
