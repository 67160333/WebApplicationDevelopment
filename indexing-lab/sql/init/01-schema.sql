-- โครงตารางของ Bookvice (ใช้ทั้ง 2 database)
--
-- ชื่อตารางและชื่อคอลัมน์ตรงกับ app/models.py ทุกตัว query ในแล็บจึงเหมือนที่ระบบยิงจริง
-- ตัดคอลัมน์ที่ไม่เกี่ยวกับการค้นหาออก (เช่น ข้อมูลสุขภาพ ลิงก์รูป) ให้ seed เร็วขึ้น
--
-- ไม่ใส่ FOREIGN KEY โดยตั้งใจ — PostgreSQL ไม่สร้าง index ให้ FK อัตโนมัติอยู่แล้ว
-- (ต่างจาก MySQL) ถ้าใส่ก็ไม่เปลี่ยนผลแล็บ แต่จะทำให้ seed ช้าลงมาก

CREATE TABLE users (
  id         SERIAL PRIMARY KEY,
  username   VARCHAR(50)  NOT NULL,
  full_name  VARCHAR(150) NOT NULL,
  role       VARCHAR(20)  NOT NULL DEFAULT 'customer'
);

CREATE TABLE shops (
  id          SERIAL PRIMARY KEY,
  owner_id    INT          NOT NULL,
  category_id INT          NOT NULL,
  name        VARCHAR(150) NOT NULL,
  province    VARCHAR(100) NOT NULL,
  rating_avg  NUMERIC(3,2) NOT NULL DEFAULT 0,
  is_active   BOOLEAN      NOT NULL DEFAULT TRUE
);

CREATE TABLE staff (
  id      SERIAL PRIMARY KEY,
  shop_id INT          NOT NULL,
  name    VARCHAR(100) NOT NULL
);

-- ตารางหลักของแล็บ — ทุกหน้าที่เกี่ยวกับการจองอ่านตารางนี้
CREATE TABLE bookings (
  id            BIGSERIAL PRIMARY KEY,
  booking_code  VARCHAR(20)   NOT NULL,
  user_id       INT           NOT NULL,
  shop_id       INT           NOT NULL,
  staff_id      INT,
  service_id    INT           NOT NULL,
  booking_date  DATE          NOT NULL,
  booking_time  TIME          NOT NULL,
  end_time      TIME          NOT NULL,
  total_price   NUMERIC(10,2) NOT NULL,
  deposit_amount NUMERIC(10,2) NOT NULL,
  status        VARCHAR(20)   NOT NULL,
  holds_slot    BOOLEAN       NOT NULL DEFAULT FALSE,
  created_at    TIMESTAMPTZ   NOT NULL
);

-- เงินแต่ละก้อน — released_at ว่าง = ยังพักอยู่ในระบบพักเงิน (ดู app/routers/escrow.py)
CREATE TABLE payments (
  id          BIGSERIAL PRIMARY KEY,
  booking_id  BIGINT        NOT NULL,
  kind        VARCHAR(10)   NOT NULL,
  amount      NUMERIC(10,2) NOT NULL,
  method      VARCHAR(15)   NOT NULL,
  status      VARCHAR(10)   NOT NULL,
  paid_at     TIMESTAMPTZ   NOT NULL,
  released_at TIMESTAMPTZ,
  payout_id   INT
);

CREATE TABLE reviews (
  id         BIGSERIAL PRIMARY KEY,
  booking_id BIGINT       NOT NULL,
  user_id    INT          NOT NULL,
  shop_id    INT          NOT NULL,
  staff_id   INT,
  rating     INT          NOT NULL,
  comment    VARCHAR(1000),
  created_at TIMESTAMPTZ  NOT NULL
);

CREATE TABLE notifications (
  id         BIGSERIAL PRIMARY KEY,
  user_id    INT          NOT NULL,
  kind       VARCHAR(40)  NOT NULL,
  title      VARCHAR(150) NOT NULL,
  is_read    BOOLEAN      NOT NULL DEFAULT FALSE,
  created_at TIMESTAMPTZ  NOT NULL
);
