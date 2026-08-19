// ============================================================
// ตัวช่วยเรียก API และจัดการ token — ใช้ร่วมกันทุกหน้า
// ============================================================

// ที่อยู่ของ API — ต้องทำงานได้ทั้งสองแบบโดยไม่ต้องแก้ไฟล์
//
//   พอร์ต 3000 = รันด้วย Docker Compose ในเครื่อง
//                nginx เสิร์ฟหน้าเว็บที่ 3000 · API อยู่คนละพอร์ตที่ 8000
//
//   พอร์ตอื่น   = FastAPI เสิร์ฟทั้งหน้าเว็บและ API จากที่เดียวกัน
//                (เช่นบน Hugging Face Space ที่เปิดได้พอร์ตเดียว)
//                ใช้ค่าว่างเพื่อให้เรียกแบบ same-origin
const API_BASE = location.port === "3000"
  ? `${location.protocol}//${location.hostname}:8000`
  : "";

// ---------- ชื่อคีย์ที่เก็บไว้ในเครื่องผู้ใช้ ----------
const STORE_TOKEN = "bookvice_token";
const STORE_USER = "bookvice_user";

// ย้ายข้อมูลจากคีย์เดิมสมัยยังชื่อ GlowGo มาที่ชื่อใหม่ — ทำครั้งเดียวตอนโหลดหน้า
// ถ้าเปลี่ยนชื่อเฉย ๆ คนที่ค้างล็อกอินไว้จะถูกเตะออกทั้งหมด
// โดยที่เขาไม่ได้ทำอะไรผิด และไม่มีอะไรอธิบายให้เข้าใจ
(function migrateStorageKeys() {
  const pairs = [
    ["glowgo_token", STORE_TOKEN],
    ["glowgo_user", STORE_USER],
    ["glowgo_favorites", "bookvice_favorites"],
  ];
  try {
    for (const [before, after] of pairs) {
      const value = localStorage.getItem(before);
      if (value === null) continue;
      if (localStorage.getItem(after) === null) localStorage.setItem(after, value);
      localStorage.removeItem(before);
    }
  } catch { /* เบราว์เซอร์ปิด localStorage อยู่ ปล่อยผ่าน หน้าอื่นยังทำงานได้ */ }
})();

// ---------- จัดการ token / ผู้ใช้ที่ล็อกอินอยู่ ----------
const Auth = {
  get token() {
    return localStorage.getItem(STORE_TOKEN);
  },
  get user() {
    try {
      const raw = localStorage.getItem(STORE_USER);
      return raw ? JSON.parse(raw) : null;
    } catch {
      // ข้อมูลเสีย ให้ถือว่ายังไม่ล็อกอิน ดีกว่าปล่อยให้ทุกหน้าพังตั้งแต่บรรทัดแรก
      return null;
    }
  },
  save(token, user) {
    localStorage.setItem(STORE_TOKEN, token);
    localStorage.setItem(STORE_USER, JSON.stringify(user));
  },
  clear() {
    localStorage.removeItem(STORE_TOKEN);
    localStorage.removeItem(STORE_USER);
  },
  get isLoggedIn() {
    return !!this.token;
  },
  // บังคับให้ล็อกอินก่อนเข้าหน้านี้ แล้วพากลับมาที่เดิม
  requireLogin() {
    // ต้องมีทั้ง token และข้อมูลผู้ใช้
    //
    // ถ้าเช็กแค่ token แล้วข้อมูลผู้ใช้เสียหาย (JSON พังหรือถูกลบไป)
    // โค้ดหลังจากนี้จะอ่าน Auth.user.role ทันทีแล้วพังตั้งแต่บรรทัดแรกของหน้า
    // ผู้ใช้จะเห็นหน้าขาวเปล่า ๆ และออกจากระบบเองก็ไม่ได้เพราะปุ่มยังไม่ถูกวาด
    if (!this.isLoggedIn || !this.user) {
      this.clear();
      location.href = `login.html?next=${encodeURIComponent(currentPage())}`;
      return false;
    }
    return true;
  },
};

// ตรวจว่า token หมดอายุหรือยัง โดยอ่านจากตัว token เอง (ไม่ต้องเรียกเซิร์ฟเวอร์)
// กันกรณีแถบเมนูแสดงว่าล็อกอินอยู่ ทั้งที่ token ใช้ไม่ได้แล้ว
function isTokenExpired(token) {
  try {
    const payload = JSON.parse(atob(token.split(".")[1]));
    return typeof payload.exp === "number" && payload.exp * 1000 <= Date.now();
  } catch {
    return true; // อ่านไม่ออก ถือว่าใช้ไม่ได้
  }
}

// เรียกตอนเปิดหน้า — ถ้า token หมดอายุให้ล้างทิ้งทันที
function clearExpiredSession() {
  const t = Auth.token;
  if (t && isTokenExpired(t)) {
    Auth.clear();
    return true;
  }
  return false;
}

// หน้าปัจจุบันพร้อม query string เช่น "shop.html?id=1"
function currentPage() {
  const file = location.pathname.split("/").pop() || "index.html";
  return file + location.search;
}

