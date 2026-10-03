-- LAB 06: index ไหนถูกใช้จริง index ไหนไม่เคยถูกใช้  (รันบน bv_lab_index หลังรัน LAB 01-04 แล้ว)
--
-- PostgreSQL นับให้เองว่าแต่ละ index ถูกใช้ไปกี่ครั้ง (idx_scan)
-- บนเว็บจริงใช้คำสั่งเดียวกันนี้ได้ (ต่อเข้าฐานข้อมูลบน Neon) เพื่อหา index ที่ไม่มีใครใช้
-- index ที่ idx_scan = 0 นาน ๆ คือภาระฟรี: กินพื้นที่และทำให้ INSERT ช้า โดยไม่ช่วยอะไร

SELECT relname      AS table_name,
       indexrelname AS index_name,
       idx_scan     AS times_used,
       pg_size_pretty(pg_relation_size(indexrelid)) AS size
FROM pg_stat_user_indexes
WHERE relname IN ('bookings', 'payments', 'reviews', 'notifications')
ORDER BY idx_scan, relname;
