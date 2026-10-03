-- index ชุดใหม่ของ Bookvice (เฉพาะ bv_lab_index)
--
-- ชุดนี้คือชุดเดียวกับที่ใส่ในโปรเจกต์จริงแล้ว (app/models.py + app/migrate.py)
-- แต่ละตัวออกแบบจาก query ที่ระบบยิงจริง ไม่ได้ทำ index ทุกคอลัมน์
-- สร้างหลัง seed เพราะเร็วกว่าสร้างก่อนแล้วค่อยใส่ข้อมูลหลายเท่า (ดู labs/05-insert-cost.sql)

\echo '>>> Creating Bookvice indexes ...'

-- รอบที่ 1 เคยมี ix_bookings_user_date (user_id, booking_date, booking_time) และ
-- ix_notif_user_created (user_id, created_at) วัดแล้วไม่เร็วขึ้นแต่ใหญ่กว่า index เดี่ยว 4 เท่า
-- รอบที่ 2 จึงกลับไปใช้ index เดี่ยว (ผลรอบแรกเก็บไว้ใน results/round1/)

-- ---------- bookings ----------
-- หน้าจัดการร้าน: WHERE shop_id = ? ORDER BY booking_date DESC, booking_time DESC LIMIT 100
CREATE INDEX ix_bookings_shop_date ON bookings (shop_id, booking_date, booking_time);
-- หน้า "การจองของฉัน": WHERE user_id = ? (ลูกค้าคนหนึ่งมีไม่กี่คิว index เดี่ยวพอ)
CREATE INDEX ix_bookings_user_id ON bookings (user_id);
-- กันจองช่างคนเดียวกันเวลาเดียวกัน (ของจริงเป็น UNIQUE แต่ข้อมูลสุ่มอาจซ้ำ จึงทำแบบธรรมดา)
-- partial index: เก็บเฉพาะคิวที่ยังกันเวลาอยู่ ไม่ใช่ทั้งล้านแถว
CREATE INDEX ix_booking_held_slot ON bookings (shop_id, staff_id, booking_date, booking_time)
  WHERE holds_slot AND status IN ('pending', 'confirmed');
CREATE INDEX ix_bookings_staff_id ON bookings (staff_id);
CREATE INDEX ix_bookings_booking_date ON bookings (booking_date);

-- ---------- payments ----------
CREATE INDEX ix_payments_booking_id ON payments (booking_id);
-- ระบบพักเงินถามบ่อยว่า "เงินก้อนไหนยังพักอยู่" ซึ่งมีไม่กี่เปอร์เซ็นต์ของทั้งตาราง
-- partial index จึงเล็กกว่า index ทั้งคอลัมน์มาก
CREATE INDEX ix_payments_held ON payments (booking_id)
  WHERE status = 'paid' AND released_at IS NULL;

-- ---------- reviews ----------
-- หน้าร้าน: WHERE shop_id = ? ORDER BY created_at DESC LIMIT 10
CREATE INDEX ix_reviews_shop_created ON reviews (shop_id, created_at);
CREATE INDEX ix_reviews_staff_id ON reviews (staff_id);

-- ---------- notifications ----------
-- กล่องแจ้งเตือน: WHERE user_id = ? (แต่ละคนมีไม่กี่รายการ index เดี่ยวพอ)
CREATE INDEX ix_notifications_user_id ON notifications (user_id);
-- จุดแดงบนกระดิ่ง: นับเฉพาะที่ยังไม่อ่าน (ราว 15% ของทั้งหมด)
CREATE INDEX ix_notif_unread ON notifications (user_id) WHERE is_read = false;

ANALYZE;
\echo '>>> Indexes ready'
