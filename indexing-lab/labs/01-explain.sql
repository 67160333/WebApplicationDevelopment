-- LAB 01: query จริงของ Bookvice — เทียบ plan และเวลา (รันบนทั้ง 2 database แล้วเทียบกัน)
--
-- ทุกข้อคัดมาจากโค้ดจริง บอกไว้ในหัวข้อว่ามาจากไฟล์และฟังก์ชันไหน
-- ค่าที่ใช้ค้นหา: ร้าน 1 = ร้านที่คิวเยอะที่สุด (~22,000 คิว) · ผู้ใช้ 4242 = ลูกค้าทั่วไป
\timing on

-- อุ่น cache ให้ทั้งสอง database เท่ากันก่อน ไม่งั้นข้อแรกจะช้าเพราะอ่านดิสก์ ไม่ใช่เพราะ index
\o /dev/null
SELECT count(*) FROM bookings;
SELECT count(*) FROM payments;
SELECT count(*) FROM reviews;
SELECT count(*) FROM notifications;
\o

\echo '\n===== Q1 หน้าจอง: ช่วงเวลาที่ถูกจองแล้วของร้านในวันหนึ่ง ====='
\echo '      (app/routers/bookings.py :: _busy_intervals — เปิดหน้าร้าน 1 ครั้งยิง 14 รอบ เพื่อดูเวลาว่างล่วงหน้า 14 วัน)'
EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM bookings
WHERE shop_id = 1 AND booking_date = '2026-10-10'
  AND status IN ('pending', 'confirmed') AND holds_slot;

\echo '\n===== Q1b หน้าจอง: เลือกช่างคนเดียว ====='
EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM bookings
WHERE shop_id = 1 AND booking_date = '2026-10-10' AND staff_id = 2
  AND status IN ('pending', 'confirmed') AND holds_slot;

\echo '\n===== Q2 หน้า "การจองของฉัน": 10 คิวล่าสุดของลูกค้า ====='
\echo '      (app/routers/bookings.py :: list_bookings — role customer)'
EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM bookings
WHERE user_id = 4242
ORDER BY booking_date DESC, booking_time DESC
LIMIT 10;

\echo '\n===== Q2b นับจำนวนคิวทั้งหมดของลูกค้า (ใช้ทำเลขหน้า) ====='
EXPLAIN (ANALYZE, BUFFERS)
SELECT count(*) FROM bookings WHERE user_id = 4242;

\echo '\n===== Q3 หน้าจัดการร้าน: 100 คิวล่าสุดของร้านดัง ====='
\echo '      (app/routers/bookings.py :: list_bookings — role owner)'
EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM bookings
WHERE shop_id = 1
ORDER BY booking_date DESC, booking_time DESC
LIMIT 100;

\echo '\n===== Q4 หน้าร้าน: รีวิวล่าสุด 10 รายการ ====='
\echo '      (app/routers/bookings.py :: list_reviews)'
EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM reviews
WHERE shop_id = 1
ORDER BY created_at DESC
LIMIT 10;

\echo '\n===== Q5 ระบบพักเงิน แบบรอบที่ 1: ตรวจทุกคิวในระบบ ====='
\echo '      (app/routers/escrow.py :: release_due รุ่นแรก — ยิงทุกครั้งที่มีคนเปิดรายการจอง)'
EXPLAIN (ANALYZE, BUFFERS)
SELECT b.id FROM bookings b
WHERE b.status = 'completed'
  AND b.id IN (SELECT booking_id FROM payments WHERE status = 'paid' AND released_at IS NULL);

\echo '\n===== Q5b ระบบพักเงิน แบบที่แก้แล้ว: ตรวจเฉพาะร้านที่เปิดกระเป๋าเงิน ====='
\echo '      (release_due(db, shop_id=...) — index ช่วยได้เต็มที่เพราะขอบเขตแคบ)'
EXPLAIN (ANALYZE, BUFFERS)
SELECT b.id FROM bookings b
WHERE b.shop_id = 1 AND b.status = 'completed'
  AND b.id IN (SELECT booking_id FROM payments WHERE status = 'paid' AND released_at IS NULL);

\echo '\n===== Q5c ระบบพักเงิน แบบที่แก้แล้ว: ตรวจเฉพาะ 10 คิวในหน้าที่เปิดอยู่ ====='
\echo '      (release_due(db, booking_ids=[...]) — หน้ารายการจองของลูกค้า)'
EXPLAIN (ANALYZE, BUFFERS)
SELECT b.id FROM bookings b
WHERE b.id IN (11, 22, 33, 44, 55, 66, 77, 88, 99, 110) AND b.status = 'completed'
  AND b.id IN (SELECT booking_id FROM payments WHERE status = 'paid' AND released_at IS NULL);

\echo '\n===== Q6 จุดแดงบนกระดิ่ง: นับแจ้งเตือนที่ยังไม่อ่าน ====='
\echo '      (app/routers/notifications.py :: unread_count — ยิงทุกหน้าที่ล็อกอินอยู่)'
EXPLAIN (ANALYZE, BUFFERS)
SELECT count(*) FROM notifications WHERE user_id = 4242 AND is_read = false;

\echo '\n===== Q7 กล่องแจ้งเตือน: 20 รายการล่าสุด ====='
\echo '      (app/routers/notifications.py :: list_notifications)'
EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM notifications
WHERE user_id = 4242
ORDER BY created_at DESC, id DESC
LIMIT 20;
