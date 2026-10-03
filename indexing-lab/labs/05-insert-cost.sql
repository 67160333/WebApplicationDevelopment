-- LAB 05: index ทำให้การจองใหม่ช้าลงแค่ไหน  (รันทั้ง 2 database แล้วเทียบเวลา)
--
-- ทุกคิวที่ลูกค้ากดจอง = INSERT 1 แถวในตาราง bookings
-- ทุก index บนตารางนั้นต้องถูกอัปเดตตามไปด้วย index ยิ่งเยอะ INSERT ยิ่งช้า
-- ใช้ ROLLBACK ข้อมูลจึงไม่เพิ่มจริง รันซ้ำได้
\timing on

\echo '\n===== INSERT คิวใหม่ 100,000 รายการ ====='
BEGIN;
INSERT INTO bookings (booking_code, user_id, shop_id, staff_id, service_id,
                      booking_date, booking_time, end_time, total_price, deposit_amount,
                      status, holds_slot, created_at)
SELECT 'NEW' || g,
       1 + floor(random() * 200000)::int,
       1 + floor(random() * 2000)::int,
       1 + floor(random() * 6000)::int,
       1 + floor(random() * 6000)::int,
       DATE '2026-10-03' + floor(random() * 90)::int,
       TIME '10:00' + floor(random() * 20)::int * interval '30 minutes',
       TIME '11:00' + floor(random() * 20)::int * interval '30 minutes',
       500, 100, 'confirmed', true, now()
FROM generate_series(1, 100000) AS g;
ROLLBACK;

\echo '\n===== จำนวน index บนตาราง bookings ของ database นี้ ====='
SELECT count(*) AS indexes_on_bookings FROM pg_indexes WHERE tablename = 'bookings';
