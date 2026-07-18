/* ============================================================
   GlowGo — หน้าโปรไฟล์ร้าน (Stage 3 ต่อ)
   ข้อมูลร้าน · บริการ+ราคา · รีวิวจริง+เขียนรีวิว(ดาว) · โปรด
   ============================================================ */

initPage("search");

const shopId = new URLSearchParams(location.search).get("id");
const shop = getShopById(shopId);
const view = document.getElementById("shopView");

if (!shop) {
  view.innerHTML = `<div class="empty glass" style="border-radius:18px">ไม่พบร้านนี้ · <a href="search.html" style="color:var(--primary)">กลับไปค้นหา</a></div>`;
} else {
  Recent.push(shop.id); // บันทึกว่าเพิ่งดูร้านนี้

  function allReviews() {
    // รวมรีวิว mock + รีวิวที่ผู้ใช้เขียน
    return [...Reviews.forShop(shop.id), ...shop.reviews];
  }

  function avgRating() {
    const rs = allReviews();
    if (!rs.length) return shop.rating;
    const sum = rs.reduce((a, r) => a + r.rating, 0);
    return (sum / rs.length).toFixed(1);
  }

  function render() {
    const servicesHTML = shop.services.map(sv => `
      <div class="summary-row">
        <span>${sv.name} <span class="hint">(${sv.duration} นาที)</span></span>
        <strong>${money(sv.price)}</strong>
      </div>`).join("");

    const reviewsHTML = allReviews().map(r => `
      <div class="review">
        <span class="who">${r.user}</span>
        ${r.verified ? '<span class="badge badge-cert" style="margin-left:6px">✔ ยืนยันแล้ว</span>' : ''}
        <div class="stars">${starRow(r.rating)}</div>
        <div>${r.text}</div>
      </div>`).join("");

    const isFav = Favorites.has(shop.id);

    view.innerHTML = `
      <a href="search.html" class="hint">← กลับไปค้นหา</a>
      <div class="card glass reveal" style="margin-top:12px">
        <div style="display:flex;gap:22px;flex-wrap:wrap;align-items:center">
          <div class="shop-thumb" style="width:120px;border-radius:16px">${shop.image}</div>
          <div style="flex:1;min-width:220px">
            <h1 class="page-title" style="margin-bottom:4px">${shop.name}</h1>
            <div class="shop-meta">${getCategoryName(shop.category)} · ${shop.zone}</div>
            <div style="margin:8px 0">
              <span class="badge badge-rating">★ ${avgRating()} (${allReviews().length} รีวิว)</span>
              ${shop.certified ? '<span class="badge badge-cert">✔ รับรองความสะอาด</span>' : ''}
            </div>
            <p style="color:var(--muted)">${shop.about}</p>
          </div>
          <div style="display:flex;flex-direction:column;gap:10px">
            <button class="btn btn-outline" id="favToggle">${isFav ? "❤️ อยู่ในโปรด" : "🤍 เพิ่มโปรด"}</button>
            <a href="booking.html?id=${shop.id}" class="btn btn-primary">จองคิว →</a>
          </div>
        </div>
      </div>

      <div style="display:grid;grid-template-columns:1fr 1fr;gap:22px;margin-top:22px" class="two-col">
        <div class="card glass">
          <h2 style="margin-bottom:12px">บริการ &amp; ราคา</h2>
          ${servicesHTML}
          <p class="hint" style="margin-top:12px">ราคาจริง โปร่งใส ไม่มีค่าใช้จ่ายแอบแฝง</p>
        </div>
        <div class="card glass">
          <h2 style="margin-bottom:12px">รีวิวจากผู้ใช้จริง</h2>
          <div id="reviewList">${reviewsHTML}</div>

          <div style="border-top:1px solid var(--line);margin-top:16px;padding-top:16px">
            <h3 style="margin-bottom:8px">เขียนรีวิวของคุณ</h3>
            <div class="star-input" id="starInput">
              ${[5,4,3,2,1].map(v => `
                <input type="radio" name="star" id="star${v}" value="${v}" ${v === 5 ? "checked" : ""}>
                <label for="star${v}">★</label>`).join("")}
            </div>
            <div class="form-group" style="margin-top:10px">
              <textarea id="reviewText" rows="2" placeholder="บอกประสบการณ์ของคุณ..."></textarea>
            </div>
            <button class="btn btn-primary btn-sm" id="submitReview">ส่งรีวิว</button>
          </div>
        </div>
      </div>`;

    document.getElementById("favToggle").addEventListener("click", () => {
      const on = Favorites.toggle(shop.id);
      toast(on ? "เพิ่มในรายการโปรด ❤️" : "นำออกจากรายการโปรด");
      renderNav("search");
      render();
    });

    document.getElementById("submitReview").addEventListener("click", () => {
      const rating = +document.querySelector('input[name="star"]:checked').value;
      const text = document.getElementById("reviewText").value.trim();
      if (!text) { toast("กรุณาเขียนความคิดเห็นก่อนส่ง"); return; }
      const user = Auth.currentUser()?.name || "ผู้ใช้ทั่วไป";
      Reviews.add(shop.id, { user, rating, text, verified: Auth.isLoggedIn() });
      toast("ขอบคุณสำหรับรีวิว! 🎉");
      render();
    });
  }

  render();

  const style = document.createElement("style");
  style.textContent = "@media(max-width:720px){.two-col{grid-template-columns:1fr!important}}";
  document.head.appendChild(style);
}
