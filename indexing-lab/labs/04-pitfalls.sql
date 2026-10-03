-- LAB 04: มี index แต่ไม่ถูกใช้ — กรณีที่เจอในโค้ด Bookvice เอง  (รันบน bv_lab_index)
-- ให้ทายก่อนรันแต่ละข้อว่าจะได้ Seq Scan หรือ Index Scan
\timing on

\echo '\n===== 4.1 ❌ ครอบคอลัมน์ด้วยฟังก์ชัน: คิวของร้าน 1 ในเดือนสิงหาคม ====='
\echo '      ix_bookings_shop_date ใช้ได้แค่ shop_id ส่วนวันที่ต้องไล่คำนวณ to_char ทุกแถวของร้าน'
EXPLAIN (ANALYZE, BUFFERS)
SELECT count(*) FROM bookings
WHERE shop_id = 1 AND to_char(booking_date, 'YYYY-MM') = '2026-08';

\echo '\n===== 4.1 ✅ เขียนเป็นช่วงวันที่ตรง ๆ ใช้ index ได้ทั้งสองคอลัมน์ ====='
EXPLAIN (ANALYZE, BUFFERS)
SELECT count(*) FROM bookings
WHERE shop_id = 1 AND booking_date >= '2026-08-01' AND booking_date < '2026-09-01';

\echo '\n===== 4.2 ค้นหาร้านด้วยคำ (shops.py :: list_shops ใช้ ILIKE ''%คำ%'') ====='
\echo '      ตาราง shops มีแค่ 2,000 แถว — ทำ index ชื่อร้านไปก็ไม่ช่วย'
\echo '      (1) % นำหน้า B-tree ใช้ไม่ได้อยู่แล้ว (2) ตารางเล็กมาก อ่านทั้งตารางเร็วกว่าเปิด index'
BEGIN;
CREATE INDEX tmp_shops_name ON shops (name);
ANALYZE shops;
EXPLAIN (ANALYZE, BUFFERS) SELECT * FROM shops WHERE is_active AND name ILIKE '%ทดสอบ 12%';
EXPLAIN (ANALYZE, BUFFERS) SELECT * FROM shops WHERE name = 'ร้านทดสอบ 1234';
ROLLBACK;

\echo '\n===== 4.3 คอลัมน์ค่าซ้ำเยอะ: index บน bookings.status (ชุดเดิมของโปรเจกต์มีตัวนี้) ====='
\echo '      รอบที่ 1 พบว่า count(*) ใช้ index นี้ได้จริง (Index Only Scan) แม้ค่า completed มี 70%'
\echo '      แต่ระบบไม่เคยค้นด้วย status ตัวเดียว — ดึงแถวจริงตามสถานะแล้วเทียบกับไม่มี index'
BEGIN;
CREATE INDEX tmp_bookings_status ON bookings (status);
ANALYZE bookings;
\echo '      [มี index] count(*) status = completed'
EXPLAIN (ANALYZE, BUFFERS) SELECT count(*) FROM bookings WHERE status = 'completed';
\echo '      [มี index] ดึงแถวทั้งหมดของ status = completed (ต้องไปอ่านแถวจริงทุกแถว)'
EXPLAIN (ANALYZE, BUFFERS) SELECT sum(total_price) FROM bookings WHERE status = 'completed';
ROLLBACK;
\echo '      [ไม่มี index] ดึงแถวทั้งหมดของ status = completed'
EXPLAIN (ANALYZE, BUFFERS) SELECT sum(total_price) FROM bookings WHERE status = 'completed';

\echo '\n===== 4.4 partial index ต้องเขียนเงื่อนไขให้ตรงกัน ====='
\echo '      ix_notif_unread สร้างด้วย WHERE is_read = false'
\echo '      แบบที่ 1: is_read = false (ตรงกับ index)'
EXPLAIN (ANALYZE, BUFFERS)
SELECT count(*) FROM notifications WHERE user_id = 4242 AND is_read = false;
\echo '      แบบที่ 2: is_read IS false (SQLAlchemy เขียน .is_(False) จะได้แบบนี้)'
EXPLAIN (ANALYZE, BUFFERS)
SELECT count(*) FROM notifications WHERE user_id = 4242 AND is_read IS false;
\echo '      ตรวจกับผู้ใช้ที่มีแจ้งเตือนยังไม่อ่านจริง (ดูว่า IS false ต้องไปอ่านแถวมากกว่าแค่ไหน)'
EXPLAIN (ANALYZE, BUFFERS)
SELECT count(*) FROM notifications WHERE user_id < 2000 AND is_read = false;
EXPLAIN (ANALYZE, BUFFERS)
SELECT count(*) FROM notifications WHERE user_id < 2000 AND is_read IS false;

\echo '\n===== 4.5 ข้ามคอลัมน์ซ้ายสุดของ composite (leftmost rule) ====='
\echo '      ix_bookings_shop_date เริ่มที่ shop_id — ถามด้วยวันที่อย่างเดียว ใช้ตัวนี้ไม่ได้'
\echo '      (แต่ยังมี ix_bookings_booking_date แยกไว้ ซึ่ง matches.py ใช้หาก๊วนรายวัน)'
EXPLAIN (ANALYZE, BUFFERS)
SELECT count(*) FROM bookings WHERE booking_date = '2026-10-10';
