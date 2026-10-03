-- ข้อมูลจำลองขนาดเท่าเว็บที่มีคนใช้จริงจำนวนมาก
--
--   ผู้ใช้   200,000 คน      ร้าน 2,000 ร้าน   ช่าง 6,000 คน (ร้านละ 3)
--   คิว   1,000,000 รายการ  ย้อนหลัง 21 เดือน + ล่วงหน้า 3 เดือน
--   เงิน   ~1,400,000 ก้อน  รีวิว ~180,000   แจ้งเตือน 1,000,000
--
-- setseed() ทำให้ทั้ง 2 database ได้ข้อมูลเหมือนกันทุกแถว เทียบเวลากันได้อย่างยุติธรรม
-- วันอ้างอิง "วันนี้" ของแล็บตายตัวที่ 2026-10-03 เพื่อให้รันซ้ำวันไหนก็ได้ผลเท่าเดิม
--
-- ความจริงที่ใส่ลงไปในข้อมูล (ไม่ใช่สุ่มเท่ากันหมด)
--   - ร้านดังมีคิวมากกว่าร้านทั่วไปมาก — ร้านที่ 1 มีราว 22,000 คิว ร้านท้าย ๆ มีหลักร้อย
--     ใช้ power(random(), 2) ให้เลขร้านน้อย ๆ ถูกสุ่มบ่อยกว่า
--   - คิวในอดีตส่วนใหญ่ใช้บริการเสร็จแล้ว คิวในอนาคตยังรอยืนยันหรือยืนยันแล้ว
--   - เงินของคิวในอดีตถูกปล่อยให้ร้านหมดแล้ว เงินที่ยังพักอยู่มีแค่ของคิวที่ยังไม่ถึง

\echo '>>> Seeding Bookvice lab data ... (1-3 นาที ขึ้นกับเครื่อง)'
SELECT setseed(0.42) \gset

INSERT INTO users (username, full_name, role)
SELECT 'user' || g, 'ผู้ใช้ ทดสอบ' || g, 'customer'
FROM generate_series(1, 200000) AS g;

INSERT INTO shops (owner_id, category_id, name, province, rating_avg, is_active)
SELECT 1 + floor(random() * 200000)::int,
       1 + floor(random() * 12)::int,
       'ร้านทดสอบ ' || g,
       (ARRAY['กรุงเทพมหานคร', 'กรุงเทพมหานคร', 'กรุงเทพมหานคร', 'นนทบุรี', 'ชลบุรี', 'เชียงใหม่'])[1 + floor(random() * 6)::int],
       round((3 + random() * 2)::numeric, 2),
       random() < 0.97
FROM generate_series(1, 2000) AS g;

INSERT INTO staff (shop_id, name)
SELECT (g - 1) / 3 + 1, 'ช่าง ' || g
FROM generate_series(1, 6000) AS g;

\echo '>>> bookings 1,000,000 rows ...'
INSERT INTO bookings (booking_code, user_id, shop_id, staff_id, service_id,
                      booking_date, booking_time, end_time,
                      total_price, deposit_amount, status, holds_slot, created_at)
SELECT 'BV' || lpad(x.g::text, 8, '0'),
       x.user_id,
       x.shop_id,
       (x.shop_id - 1) * 3 + 1 + floor(random() * 3)::int,
       x.shop_id * 3 + floor(random() * 3)::int,
       x.d,
       x.t,
       x.t + interval '1 hour',
       x.price,
       round(x.price * 0.2, 2),
       x.status,
       x.status = 'confirmed' OR (x.status = 'pending' AND x.r > 0.85),
       (x.d - floor(random() * 30)::int)::timestamptz + x.t
FROM (
  SELECT g,
         1 + floor(random() * 200000)::int                  AS user_id,
         1 + floor(2000 * power(random(), 2))::int          AS shop_id,
         DATE '2025-01-01' + floor(random() * 730)::int     AS d,
         TIME '10:00' + floor(random() * 20)::int * interval '30 minutes' AS t,
         (200 + floor(random() * 2800))::numeric            AS price,
         random()                                           AS r
  FROM generate_series(1, 1000000) AS g
) AS x0
-- คำนวณสถานะครั้งเดียวแล้วใช้สองที่ (status กับ holds_slot) ค่าจึงไม่ขัดกันเอง
CROSS JOIN LATERAL (
  SELECT x0.g, x0.user_id, x0.shop_id, x0.d, x0.t, x0.price, x0.r,
         CASE
           WHEN x0.d < DATE '2026-10-03' THEN CASE WHEN x0.r < 0.82 THEN 'completed' ELSE 'cancelled' END
           ELSE CASE WHEN x0.r < 0.70 THEN 'confirmed' ELSE 'pending' END
         END AS status
) AS x;

\echo '>>> payments ...'
-- มัดจำ: ทุกคิวที่ล็อกช่องเวลาแล้วหรือผ่านไปแล้ว
-- เงินสดอยู่ในมือร้านตั้งแต่แรก จึงถูกปล่อยทันที · ออนไลน์ของคิวที่ผ่านไปแล้วถูกปล่อยวันถัดไป
INSERT INTO payments (booking_id, kind, amount, method, status, paid_at, released_at)
SELECT p.id, 'deposit', p.deposit_amount, p.method,
       CASE WHEN p.status = 'cancelled' AND random() < 0.5 THEN 'refunded' ELSE 'paid' END,
       p.created_at,
       CASE WHEN p.method = 'cash' THEN p.created_at
            WHEN p.booking_date < DATE '2026-10-03' THEN p.booking_date + 1
            ELSE NULL END
FROM (
  SELECT b.*, CASE WHEN random() < 0.1 THEN 'cash' ELSE 'promptpay' END AS method
  FROM bookings b
  WHERE b.status <> 'pending' OR b.holds_slot
) AS p;

-- ยอดคงเหลือ: คิวที่ใช้บริการเสร็จแล้วราว 60% จ่ายส่วนที่เหลือผ่านเว็บ
INSERT INTO payments (booking_id, kind, amount, method, status, paid_at, released_at)
SELECT id, 'balance', total_price - deposit_amount, 'promptpay', 'paid',
       booking_date::timestamptz + booking_time,
       booking_date + 1
FROM bookings
WHERE status = 'completed' AND random() < 0.6;

\echo '>>> reviews ...'
INSERT INTO reviews (booking_id, user_id, shop_id, staff_id, rating, comment, created_at)
SELECT id, user_id, shop_id, staff_id,
       3 + floor(random() * 3)::int,
       CASE WHEN random() < 0.6 THEN 'บริการดี ช่างใส่ใจ รีวิวที่ ' || id END,
       booking_date::timestamptz + booking_time + interval '1 day' * (1 + floor(random() * 5))
FROM bookings
WHERE status = 'completed' AND random() < 0.22;

\echo '>>> notifications 1,000,000 rows ...'
INSERT INTO notifications (user_id, kind, title, is_read, created_at)
SELECT 1 + floor(random() * 200000)::int,
       (ARRAY['booking_confirmed', 'booking_completed', 'payment_received', 'booking_moved'])[1 + floor(random() * 4)::int],
       'แจ้งเตือนทดสอบ ' || g,
       random() < 0.85,
       TIMESTAMPTZ '2025-01-01' + random() * interval '640 days'
FROM generate_series(1, 1000000) AS g;

ANALYZE;
\echo '>>> Seed done'
