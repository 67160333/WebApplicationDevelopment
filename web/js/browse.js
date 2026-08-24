/* ============================================================
   เครื่องมือกลางของหน้ารายการร้าน — ใช้ร่วมกันทั้ง 4 กลุ่ม
   ============================================================

   ทำไมต้องมีไฟล์นี้
   ------------------------------------------------------------
   อาจารย์ให้ฟีดแบ็กว่า "แยกประเภทไม่ชัดเจน ถ้าเข้าสนามบอล UI ก็ควรเปลี่ยนทั้งหมด"
   ทางแก้คือแยกเป็นไฟล์จริง 4 หน้า ไม่ใช่หน้าเดียวที่สลับข้อความไปมา

   แต่ถ้าคัดลอกโค้ดค้นหา · แบ่งหน้า · ร้านโปรด · ใกล้ฉัน ไปวางทั้ง 4 หน้า
   เท่ากับมีโค้ดชุดเดียวกัน 4 ก๊อปปี้ แก้บั๊กทีต้องแก้ 4 ที่ แล้วจะลืมสักที่แน่นอน
   (เคยเกิดมาแล้วกับคลาส .svc-list ที่พิมพ์ผิดแล้วไม่มีใครเห็นเป็นเดือน)

   ไฟล์นี้จึงเก็บ **กลไก** ที่ทุกกลุ่มใช้เหมือนกัน
   ส่วน **หน้าตาและสิ่งที่แสดงบนการ์ด** แต่ละหน้าส่งเข้ามาเองผ่าน cfg

   สิ่งที่แต่ละกลุ่มกำหนดเองได้
   ------------------------------------------------------------
   cfg.group          กลุ่มใหญ่ที่หน้านี้แสดง (care / play / auto / come)
   cfg.card(s)        วาดการ์ดร้านหนึ่งใบ — ต่างกันทุกกลุ่ม
   cfg.filters        เปิด/ปิดตัวกรองแต่ละตัว
   cfg.searchLabel    ข้อความในช่องค้นหา
   cfg.quickChips     ปุ่มลัดของกลุ่มนั้น ๆ
   cfg.sortHint       ข้อความบอกว่าเรียงยังไง
============================================================ */

