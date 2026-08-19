# ใช้ base image ตามที่เอกสารประกอบการสอนแนะนำ
FROM python:3.12-slim

# ตั้งค่า environment ให้ Python ทำงานเหมาะกับ container
#   PYTHONDONTWRITEBYTECODE : ไม่สร้างไฟล์ .pyc
#   PYTHONUNBUFFERED        : ให้ log ออกมาทันที ไม่ค้างใน buffer
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# ติดตั้ง dependency ก่อน copy โค้ด เพื่อให้ Docker ใช้ layer cache ได้
# (ถ้าแก้แค่โค้ด ไม่ต้องติดตั้ง library ใหม่ทั้งหมด → build เร็วขึ้นมาก)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# คัดลอกซอร์สโค้ดเข้า image
COPY ./app ./app

# พอร์ตที่ uvicorn เปิดฟังอยู่
EXPOSE 8000

# รันด้วย uvicorn ตามที่เอกสารกำหนด
# ต้องใช้ --host 0.0.0.0 เพื่อให้เข้าถึงได้จากนอก container (ถ้าใช้ 127.0.0.1 จะเข้าไม่ได้)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