// ตรวจว่า next ที่ส่งมาเป็นหน้าในเว็บเราจริง (กันการพาไปเว็บอื่น)
function safeNext(next) {
  if (!next) return null;
  try {
    next = decodeURIComponent(next);
  } catch {
    return null;
  }
  // ต้องเป็นไฟล์ .html ของเราเอง ห้ามมี / หรือ : นำหน้า
  return /^[\w-]+\.html(\?[^#]*)?$/.test(next) ? next : null;
}

// ---------- เรียก API ----------
async function api(path, options = {}) {
  const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
  if (Auth.token) headers["Authorization"] = `Bearer ${Auth.token}`;

  let res;
  try {
    res = await fetch(`${API_BASE}${path}`, { ...options, headers });
  } catch {
    throw new Error("เชื่อมต่อเซิร์ฟเวอร์ไม่ได้ กรุณาตรวจสอบว่าระบบทำงานอยู่");
  }

  // token หมดอายุหรือถูกยกเลิก → พาไปล็อกอิน แล้วกลับมาหน้าเดิม
  if (res.status === 401 && Auth.isLoggedIn) {
    Auth.clear();
    const next = encodeURIComponent(currentPage());
    location.href = `login.html?expired=1&next=${next}`;
    throw new Error("เซสชันหมดอายุ");
  }

  let data = null;
  if (res.status !== 204) {
    try {
      data = await res.json();
    } catch {
      data = null;
    }
  }

  if (!res.ok) throw new Error(formatError(data, res.status));
  return data;
}

// แปลง error ของ FastAPI ให้อ่านง่าย
// (422 จาก Pydantic จะมาเป็น array บอกว่า field ไหนผิด)
function formatError(data, status) {
  if (!data) return `เกิดข้อผิดพลาด (${status})`;
  const d = data.detail;
  if (typeof d === "string") return d;
  if (Array.isArray(d)) {
    return d
      .map((e) => {
        const field = (e.loc || []).filter((x) => x !== "body").join(".");
        return field ? `${field}: ${e.msg}` : e.msg;
      })
      .join("\n");
  }
  return `เกิดข้อผิดพลาด (${status})`;
}

// อัปโหลดไฟล์ — ใช้ XMLHttpRequest แทน fetch เพราะต้องรายงานความคืบหน้าให้ผู้ใช้เห็น
// (fetch ยังอ่านความคืบหน้าตอน "อัปโหลดขึ้น" ไม่ได้ อ่านได้แค่ตอนดาวน์โหลดลงมา)
function apiUpload(path, file, onProgress) {
  return new Promise((resolve, reject) => {
    const form = new FormData();
    form.append("file", file);

    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${API_BASE}${path}`);
    if (Auth.token) xhr.setRequestHeader("Authorization", `Bearer ${Auth.token}`);
    // ไม่ตั้ง Content-Type เอง ต้องปล่อยให้เบราว์เซอร์ใส่ boundary ของ multipart ให้
    // ถ้าตั้งเองเซิร์ฟเวอร์จะแยกส่วนของไฟล์ไม่ออก

    if (typeof onProgress === "function") {
      xhr.upload.onprogress = (e) => {
        if (e.lengthComputable) onProgress(Math.round((e.loaded / e.total) * 100));
      };
    }

    xhr.onload = () => {
      let data = null;
      try {
        data = JSON.parse(xhr.responseText);
      } catch {
        data = null;
      }
      if (xhr.status >= 200 && xhr.status < 300) return resolve(data);
      if (xhr.status === 401 && Auth.isLoggedIn) {
        Auth.clear();
        location.href = `login.html?expired=1&next=${encodeURIComponent(currentPage())}`;
      }
      reject(new Error(formatError(data, xhr.status)));
    };
    xhr.onerror = () => reject(new Error("อัปโหลดไม่สำเร็จ กรุณาตรวจสอบการเชื่อมต่อ"));
    xhr.send(form);
  });
}

const apiGet = (p) => api(p);
const apiPost = (p, body) => api(p, { method: "POST", body: JSON.stringify(body) });
const apiPut = (p, body) => api(p, { method: "PUT", body: JSON.stringify(body) });
const apiPatch = (p, body) => api(p, { method: "PATCH", body: JSON.stringify(body) });
const apiDelete = (p) => api(p, { method: "DELETE" });

// ---------- จัดรูปแบบข้อมูลสำหรับแสดงผล ----------
const baht = (n) =>
  Number(n).toLocaleString("th-TH", { minimumFractionDigits: 0, maximumFractionDigits: 2 });

const thaiDate = (iso) =>
  new Date(iso.length === 10 ? iso + "T00:00:00" : iso).toLocaleDateString("th-TH", {
    day: "numeric",
    month: "long",
    year: "numeric",
  });

const shortTime = (t) => (t ? String(t).slice(0, 5) : "");

// วันที่ในรูปแบบ YYYY-MM-DD ตามเวลาเครื่องผู้ใช้
// (ไม่ใช้ toISOString เพราะแปลงเป็น UTC แล้ววันจะเพี้ยนตอนดึก)
function localDate(d = new Date()) {
  const p = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
}

// วันที่ของวันนี้ + n วัน
function dateAfter(days) {
  const d = new Date();
  d.setDate(d.getDate() + days);
  return d;
}

// หนีอักขระพิเศษ ป้องกันข้อความจากผู้ใช้ทำให้หน้าเว็บเพี้ยน
function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c])
  );
}
