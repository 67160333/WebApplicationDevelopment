-- LAB 03: index ชุดเดิมของโปรเจกต์ vs ชุดใหม่  (รันบน bv_lab_index)
--
-- ก่อนทำแล็บนี้ Bookvice มี index อยู่แล้ว แต่เป็น index "คอลัมน์เดียว" ที่ได้จาก
-- index=True ใน models.py ทีละคอลัมน์ ไม่ได้ออกแบบจาก query จริง
-- แล็บนี้สลับกลับไปใช้ชุดเดิมชั่วคราว (ใน transaction) แล้วรัน query ชุดเดียวกับ LAB 01
-- ท้ายไฟล์ ROLLBACK คืนชุดใหม่ให้เอง รันซ้ำได้
\timing on

BEGIN;

-- ถอดตัวที่ชุดใหม่เพิ่มเข้ามา (ix_bookings_user_id กับ ix_notifications_user_id มีทั้งสองชุด จึงไม่ต้องแตะ)
DROP INDEX ix_bookings_shop_date;
DROP INDEX ix_payments_held;
DROP INDEX ix_reviews_shop_created;
DROP INDEX ix_notif_unread;

-- ใส่ตัวที่ชุดเดิมมีแต่ชุดใหม่ถอดออก (ตรงกับ models.py ก่อนแก้ — index=True ทีละคอลัมน์)
CREATE INDEX old_bookings_shop_id   ON bookings (shop_id);
CREATE INDEX old_bookings_status    ON bookings (status);
CREATE INDEX old_payments_status    ON payments (status);
CREATE INDEX old_reviews_shop_id    ON reviews (shop_id);
CREATE INDEX old_notif_is_read      ON notifications (is_read);
CREATE INDEX old_notif_user_unread  ON notifications (user_id, is_read);
ANALYZE bookings, payments, reviews, notifications;

\echo '\n===== [ชุดเดิม] Q1 หน้าจอง: ร้าน + วันที่ ====='
\echo '      ทั้งสองชุดใช้ ix_booking_held_slot เหมือนกัน (partial index ขึ้นต้นด้วย shop_id)'
EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM bookings
WHERE shop_id = 1 AND booking_date = '2026-10-10'
  AND status IN ('pending', 'confirmed') AND holds_slot;

\echo '\n===== [ชุดเดิม] Q3 หน้าจัดการร้าน: index shop_id อย่างเดียว ต้องดึงคิวทั้งร้าน (~22,000) มาเรียงก่อนตัด 100 ====='
EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM bookings WHERE shop_id = 1
ORDER BY booking_date DESC, booking_time DESC LIMIT 100;

\echo '\n===== [ชุดเดิม] Q4 รีวิวร้าน ====='
EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM reviews WHERE shop_id = 1 ORDER BY created_at DESC LIMIT 10;

\echo '\n===== [ชุดเดิม] Q5 ระบบพักเงิน: index status มีค่า paid เกือบทั้งตาราง ช่วยอะไรไม่ได้ ====='
EXPLAIN (ANALYZE, BUFFERS)
SELECT b.id FROM bookings b
WHERE b.status = 'completed'
  AND b.id IN (SELECT booking_id FROM payments WHERE status = 'paid' AND released_at IS NULL);

\echo '\n===== [ชุดเดิม] Q6 จุดแดงบนกระดิ่ง: index (user_id, is_read) ทั้งตาราง ====='
EXPLAIN (ANALYZE, BUFFERS)
SELECT count(*) FROM notifications WHERE user_id = 4242 AND is_read = false;

\echo '\n===== ขนาดรวมของ index ชุดเดิม (ก่อน ROLLBACK) ====='
SELECT relname AS table_name, pg_size_pretty(pg_indexes_size(relid)) AS index_size
FROM pg_statio_user_tables
WHERE relname IN ('bookings', 'payments', 'reviews', 'notifications')
ORDER BY relname;

ROLLBACK;  -- คืน index ชุดใหม่ทั้งหมด

\echo '\n===== ขนาดรวมของ index ชุดใหม่ (หลัง ROLLBACK) ====='
SELECT relname AS table_name, pg_size_pretty(pg_indexes_size(relid)) AS index_size
FROM pg_statio_user_tables
WHERE relname IN ('bookings', 'payments', 'reviews', 'notifications')
ORDER BY relname;
