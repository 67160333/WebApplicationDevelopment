"""ทดสอบแบบเดินเรื่องจริง (end-to-end): เดินเส้นทางตั้งแต่เปิดร้านใหม่ -> ลูกค้าจอง -> จ่ายเงิน -> พักเงิน -> ปล่อยเงิน -> โอนเข้าร้าน
รันบน SQLite ชั่วคราว ไม่แตะฐานข้อมูลจริง

วิธีรัน: docker compose exec api python tests/e2e_open_shop.py (หรือดับเบิลคลิก run-tests.bat)
"""
import os, sys, tempfile
from datetime import date, timedelta, datetime, timezone

PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = tempfile.NamedTemporaryFile(suffix=".db", delete=False).name
os.environ.update({"DATABASE_URL": f"sqlite:///{DB}", "SEED_ON_START": "true",
                   "JWT_SECRET": "e2e", "SERVE_WEB": "false", "UPLOAD_DIR": tempfile.mkdtemp()})
sys.path.insert(0, PROJ)
import app.main as m
m.run_migrations = lambda e: None
from fastapi.testclient import TestClient
from app.database import SessionLocal
from app.models import Booking, Payment

problems = []
def step(n, label, r, want=(200, 201)):
    good = r.status_code in (want if isinstance(want, tuple) else (want,))
    print(f"{'OK ' if good else 'BAD'} {n:>2}. {label}  [{r.status_code}]")
    if not good:
        print("      ", r.text[:300]); problems.append(label)
    return r.json() if r.headers.get("content-type", "").startswith("application/json") else None

def H(tok): return {"Authorization": f"Bearer {tok}"}

