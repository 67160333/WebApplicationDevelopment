/* ============================================================
   GlowGo — Shared App Logic
   จัดการ: ธีม, navbar, auth mock, การจอง, แต้ม, รายการโปรด, รีวิว
   เก็บสถานะใน localStorage เพื่อจำลอง session จริง
   ============================================================ */

const Store = {
  key: "glowgo_state",
  _default: { user: null, bookings: [], points: 0, favorites: [], theme: "light", userReviews: {}, recent: [] },

  get() {
    try {
      return { ...this._default, ...(JSON.parse(localStorage.getItem(this.key)) || {}) };
    } catch {
      return { ...this._default };
    }
  },
  set(state) { localStorage.setItem(this.key, JSON.stringify(state)); },
  update(patch) { const next = { ...this.get(), ...patch }; this.set(next); return next; },
};

/* ---------- Theme (สลับ light/dark, จำค่า) ---------- */
const Theme = {
  current() { return Store.get().theme || "light"; },
  apply(t) { document.documentElement.dataset.theme = t; },
  init() { this.apply(this.current()); },
  toggle() {
    const next = this.current() === "dark" ? "light" : "dark";
    Store.update({ theme: next });
    this.apply(next);
    renderNav(window.__activeNav);
    toast(next === "dark" ? "🌙 โหมดกลางคืน" : "☀️ โหมดกลางวัน");
  },
};

/* ---------- Favorites (รายการโปรด) ---------- */
const Favorites = {
  list() { return Store.get().favorites || []; },
  has(id) { return this.list().includes(id); },
  toggle(id) {
    const s = Store.get();
    const set = new Set(s.favorites || []);
    set.has(id) ? set.delete(id) : set.add(id);
    s.favorites = [...set];
    Store.set(s);
    return set.has(id);
  },
};

/* ---------- User Reviews (รีวิวที่ผู้ใช้เขียน เก็บต่อร้าน) ---------- */
const Reviews = {
  forShop(shopId) { return (Store.get().userReviews || {})[shopId] || []; },
  add(shopId, review) {
    const s = Store.get();
    s.userReviews = s.userReviews || {};
    s.userReviews[shopId] = s.userReviews[shopId] || [];
    s.userReviews[shopId].unshift(review);
    Store.set(s);
  },
};

/* ---------- Recently viewed (ดูล่าสุด) ---------- */
const Recent = {
  list() { return Store.get().recent || []; },
  push(id) {
    const s = Store.get();
    s.recent = [id, ...(s.recent || []).filter(x => x !== id)].slice(0, 4);
    Store.set(s);
  },
};

/* ---------- Auth (mock) ---------- */
const Auth = {
  isLoggedIn() { return !!Store.get().user; },
  currentUser() { return Store.get().user; },
  login(name, email) { Store.update({ user: { name: name || "มายด์", email } }); },
  logout() { Store.update({ user: null }); location.href = resolvePath("index.html"); },
  requireLogin(redirectTo) {
    if (!this.isLoggedIn()) {
      const target = redirectTo || location.pathname.split("/").pop();
      location.href = resolvePath("pages/login.html") + "?next=" + encodeURIComponent(target);
      return false;
    }
    return true;
  },
};

/* ---------- Path helper ---------- */
function resolvePath(path) {
  const inPages = location.pathname.includes("/pages/");
  if (inPages) return path.startsWith("pages/") ? "../" + path : (path === "index.html" ? "../" + path : path);
  return path;
}

/* ---------- Navbar ---------- */
function renderNav(active) {
  window.__activeNav = active;
  const inPages = location.pathname.includes("/pages/");
  const base = inPages ? "../" : "";
  const p = inPages ? "" : "pages/";
  const user = Auth.currentUser();
  const favCount = Favorites.list().length;

  const userBlock = user
    ? `<a href="${base}pages/account.html" class="nav-user">👤 ${user.name}</a>
       <a href="#" onclick="Auth.logout();return false;">ออกจากระบบ</a>`
    : `<a href="${base}pages/login.html" class="btn btn-outline btn-sm">เข้าสู่ระบบ</a>`;

  const link = (href, label, key) =>
    `<a href="${href}" class="${active === key ? "active" : ""}">${label}</a>`;

  const themeIcon = Theme.current() === "dark" ? "☀️" : "🌙";

  document.getElementById("nav").innerHTML = `
    <nav class="nav glass"><div class="nav-inner">
      <a href="${base}index.html" class="brand">Glow<span>Go</span></a>
      <div class="nav-links">
        ${link(base + "index.html", "หน้าแรก", "home")}
        ${link(base + p + "search.html", "ค้นหา", "search")}
        ${link(base + p + "account.html", `การจอง${favCount ? " ♥" + favCount : ""}`, "account")}
        ${userBlock}
        <button class="theme-btn" title="สลับธีม" onclick="Theme.toggle()">${themeIcon}</button>
      </div>
    </div></nav>`;
}

/* ---------- Footer + background blob ---------- */
function renderFooter() {
  if (!document.querySelector(".blob3")) {
    const b = document.createElement("div");
    b.className = "blob3";
    document.body.appendChild(b);
  }
  const el = document.getElementById("footer");
  if (!el) return;
  const up = location.pathname.includes("/pages/") ? "../" : "";
  el.innerHTML = `
    <footer class="footer"><div class="container">
      <strong style="color:var(--primary)">GlowGo</strong> — จองบริการสุขภาพ &amp; ความงามครบวงจร ·
      โปรเจกต์แปลงจาก User Journey Map ·
      <a href="${up}docs/USER_JOURNEY.md">journey mapping</a>
    </div></footer>`;
}

/* ---------- Toast ---------- */
function toast(msg) {
  let t = document.querySelector(".toast");
  if (!t) { t = document.createElement("div"); t.className = "toast"; document.body.appendChild(t); }
  t.textContent = msg;
  t.classList.add("show");
  clearTimeout(t._timer);
  t._timer = setTimeout(() => t.classList.remove("show"), 2200);
}

/* ---------- helpers ---------- */
const money = (n) => "฿" + Number(n).toLocaleString("th-TH");
const starRow = (n) => "★".repeat(Math.round(n)) + "☆".repeat(5 - Math.round(n));

/* ---------- favorite button html + handler ---------- */
function favBtnHTML(shopId) {
  return `<button class="fav-btn ${Favorites.has(shopId) ? "on" : ""}" data-fav="${shopId}"
    onclick="toggleFav(event,'${shopId}')">${Favorites.has(shopId) ? "❤️" : "🤍"}</button>`;
}
function toggleFav(e, id) {
  e.preventDefault(); e.stopPropagation();
  const on = Favorites.toggle(id);
  const btn = e.currentTarget;
  btn.textContent = on ? "❤️" : "🤍";
  btn.classList.toggle("on", on);
  if (on) btn.classList.remove("on"), void btn.offsetWidth, btn.classList.add("on");
  toast(on ? "เพิ่มในรายการโปรด ❤️" : "นำออกจากรายการโปรด");
  renderNav(window.__activeNav);
}

/* ---------- init ทุกหน้า ---------- */
function initPage(activeKey) {
  Theme.init();
  renderNav(activeKey);
  renderFooter();
}
