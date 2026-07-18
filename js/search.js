/* ============================================================
   GlowGo — หน้าค้นหา & เลือกบริการ (Stage 3)
   ค้นหา + กรอง + จัดเรียง + เทียบร้าน + รายการโปรด
   ============================================================ */

initPage("search");

const els = {
  q: document.getElementById("q"),
  cat: document.getElementById("catFilter"),
  zone: document.getElementById("zoneFilter"),
  sort: document.getElementById("sortBy"),
  cert: document.getElementById("certOnly"),
  fav: document.getElementById("favOnly"),
  results: document.getElementById("results"),
  count: document.getElementById("count"),
};

els.cat.innerHTML += CATEGORIES.map(c => `<option value="${c.id}">${c.icon} ${c.name}</option>`).join("");
els.zone.innerHTML += ZONES.map(z => `<option value="${z}">${z}</option>`).join("");

// รับพารามิเตอร์จาก URL
const params = new URLSearchParams(location.search);
if (params.get("cat")) els.cat.value = params.get("cat");
if (params.get("q")) els.q.value = params.get("q");

function shopCardHTML(s, i) {
  return `
    <div class="shop-card glass reveal" style="animation-delay:${i * 50}ms">
      ${favBtnHTML(s.id)}
      <a href="shop.html?id=${s.id}">
        <div class="shop-thumb">${s.image}</div>
        <div class="shop-body">
          <h3>${s.name}</h3>
          <div class="shop-meta">${getCategoryName(s.category)} · ${s.zone} · ${s.reviewCount} รีวิว</div>
          <div>
            <span class="badge badge-rating">★ ${s.rating}</span>
            ${s.certified ? '<span class="badge badge-cert">✔ รับรองสะอาด</span>' : ''}
          </div>
          <div class="shop-price">เริ่ม ${money(s.priceFrom)}</div>
        </div>
      </a>
    </div>`;
}

function render() {
  let list = SHOPS.slice();
  const q = els.q.value.trim().toLowerCase();

  if (q) list = list.filter(s =>
    s.name.toLowerCase().includes(q) ||
    getCategoryName(s.category).includes(q) ||
    s.zone.includes(q)
  );
  if (els.cat.value) list = list.filter(s => s.category === els.cat.value);
  if (els.zone.value) list = list.filter(s => s.zone === els.zone.value);
  if (els.cert.checked) list = list.filter(s => s.certified);
  if (els.fav.checked) list = list.filter(s => Favorites.has(s.id));

  switch (els.sort.value) {
    case "priceLow":  list.sort((a, b) => a.priceFrom - b.priceFrom); break;
    case "priceHigh": list.sort((a, b) => b.priceFrom - a.priceFrom); break;
    case "reviews":   list.sort((a, b) => b.reviewCount - a.reviewCount); break;
    default:          list.sort((a, b) => b.rating - a.rating);
  }

  els.count.textContent = `พบ ${list.length} ร้าน`;
  els.results.innerHTML = list.length
    ? list.map(shopCardHTML).join("")
    : `<div class="empty glass" style="border-radius:18px">ไม่พบร้านที่ตรงกับเงื่อนไข ลองปรับตัวกรองดูนะ</div>`;
}

[els.q, els.cat, els.zone, els.sort, els.cert, els.fav].forEach(el =>
  el.addEventListener("input", render)
);
render();