const BrowsePage = (() => {
  let cfg = null;
  let params = null;

  let onlyFav = false;
  let availMode = "";
  let catFilter = "";
  let myPos = null;
  let nearRadius = 20;

  // ลำดับคำขอ — กันผลลัพธ์เก่ามาทับผลลัพธ์ใหม่
  // อาการที่เคยเจอ: เปิดหน้าแล้วรีบกดปุ่มกรองทันที คำขอทั้งสองวิ่งพร้อมกัน
  // ถ้าคำขอแรกกลับมาช้ากว่า มันจะวาดทับผลของคำขอที่สอง
  let loadSeq = 0;

  const $ = (id) => document.getElementById(id);

  /* ---------- แถบตัวกรอง ---------- */
  function filterBar() {
    const f = cfg.filters || {};
    const chips = (cfg.quickChips || []).map((c) =>
      `<button type="button" class="quick${c.value === "" ? " is-active" : ""}"
               data-avail="${c.value}">${esc(c.label)}</button>`
    ).join("");

    const cats = f.category
      ? `<div>
           <label class="label" for="fCat">${esc(cfg.categoryLabel || "ประเภทบริการ")}</label>
           <select id="fCat" class="select"><option value="">ทุกประเภท</option></select>
         </div>`
      : "";
    const rating = f.rating
      ? `<div>
           <label class="label" for="fRating">คะแนนขั้นต่ำ</label>
           <select id="fRating" class="select">
             <option value="">ไม่จำกัด</option>
             <option value="4">4.0 ขึ้นไป</option>
             <option value="3">3.0 ขึ้นไป</option>
           </select>
         </div>`
      : "";
    const cert = f.certified
      ? `<label class="flex items-center gap-2.5 text-sm cursor-pointer">
           <input type="checkbox" id="fCert"
                  style="width:16px;height:16px;accent-color:var(--navy-800)" />
           <span>เฉพาะร้านที่ผ่านการรับรองมาตรฐาน</span>
         </label>`
      : "<span></span>";

    return `
      <div class="card card-pad mt-6">
        <form id="filterForm" onsubmit="return false">
          <div class="search-line">
            <span class="search-ic">${icon("search", 18)}</span>
            <input id="fSearch" class="input search-input" autocomplete="off"
                   placeholder="${esc(cfg.searchLabel || "ค้นหาชื่อร้าน")}" />
          </div>

          ${chips || f.near ? `
            <div class="quick-row mt-4">
              ${chips}
              ${f.near ? `<button type="button" class="quick" id="nearBtn">ใกล้ฉัน</button>` : ""}
            </div>` : ""}

          ${cats || rating || f.district || f.certified ? `
            <details id="moreFilter" class="more-fields" style="margin-top:14px">
              <summary id="moreSummary">ตัวกรองเพิ่มเติม</summary>
              <div class="grid sm:grid-cols-3 gap-4 pt-4">
                ${cats}
                ${f.district ? `
                  <div>
                    <label class="label" for="fDistrict">โซน / เขต</label>
                    <select id="fDistrict" class="select"><option value="">ทุกพื้นที่</option></select>
                  </div>` : ""}
                ${rating}
                <div class="sm:col-span-3 flex items-center justify-between gap-4 flex-wrap">
                  ${cert}
                  <button type="button" id="resetBtn" class="btn btn-ghost btn-sm">ล้างตัวกรองทั้งหมด</button>
                </div>
              </div>
            </details>` : ""}
        </form>
      </div>

      <div class="flex items-center justify-between gap-3 mt-6 flex-wrap">
        <p id="resultCount" class="text-sm text-muted" style="margin:0"></p>
        <button id="favTab" class="btn btn-outline btn-sm" style="display:none"></button>
      </div>
      <div id="shops" class="mt-4 grid sm:grid-cols-2 lg:grid-cols-3 gap-5"></div>
      <div id="pagination" class="mt-10 flex justify-center items-center gap-1.5"></div>`;
  }

  /* ---------- เติมตัวเลือกจากข้อมูลจริง ---------- */
  async function loadOptions() {
    const catSel = $("fCat");
    if (catSel) {
      try {
        const cats = await apiGet("/api/categories");
        // แสดงเฉพาะหมวดที่อยู่ในกลุ่มนี้ — ไม่งั้นคนดูสนามบอลจะเห็นตัวเลือก "ทำเล็บ"
        cats.filter((c) => !cfg.group || c.group_key === cfg.group)
            .forEach((c) => catSel.add(new Option(c.name, c.id)));
        catSel.value = params.get("category_id") || "";
      } catch {}
    }

    const distSel = $("fDistrict");
    if (distSel) {
      try {
        const q = new URLSearchParams({ page: 1, limit: 100 });
        if (cfg.group) q.set("group", cfg.group);
        const all = await apiGet(`/api/shops?${q}`);
        [...new Set(all.items.map((s) => s.district).filter(Boolean))]
          .sort()
          .forEach((d) => distSel.add(new Option(d, d)));
        distSel.value = params.get("district") || "";
      } catch {}
    }
  }

  function updateMoreSummary() {
    const box = $("moreSummary");
    if (!box) return;
    const n = [
      $("fCat") && $("fCat").value,
      $("fDistrict") && $("fDistrict").value,
      $("fRating") && $("fRating").value,
      $("fCert") && $("fCert").checked ? "1" : "",
    ].filter(Boolean).length;
    box.innerHTML = n
      ? `ตัวกรองเพิ่มเติม <span class="badge badge-confirmed">${n}</span>`
      : "ตัวกรองเพิ่มเติม";
    if (n) $("moreFilter").open = true;
  }

  function buildQuery(page) {
    const q = new URLSearchParams({ page, limit: cfg.limit || 9 });
    if (cfg.group) q.set("group", cfg.group);

    const s = $("fSearch").value.trim();
    if (s) q.set("search", s);
    // ตัวกรองหมวดมาได้สองทาง — ดรอปดาวน์ หรือปุ่มชิปด้านบน (หน้ากีฬาใช้ชิป)
    const c = catFilter || ($("fCat") ? $("fCat").value : "");
    if (c) q.set("category_id", c);
    if ($("fDistrict") && $("fDistrict").value) q.set("district", $("fDistrict").value);
    if ($("fRating") && $("fRating").value) q.set("min_rating", $("fRating").value);
    if ($("fCert") && $("fCert").checked) q.set("certified", "true");

    if (availMode === "today") q.set("available_on", localDate());
    if (availMode === "tomorrow") q.set("available_on", localDate(dateAfter(1)));

    if (myPos) {
      q.set("near_lat", myPos.lat.toFixed(6));
      q.set("near_lng", myPos.lng.toFixed(6));
      q.set("radius_km", nearRadius);
    }
    return q;
  }

  /* ---------- โหลดและวาดรายการ ---------- */
  async function load(page = 1) {
    const my = ++loadSeq;
    const box = $("shops");
    const count = $("resultCount");
    const pager = $("pagination");

    // จำนวนโครงร่างต้องเท่ากับจำนวนร้านต่อหน้าเป๊ะ ๆ
    // ไม่งั้นหน้าจะยืดหรือหดตอนข้อมูลมาถึง แล้วส่วนท้ายเว็บกระโดดตาม
    box.innerHTML = skeletonCards(cfg.limit || 9, 144, 316);
    count.textContent = "กำลังค้นหา";
    pager.innerHTML = "";

    try {
      const q = buildQuery(page);
      if (onlyFav) q.set("limit", 100);
      const res = await apiGet(`/api/shops?${q}`);
      if (my !== loadSeq) return;

      // เก็บตัวกรองไว้ในลิงก์ให้แชร์และกดย้อนกลับได้
      // แต่ตัดพิกัดผู้ใช้ออกเสมอ — ที่อยู่เป็นข้อมูลส่วนตัว ไม่ควรค้างในแถบที่อยู่
      const shown = new URLSearchParams(q);
      ["near_lat", "near_lng", "radius_km", "group", "limit"].forEach((k) => shown.delete(k));
      history.replaceState(null, "", `${cfg.page}${shown.toString() ? "?" + shown : ""}`);

      let items = res.items;
      if (onlyFav) {
        const fav = Favorites.list();
        items = items.filter((s) => fav.includes(s.id));
      }

      if (!items.length) {
        count.textContent = "";
        box.innerHTML = onlyFav
          ? emptyHTML("heart", "ยังไม่มีร้านโปรดในหมวดนี้",
              "กดรูปหัวใจบนการ์ดเพื่อบันทึกไว้ดูทีหลัง")
          : myPos
          ? emptyHTML("mapPin", `ไม่มีที่ไหนในรัศมี ${nearRadius} กิโลเมตร`,
              "กดปุ่มใกล้ฉันอีกครั้งเพื่อดูทั้งหมดโดยไม่จำกัดระยะทาง")
          : emptyHTML("search",
              availMode ? (cfg.emptyAvail || "ไม่มีที่ไหนว่างในวันนั้น") : (cfg.empty || "ไม่พบที่ตรงกับเงื่อนไข"),
              availMode ? "ลองเลือกวันอื่น หรือกดดูทั้งหมด" : "ลองปรับตัวกรองหรือใช้คำค้นอื่น");
        return;
      }

      count.textContent = onlyFav
        ? `บันทึกไว้ ${items.length} แห่ง`
        : myPos
        ? `พบ ${res.total} แห่งในรัศมี ${nearRadius} กม. · เรียงจากใกล้ที่สุด`
        : `พบ ${res.total} แห่ง · หน้า ${res.page} จาก ${res.total_pages}${cfg.sortHint ? " · " + cfg.sortHint : ""}`;

      box.innerHTML = items.map(wrapCard).join("");
      bindFav();
      revealOnScroll("#shops .reveal");
      if (!onlyFav) renderPagination(res);
      if (cfg.afterRender) cfg.afterRender(items);
    } catch (err) {
      if (my !== loadSeq) return;
      count.textContent = "ค้นหาไม่สำเร็จ";
      box.innerHTML = `
        <div class="card card-pad text-center fill-row">
          <p class="text-sm" style="color:var(--danger)">${esc(err.message)}</p>
          <button type="button" id="retryBtn" class="btn btn-outline btn-sm" style="margin-top:12px">
            ลองใหม่อีกครั้ง
          </button>
        </div>`;
      $("retryBtn").addEventListener("click", (e) => {
        btnBusy(e.currentTarget, true, "กำลังลองใหม่");
        load(page);
      });
    }
  }

  // ห่อการ์ดของแต่ละกลุ่มด้วยโครงเดียวกัน เพื่อให้ปุ่มหัวใจอยู่ที่เดิมทุกหน้า
  function wrapCard(s) {
    const fav = Favorites.has(s.id);
    return `
      <div class="shop-cell reveal">
        ${cfg.card(s)}
        <button type="button" class="fav-btn ${fav ? "is-on" : ""}" data-fav="${s.id}"
                aria-pressed="${fav}"
                title="${fav ? "บันทึกไว้แล้ว" : "บันทึกไว้ดูทีหลัง"}"
                aria-label="${fav ? "เอาออกจากรายการที่บันทึก" : "บันทึกไว้ดูทีหลัง"}">${icon("heart", 17)}</button>
      </div>`;
  }

  function bindFav() {
    document.querySelectorAll("[data-fav]").forEach((b) =>
      b.addEventListener("click", (e) => {
        e.preventDefault();
        e.stopPropagation();
        const on = Favorites.toggle(b.dataset.fav);
        b.classList.toggle("is-on", on);
        b.title = on ? "บันทึกไว้แล้ว" : "บันทึกไว้ดูทีหลัง";
        b.setAttribute("aria-pressed", String(on));
        b.setAttribute("aria-label", on ? "เอาออกจากรายการที่บันทึก" : "บันทึกไว้ดูทีหลัง");
        toast(on ? "บันทึกไว้แล้ว" : "เอาออกแล้ว");
        updateFavTab();
        if (!on && onlyFav) load(1);
      })
    );
  }

  function updateFavTab() {
    const n = Favorites.count();
    const btn = $("favTab");
    btn.style.display = n ? "" : "none";
    btn.innerHTML = `${icon("heart", 14)} ที่บันทึกไว้ <span class="num">${n}</span>`;
    btn.classList.toggle("btn-primary", onlyFav);
    btn.classList.toggle("btn-outline", !onlyFav);
  }

  function renderPagination(res) {
    if (res.total_pages <= 1) return;
    const box = $("pagination");
    const btn = (label, page, disabled, active, aria) => `
      <button data-page="${page}" ${disabled ? "disabled" : ""}
        ${active ? 'aria-current="page"' : ""}
        ${aria ? `aria-label="${esc(aria)}"` : ""}
        class="btn btn-sm ${active ? "btn-primary" : "btn-outline"}"
        ${disabled ? 'style="opacity:.4;cursor:not-allowed"' : ""}>${label}</button>`;

    // แสดงเลขหน้าแค่ช่วงรอบ ๆ หน้าปัจจุบัน ไม่งั้นแถวปุ่มจะยาวล้นจอเมื่อร้านเยอะ
    const cur = res.page, last = res.total_pages;
    const around = new Set([1, last, cur - 1, cur, cur + 1]);
    const pages = [...around].filter((p) => p >= 1 && p <= last).sort((a, b) => a - b);

    let html = btn(icon("chevronLeft", 14), cur - 1, cur <= 1, false, "หน้าก่อนหน้า");
    let prev = 0;
    for (const p of pages) {
      if (p - prev > 1) html += `<span class="page-gap">…</span>`;
      html += btn(p, p, false, p === cur, `หน้า ${p}`);
      prev = p;
    }
    html += btn(icon("chevronRight", 14), cur + 1, cur >= last, false, "หน้าถัดไป");
    box.innerHTML = html;

    box.querySelectorAll("button[data-page]").forEach((b) =>
      b.addEventListener("click", () => {
        load(Number(b.dataset.page));
        window.scrollTo({ top: 0, behavior: "smooth" });
      })
    );
  }

  /* ---------- ผูกเหตุการณ์ ---------- */
  function bindControls() {
    let typeTimer = null;
    $("fSearch").addEventListener("input", () => {
      clearTimeout(typeTimer);
      typeTimer = setTimeout(() => load(1), 350);
    });

    ["fCat", "fDistrict", "fRating", "fCert"].forEach((id) => {
      const el = $(id);
      if (el) el.addEventListener("change", () => { updateMoreSummary(); load(1); });
    });

    const reset = $("resetBtn");
    if (reset) reset.addEventListener("click", () => {
      $("filterForm").reset();
      availMode = "";
      catFilter = "";
      myPos = null;
      setNear(false);
      paintQuick();
      if (cfg.onResetChips) cfg.onResetChips();
      updateMoreSummary();
      load(1);
      toast("ล้างตัวกรองแล้ว");
    });

    document.querySelectorAll("[data-avail]").forEach((b) =>
      b.addEventListener("click", () => {
        availMode = b.dataset.avail;
        paintQuick();
        load(1);
      })
    );
    paintQuick();

    $("favTab").addEventListener("click", () => {
      onlyFav = !onlyFav;
      updateFavTab();
      load(1);
      window.scrollTo({ top: 0, behavior: "smooth" });
    });

    const nearBtn = $("nearBtn");
    if (nearBtn) nearBtn.addEventListener("click", async () => {
      if (myPos) {                    // กดซ้ำเพื่อปิดโหมด
        myPos = null;
        setNear(false);
        load(1);
        return;
      }
      // ขอตำแหน่งใช้เวลาหลายวินาที ถ้าปุ่มไม่บอกอะไรจะดูเหมือนเว็บค้าง
      btnBusy(nearBtn, true, "กำลังหาตำแหน่ง");
      try {
        myPos = await askLocation();
        const dist = $("fDistrict");
        // เลือกเขตค้างไว้แล้วจะไม่เจอที่ใกล้ตัวเลย จึงต้องล้างก่อน
        if (dist && dist.value) { dist.value = ""; updateMoreSummary(); }
        btnBusy(nearBtn, false);
        setNear(true);
        await load(1);
      } catch (err) {
        myPos = null;
        btnBusy(nearBtn, false);
        setNear(false);
        toast(err.message, "error", 5000);
      }
    });
  }

  function setNear(on) {
    const b = $("nearBtn");
    if (!b) return;
    b.classList.toggle("is-active", on);
    b.setAttribute("aria-pressed", String(on));
    b.textContent = on ? `ใกล้ฉัน · ${nearRadius} กม.` : "ใกล้ฉัน";
    b.title = on ? "กดอีกครั้งเพื่อเลิกเรียงตามระยะทาง" : "เรียงจากที่ใกล้ตัวคุณที่สุด";
  }

  const paintQuick = () =>
    document.querySelectorAll("[data-avail]").forEach((x) => {
      const on = x.dataset.avail === availMode;
      x.classList.toggle("is-active", on);
      x.setAttribute("aria-pressed", String(on));
    });

  /* ---------- ทางเข้าหลัก ---------- */
  function init(config) {
    cfg = config;
    params = new URLSearchParams(location.search);
    onlyFav = params.get("fav") === "1";
    availMode = params.get("avail") || "";

    // หน้ากีฬาและหน้ารถใช้ชิปแทนดรอปดาวน์ จึงไม่มี #fCat ให้ใส่ค่า
    // ถ้าไม่รับ ?category_id= ตรงนี้ ลิงก์ลึกจากหน้าแรก (เช่น "ฟุตบอล")
    // จะเปิดมาเป็นรายการทั้งกลุ่ม ไม่ได้กรองอะไรเลย
    if (!(config.filters || {}).category) {
      catFilter = params.get("category_id") || "";
    }

    const host = $("browse");
    host.innerHTML = filterBar();

    $("fSearch").value = params.get("search") || "";
    if ($("fRating")) $("fRating").value = params.get("min_rating") || "";
    if ($("fCert")) $("fCert").checked = params.get("certified") === "true";

    bindControls();
    updateFavTab();
    updateMoreSummary();
    loadOptions().then(() => {
      updateMoreSummary();
      load(Number(params.get("page")) || 1);
    });
  }

  /* หน้าที่ใช้ชิปเลือกหมวดเอง (เช่นหน้ากีฬา) เรียกอันนี้เพื่อสั่งกรอง */
  function setCategory(id) {
    catFilter = id ? String(id) : "";
    load(1);
  }

  return { init, reload: load, setCategory };
})();

