/* ============================================================
   GlowGo — หน้าการจองของฉัน (Stage 5: หลังใช้บริการ / ซ้ำ)
   แดชบอร์ดสถิติ · แต้มสะสม · รายการโปรด · การจอง+รีวิว+จองซ้ำ
   ============================================================ */

initPage("account");

const view = document.getElementById("accountView");

if (!Auth.isLoggedIn()) {
  Auth.requireLogin("account.html");
}

function render() {
  const s = Store.get();
  const user = s.user || { name: "ผู้ใช้" };
  const bookings = s.bookings || [];
  const points = s.points || 0;
  const favs = (s.favorites || []).map(getShopById).filter(Boolean);

  const totalSpent = bookings.reduce((a, b) => a + (b.paid ?? b.deposit ?? 0), 0);

  const statsHTML = `
    <div class="stat-grid">
      <div class="stat glass"><div class="big">${bookings.length}</div><div class="lbl">การจองทั้งหมด</div></div>
      <div class="stat glass"><div class="big">${money(totalSpent)}</div><div class="lbl">ยอดชำระรวม</div></div>
      <div class="stat glass"><div class="big">${points}</div><div class="lbl">แต้มสะสม</div></div>
      <div class="stat glass"><div class="big">${favs.length}</div><div class="lbl">ร้านโปรด ❤️</div></div>
    </div>`;

  const bookingsHTML = bookings.length
    ? bookings.map(bookingCard).join("")
    : `<div class="empty glass" style="border-radius:18px">ยังไม่มีการจอง · <a href="search.html" style="color:var(--primary)">ค้นหาบริการเลย</a></div>`;

  const favsHTML = favs.length
    ? `<div class="shop-grid">${favs.map(favCard).join("")}</div>`
    : `<div class="empty glass" style="border-radius:18px">ยังไม่มีร้านโปรด · กด 🤍 ที่ร้านที่ถูกใจได้เลย</div>`;

  view.innerHTML = `
    <h1 class="page-title">สวัสดี ${user.name} 👋</h1>
    <p class="page-sub">ภาพรวมการใช้งานและการจองของคุณ</p>

    ${statsHTML}

    <div class="points-card reveal">
      <div class="hint" style="color:#fff;opacity:.9">แต้มสะสม GlowGo</div>
      <div class="num">${points} <span style="font-size:18px">แต้ม</span></div>
      <div style="opacity:.95">ทุก 100 บาท = 1 แต้ม · ใช้เป็นส่วนลดมัดจำการจองครั้งต่อไปได้</div>
    </div>

    <h2 style="margin:24px 0 14px">❤️ ร้านโปรดของฉัน</h2>
    ${favsHTML}

    <h2 style="margin:28px 0 14px">🗓️ การจองของฉัน</h2>
    <div id="bookingList">${bookingsHTML}</div>`;

  bindCardEvents();
}

function favCard(s) {
  return `
    <div class="shop-card glass">
      ${favBtnHTML(s.id)}
      <a href="shop.html?id=${s.id}">
        <div class="shop-thumb">${s.image}</div>
        <div class="shop-body">
          <h3>${s.name}</h3>
          <div class="shop-meta">${getCategoryName(s.category)} · ${s.zone}</div>
          <div><span class="badge badge-rating">★ ${s.rating}</span></div>
          <div class="shop-price">เริ่ม ${money(s.priceFrom)}</div>
        </div>
      </a>
    </div>`;
}

function bookingCard(b) {
  return `
    <div class="card glass" style="margin-bottom:16px">
      <div style="display:flex;gap:16px;align-items:center;flex-wrap:wrap">
        <div class="shop-thumb" style="width:70px;border-radius:14px;font-size:36px;padding:14px 0">${b.shopImage}</div>
        <div style="flex:1;min-width:200px">
          <h3>${b.shopName}</h3>
          <div class="shop-meta">${b.service} · ${b.date} ${b.time}</div>
          <div>
            <span class="badge badge-cert">✔ ยืนยันแล้ว</span>
            <span class="hint">จ่าย ${money(b.paid ?? b.deposit)}${b.discount ? " (ใช้แต้ม -" + money(b.discount) + ")" : ""} · เหลือจ่ายที่ร้าน ${money(b.price - b.deposit)}</span>
          </div>
        </div>
        <div style="display:flex;flex-direction:column;gap:8px">
          <a href="booking.html?id=${b.shopId}" class="btn btn-outline btn-sm">จองซ้ำ</a>
          ${b.reviewed
            ? '<span class="badge badge-rating" style="text-align:center;padding:8px">★ รีวิวแล้ว</span>'
            : `<button class="btn btn-primary btn-sm" data-review="${b.id}">เขียนรีวิว</button>`}
        </div>
      </div>
      <div id="reviewBox-${b.id}"></div>
    </div>`;
}

function bindCardEvents() {
  document.querySelectorAll("[data-review]").forEach(btn =>
    btn.addEventListener("click", () => openReview(btn.dataset.review)));
}

function openReview(bookingId) {
  const box = document.getElementById("reviewBox-" + bookingId);
  box.innerHTML = `
    <div style="border-top:1px solid var(--line);margin-top:14px;padding-top:14px">
      <div class="star-input" id="star-${bookingId}">
        ${[5,4,3,2,1].map(v => `
          <input type="radio" name="star-${bookingId}" id="s${bookingId}-${v}" value="${v}" ${v === 5 ? "checked" : ""}>
          <label for="s${bookingId}-${v}">★</label>`).join("")}
      </div>
      <div class="form-group" style="margin-top:10px">
        <textarea id="text-${bookingId}" rows="2" placeholder="บริการเป็นอย่างไรบ้าง?"></textarea>
      </div>
      <button class="btn btn-primary btn-sm" data-submit="${bookingId}">ส่งรีวิว</button>
    </div>`;
  box.querySelector("[data-submit]").addEventListener("click", () => submitReview(bookingId));
}

function submitReview(bookingId) {
  const s = Store.get();
  const b = s.bookings.find(x => x.id === bookingId);
  if (!b) return;
  const rating = +document.querySelector(`input[name="star-${bookingId}"]:checked`).value;
  const text = (document.getElementById("text-" + bookingId).value || "").trim();
  b.reviewed = true;
  s.points = (s.points || 0) + 5; // โบนัสรีวิว
  s.userReviews = s.userReviews || {};
  s.userReviews[b.shopId] = s.userReviews[b.shopId] || [];
  s.userReviews[b.shopId].unshift({ user: s.user?.name || "ผู้ใช้", rating, text: text || "บริการดี", verified: true });
  Store.set(s);
  toast("ขอบคุณสำหรับรีวิว! +5 แต้ม 🎉");
  render();
}

render();
