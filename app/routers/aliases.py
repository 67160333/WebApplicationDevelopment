"""เส้นทางตามรูปแบบที่โจทย์กำหนดเป๊ะ ๆ

โจทย์ระบุเส้นทางแบบไม่มี /api นำหน้า เช่น POST /register, GET /me, GET /users
ไฟล์นี้จึงเปิดเส้นทางชุดนั้นเพิ่มให้ โดยเรียกใช้ฟังก์ชันตัวเดียวกันกับ router หลัก
(ไม่ได้เขียนโค้ดซ้ำ — แค่ผูก path เพิ่ม) ทำให้เรียกได้ทั้งสองแบบ:

    POST /register            เท่ากับ   POST /api/auth/register
    GET  /me                  เท่ากับ   GET  /api/users/me
    GET  /users               เท่ากับ   GET  /api/users
"""

from fastapi import APIRouter, Depends

from app.routers import auth, users
from app.schemas import (
    Message,
    Page,
    TokenResponse,
    UserOut,
    UsernameAvailable,
)
from app.security import require_roles

# ใช้เลข 9 เพื่อให้ต่อท้ายหมวด 1-8 ใน Swagger
# เดิมใช้เลข 5 ซึ่งชนกับ "5. Staff Profiles" ทำให้หน้า /docs มีหัวข้อเลข 5 สองอัน
router = APIRouter(tags=["9. เส้นทางตามรูปแบบในโจทย์"])

# ---------- 1. Authentication ----------
router.add_api_route(
    "/register", auth.register, methods=["POST"],
    response_model=TokenResponse, status_code=201, summary="สมัครสมาชิก",
)
router.add_api_route(
    "/login", auth.login, methods=["POST"],
    response_model=TokenResponse, summary="เข้าสู่ระบบ",
)
router.add_api_route(
    "/logout", auth.logout, methods=["POST"],
    response_model=Message, summary="ออกจากระบบ",
)
router.add_api_route(
    "/change-password", auth.change_password, methods=["POST"],
    response_model=Message, summary="เปลี่ยนรหัสผ่าน",
)

# ---------- 2. User Management ----------
router.add_api_route(
    "/me", users.get_me, methods=["GET"],
    response_model=UserOut, summary="ดึงข้อมูลตัวเอง",
)
router.add_api_route(
    "/check-username/{name}", users.check_username, methods=["GET"],
    response_model=UsernameAvailable, summary="ตรวจสอบ username ว่างไหม",
)
router.add_api_route(
    "/users", users.list_users, methods=["GET"],
    response_model=Page[UserOut],
    dependencies=[Depends(require_roles("admin"))],
    summary="ดึงข้อมูล user ทั้งหมด (pagination)",
)
router.add_api_route(
    "/users/{user_id}", users.get_user, methods=["GET"],
    response_model=UserOut, summary="ดึงข้อมูล user",
)
router.add_api_route(
    "/users/{user_id}", users.update_user, methods=["PUT"],
    response_model=UserOut, summary="แก้ไขข้อมูล user",
)
router.add_api_route(
    "/users/{user_id}", users.delete_user, methods=["DELETE"],
    response_model=Message, summary="ลบ user",
)