/* ============================================================
   ชิ้นส่วนการ์ดที่ใช้ซ้ำได้
   ============================================================ */

/** แถวล่างสุดของการ์ด — เขต · ระยะทาง · เปิด/ปิด */
function cardFoot(s) {
  const st = shopStatus(s);
  return `
    <div class="flex items-center gap-2.5 mt-3 pt-3 text-xs text-muted flex-wrap"
         style="border-top:1px solid var(--border)">
      <span class="flex items-center gap-1.5">${icon("mapPin", 13)} ${esc(s.district || "—")}</span>
      ${s.distance_km != null
        ? `<span class="dist-chip num">${icon("navigate", 11)} ${distanceText(s.distance_km)}</span>`
        : ""}
      <span class="shop-st ${st.cls}">${st.text}</span>
    </div>`;
}

/** "เริ่มต้น ฿xxx" — ใช้ได้ทุกกลุ่ม ถ้าร้านยังไม่มีบริการจะไม่แสดงอะไร */
function priceFrom(s) {
  if (s.price_from == null) return "";
  return `<span class="num">เริ่ม ฿${baht(s.price_from)}</span>`;
}

/** แปลงนาทีเป็นข้อความที่คนอ่านเข้าใจ — 480 นาทีไม่มีใครนึกออกว่านานแค่ไหน */
function durationText(min) {
  if (min == null) return "";
  if (min < 60) return `${min} นาที`;
  const h = Math.floor(min / 60), m = min % 60;
  return m ? `${h} ชม. ${m} นาที` : `${h} ชั่วโมง`;
}
