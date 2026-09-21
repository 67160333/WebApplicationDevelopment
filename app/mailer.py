"""ส่งอีเมล — ใช้ Resend ถ้าตั้งค่าไว้ ถ้าไม่ตั้งก็พิมพ์ลง log แทน

ทำไมต้องมีโหมด "พิมพ์ลง log"
============================================================
ระบบลืมรหัสผ่านจะทดสอบไม่ได้เลยถ้าไม่มีคีย์ส่งอีเมล ซึ่งแปลว่า
ต้องไปสมัครบริการภายนอกก่อนถึงจะเขียนโค้ดต่อได้ — ติดกันเป็นลูกโซ่

โหมดนี้ทำให้ฟีเจอร์ใช้งานและทดสอบได้ทันทีตั้งแต่วันแรก
พอวันไหนใส่ RESEND_API_KEY เข้ามา มันจะเปลี่ยนไปส่งจริงเองโดยไม่ต้องแก้โค้ด

**ข้อควรระวัง** โหมด log เหมาะกับตอนพัฒนาเท่านั้น
บนเว็บจริงถ้าไม่ตั้งคีย์ ลิงก์ตั้งรหัสผ่านใหม่จะไปโผล่ใน log ของเซิร์ฟเวอร์
ซึ่งคนที่เข้าถึง log ได้จะเห็น จึงเตือนดัง ๆ ตอนเริ่มระบบ
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request

from app.config import settings

RESEND_ENDPOINT = "https://api.resend.com/emails"


def mail_is_live() -> bool:
    return bool(settings.RESEND_API_KEY)


def send_email(to: str, subject: str, html: str, text: str = "") -> bool:
    """ส่งอีเมลหนึ่งฉบับ คืน True เมื่อส่งออกไปแล้วจริง

    ไม่โยน exception ออกไปไม่ว่ากรณีใด — การส่งอีเมลล้มเหลวไม่ควรทำให้
    คำขอของผู้ใช้พังทั้งก้อน ตัวเรียกจะตัดสินใจเองว่าจะบอกผู้ใช้ว่าอย่างไร
    """
    if not mail_is_live():
        print("=" * 70)
        print(f"[อีเมลจำลอง] ถึง: {to}")
        print(f"[อีเมลจำลอง] เรื่อง: {subject}")
        print(f"[อีเมลจำลอง] เนื้อหา:\n{text or html}")
        print("ตั้ง RESEND_API_KEY เพื่อส่งอีเมลจริง")
        print("=" * 70)
        return False

    payload = json.dumps({
        "from": settings.MAIL_FROM,
        "to": [to],
        "subject": subject,
        "html": html,
        **({"text": text} if text else {}),
    }).encode("utf-8")

    req = urllib.request.Request(
        RESEND_ENDPOINT,
        data=payload,
        headers={
            "Authorization": f"Bearer {settings.RESEND_API_KEY}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        # ตั้งเพดานเวลาไว้ ไม่งั้นถ้า Resend ช้า คำขอของผู้ใช้จะค้างตามไปด้วย
        with urllib.request.urlopen(req, timeout=10) as res:
            return 200 <= res.status < 300
    except urllib.error.HTTPError as exc:
        print(f"ส่งอีเมลไม่สำเร็จ ({exc.code}): {exc.read()[:300]!r}")
    except Exception as exc:
        print(f"ส่งอีเมลไม่สำเร็จ: {exc}")
    return False


def reset_password_email(link: str, minutes: int) -> tuple[str, str, str]:
    """คืน (หัวข้อ, html, ข้อความล้วน) ของอีเมลตั้งรหัสผ่านใหม่

    ส่งทั้งสองรูปแบบ เพราะโปรแกรมอ่านอีเมลบางตัวปิด HTML ไว้
    และอีเมลที่มีแต่ HTML มีโอกาสโดนคัดเป็นสแปมสูงกว่า
    """
    subject = "ตั้งรหัสผ่านใหม่ของ Bookvice"
    text = (
        "มีคำขอตั้งรหัสผ่านใหม่สำหรับบัญชี Bookvice ของคุณ\n\n"
        f"เปิดลิงก์นี้เพื่อตั้งรหัสผ่านใหม่ (ใช้ได้ {minutes} นาที และใช้ได้ครั้งเดียว):\n"
        f"{link}\n\n"
        "ถ้าคุณไม่ได้เป็นคนขอ ไม่ต้องทำอะไร รหัสผ่านเดิมยังใช้ได้ตามปกติ\n\n"
        "— Bookvice (โปรเจกต์รายวิชา 89033167)"
    )
    html = f"""<!DOCTYPE html><html lang="th"><body style="margin:0;padding:24px;background:#eef7ff;
font-family:'Noto Sans Thai Looped','IBM Plex Sans Thai',Tahoma,sans-serif;color:#0f1b2d">
<div style="max-width:520px;margin:0 auto;background:#fff;border:1px solid #dfe8f4;border-radius:10px;padding:28px">
  <p style="margin:0 0 4px;font-size:18px;font-weight:600">ตั้งรหัสผ่านใหม่</p>
  <p style="margin:0 0 20px;font-size:15px;line-height:1.8;color:#66748a">
    มีคำขอตั้งรหัสผ่านใหม่สำหรับบัญชี Bookvice ของคุณ
    กดปุ่มด้านล่างเพื่อตั้งรหัสใหม่ ลิงก์นี้ใช้ได้ {minutes} นาที และใช้ได้ครั้งเดียว
  </p>
  <a href="{link}" style="display:inline-block;background:#1a63d8;color:#fff;text-decoration:none;
     padding:12px 26px;border-radius:6px;font-size:15px;font-weight:600">ตั้งรหัสผ่านใหม่</a>
  <p style="margin:22px 0 0;font-size:13px;line-height:1.7;color:#96a2b4;word-break:break-all">
    ถ้าปุ่มกดไม่ได้ คัดลอกลิงก์นี้ไปวางในเบราว์เซอร์<br />{link}
  </p>
  <hr style="border:0;border-top:1px solid #dfe8f4;margin:22px 0" />
  <p style="margin:0;font-size:13px;line-height:1.7;color:#66748a">
    <b>ถ้าคุณไม่ได้เป็นคนขอ ไม่ต้องทำอะไร</b> รหัสผ่านเดิมยังใช้ได้ตามปกติ
  </p>
  <p style="margin:14px 0 0;font-size:12px;color:#96a2b4">
    Bookvice · โปรเจกต์รายวิชา 89033167 Web Application Development
  </p>
</div></body></html>"""
    return subject, html, text
