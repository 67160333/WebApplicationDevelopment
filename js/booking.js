/* ============================================================
   GlowGo — หน้าจอง & ชำระเงิน (Stage 4)
   จองจบหน้าเดียว: เลือกบริการ → วัน-เวลา → แลกแต้ม → จ่ายมัดจำ
   แก้ pain point "กังวล": คุ้มครองมัดจำ + ราคาชัด + จองน้อยขั้นตอน
   ============================================================ */

initPage("");

const shopId = new URLSearchParams(location.search).get("id");
const shop = getShopById(shopId);
const view = document.getElementById("bookingView");

if (!Auth.isLoggedIn()) {
  Auth.requireLogin("booking.html?id=" + shopId);
}

if (!shop) {
  view.innerHTML = `<div class="empty glass" style="border-radius:18px">ไม่พบร้าน · <a href="search.html" style="color:var(--primary)">กลับไปค้นหา</a></div>`;
} else {
  const taken = new Set(["12:00", "15:00"]);
  const state = { serviceIdx: 0, slot: null, method: "promptpay", usefPoints: false };

  const depositOf = (price) => Math.round(price * 0.3);
  const todayStr = () => new Date().toISOString().slice(0, 10);
  const availablePoints = () => Store.get().points || 0;

  function render() {
    const sv = shop.services[state.serviceIdx];
    const deposit = depositOf(sv.price);
    const discount = state.usefPoints ? Math.min(availablePoints(), deposit) : 0;
    const payNow = deposit - discount;

    view.innerHTML = `
      <a href="shop.html?id=${shop.id}" class="hint">← กลับไปหน้าร้าน</a>
      <span class="emotion-tag" style="display:block;margin:12px 0">ขั้นที่ 4 · กังวล = Moment of Truth — เราคุ้มครองมัดจำและแสดงราคาชัดเจน</span>
      <h1 class="page-title">จองคิว · ${shop.name}</h1>

      <div class="stepper">
        <div class="step done">1. เลือกบริการ</div>
        <div class="step ${state.slot ? "done" : ""}">2. เลือกวัน-เวลา</div>
        <div class="step">3. ชำระมัดจำ</div>
      </div>

      <div style="display:grid;grid-template-columns:1.4fr 1fr;gap:22px" class="bk-grid">
        <div>
          <div class="card glass" style="margin-bottom:20px">
            <h3 style="margin-bottom:12px">1. เลือกบริการ</h3>
            <div class="form-group">
              <select id="svSelect">
                ${shop.services.map((s, i) =>
                  `<option value="${i}" ${i === state.serviceIdx ? "selected" : ""}>${s.name} — ${money(s.price)} (${s.duration} นาที)</option>`
                ).join("")}
              </select>
            </div>
          </div>

          <div class="card glass" style="margin-bottom:20px">
            <h3 style="margin-bottom:12px">2. เลือกวันและเวลา</h3>
            <div class="form-group">
              <label>วันที่</label>
              <input type="date" id="dateInput" value="${todayStr()}" min="${todayStr()}">
            </div>
            <label style="font-weight:700;font-size:14px">เวลาที่ว่าง</label>
            <div class="slot-grid" id="slots" style="margin-top:8px">
              ${TIME_SLOTS.map(t => `
                <div class="slot ${taken.has(t) ? "taken" : ""} ${state.slot === t ? "selected" : ""}" data-t="${t}">${t}</div>
              `).join("")}
            </div>
          </div>

          <div class="card glass">
            <h3 style="margin-bottom:12px">3. วิธีชำระมัดจำ</h3>
            <div class="form-group">
              <label><input type="radio" name="pay" value="promptpay" ${state.method === "promptpay" ? "checked" : ""} style="width:auto"> พร้อมเพย์ (PromptPay)</label>
              <label style="margin-top:8px"><input type="radio" name="pay" value="card" ${state.method === "card" ? "checked" : ""} style="width:auto"> บัตรเครดิต/เดบิต</label>
            </div>
          </div>
        </div>

        <div>
          <div class="card glass" style="position:sticky;top:90px">
            <h3 style="margin-bottom:12px">สรุปการจอง</h3>
            <div class="summary-row"><span>ร้าน</span><strong>${shop.name}</strong></div>
            <div class="summary-row"><span>บริการ</span><strong>${sv.name}</strong></div>
            <div class="summary-row"><span>วัน-เวลา</span><strong>${state.slot ? (document.getElementById("dateInput")?.value || todayStr()) + " " + state.slot : "ยังไม่เลือก"}</strong></div>
            <div class="summary-row"><span>ราคาเต็ม</span><span>${money(sv.price)}</span></div>
            <div class="summary-row"><span>มัดจำ (30%)</span><span>${money(deposit)}</span></div>

            ${availablePoints() > 0 ? `
            <label style="display:flex;gap:8px;align-items:center;margin:10px 0;font-size:14px;font-weight:600">
              <input type="checkbox" id="usePoints" ${state.usefPoints ? "checked" : ""} style="width:auto">
              ใช้แต้มเป็นส่วนลด (มี ${availablePoints()} แต้ม = ${money(availablePoints())})
            </label>` : `<p class="hint">จองครั้งนี้จะได้รับ ${Math.round(sv.price / 100)} แต้ม</p>`}

            ${discount > 0 ? `<div class="summary-row"><span>ส่วนลดจากแต้ม</span><strong style="color:var(--ok)">- ${money(discount)}</strong></div>` : ""}
            <div class="summary-row"><span>จ่ายที่ร้าน</span><span>${money(sv.price - deposit)}</span></div>
            <div class="summary-row total"><span>ชำระตอนนี้</span><span>${money(payNow)}</span></div>
            <p class="hint" style="margin:10px 0">🛡️ มัดจำได้รับการคุ้มครอง — หากร้านยกเลิก คืนเต็มจำนวน</p>
            <button class="btn btn-primary btn-block" id="payBtn" ${state.slot ? "" : "disabled"}>
              ${state.slot ? "ยืนยันจอง & จ่าย " + money(payNow) : "เลือกเวลาก่อนจอง"}
            </button>
          </div>
        </div>
      </div>`;

    document.getElementById("svSelect").addEventListener("change", (e) => { state.serviceIdx = +e.target.value; render(); });
    document.querySelectorAll(".slot:not(.taken)").forEach(el =>
      el.addEventListener("click", () => { state.slot = el.dataset.t; render(); }));
    document.querySelectorAll('input[name="pay"]').forEach(el =>
      el.addEventListener("change", (e) => { state.method = e.target.value; }));
    const up = document.getElementById("usePoints");
    if (up) up.addEventListener("change", (e) => { state.usefPoints = e.target.checked; render(); });
    const payBtn = document.getElementById("payBtn");
    if (payBtn) payBtn.addEventListener("click", confirmBooking);
    const dateEl = document.getElementById("dateInput");
    if (dateEl) dateEl.addEventListener("change", render);
  }

  function confirmBooking() {
    const sv = shop.services[state.serviceIdx];
    const deposit = depositOf(sv.price);
    const discount = state.usefPoints ? Math.min(availablePoints(), deposit) : 0;
    const date = document.getElementById("dateInput").value || todayStr();

    const s = Store.get();
    const earned = Math.round(sv.price / 100);
    const booking = {
      id: "bk" + Date.now(),
      shopId: shop.id, shopName: shop.name, shopImage: shop.image,
      service: sv.name, price: sv.price, deposit,
      discount, paid: deposit - discount,
      date, time: state.slot, method: state.method,
      status: "confirmed", reviewed: false,
    };
    s.bookings = s.bookings || [];
    s.bookings.unshift(booking);
    s.points = (s.points || 0) - discount + earned; // หักที่ใช้ + ได้แต้มใหม่
    Store.set(s);

    toast("จองสำเร็จ! +" + earned + " แต้ม 🎉");
    setTimeout(() => location.href = "account.html", 1000);
  }

  render();

  const style = document.createElement("style");
  style.textContent = "@media(max-width:760px){.bk-grid{grid-template-columns:1fr!important}}";
  document.head.appendChild(style);
}
