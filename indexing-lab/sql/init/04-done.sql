-- ป้ายบอกว่าเตรียมฐานข้อมูลเสร็จแล้ว — run-lab.bat รอจนเห็นตารางนี้ก่อนเริ่มรันแล็บ
CREATE TABLE lab_ready (ready_at TIMESTAMPTZ DEFAULT now());
INSERT INTO lab_ready DEFAULT VALUES;
VACUUM ANALYZE;
\echo '>>> Lab ready'
