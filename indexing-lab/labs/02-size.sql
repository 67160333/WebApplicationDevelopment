-- LAB 02: index ของ Bookvice ใช้พื้นที่เท่าไร (รันทั้ง 2 database)

\echo '\n===== ขนาดตารางเทียบกับ index ====='
SELECT relname                                         AS table_name,
       pg_size_pretty(pg_relation_size(relid))         AS table_size,
       pg_size_pretty(pg_indexes_size(relid))          AS index_size,
       pg_size_pretty(pg_total_relation_size(relid))   AS total_size
FROM pg_statio_user_tables
WHERE relname IN ('bookings', 'payments', 'reviews', 'notifications')
ORDER BY pg_relation_size(relid) DESC;

\echo '\n===== ขนาดของแต่ละ index (สังเกต partial index ตัวที่ขึ้นต้น ix_payments_held / ix_notif_unread / ix_booking_held_slot) ====='
SELECT relname      AS table_name,
       indexrelname AS index_name,
       pg_size_pretty(pg_relation_size(indexrelid)) AS size
FROM pg_stat_user_indexes
WHERE relname IN ('bookings', 'payments', 'reviews', 'notifications')
ORDER BY relname, pg_relation_size(indexrelid) DESC;

\echo '\n===== partial index เก็บกี่แถว เทียบกับทั้งตาราง ====='
SELECT 'payments ที่ยังพักเงินอยู่' AS what,
       count(*) FILTER (WHERE status = 'paid' AND released_at IS NULL) AS in_index,
       count(*) AS whole_table
FROM payments
UNION ALL
SELECT 'แจ้งเตือนที่ยังไม่อ่าน',
       count(*) FILTER (WHERE is_read = false), count(*)
FROM notifications
UNION ALL
SELECT 'คิวที่ยังกันเวลาอยู่',
       count(*) FILTER (WHERE holds_slot AND status IN ('pending', 'confirmed')), count(*)
FROM bookings;