with TestClient(m.app) as c:
    o = step(1, "สมัครเป็นเจ้าของร้าน", c.post("/api/auth/register", json={
        "username": "newowner", "email": "newowner@example.com", "password": "Password123",
        "full_name": "เจ้าของ ร้านใหม่", "role": "owner"}), 201)
    ow = H(o["access_token"])
    cat = c.get("/api/categories").json()[0]
    shop = step(2, "สร้างร้าน (หยุดวันจันทร์)", c.post("/api/shops", headers=ow, json={
        "category_id": cat["id"], "name": "ร้านทดสอบเปิดใหม่", "district": "บางรัก",
        "open_time": "09:00:00", "close_time": "20:00:00", "closed_weekdays": "1"}), 201)
    sid = shop["id"]
    svc = step(3, "เพิ่มบริการ 800 บาท 60 นาที", c.post(f"/api/shops/{sid}/services", headers=ow,
        json={"name": "ตัดผมชาย", "price": 800, "duration_minutes": 60}), 201)
    st = step(4, "เพิ่มช่าง + ความถนัด", c.post(f"/api/shops/{sid}/staff", headers=ow, json={
        "name": "ช่างบีม", "position": "ช่างตัดผม", "specialties": "ตัดผมชาย, ไถข้าง",
        "experience_years": 5, "work_days": "0,2,3,4,5,6"}), 201)
    step(5, "ตั้งบัญชีธนาคารรับเงิน", c.put(f"/api/shops/{sid}/bank", headers=ow, json={
        "bank_name": "กสิกรไทย", "bank_account_no": "1234567890", "bank_account_name": "ร้านทดสอบ"}))

    # ลูกค้า
    cu = c.post("/api/auth/register", json={"username": "newcust", "email": "newcust@example.com",
        "password": "Password123", "full_name": "ลูกค้า ทดสอบ"})
    cust = H(step(6, "ลูกค้าสมัครสมาชิก", cu, 201)["access_token"])
    found = c.get("/api/shops?search=เปิดใหม่").json()["items"]
    print(f"{'OK ' if any(s['id']==sid for s in found) else 'BAD'}  7. ลูกค้าค้นเจอร้านใหม่ในหน้ารายการร้าน")
    prof = step(8, "เปิดหน้าโปรไฟล์ช่าง", c.get(f"/api/staff/{st['id']}"))
    print(f"      ความถนัด: {prof.get('specialties')} · ประสบการณ์ {prof.get('experience_years')} ปี")

    d = date.today() + timedelta(days=3)
    while d.weekday() == 0:      # วันจันทร์ร้านหยุด
        d += timedelta(days=1)
    bk = step(9, f"จองคิว {d} 10:00 กับช่างบีม", c.post("/api/bookings", headers=cust, json={
        "service_id": svc["id"], "staff_id": st["id"], "booking_date": str(d), "booking_time": "10:00:00"}), 201)
    bid = bk["id"]
    print(f"      ราคา {bk['total_price']} · มัดจำ {bk['deposit_amount']}")
    step(10, "ลูกค้าคนเดิมกดจองช่องเดิมซ้ำ (ต้องถูกปฏิเสธ)", c.post("/api/bookings", headers=cust, json={
        "service_id": svc["id"], "staff_id": st["id"], "booking_date": str(d), "booking_time": "10:00:00"}), 409)
    step(11, "จ่ายมัดจำ PromptPay (จำลอง)", c.post(f"/api/bookings/{bid}/payment", headers=cust,
        json={"kind": "deposit", "method": "promptpay"}), 201)
    w = c.get(f"/api/shops/{sid}/wallet", headers=ow).json()
    print(f"      กระเป๋าร้าน: พักไว้ {w['held']} · ถอนได้ {w['available_net']}")
    step(12, "ร้านกดยืนยันคิว", c.patch(f"/api/bookings/{bid}/status", headers=ow, json={"status": "confirmed"}))
    step(13, "ร้านกดเสร็จงานก่อนถึงเวลานัด (ต้องถูกปฏิเสธ)",
         c.patch(f"/api/bookings/{bid}/status", headers=ow, json={"status": "completed"}), (400, 409, 422))

    # เลื่อนเวลา: ให้คิวนี้เป็นของเมื่อวาน (เหมือนวันนัดผ่านไปแล้ว)
    db = SessionLocal(); b = db.get(Booking, bid); b.booking_date = date.today() - timedelta(days=1); db.commit(); db.close()
    step(14, "ลูกค้าจ่ายยอดคงเหลือ", c.post(f"/api/bookings/{bid}/payment", headers=cust,
        json={"kind": "balance", "method": "card"}), 201)
    step(15, "ร้านกดเสร็จงาน (หลังเวลานัด)", c.patch(f"/api/bookings/{bid}/status", headers=ow, json={"status": "completed"}))
    w = c.get(f"/api/shops/{sid}/wallet", headers=ow).json()
    print(f"      กระเป๋าร้าน: พักไว้ {w['held']} · ถอนได้ {w['available_net']}  <- เงินยังไม่ถึงร้าน")
    step(16, "ร้านกดถอนตอนเงินยังพัก (ต้องถูกปฏิเสธ)", c.post(f"/api/shops/{sid}/payouts", headers=ow), (400, 409, 422))
    step(17, "ลูกค้ากด 'ได้รับบริการแล้ว'", c.post(f"/api/bookings/{bid}/confirm-service", headers=cust))
    w = c.get(f"/api/shops/{sid}/wallet", headers=ow).json()
    print(f"      กระเป๋าร้าน: พักไว้ {w['held']} · ถอนได้ {w['available_gross']} - ค่าธรรมเนียม {w['available_fee']} = {w['available_net']}")
    p = step(18, "ร้านกดโอนเข้าบัญชี", c.post(f"/api/shops/{sid}/payouts", headers=ow), 201)
    if p: print(f"      โอน {p['net']} เข้า {p['account_label']} · อ้างอิง {p['reference']}")

    # เส้นทางที่ 2: ลูกค้าแจ้งปัญหา -> แอดมินตัดสินคืนเงิน
    d2 = d + timedelta(days=1)
    while d2.weekday() == 0: d2 += timedelta(days=1)
    b2 = c.post("/api/bookings", headers=cust, json={"service_id": svc["id"], "staff_id": st["id"],
        "booking_date": str(d2), "booking_time": "11:00:00"}).json()["id"]
    c.post(f"/api/bookings/{b2}/payment", headers=cust, json={"kind": "deposit", "method": "promptpay"})
    c.patch(f"/api/bookings/{b2}/status", headers=ow, json={"status": "confirmed"})
    db = SessionLocal(); x = db.get(Booking, b2); x.booking_date = date.today() - timedelta(days=1); db.commit(); db.close()
    c.post(f"/api/bookings/{b2}/payment", headers=cust, json={"kind": "balance", "method": "promptpay"})
    c.patch(f"/api/bookings/{b2}/status", headers=ow, json={"status": "completed"})
    step(19, "ลูกค้าแจ้งปัญหา (เงินถูกล็อก)", c.post(f"/api/bookings/{b2}/dispute", headers=cust,
        json={"note": "ช่างตัดผมไม่ตรงกับที่ตกลงไว้เลย"}))
    adm = H(c.post("/api/auth/login", json={"username": "admin", "password": "Password123"}).json().get("access_token", ""))
    q = c.get("/api/admin/disputes", headers=adm)
    print(f"{'OK ' if q.status_code==200 and any(x['booking_id']==b2 for x in q.json()) else 'BAD'} 20. แอดมินเห็นเรื่องในคิวข้อพิพาท [{q.status_code}]")
    step(21, "แอดมินตัดสินคืนเงินลูกค้า", c.post(f"/api/bookings/{b2}/resolve-dispute", headers=adm,
        json={"decision": "refund", "reason": "ร้านยอมรับว่าผิดพลาด"}))
    db = SessionLocal()
    st2 = [(p.kind, p.status) for p in db.query(Payment).filter(Payment.booking_id == b2)]
    db.close()
    print(f"      สถานะเงินคิวที่ 2: {st2}")
    w = c.get(f"/api/shops/{sid}/wallet", headers=ow).json()
    print(f"      กระเป๋าร้านตอนจบ: พักไว้ {w['held']} · ถอนได้ {w['available_net']} · โอนแล้วรวม {w['paid_out_total']}")

print("\nผล:", "ผ่านทุกขั้น" if not problems else f"มีปัญหา {len(problems)} ขั้น: {problems}")
