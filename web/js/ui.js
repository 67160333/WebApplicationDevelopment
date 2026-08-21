// ============================================================
// ส่วนประกอบหน้าตา (UI) ที่ใช้ร่วมกันทุกหน้า
// ============================================================

// ---------- ชุดไอคอน ----------
// วาดเองทั้งหมดบนตาราง 24×24 เส้นหนาเท่ากันทุกตัว หัวเส้นมนเหมือนกันหมด
// ไม่ได้คัดลอกจากชุดใด จึงไม่มีเรื่องลิขสิทธิ์และไม่ต้องใส่เครดิต
//
// กฎการวาดที่ยึดตลอดชุด เพื่อให้ไอคอนดูเป็นครอบครัวเดียวกัน:
//   - ระยะขอบ 2px ทุกด้าน รูปทรงจริงอยู่ในกรอบ 20×20
//   - มุมโค้งรัศมี 2 สำหรับสี่เหลี่ยม
//   - เส้นตรงชิดเส้นตาราง เลี่ยงพิกัดทศนิยมที่ทำให้เส้นเบลอ
const ICON = {
  search: '<circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/>',
  mapPin: '<path d="M12 21s7-5.6 7-11a7 7 0 1 0-14 0c0 5.4 7 11 7 11Z"/><circle cx="12" cy="10" r="2.6"/>',
  clock: '<circle cx="12" cy="12" r="8.5"/><path d="M12 7.5V12l3 1.8"/>',
  shield: '<path d="M12 21c4.4-1.8 7-5.3 7-9.4V5.6L12 3 5 5.6v6c0 4.1 2.6 7.6 7 9.4Z"/><path d="m9.2 11.8 2 2 3.6-3.6"/>',
  calendar: '<rect x="3.5" y="5" width="17" height="15.5" rx="2"/><path d="M3.5 9.5h17M8.5 3v4M15.5 3v4"/>',
  user: '<circle cx="12" cy="8" r="3.6"/><path d="M4.8 20.2a7.2 7.2 0 0 1 14.4 0"/>',
  phone: '<path d="M8.4 4H5.2A1.7 1.7 0 0 0 3.5 5.9C4 13.5 10.5 20 18.1 20.5a1.7 1.7 0 0 0 1.9-1.7v-3.2l-3.8-1.3-1.9 1.9a13.6 13.6 0 0 1-5.5-5.5l1.9-1.9L8.4 4Z"/>',
  star: '<path d="m12 3.5 2.7 5.5 6 .9-4.35 4.2 1.03 5.9L12 17.2 6.62 20l1.03-5.9L3.3 9.9l6-.9L12 3.5Z"/>',
  check: '<path d="m5 12.5 4.5 4.5L19 7.5"/>',
  chevronRight: '<path d="m9.5 5 7 7-7 7"/>',
  chevronLeft: '<path d="m14.5 5-7 7 7 7"/>',
  arrowLeft: '<path d="M19.5 12h-15M10.5 5.5 4 12l6.5 6.5"/>',
  x: '<path d="M18 6 6 18M6 6l12 12"/>',
  logout: '<path d="M9.5 20.5H5.5a2 2 0 0 1-2-2v-13a2 2 0 0 1 2-2h4"/><path d="m15.5 8 4 4-4 4"/><path d="M19.5 12h-10"/>',
  sparkle: '<path d="M12 3.5v3.2M12 17.3v3.2M3.5 12h3.2M17.3 12h3.2"/><path d="m6.5 6.5 2.3 2.3M15.2 15.2l2.3 2.3M17.5 6.5l-2.3 2.3M8.8 15.2l-2.3 2.3"/>',
  filter: '<path d="M3.5 5.5h17l-6.5 7.5v5.5l-4 2v-7.5L3.5 5.5Z"/>',
  creditCard: '<rect x="2.5" y="5" width="19" height="14" rx="2"/><path d="M2.5 9.5h19"/><path d="M6 15h3"/>',
  info: '<circle cx="12" cy="12" r="8.5"/><path d="M12 11.2v5M12 7.9h.01"/>',
  lock: '<rect x="4.5" y="10.5" width="15" height="10" rx="2"/><path d="M8 10.5V7.5a4 4 0 0 1 8 0v3"/>',
  share: '<path d="M4.5 13v5.5a2 2 0 0 0 2 2h11a2 2 0 0 0 2-2V13"/><path d="m8.5 7 3.5-3.5L15.5 7"/><path d="M12 3.5V15"/>',
  scissors: '<circle cx="6.5" cy="6.5" r="2.8"/><circle cx="6.5" cy="17.5" r="2.8"/><path d="M19.5 4.5 8.6 15.4M14.4 14.4l5.1 5.1M8.6 8.6 12 12"/>',
  droplet: '<path d="M12 3.5 7 9a7 7 0 1 0 10 0l-5-5.5Z"/>',
  leaf: '<path d="M11 20.5A7 7 0 0 1 9.8 6.6C15.5 5.5 17 5 19 2.5c1 2 2 4.2 2 8 0 5.5-4.8 10-10 10Z"/><path d="M3 21c0-3 1.9-5.4 5.1-6 2.4-.5 4.9-2 5.9-3"/>',
  brush: '<path d="m9 12 8-8a2.8 2.8 0 0 1 4 4l-8 8"/><path d="M7 15a3 3 0 0 0-3 3c0 1.3-2.5 1.5-2 2 1.1 1.1 2.5 2 4 2a4 4 0 0 0 4-4 3 3 0 0 0-3-3Z"/>',
  pulse: '<path d="M2.5 12h4L9 4.5l6 15 2.5-7.5h4"/>',
  bell: '<path d="M18 8.5a6 6 0 0 0-12 0c0 6-2.5 7.5-2.5 7.5h17S18 14.5 18 8.5Z"/><path d="M13.8 19.5a2 2 0 0 1-3.6 0"/>',
  printer: '<path d="M6.5 9V3.5h11V9"/><rect x="3.5" y="9" width="17" height="8" rx="2"/><rect x="6.5" y="14" width="11" height="6.5" rx="1"/>',
  heart: '<path d="M12 20.5S3.5 15 3.5 9.4A4.4 4.4 0 0 1 12 7.4a4.4 4.4 0 0 1 8.5 2c0 5.6-8.5 11.1-8.5 11.1Z"/>',
  camera: '<path d="M4.5 7.5h2.8l1.6-2.2h6.2l1.6 2.2h2.8a1.5 1.5 0 0 1 1.5 1.5v9a1.5 1.5 0 0 1-1.5 1.5h-15A1.5 1.5 0 0 1 3 18V9a1.5 1.5 0 0 1 1.5-1.5Z"/><circle cx="12" cy="13" r="3.2"/>',
  upload: '<path d="M20.5 15.5v3a2 2 0 0 1-2 2h-13a2 2 0 0 1-2-2v-3"/><path d="m7.5 8.5 4.5-4.5 4.5 4.5"/><path d="M12 4v12"/>',
  trash: '<path d="M3.5 6.5h17"/><path d="M9 6.5v-2a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"/><path d="M18.5 6.5v13a1.5 1.5 0 0 1-1.5 1.5H7a1.5 1.5 0 0 1-1.5-1.5v-13"/><path d="M10 11v5.5M14 11v5.5"/>',
  navigate: '<path d="m3.5 11 17-7.5-7.5 17-2-7.5-7.5-2Z"/>',
  qr: '<rect x="3.5" y="3.5" width="7" height="7" rx="1"/><rect x="13.5" y="3.5" width="7" height="7" rx="1"/><rect x="3.5" y="13.5" width="7" height="7" rx="1"/><path d="M13.5 13.5h3v3h-3zM20.5 13.5h-2M13.5 20.5h3M20.5 17v3.5"/>',
  receipt: '<path d="M5.5 20.5v-16a1 1 0 0 1 1-1h11a1 1 0 0 1 1 1v16l-3-1.8-3 1.8-3-1.8-3 1.8Z"/><path d="M9 8h6M9 12h6"/>',
  crosshair: '<circle cx="12" cy="12" r="7.5"/><circle cx="12" cy="12" r="2"/><path d="M12 2.5v2M12 19.5v2M2.5 12h2M19.5 12h2"/>',
  // ลูกฟุตบอล — วงกลมกับห้าเหลี่ยมกลางลูก
  football: '<circle cx="12" cy="12" r="8.5"/><path d="m12 8.2 3.1 2.3-1.2 3.7h-3.8l-1.2-3.7L12 8.2Z"/><path d="M12 3.5v4.7M4.4 9.4l4.5 1.1M19.6 9.4l-4.5 1.1M7.3 19.4l2.8-3.2M16.7 19.4l-2.8-3.2"/>',
  // ลูกขนไก่ — หัวลูกกับขนที่บานออก
  badminton: '<circle cx="12" cy="17.8" r="2.7"/><path d="M9.7 16.3 6.2 5.4a1 1 0 0 1 1.4-1.2l4.4 2.5 4.4-2.5a1 1 0 0 1 1.4 1.2l-3.5 10.9"/><path d="M12 6.7v9.3M9.4 8.6h5.2M8.5 12h7"/>',
  // กล่องพัสดุ — ใช้แทนบริการส่งของ
  parcel: '<path d="M12 3.2 4 7.1v9.8l8 3.9 8-3.9V7.1l-8-3.9Z"/><path d="M4 7.1 12 11l8-3.9M12 11v9.8"/><path d="m8 5.2 8 3.9"/>',
};

// สร้าง SVG จากชื่อไอคอน
function icon(name, size = 16, cls = "") {
  const path = ICON[name] || "";
  return `<svg class="${cls}" width="${size}" height="${size}" viewBox="0 0 24 24" fill="none"
    stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"
    style="display:inline-block;vertical-align:-.15em;flex-shrink:0">${path}</svg>`;
}


// ============================================================
// โลโก้ Bookvice
// ============================================================
// ตัว B ประกอบจากห่วงสองวง — ห่วงบนคือปฏิทิน ห่วงล่างคือเครื่องหมายถูก
// สื่อความหมายตรงตัว: "จอง" (ปฏิทิน) แล้ว "ยืนยันแล้ว" (ถูก)
//
// gradient ต้องมี id ไม่ซ้ำในหน้าเดียวกัน ไม่งั้นตัวที่วาดทีหลังจะไปใช้ของตัวแรก
// จึงสุ่มต่อท้ายทุกครั้งที่เรียก
function brandMark(size = 28, spine = "#16233F") {
  // แกนตั้งของตัว B ต้องเปลี่ยนสีตามพื้นหลัง
  // บนแถบเมนูสีกรมท่า ถ้าใช้สีกรมท่าเหมือนกันจะกลืนหายไปจนเหลือแค่ห่วงสองวง
  const g = "bv" + Math.random().toString(36).slice(2, 7);

  // ต่ำกว่า 22px ตารางปฏิทินจะเล็กจนกลายเป็นจุดมั่ว ๆ อ่านไม่ออกว่าคืออะไร
  // และยังไปกวนรูปทรงตัว B ให้ดูรก จึงตัดทิ้งเมื่อย่อเล็ก เหลือแค่โครง B กับเครื่องหมายถูก
  // (หลักการเดียวกับโลโก้ที่มีหลายเวอร์ชันตามขนาด — รูปทรงและสีเหมือนกัน ต่างแค่รายละเอียด)
  const calendar = size < 22 ? "" : `
      <g fill="#fff">
        <rect x="15.4" y="10.6" width="12" height="2" rx="1"/>
        <rect x="15.4" y="15" width="3.2" height="3.2" rx="1"/>
        <rect x="20.2" y="15" width="3.2" height="3.2" rx="1"/>
        <rect x="25" y="15" width="3.2" height="3.2" rx="1"/>
        <rect x="15.4" y="19.8" width="3.2" height="3.2" rx="1"/>
        <rect x="20.2" y="19.8" width="3.2" height="3.2" rx="1"/>
      </g>`;

  return `
    <svg width="${size}" height="${size}" viewBox="0 0 48 48" fill="none"
         style="display:block;flex-shrink:0" aria-hidden="true">
      <defs>
        <!-- ไล่จากส้มอ่อนไปส้มเข้ม อยู่ในโทนเดียวกันตลอดเส้น
             ของเดิมไล่จากส้มไปฟ้าเทา ซึ่งช่วงกลางตกไปอยู่ในสีเทาอมม่วง
             ทำให้มุมขวาบนดูหม่นเหมือนภาพซีด และไม่เข้ากับครึ่งล่างที่เป็นสีสด -->
        <linearGradient id="${g}a" x1="11" y1="5" x2="36" y2="27" gradientUnits="userSpaceOnUse">
          <stop stop-color="#F9AE8B"/><stop offset="1" stop-color="#E8785A"/>
        </linearGradient>
        <linearGradient id="${g}b" x1="11" y1="21" x2="38" y2="43" gradientUnits="userSpaceOnUse">
          <stop stop-color="#3FC0D6"/><stop offset="1" stop-color="#22A898"/>
        </linearGradient>
      </defs>

      <!-- ห่วงบน: ปฏิทิน -->
      <path d="M11 5h16a11 11 0 0 1 0 22H11z" fill="url(#${g}a)"/>${calendar}

      <!-- ห่วงล่าง: เครื่องหมายถูก -->
      <path d="M11 21h18a11 11 0 0 1 0 22H11z" fill="url(#${g}b)"/>
      <path d="m16.5 32.5 4.5 4.5 9-9" stroke="#fff" stroke-width="3.4"
            stroke-linecap="round" stroke-linejoin="round"/>

      <!-- แกนตั้งของตัว B -->
      <rect x="5" y="5" width="6.5" height="38" rx="3.25" fill="${spine}"/>
    </svg>`;
}

// ไอคอนประจำหมวดหมู่บริการ
const CATEGORY_ICON = {
  "spa-massage": "leaf",
  nail: "brush",
  hair: "scissors",
  "beauty-clinic": "pulse",
  tattoo: "droplet",
  football: "football",
  badminton: "badminton",
  delivery: "parcel",
};

// ---------- ดาวคะแนน ----------
// รองรับครึ่งดาว เพราะถ้าปัดเศษทิ้ง ตัวเลข 4.5 จะแสดงเป็นดาว 4 ดวง
// ซึ่งขัดกับตัวเลขที่เขียนอยู่ข้าง ๆ และดูเหมือนระบบคำนวณผิด
function starRow(avg, size = 15) {
  const v = Number(avg) || 0;
  const uid = "h" + Math.random().toString(36).slice(2, 8);
  let out = '<span class="stars" role="img" aria-label="' + v.toFixed(1) + ' จาก 5 ดาว">';

  for (let i = 1; i <= 5; i++) {
    const full = v >= i - 0.25;                       // เกือบเต็มก็นับเต็ม
    const half = !full && v >= i - 0.75;              // อยู่กลาง ๆ ให้ครึ่งดวง
    const fill = full ? "currentColor" : half ? `url(#${uid}${i})` : "none";

    out += `<svg width="${size}" height="${size}" viewBox="0 0 24 24"
      fill="${fill}" stroke="currentColor" stroke-width="1.4" stroke-linejoin="round"
      class="${full || half ? "" : "star-empty"}">
      ${half ? `<defs><linearGradient id="${uid}${i}">
          <stop offset="50%" stop-color="currentColor"/>
          <stop offset="50%" stop-color="transparent"/>
        </linearGradient></defs>` : ""}
      ${ICON.star}</svg>`;
  }
  return out + "</span>";
}

// ---------- ป้ายสถานะการจอง ----------
const STATUS_TEXT = {
  pending: "รอยืนยัน",
  confirmed: "ยืนยันแล้ว",
  completed: "ใช้บริการแล้ว",
  cancelled: "ยกเลิกแล้ว",
};

function statusBadge(status) {
  return `<span class="badge badge-${status}">${STATUS_TEXT[status] || status}</span>`;
}

// ============================================================
// ภาพประกอบร้าน — สร้างลายกราฟิกเฉพาะตัวจากเลขที่ร้าน
// ทำให้ทุกร้านมีภาพต่างกันโดยไม่ต้องใช้รูปจริง และไม่ต้องพึ่งไฟล์ภายนอก
// ============================================================

// ชุดสีไล่เฉด 6 แบบ เลือกตามเลขที่ร้าน
const ART_PALETTES = [
  ["#12325c", "#2d5fa8", "#5b8fd6"],
  ["#123f5c", "#1f6f96", "#57a9c9"],
  ["#1a2f56", "#3a5ba0", "#7fa3dd"],
  ["#14385a", "#2a6f8e", "#63b0c4"],
  ["#1d2b52", "#44518f", "#8a92d2"],
  ["#0f3350", "#276b83", "#5fb0ae"],
];

// ที่อยู่เต็มของไฟล์ที่อัปโหลด — API คืนมาเป็นเส้นทางสั้น ๆ เช่น /uploads/shops/4/ab12.webp
const fileUrl = (path) => (path ? `${API_BASE}${path}` : "");

function shopArt(shop, heightClass = "h-32", opts = {}) {
  const id = Number(shop.id) || 1;

  // ถ้าร้านอัปโหลดรูปจริงไว้แล้ว ใช้รูปแทนภาพวาด
  // ภาพวาดเป็นแค่ตัวสำรองสำหรับร้านที่ยังไม่มีรูป จะได้ไม่มีกรอบว่างโล่ง
  if (shop.cover_url) {
    const tagReal = opts.tag ? `<span class="art-tag">${esc(opts.tag)}</span>` : "";
    return `
      <div class="shop-art thumb ${heightClass} has-photo">
        <img src="${esc(fileUrl(shop.cover_url))}" alt="${esc(shop.name || "ร้าน")}"
             loading="lazy" decoding="async"
             onerror="this.closest('.shop-art').classList.add('img-failed')" />
        <span class="art-shade" aria-hidden="true"></span>
        ${tagReal}
      </div>`;
  }

  const p = ART_PALETTES[id % ART_PALETTES.length];
  const variant = id % 4;
  const gid = `g${id}_${Math.random().toString(36).slice(2, 7)}`;

  // ลายพื้นหลัง 4 แบบ หมุนเวียนตามเลขที่ร้าน
  const shapes = [
    // 1) วงกลมซ้อนกัน
    `<circle cx="26" cy="72" r="46" fill="${p[2]}" opacity=".38"/>
     <circle cx="86" cy="26" r="34" fill="${p[2]}" opacity=".28"/>
     <circle cx="70" cy="80" r="22" fill="#fff" opacity=".13"/>`,
    // 2) คลื่นซ้อนชั้น
    `<path d="M0 62 Q25 40 50 62 T100 62 V100 H0Z" fill="${p[2]}" opacity=".34"/>
     <path d="M0 76 Q25 56 50 76 T100 76 V100 H0Z" fill="#fff" opacity=".14"/>`,
    // 3) เส้นทแยงและวงแหวน
    `<g stroke="#fff" stroke-width="1.1" opacity=".2" fill="none">
       <path d="M-10 30 L110 -30M-10 55 L110 -5M-10 80 L110 20M-10 105 L110 45"/>
     </g>
     <circle cx="76" cy="66" r="30" fill="none" stroke="${p[2]}" stroke-width="7" opacity=".5"/>`,
    // 4) ใบไม้/หยดน้ำ
    `<path d="M20 88 C20 50 46 26 82 22 C80 60 56 86 20 88Z" fill="${p[2]}" opacity=".4"/>
     <path d="M4 66 C22 62 34 50 38 32" stroke="#fff" stroke-width="2" fill="none" opacity=".24"/>
     <circle cx="24" cy="24" r="12" fill="#fff" opacity=".12"/>`,
  ][variant];

  const tag = opts.tag ? `<span class="art-tag">${esc(opts.tag)}</span>` : "";

  return `
    <div class="shop-art thumb ${heightClass}" style="background:none">
      <svg viewBox="0 0 100 100" preserveAspectRatio="xMidYMid slice" aria-hidden="true">
        <defs>
          <linearGradient id="${gid}" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stop-color="${p[0]}"/>
            <stop offset="55%" stop-color="${p[1]}"/>
            <stop offset="100%" stop-color="${p[2]}"/>
          </linearGradient>
          <!-- ผิวหยาบละเอียด ช่วยให้ไล่สีไม่เป็นแถบและดูมีเนื้อเหมือนภาพถ่าย -->
          <filter id="n${gid}">
            <feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="3"/>
            <feColorMatrix type="saturate" values="0"/>
          </filter>
          <!-- ขอบมืดลงเล็กน้อย ทำให้ตัวหนังสือด้านบนอ่านง่ายขึ้น -->
          <radialGradient id="v${gid}" cx="50%" cy="35%" r="78%">
            <stop offset="55%" stop-color="#000" stop-opacity="0"/>
            <stop offset="100%" stop-color="#000" stop-opacity=".3"/>
          </radialGradient>
        </defs>
        <rect width="100" height="100" fill="url(#${gid})"/>
        ${shapes}
        <rect width="100" height="100" filter="url(#n${gid})" opacity=".055"/>
        <rect width="100" height="100" fill="url(#v${gid})"/>
      </svg>
      ${tag}
    </div>`;
}

// ============================================================
// เผยเนื้อหาตอนเลื่อนหน้าจอถึง
// ============================================================
// ตัวยกเลิกของรอบก่อน — ดูเหตุผลในตัว revealOnScroll
const _revealStops = new Map();

// ตัวเลือกไหนเคยเล่นเอฟเฟกต์ไปแล้วรอบหนึ่ง — ดูเหตุผลในตัว revealOnScroll
const _revealDone = new Set();

function revealOnScroll(selector = ".reveal") {
  // ยกเลิกรอบก่อนหน้า "ของตัวเลือกเดียวกัน" เท่านั้น
  //
  // ทำไมต้องแยกตามตัวเลือก: หน้าแรกเรียกฟังก์ชันนี้สองครั้ง
  //   1) revealOnScroll()                 -> ดูแลทุก .reveal ทั้งหน้า (5 section)
  //   2) revealOnScroll("#shops .reveal") -> ดูแลเฉพาะการ์ดร้าน เรียกทีหลังตอน API ตอบกลับ
  // ถ้าเก็บตัวยกเลิกไว้ตัวเดียวรวมกัน รอบที่ 2 จะไปถอด listener ของรอบที่ 1 ทิ้ง
  // section ที่ยังไม่ถูกเลื่อนถึงจะค้างที่ opacity: 0 ตลอดกาล
  // ผลคือเลื่อนลงไปแล้วเจอหน้าว่างเปล่า ทั้งที่เนื้อหาอยู่ครบใน DOM
  //
  // ส่วนเหตุผลที่ต้องยกเลิกรอบเดิม: หน้าค้นหาเรียกด้วยตัวเลือกเดิมซ้ำทุกครั้งที่พิมพ์คำค้น
  // ถ้าไม่ถอดของเก่า listener จะค้างบน window พร้อม reference การ์ดที่หลุดจากหน้าไปแล้ว
  const prevStop = _revealStops.get(selector);
  if (prevStop) prevStop();

  let pending = [...document.querySelectorAll(selector)]
    .filter((el) => !el.classList.contains("is-in"));
  if (!pending.length) return;

  // เล่นเอฟเฟกต์ได้ "ครั้งเดียวต่อหนึ่งตัวเลือก" รอบต่อไปให้แสดงทันที
  //
  // เหตุผล: รายการถูกวาดใหม่ทุกครั้งที่ผู้ใช้ทำอะไรสักอย่าง (จ่ายเงิน · ยกเลิก ·
  // เปลี่ยนตัวกรอง · เปลี่ยนหน้า) การ์ดชุดใหม่จึงเริ่มที่ opacity 0 อีกรอบเสมอ
  // ถ้าตอนนั้นผู้ใช้เลื่อนหน้าอยู่กลาง ๆ การ์ดที่อยู่ต่ำกว่าขอบจอจะถูกซ่อนทั้งแถบ
  // สิ่งที่เห็นคือ "จ่ายเงินเสร็จแล้วหน้าเว็บว่างเปล่า" ทั้งที่เนื้อหาอยู่ครบใน DOM
  // และต้องเลื่อนจอเองถึงจะกลับมา — ผู้ใช้รายงานเข้ามาว่าเป็นบั๊กจริง
  //
  // เอฟเฟกต์นี้มีไว้สร้างความรู้สึกตอน "เห็นหน้านี้ครั้งแรก" ไม่ใช่ตอนอัปเดตข้อมูล
  // ครั้งที่สองเป็นต้นไปจึงแสดงทันที ผู้ใช้เห็นผลลัพธ์ของสิ่งที่เพิ่งกดทันที
  const replayed = _revealDone.has(selector);
  _revealDone.add(selector);

  // ผู้ใช้ตั้งค่าลดการเคลื่อนไหว -> แสดงทันทีทั้งหมด
  if (replayed || window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
    pending.forEach((el) => el.classList.add("is-in"));
    return;
  }

  let ticking = false;

  // กวาดดูว่าชิ้นไหนโผล่เข้ามาในจอแล้วบ้าง
  // ใช้วิธีวัดตำแหน่งเองแทน IntersectionObserver เพราะถ้าผู้ใช้กระโดดข้าม
  // (เลื่อนเร็ว ๆ / กด End / เบราว์เซอร์จำตำแหน่งเดิมตอนรีเฟรช)
  // ตัว observer จะไม่ยิง แล้วเนื้อหาจะค้างเป็นช่องว่างเปล่า
  function sweep() {
    ticking = false;
    const limit = window.innerHeight - 60;   // ต้องโผล่พ้นขอบล่างเข้ามาหน่อยถึงจะนับ
    let order = 0;

    // ถ้าหน้านี้เลื่อนไม่ได้แล้ว (เนื้อหาสั้นกว่าจอ หรืออยู่ล่างสุดแล้ว)
    // จะไม่มี scroll event มาอีกตลอดกาล ชิ้นที่เหลือต้องแสดงเลย ไม่งั้นค้างเป็นช่องว่าง
    const stuck =
      document.documentElement.scrollHeight - window.innerHeight - window.scrollY <= 2;

    pending = pending.filter((el) => {
      if (!stuck && el.getBoundingClientRect().top > limit) return true;  // ยังไม่ถึง รอรอบหน้า
      setTimeout(() => el.classList.add("is-in"), order++ * 70); // ไล่ขึ้นมาทีละชิ้น
      return false;
    });

    if (!pending.length) stop();
  }

  function stop() {
    window.removeEventListener("scroll", onScroll);
    window.removeEventListener("resize", onScroll);
    if (_revealStops.get(selector) === stop) _revealStops.delete(selector);
  }

  function onScroll() {
    if (ticking) return;
    ticking = true;
    requestAnimationFrame(sweep);
  }

  _revealStops.set(selector, stop);         // ให้รอบถัดไปของตัวเลือกนี้ยกเลิกรอบนี้ได้
  window.addEventListener("scroll", onScroll, { passive: true });
  window.addEventListener("resize", onScroll);
  sweep();   // ตรวจรอบแรกทันที เผื่อบางส่วนอยู่ในจอตั้งแต่เปิดหน้า
}

// ============================================================
// นับตัวเลขขึ้นจาก 0
// ============================================================
function countUp(el, target, duration = 900) {
  const end = Number(target) || 0;
  if (!end) { el.textContent = String(target); return; }

  const start = performance.now();
  const step = (now) => {
    const t = Math.min((now - start) / duration, 1);
    // ชะลอตอนท้ายให้ดูนุ่ม
    const eased = 1 - Math.pow(1 - t, 3);
    el.textContent = Math.round(end * eased).toLocaleString("th-TH");
    if (t < 1) requestAnimationFrame(step);
  };
  requestAnimationFrame(step);
}

// ---------- แถบเมนูด้านบน ----------
function renderNavbar(active = "") {
  // ล้างเซสชันที่หมดอายุก่อน เพื่อไม่ให้แสดงว่าล็อกอินอยู่ทั้งที่ใช้งานไม่ได้แล้ว
  clearExpiredSession();
  const user = Auth.user;
  const link = (href, label, key) =>
    `<a href="${href}" class="nav-link ${active === key ? "is-active" : ""}">${label}</a>`;

  // ลิงก์เฉพาะบทบาท — เจ้าของร้านเห็นหน้าจัดการร้าน, admin เห็นหน้าผู้ดูแล
  const roleLink = user
    ? user.role === "owner"
      ? link("manage.html", "จัดการร้าน", "manage")
      : user.role === "admin"
        ? link("admin.html", "ผู้ดูแลระบบ", "admin")
        : ""
    : "";

  const right = user
    ? `<div class="flex items-center gap-1.5">
         ${roleLink}
         <button id="bellBtn" class="bell" aria-label="การแจ้งเตือน" title="การแจ้งเตือน">
           ${icon("bell", 18)}<span id="bellDot" class="bell-dot" hidden></span>
         </button>
         ${link("bookings.html", "การจองของฉัน", "bookings")}
         <a href="profile.html" class="flex items-center gap-2.5 pl-3.5 pr-1.5 py-1.5 no-underline"
            style="background:rgba(255,255,255,.1);border-radius:999px">
           <span class="text-sm hidden sm:inline" style="color:rgba(255,255,255,.92)">${esc(user.full_name)}</span>
           <span class="w-7 h-7 grid place-items-center text-xs font-semibold"
                 style="background:var(--blue-600);color:#fff;border-radius:999px">${esc(user.full_name.trim().charAt(0))}</span>
         </a>
       </div>`
    : `<div class="flex items-center gap-1.5">
         <a href="login.html" class="nav-link flex items-center gap-1.5">${icon("user", 14)} เข้าสู่ระบบ</a>
         <a href="register.html" class="btn btn-primary btn-sm">สมัครสมาชิก</a>
       </div>`;

  document.getElementById("navbar").innerHTML = `
    <header style="background:var(--navy-800)" class="sticky top-0 z-40">
      <div class="max-w-6xl mx-auto px-5 h-16 flex items-center gap-6">
        <a href="index.html" class="flex items-center gap-2.5 shrink-0 no-underline">
          ${brandMark(28, "#fff")}
          <span class="text-xl text-white brand-name">Bookvice</span>
        </a>
        <nav class="hidden md:flex items-center gap-1 mx-auto">
          ${link("index.html", "หน้าแรก", "home")}
          ${link("shops.html", "ค้นหาร้าน", "shops")}
          ${link("promotions.html", "ราคาและดีล", "promo")}
        </nav>
        <div class="ml-auto md:ml-0">${right}</div>
      </div>
    </header>

    <!-- กล่องการแจ้งเตือน -->
    <div id="notifPanel" class="notif-panel" hidden>
      <div class="notif-head">
        <span>การแจ้งเตือน</span>
        <button id="notifReadAll" class="btn btn-ghost btn-sm" style="padding:2px 8px">อ่านทั้งหมด</button>
      </div>
      <div id="notifList" class="notif-list"></div>
    </div>`;

  renderMobileNav(active);
  if (user) bindBell();
}

// ============================================================
// แถบเมนูล่างสำหรับมือถือ
// จอเล็กจะซ่อนลิงก์ในแถบบนทั้งหมด ถ้าไม่มีอันนี้ผู้ใช้จะไปหน้าอื่นไม่ได้เลย
// วางไว้ล่างจอเพราะนิ้วโป้งเอื้อมถึงง่ายกว่าเมนูแฮมเบอร์เกอร์มุมบน
// ============================================================
function renderMobileNav(active = "") {
  if (document.getElementById("mobileNav")) return;

  const user = Auth.user;
  const items = [
    ["index.html", "หน้าแรก", "home", "sparkle"],
    ["shops.html", "ค้นหา", "shops", "search"],
    ["promotions.html", "ราคาและดีล", "promo", "creditCard"],
    user
      ? ["bookings.html", "การจอง", "bookings", "calendar"]
      : ["register.html", "สมัคร", "register", "calendar"],
    user
      ? ["profile.html", "บัญชี", "profile", "user"]
      : ["login.html", "เข้าสู่ระบบ", "login", "user"],
  ];

  const el = document.createElement("nav");
  el.id = "mobileNav";
  el.className = "mnav";
  el.innerHTML = items.map(([href, label, key, ic]) => `
    <a href="${href}" class="mnav-item ${active === key ? "is-active" : ""}">
      ${icon(ic, 20)}<span>${label}</span>
    </a>`).join("");
  document.body.appendChild(el);
}

// เก็บ handler ของรอบก่อนไว้ถอดทิ้ง — ดูเหตุผลในตัว bindBell
let _bellOutsideClick = null;

// ============================================================
// กระดิ่งแจ้งเตือน — ดึงเฉพาะจำนวนตอนเปิดหน้า รายการค่อยดึงตอนกด
// ============================================================
function bindBell() {
  const btn = document.getElementById("bellBtn");
  const dot = document.getElementById("bellDot");
  const panel = document.getElementById("notifPanel");
  const list = document.getElementById("notifList");
  if (!btn) return;

  async function refreshCount() {
    try {
      const r = await apiGet("/api/notifications/unread-count");
      dot.hidden = !r.unread;
      dot.textContent = r.unread > 9 ? "9+" : r.unread;
    } catch { dot.hidden = true; }
  }

  const KIND_ICON = {
    booking_confirmed: "check", booking_cancelled: "x", booking_completed: "star",
    booking_new: "calendar", booking_moved: "clock", review_reply: "user",
  };

  async function loadList() {
    list.innerHTML = '<p class="notif-empty">กำลังโหลด</p>';
    try {
      const r = await apiGet("/api/notifications?page=1&limit=12");
      if (!r.items.length) {
        list.innerHTML = '<p class="notif-empty">ยังไม่มีการแจ้งเตือน</p>';
        return;
      }
      list.innerHTML = r.items.map((n) => `
        <a class="notif-item ${n.is_read ? "" : "is-new"}" href="${esc(n.link || "bookings.html")}"
           data-nid="${n.id}">
          <span class="notif-ic">${icon(KIND_ICON[n.kind] || "info", 15)}</span>
          <span style="min-width:0">
            <span class="notif-title">${esc(n.title)}</span>
            ${n.body ? `<span class="notif-body">${esc(n.body)}</span>` : ""}
            <span class="notif-time">${thaiDate(n.created_at.slice(0, 10))}</span>
          </span>
        </a>`).join("");

      // กดแล้วทำเครื่องหมายว่าอ่านก่อนค่อยเปลี่ยนหน้า
      list.querySelectorAll("[data-nid]").forEach((a) =>
        a.addEventListener("click", () => {
          apiPatch(`/api/notifications/${a.dataset.nid}/read`, {}).catch(() => {});
        })
      );
    } catch (err) {
      list.innerHTML = `<p class="notif-empty">${esc(err.message)}</p>`;
    }
  }

  btn.addEventListener("click", (e) => {
    e.stopPropagation();
    panel.hidden = !panel.hidden;
    if (!panel.hidden) loadList();
  });

  document.getElementById("notifReadAll").addEventListener("click", async (e) => {
    e.stopPropagation();
    try {
      await apiPost("/api/notifications/read-all", {});
      dot.hidden = true;
      loadList();
    } catch {}
  });

  // คลิกที่อื่นแล้วปิด
  //
  // listener ตัวนี้อยู่บน document ซึ่งไม่หายไปพร้อมแถบเมนูที่ถูกวาดใหม่
  // ต่างจาก listener บนปุ่มกระดิ่งเอง หน้าไหนที่เรียก renderNavbar() ซ้ำ ๆ
  // (เช่นหน้าโปรไฟล์ที่เรียกใหม่ทุกครั้งที่กดบันทึก) จะสะสมตัวค้างไว้เรื่อย ๆ
  // แต่ละตัวยังอ้างกล่องแจ้งเตือนเก่าที่หลุดจากหน้าไปแล้ว
  if (_bellOutsideClick) document.removeEventListener("click", _bellOutsideClick);
  _bellOutsideClick = (e) => {
    if (!panel.hidden && !panel.contains(e.target)) panel.hidden = true;
  };
  document.addEventListener("click", _bellOutsideClick);

  refreshCount();
}

// ---------- ส่วนท้าย ----------
function renderFooter() {
  const el = document.getElementById("footer");
  if (!el) return;

  const col = (title, items) => `
    <div>
      <div class="text-sm font-semibold text-white">${title}</div>
      <ul class="mt-3.5 space-y-2.5 text-sm list-none p-0 m-0" style="color:rgba(255,255,255,.62)">
        ${items.map(([label, href]) =>
          href
            ? `<li><a href="${href}" class="no-underline" style="color:inherit">${label}</a></li>`
            : `<li>${label}</li>`
        ).join("")}
      </ul>
    </div>`;

  el.innerHTML = `
    <footer style="background:var(--navy-900)" class="mt-20">
      <div class="max-w-6xl mx-auto px-5 py-14">
        <div class="grid sm:grid-cols-2 lg:grid-cols-4 gap-10">
          <div>
            <div class="flex items-center gap-2.5">
              ${brandMark(26, "#fff")}
              <span class="text-lg text-white brand-name">Bookvice</span>
            </div>
            <p class="text-sm mt-2" style="color:var(--teal-400);font-weight:500">
              จองง่าย ได้ครบ จบที่เดียว
            </p>
            <p class="text-sm mt-3.5" style="color:rgba(255,255,255,.55);max-width:30ch">
              แพลตฟอร์มจองบริการสุขภาพและความงาม รวมร้านที่ผ่านการคัดกรองมาตรฐานไว้ในที่เดียว
            </p>
          </div>
          ${col("สำหรับผู้ใช้บริการ", [
            ["ค้นหาร้าน", "shops.html"],
            ["ราคาและดีล", "promotions.html"],
            ["การจองของฉัน", "bookings.html"],
            ["คำถามที่พบบ่อย", "index.html#main"],
          ])}
          ${col("สำหรับร้านค้า", [
            ["เปิดร้านบน Bookvice", "register.html"],
            ["จัดการร้านของฉัน", "manage.html"],
          ])}
          ${col("เอกสารระบบ", [
            ["เอกสาร API (Swagger)", `${API_BASE}/docs`],
            ["เอกสาร API (ReDoc)", `${API_BASE}/redoc`],
          ])}
        </div>

        <div class="mt-12 pt-6" style="border-top:1px solid rgba(255,255,255,.1)">
          <div class="text-xs" style="color:rgba(255,255,255,.4);line-height:1.8">
            โปรเจกต์รายวิชา 89033167 Web Application Development · จัดทำเพื่อการศึกษา<br />
            ข้อมูลร้านและรีวิวในระบบเป็นข้อมูลตัวอย่างสำหรับสาธิต
            และการชำระเงินเป็นการจำลอง ไม่มีการตัดเงินจริง
          </div>
        </div>
      </div>
    </footer>`;
}

// ---------- แจ้งเตือน ----------
function showAlert(el, message, type = "error") {
  if (!el) return;
  el.className = `alert alert-${type}`;
  el.textContent = message;
  el.style.display = "block";

  // role="alert" ทำให้โปรแกรมอ่านหน้าจออ่านข้อความนี้ทันทีที่โผล่
  // ถ้าไม่ใส่ คนที่มองไม่เห็นจะกดปุ่มแล้วเงียบไปเฉย ๆ ไม่รู้ว่าพลาดตรงไหน
  el.setAttribute("role", type === "error" ? "alert" : "status");

  // เล่นแอนิเมชันเข้าใหม่ทุกครั้ง แม้ข้อความเดิมจะยังค้างอยู่
  // (ถอดคลาสแล้วบังคับให้เบราว์เซอร์คำนวณใหม่ก่อนใส่กลับ ไม่งั้นจะไม่เล่นซ้ำ)
  el.classList.remove("is-in");
  void el.offsetWidth;
  el.classList.add("is-in");
}

function hideAlert(el) {
  if (!el) return;
  el.style.display = "none";
  el.classList.remove("is-in");
  el.removeAttribute("role");
}

/**
 * ครอบงานที่ต้องรอเซิร์ฟเวอร์ ให้ปุ่มเข้าสถานะกำลังทำงานและคืนสภาพเสมอ
 *
 * รวม try/finally ไว้ที่เดียว หน้าเรียกใช้จึงลืมคืนปุ่มไม่ได้
 * ข้อผิดพลาดยังถูกโยนต่อออกไปเหมือนเดิม ผู้เรียกจัดการเองได้ตามใจ
 */
async function withBusy(btn, label, task) {
  btnBusy(btn, true, label);
  try {
    return await task();
  } finally {
    btnBusy(btn, false);
  }
}

// ---------- สถานะโหลด / ว่างเปล่า ----------
const loadingHTML = (text = "กำลังโหลด") => `
  <div class="py-16 text-center fill-row">
    <div class="spinner mx-auto"></div>
    <p class="mt-3 text-sm text-muted">${text}</p>
  </div>`;

const emptyHTML = (iconName, title, sub = "") => `
  <div class="py-16 text-center fill-row">
    <div class="mx-auto w-12 h-12 rounded-full grid place-items-center"
         style="background:var(--navy-50);color:var(--navy-800)">${icon(iconName, 22)}</div>
    <p class="mt-4 font-medium">${title}</p>
    ${sub ? `<p class="text-sm text-muted mt-1">${sub}</p>` : ""}
  </div>`;

// ============================================================
// ร้านโปรด — เก็บไว้ในเครื่องผู้ใช้ ไม่ต้องล็อกอินก็กดบันทึกได้
// ============================================================
const Favorites = {
  KEY: "bookvice_favorites",

  list() {
    try {
      const raw = JSON.parse(localStorage.getItem(this.KEY) || "[]");
      return Array.isArray(raw) ? raw.map(Number).filter(Number.isFinite) : [];
    } catch {
      return [];   // ข้อมูลเสีย ให้ถือว่ายังไม่มีร้านโปรด ดีกว่าปล่อยให้หน้าพัง
    }
  },

  has(id) { return this.list().includes(Number(id)); },
  count() { return this.list().length; },

  /** สลับสถานะร้านโปรด คืนค่าใหม่ว่าอยู่ในรายการหรือไม่ */
  toggle(id) {
    id = Number(id);
    const list = this.list();
    const i = list.indexOf(id);
    if (i >= 0) list.splice(i, 1);
    else list.push(id);
    localStorage.setItem(this.KEY, JSON.stringify(list));
    return i < 0;
  },
};

// ============================================================
// ร้านนี้เปิดอยู่ไหมตอนนี้ — ช่วยให้ลูกค้ารู้ว่าโทรไปได้เลยหรือยัง
// ============================================================
function shopStatus(shop) {
  const toMin = (t) => Number(String(t).slice(0, 2)) * 60 + Number(String(t).slice(3, 5));
  const now = new Date();
  const cur = now.getHours() * 60 + now.getMinutes();
  const open = toMin(shop.open_time);
  const close = toMin(shop.close_time);

  if (cur < open) {
    const left = open - cur;
    return left <= 60
      ? { text: `เปิดในอีก ${left} นาที`, cls: "st-soon" }
      : { text: `เปิด ${shortTime(shop.open_time)} น.`, cls: "st-closed" };
  }
  if (cur >= close) return { text: "ปิดแล้ววันนี้", cls: "st-closed" };

  const left = close - cur;
  if (left <= 60) return { text: `ใกล้ปิด · อีก ${left} นาที`, cls: "st-soon" };
  return { text: "เปิดอยู่ตอนนี้", cls: "st-open" };
}

// ============================================================
// แจ้งเตือนแบบลอย (toast) — ไม่ดันเนื้อหาให้กระโดดเหมือนกล่อง alert
// ============================================================
function toast(message, type = "success", ms = 3200) {
  let box = document.getElementById("toastBox");
  if (!box) {
    box = document.createElement("div");
    box.id = "toastBox";
    box.className = "toast-box";
    document.body.appendChild(box);
  }

  const el = document.createElement("div");
  el.className = `toast toast-${type}`;
  el.innerHTML = `${icon(type === "error" ? "info" : "check", 15)}<span>${esc(message)}</span>`;
  box.appendChild(el);

  // ให้เวลาเบราว์เซอร์วาดก่อน แล้วค่อยเลื่อนขึ้นมา จะได้เห็นแอนิเมชัน
  requestAnimationFrame(() => el.classList.add("is-in"));
  setTimeout(() => {
    el.classList.remove("is-in");
    setTimeout(() => el.remove(), 260);
  }, ms);
}

// ============================================================
// โครงร่างระหว่างโหลด — เห็นรูปทรงหน้าก่อน ไม่ใช่จอว่างกับวงกลมหมุน
// ============================================================
// โครงร่างการ์ดร้านระหว่างโหลด
//
// พารามิเตอร์ cardH คือ "ความสูงของการ์ดจริง" ของหน้านั้น ๆ (วัดมาแล้ว)
// ต้องใส่ให้ตรง ไม่งั้นพอข้อมูลมาถึง การ์ดจริงจะสูงกว่าโครงร่าง
// แล้วดันทุกอย่างข้างล่าง (รวมท้ายเว็บ) กระโดดลงไป
//   หน้าแรก 338px · หน้าค้นหา 316px — ต่างกันเพราะรูปหน้าปกคนละความสูง (h-40 กับ h-36)
const skeletonCards = (n = 6, artH = 144, cardH = 316) => `
  <div class="sk-grid">${Array.from({ length: n }, () => `
    <div class="card overflow-hidden" style="min-height:${cardH}px">
      <div class="skeleton" style="height:${artH}px;border-radius:0"></div>
      <div class="p-5">
        <div class="skeleton" style="height:16px;width:65%"></div>
        <div class="skeleton" style="height:12px;width:95%;margin-top:10px"></div>
        <div class="skeleton" style="height:12px;width:80%;margin-top:6px"></div>
        <div class="skeleton" style="height:12px;width:45%;margin-top:16px"></div>
      </div>
    </div>`).join("")}</div>`;

// โครงร่างแบบ "รายการเรียงลง" — ใช้กับหน้าที่เนื้อหาเป็นแถวยาว ๆ
// เช่นรายการจอง หรือตารางผู้ใช้ในหน้าผู้ดูแล
//
// ทำไมไม่ใช้ loadingHTML() เฉย ๆ: วงกลมหมุนสูงราว 130px แต่ของจริงสูงเป็นพันพิกเซล
// พอข้อมูลมาถึง หน้าจะยืดออกทีเดียวแล้วดันทุกอย่างข้างล่างลงไป — นั่นคืออาการ "ไม่สมูท"
// โครงร่างที่สูงใกล้ของจริงทำให้ตำแหน่งแทบไม่ขยับเลยตอนข้อมูลมาถึง
const skeletonRows = (n = 3, height = 240) => `
  <div class="sk-rows" aria-busy="true" aria-label="กำลังโหลด">${Array.from({ length: n }, () => `
    <div class="card card-pad">
      <div class="skeleton" style="height:15px;width:42%"></div>
      <div class="skeleton" style="height:12px;width:70%;margin-top:14px"></div>
      <div class="skeleton" style="height:12px;width:55%;margin-top:8px"></div>
      <div class="skeleton" style="height:${Math.max(height - 118, 40)}px;margin-top:16px"></div>
    </div>`).join("")}</div>`;

// โครงร่างของกล่องตัวเลขสรุปด้านบน (หน้าผู้ดูแล)
const skeletonTiles = (n = 4) =>
  Array.from({ length: n }, () => `
    <div class="card p-4">
      <div class="skeleton" style="height:11px;width:60%"></div>
      <div class="skeleton" style="height:22px;width:40%;margin-top:8px"></div>
    </div>`).join("");

// ============================================================
// ล็อกการเลื่อนหน้าหลังตอนเปิดกล่องซ้อน ไม่ให้พื้นหลังไถลตาม
// ============================================================
function lockScroll(on) {
  if (on) {
    // จำตำแหน่งแถบเลื่อนไว้ กันหน้ากระตุกตอนแถบหาย
    const bar = window.innerWidth - document.documentElement.clientWidth;
    document.body.style.paddingRight = bar > 0 ? `${bar}px` : "";
    document.body.classList.add("no-scroll");
  } else {
    document.body.classList.remove("no-scroll");
    document.body.style.paddingRight = "";
  }
}

// ---------- ขังโฟกัสไว้ในกล่องซ้อน ----------
//
// ถ้าไม่ทำ กด Tab ในกล่องซ้อนแล้วโฟกัสจะไหลออกไปยังลิงก์บนหน้าหลังกล่อง
// ทั้งที่ตามองไม่เห็น คนใช้แป้นพิมพ์และโปรแกรมอ่านหน้าจอจะหลงทางทันที
const FOCUSABLE = [
  "a[href]", "button:not([disabled])", "input:not([disabled])",
  "select:not([disabled])", "textarea:not([disabled])",
  '[tabindex]:not([tabindex="-1"])',
].join(",");

// จำว่าใครเป็นคนกดเปิดกล่อง เพื่อคืนโฟกัสให้ตอนปิด
const _modalMemo = new WeakMap();

// เอาเฉพาะที่มองเห็นจริง — ปุ่มในส่วนที่ถูกซ่อนอยู่ไม่ควรรับโฟกัส
const _visible = (root) =>
  [...root.querySelectorAll(FOCUSABLE)].filter((n) => n.getClientRects().length > 0);

// เปิด/ปิดกล่องซ้อนพร้อมล็อกการเลื่อน ใช้แทน classList.add("is-open") ทุกที่
function openModal(el) {
  if (!el || el.classList.contains("is-open")) return;

  const onKey = (e) => {
    if (e.key !== "Tab") return;
    const items = _visible(el);
    if (!items.length) return;
    const first = items[0];
    const last = items[items.length - 1];
    if (e.shiftKey && document.activeElement === first) {
      e.preventDefault();
      last.focus();
    } else if (!e.shiftKey && document.activeElement === last) {
      e.preventDefault();
      first.focus();
    }
  };

  _modalMemo.set(el, { opener: document.activeElement, onKey });
  el.addEventListener("keydown", onKey);
  el.classList.add("is-open");
  lockScroll(true);

  // ย้ายโฟกัสเข้าไปในกล่อง ให้ Esc และ Tab ทำงานทันทีโดยไม่ต้องกดอะไรก่อน
  // ใส่ data-autofocus บนปุ่มที่อยากให้โฟกัสเป็นอันดับแรกได้
  requestAnimationFrame(() => {
    if (!el.classList.contains("is-open")) return;
    const target = el.querySelector("[data-autofocus]") || _visible(el)[0];
    if (target) target.focus({ preventScroll: true });
  });
}

function closeModalEl(el) {
  if (!el) return;
  const memo = _modalMemo.get(el);
  if (memo) {
    el.removeEventListener("keydown", memo.onKey);
    _modalMemo.delete(el);
  }

  el.classList.remove("is-open");
  // ยังมีกล่องอื่นเปิดอยู่ไหม ถ้าไม่มีค่อยปลดล็อก
  if (!document.querySelector(".modal-backdrop.is-open")) lockScroll(false);

  // คืนโฟกัสให้ปุ่มที่กดเปิด — ไม่งั้นโฟกัสจะเด้งกลับไปต้นหน้า
  // เช็ก document.contains ก่อน เพราะบางหน้าวาดปุ่มใหม่ระหว่างที่กล่องเปิดอยู่
  const back = memo && memo.opener;
  if (back && typeof back.focus === "function" && document.contains(back)) {
    back.focus({ preventScroll: true });
  }
}

// ============================================================
// สถานะ "กำลังทำงาน" ของปุ่ม
//
// ก่อนหน้านี้แต่ละหน้าเขียนเอง เป็น btn.textContent = "กำลัง..."
// ซึ่งมีปัญหาสองอย่าง: ไอคอนในปุ่มหายไป และความกว้างปุ่มกระโดด
// ทำให้ปุ่มข้าง ๆ ขยับตามทุกครั้งที่กด
//
// ตัวช่วยนี้ล็อกความกว้างเดิมไว้ก่อนสลับข้อความ ปุ่มจึงอยู่นิ่ง
// และคืนเนื้อหาเดิมกลับให้ครบตอนจบ โดยที่หน้าเรียกใช้ไม่ต้องจำเอง
// ============================================================
const _btnMemo = new WeakMap();

function btnBusy(btn, on = true, label = "กำลังทำรายการ") {
  if (!btn) return;

  if (on) {
    if (_btnMemo.has(btn)) return;          // กดรัว ๆ ไม่ให้ทับสถานะเดิม
    _btnMemo.set(btn, { html: btn.innerHTML, minWidth: btn.style.minWidth });

    // วัดความกว้างก่อนเปลี่ยนเนื้อหา แล้วตรึงไว้ ปุ่มจะได้ไม่หด
    btn.style.minWidth = `${Math.ceil(btn.getBoundingClientRect().width)}px`;
    btn.classList.add("is-busy");
    btn.setAttribute("aria-busy", "true");
    if ("disabled" in btn) btn.disabled = true;
    btn.innerHTML =
      `<span class="btn-spin" aria-hidden="true"></span><span>${esc(label)}</span>`;
    return;
  }

  const prev = _btnMemo.get(btn);
  if (!prev) return;
  _btnMemo.delete(btn);
  btn.innerHTML = prev.html;
  btn.style.minWidth = prev.minWidth;
  btn.classList.remove("is-busy");
  btn.removeAttribute("aria-busy");
  if ("disabled" in btn) btn.disabled = false;
}

/** แสดงเครื่องหมายถูกในปุ่มสั้น ๆ แล้วคืนสภาพเดิม — ใช้กับงานที่ทำเสร็จในที่ */
function btnOk(btn, label = "เรียบร้อย", ms = 1500) {
  if (!btn) return;
  btnBusy(btn, false);                       // เผื่อยังค้างสถานะกำลังทำงานอยู่
  const memo = { html: btn.innerHTML, minWidth: btn.style.minWidth };
  btn.style.minWidth = `${Math.ceil(btn.getBoundingClientRect().width)}px`;
  btn.classList.add("is-ok");
  btn.innerHTML = `${icon("check", 15)}<span>${esc(label)}</span>`;
  setTimeout(() => {
    btn.innerHTML = memo.html;
    btn.style.minWidth = memo.minWidth;
    btn.classList.remove("is-ok");
  }, ms);
}

// ============================================================
// กล่องถามยืนยัน และกล่องกรอกข้อความ
//
// มาแทน confirm() / prompt() / alert() ของเบราว์เซอร์ ซึ่งมีปัญหาคือ
// หน้าตาไม่เข้ากับเว็บเลย ทำให้ดูเหมือนงานที่ยังทำไม่เสร็จ
// จัดข้อความยาว ๆ ไม่ได้ และแยกไม่ออกว่าปุ่มไหนคือปุ่มที่ลบของจริง
//
// ทั้งสองฟังก์ชันคืน Promise จึงเขียนต่อด้วย await ได้ตรง ๆ
// ============================================================
function _dialogShell({ title, message, bodyHTML = "", confirmText, cancelText, tone }) {
  const back = document.createElement("div");
  back.className = "modal-backdrop dlg";
  back.setAttribute("role", "dialog");
  back.setAttribute("aria-modal", "true");
  back.innerHTML = `
    <div class="modal dlg-modal">
      <div class="dlg-body">
        <h2 class="dlg-title">${esc(title)}</h2>
        ${message ? `<p class="dlg-msg">${esc(message)}</p>` : ""}
        ${bodyHTML}
        <div class="dlg-actions">
          <button type="button" class="btn btn-outline" data-dlg="cancel">${esc(cancelText)}</button>
          <button type="button" class="btn ${tone === "danger" ? "btn-danger-solid" : "btn-primary"}"
                  data-dlg="ok">${esc(confirmText)}</button>
        </div>
      </div>
    </div>`;
  document.body.appendChild(back);
  return back;
}

function _closeDialog(back) {
  closeModalEl(back);
  // รอให้แอนิเมชันปิดเล่นจบก่อนค่อยถอดออกจากหน้า
  setTimeout(() => back.remove(), 220);
}

/**
 * ถามยืนยันก่อนทำสิ่งที่ย้อนกลับไม่ได้
 * เรียกได้ทั้ง confirmDialog("ข้อความ") และแบบใส่ตัวเลือกครบ
 * @returns {Promise<boolean>}
 */
function confirmDialog(opts = {}) {
  const o = typeof opts === "string" ? { message: opts } : opts;
  const {
    title = "ยืนยันการทำรายการ",
    message = "",
    confirmText = "ยืนยัน",
    cancelText = "ยกเลิก",
    tone = "default",
  } = o;

  const back = _dialogShell({ title, message, confirmText, cancelText, tone });

  // งานที่ลบของจริงให้โฟกัสปุ่มยกเลิกไว้ก่อน กด Enter ทันทีจะได้ไม่ลบโดยไม่ตั้งใจ
  const first = tone === "danger" ? "cancel" : "ok";
  back.querySelector(`[data-dlg="${first}"]`).setAttribute("data-autofocus", "");

  return new Promise((resolve) => {
    const done = (value) => { _closeDialog(back); resolve(value); };
    back.querySelector('[data-dlg="ok"]').addEventListener("click", () => done(true));
    back.querySelector('[data-dlg="cancel"]').addEventListener("click", () => done(false));
    back.addEventListener("click", (e) => { if (e.target === back) done(false); });
    back.addEventListener("keydown", (e) => { if (e.key === "Escape") done(false); });
    openModal(back);
  });
}

/**
 * ขอข้อความจากผู้ใช้หนึ่งช่อง
 * @returns {Promise<string|null>} null = ผู้ใช้กดยกเลิก · "" = ล้างข้อความทิ้ง
 */
function promptDialog(opts = {}) {
  const {
    title = "กรอกข้อความ",
    message = "",
    label = "",
    value = "",
    placeholder = "",
    maxlength = 1000,
    rows = 3,
    confirmText = "บันทึก",
    cancelText = "ยกเลิก",
  } = opts;

  const bodyHTML = `
    ${label ? `<label class="label" for="dlgInput" style="margin-top:14px">${esc(label)}</label>` : ""}
    <textarea id="dlgInput" class="textarea" rows="${rows}" maxlength="${maxlength}"
              data-autofocus placeholder="${esc(placeholder)}">${esc(value)}</textarea>
    <p class="hint"><span id="dlgCount">0</span>/${maxlength} ตัวอักษร</p>`;

  const back = _dialogShell({
    title, message, bodyHTML, confirmText, cancelText, tone: "default",
  });

  const input = back.querySelector("#dlgInput");
  const count = back.querySelector("#dlgCount");
  const paint = () => { count.textContent = input.value.length; };
  input.addEventListener("input", paint);
  paint();

  return new Promise((resolve) => {
    const done = (value) => { _closeDialog(back); resolve(value); };
    back.querySelector('[data-dlg="ok"]').addEventListener("click", () => done(input.value.trim()));
    back.querySelector('[data-dlg="cancel"]').addEventListener("click", () => done(null));
    back.addEventListener("click", (e) => { if (e.target === back) done(null); });
    back.addEventListener("keydown", (e) => {
      if (e.key === "Escape") done(null);
      // Ctrl/⌘ + Enter ส่งได้เลย ไม่ต้องเอื้อมไปกดปุ่ม
      if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) done(input.value.trim());
    });
    openModal(back);
    // วางเคอร์เซอร์ท้ายข้อความเดิม ไม่ใช่คลุมทั้งก้อน จะได้พิมพ์ต่อได้ทันที
    requestAnimationFrame(() => input.setSelectionRange(input.value.length, input.value.length));
  });
}

// ============================================================
// โหลดหน้าถัดไปล่วงหน้าตอนผู้ใช้ชี้เมาส์ — กดแล้วเปิดไวขึ้น
// ============================================================
function prefetchOnHover(selector = "a[href$='.html'], a[href*='.html?']") {
  const done = new Set();
  document.addEventListener("mouseover", (e) => {
    const a = e.target.closest(selector);
    if (!a || done.has(a.href) || a.target === "_blank") return;
    if (!a.href.startsWith(location.origin)) return;
    done.add(a.href);
    const link = document.createElement("link");
    link.rel = "prefetch";
    link.href = a.href;
    document.head.appendChild(link);
  }, { passive: true });
}


// ============================================================
// สลิปการจอง — เปิดหน้าต่างใหม่แล้วสั่งพิมพ์
// ใช้หน้าต่างแยกเพื่อไม่ให้สไตล์ของเว็บหลักไปกวนหน้ากระดาษ
// และผู้ใช้กด "บันทึกเป็น PDF" จากกล่องพิมพ์ของเบราว์เซอร์ได้เลย
// ============================================================
function printSlip(data) {
  const row = (label, value) =>
    value ? `<tr><th>${esc(label)}</th><td>${esc(String(value))}</td></tr>` : "";

  const html = `<!DOCTYPE html><html lang="th"><head><meta charset="UTF-8">
<title>สลิปการจอง ${esc(data.code)}</title>
<style>
  @page { size: A5; margin: 14mm; }
  * { box-sizing: border-box; }
  body { font-family: 'IBM Plex Sans Thai', 'Tahoma', sans-serif; color: #14202f;
         font-size: 13px; line-height: 1.75; margin: 0; }
  .head { display: flex; justify-content: space-between; align-items: flex-start;
          border-bottom: 2px solid #0f294b; padding-bottom: 10px; }
  .brand { font-size: 19px; font-weight: 700; color: #0f294b; letter-spacing: -.02em; }
  .sub { font-size: 11px; color: #667; }
  .code { text-align: right; }
  .code b { font-size: 17px; letter-spacing: .04em; }
  table { width: 100%; border-collapse: collapse; margin-top: 14px; }
  th, td { text-align: left; padding: 7px 0; vertical-align: top;
           border-bottom: 1px dashed #d6dee9; }
  th { width: 34%; font-weight: 500; color: #667; }
  td { font-weight: 500; }
  .total { display: flex; justify-content: space-between; align-items: baseline;
           margin-top: 16px; padding-top: 12px; border-top: 2px solid #0f294b; }
  .total .big { font-size: 21px; font-weight: 700; color: #0f294b; }
  .note { margin-top: 16px; padding: 9px 12px; background: #eef4fd;
          border-left: 3px solid #1a63d8; font-size: 11.5px; }
  footer { margin-top: 20px; text-align: center; font-size: 10.5px; color: #8894a6; }
</style></head><body>
  <div class="head">
    <div>
      <div class="brand">Bookvice</div>
      <div class="sub">จองง่าย ได้ครบ จบที่เดียว</div>
    </div>
    <div class="code">
      <div class="sub">รหัสการจอง</div>
      <b>${esc(data.code)}</b>
    </div>
  </div>

  <table>
    ${row("ร้าน", data.shop)}
    ${row("บริการ", data.service)}
    ${row("วันที่", data.date)}
    ${row("เวลา", data.time)}
    ${row(data.staffLabel ? `${data.staffLabel}ผู้ให้บริการ` : "ผู้ให้บริการ", data.staff)}
    ${row("ลูกค้า", data.customer)}
    ${row("เบอร์ติดต่อ", data.phone)}
    ${row("สถานะ", data.status)}
    ${row("สิ่งที่แจ้งไว้", data.note)}
  </table>

  <div class="total">
    <span>ยอดรวม</span>
    <span class="big">${esc(data.price)}</span>
  </div>
  ${data.deposit ? `<div class="sub" style="text-align:right">มัดจำ ${esc(data.deposit)}</div>` : ""}

  <div class="note">
    กรุณามาถึงก่อนเวลานัด 10 นาที · หากต้องการเลื่อนหรือยกเลิก
    โปรดแจ้งล่วงหน้าอย่างน้อย 2 ชั่วโมง
  </div>

  <footer>พิมพ์เมื่อ ${new Date().toLocaleString("th-TH")} · Bookvice</footer>
</body></html>`;

  openPrintWindow(html, 520, 720);
}


// ============================================================
// เปิดหน้าต่างสำหรับพิมพ์
// ============================================================
//
// **ห้ามเรียก w.print() จากหน้าหลักเด็ดขาด**
//
// window.print() เป็นคำสั่งแบบ "หยุดรอ" มันจะค้างอยู่จนกว่าผู้ใช้จะปิดกล่องพิมพ์
// และเพราะหน้าต่างที่เปิดด้วย window.open เป็นโดเมนเดียวกัน มันจึงใช้เธรดร่วมกับ
// หน้าหลัก ผลคือ **หน้าหลักค้างทั้งหน้า** เลื่อนไม่ได้ กดอะไรไม่ได้ จนกว่าจะจัดการ
// กล่องพิมพ์เสร็จ — ถ้าหน้าต่างนั้นไปโผล่หลังหน้าต่างอื่นหรือผู้ใช้ไม่ทันสังเกต
// จะดูเหมือนเว็บพังไปเลย (ผู้ใช้รายงานเข้ามาว่า "จ่ายเงินเสร็จแล้วเลื่อนไปไหนไม่ได้")
//
// ทางแก้คือฝังสคริปต์ไว้ในหน้าต่างลูก ให้มันสั่งพิมพ์ตัวเอง
// การหยุดรอจึงเกิดในหน้าต่างลูกเท่านั้น หน้าหลักยังใช้งานได้ตามปกติ
function openPrintWindow(html, width = 620, height = 800) {
  const w = window.open("", "_blank", `width=${width},height=${height}`);
  if (!w) {
    toast("เบราว์เซอร์บล็อกหน้าต่างใหม่ กรุณาอนุญาตป๊อปอัปแล้วลองอีกครั้ง", "error");
    return false;
  }

  const selfPrint = `<script>
    window.addEventListener("load", function () {
      window.focus();
      // หน่วงนิดหนึ่งให้ฟอนต์วาดเสร็จก่อน ไม่งั้นบางเบราว์เซอร์พิมพ์ออกมาเป็นหน้าว่าง
      setTimeout(function () { window.print(); }, 150);
    });
  <\/script>`;

  w.document.write(html.replace("</body>", `${selfPrint}</body>`));
  w.document.close();
  return true;
}


// ============================================================
// เวลาแบบเล่าเรื่อง — "3 วันที่แล้ว" อ่านง่ายกว่าวันที่เต็มสำหรับเรื่องที่เพิ่งเกิด
// เกิน 30 วันค่อยกลับไปใช้วันที่เต็ม เพราะ "125 วันที่แล้ว" ไม่ช่วยอะไร
// ============================================================
function timeAgo(iso) {
  const then = new Date(iso);
  if (isNaN(then)) return "";
  const mins = Math.floor((Date.now() - then.getTime()) / 60000);

  if (mins < 1) return "เมื่อสักครู่";
  if (mins < 60) return `${mins} นาทีที่แล้ว`;

  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs} ชั่วโมงที่แล้ว`;

  const days = Math.floor(hrs / 24);
  if (days === 1) return "เมื่อวาน";
  if (days < 7) return `${days} วันที่แล้ว`;
  if (days < 30) return `${Math.floor(days / 7)} สัปดาห์ที่แล้ว`;

  return thaiDate(String(iso).slice(0, 10));
}

// ============================================================
// แกลเลอรีรูปร้าน + กล่องดูรูปเต็มจอ
// ============================================================

// วาดแกลเลอรี: รูปใหญ่หนึ่งรูป + รูปย่อยด้านข้าง (บนมือถือเลื่อนแนวนอน)
function galleryHTML(images) {
  if (!images || !images.length) return "";
  const first = images[0];
  const rest = images.slice(1, 5);
  const more = images.length - 5;

  const thumb = (im, i, overlay) => `
    <button type="button" class="gal-thumb" data-gal="${i}"
            aria-label="ดูรูปที่ ${i + 1} จาก ${images.length}">
      <img src="${esc(fileUrl(im.url))}" alt="" loading="lazy" decoding="async" />
      ${overlay ? `<span class="gal-more num">+${overlay}</span>` : ""}
    </button>`;

  return `
    <div class="gallery" id="gallery">
      <button type="button" class="gal-main" data-gal="0" aria-label="ดูรูปขนาดเต็ม">
        <img src="${esc(fileUrl(first.url))}" alt="${esc(first.caption || "รูปร้าน")}"
             decoding="async" />
        <span class="gal-count num">${icon("camera", 13)} ${images.length}</span>
      </button>
      ${rest.length ? `<div class="gal-side">
        ${rest.map((im, i) => thumb(im, i + 1, i === rest.length - 1 && more > 0 ? more : 0)).join("")}
      </div>` : ""}
    </div>`;
}

// กล่องดูรูปเต็มจอ — เลื่อนด้วยลูกศรซ้าย/ขวา ปิดด้วย Esc
function bindGallery(images) {
  const box = document.getElementById("gallery");
  if (!box || !images.length) return;

  let at = 0;
  const overlay = document.createElement("div");
  overlay.className = "lightbox";
  overlay.setAttribute("role", "dialog");
  overlay.setAttribute("aria-modal", "true");
  overlay.innerHTML = `
    <button class="lb-close" aria-label="ปิด">${icon("x", 20)}</button>
    <button class="lb-nav lb-prev" aria-label="รูปก่อนหน้า">${icon("chevronLeft", 22)}</button>
    <figure class="lb-stage">
      <img alt="" />
      <figcaption class="lb-cap"></figcaption>
    </figure>
    <button class="lb-nav lb-next" aria-label="รูปถัดไป">${icon("chevronRight", 22)}</button>`;
  document.body.appendChild(overlay);

  const img = overlay.querySelector("img");
  const cap = overlay.querySelector(".lb-cap");

  function show(i) {
    at = (i + images.length) % images.length;   // วนกลับต้น/ท้ายได้
    img.src = fileUrl(images[at].url);
    img.alt = images[at].caption || `รูปร้าน ${at + 1}`;
    cap.textContent = `${at + 1} / ${images.length}${images[at].caption ? " · " + images[at].caption : ""}`;
  }

  // ใช้ openModal/closeModalEl ตัวเดียวกับกล่องซ้อนอื่น จะได้ขังโฟกัสไว้ในกล่อง
  // และคืนโฟกัสกลับไปที่รูปที่กดเปิด เหมือนกันทั้งเว็บ
  function open(i) {
    show(i);
    openModal(overlay);
  }
  function close() {
    closeModalEl(overlay);
  }

  box.addEventListener("click", (e) => {
    const btn = e.target.closest("[data-gal]");
    if (btn) open(Number(btn.dataset.gal));
  });

  overlay.querySelector(".lb-close").onclick = close;
  overlay.querySelector(".lb-prev").onclick = () => show(at - 1);
  overlay.querySelector(".lb-next").onclick = () => show(at + 1);
  // คลิกพื้นหลังเพื่อปิด แต่คลิกที่ตัวรูปต้องไม่ปิด
  overlay.addEventListener("click", (e) => {
    if (e.target === overlay) close();
  });

  document.addEventListener("keydown", (e) => {
    if (!overlay.classList.contains("is-open")) return;
    if (e.key === "Escape") close();
    if (e.key === "ArrowLeft") show(at - 1);
    if (e.key === "ArrowRight") show(at + 1);
  });
}

// ============================================================
// แผนที่ (Leaflet + OpenStreetMap — ไม่ต้องใช้คีย์และไม่มีค่าใช้จ่าย)
// ============================================================
const LEAFLET_CSS = "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css";
const LEAFLET_JS = "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js";

let _leafletReady = null;

// โหลด Leaflet แค่ตอนที่มีแผนที่จะแสดงจริง ๆ
// ถ้าใส่ไว้ในทุกหน้าตั้งแต่แรก หน้าที่ไม่มีแผนที่จะโหลดช้าลงโดยเปล่าประโยชน์
function loadLeaflet() {
  if (_leafletReady) return _leafletReady;
  _leafletReady = new Promise((resolve, reject) => {
    const css = document.createElement("link");
    css.rel = "stylesheet";
    css.href = LEAFLET_CSS;
    document.head.appendChild(css);

    const js = document.createElement("script");
    js.src = LEAFLET_JS;
    js.onload = () => resolve(window.L);
    js.onerror = () => reject(new Error("โหลดแผนที่ไม่สำเร็จ"));
    document.head.appendChild(js);
  });
  return _leafletReady;
}

// วาดแผนที่แสดงตำแหน่งร้านหนึ่งร้าน
async function renderShopMap(elId, shop) {
  const el = document.getElementById(elId);
  if (!el || shop.latitude == null || shop.longitude == null) return;

  const lat = Number(shop.latitude);
  const lng = Number(shop.longitude);

  let L;
  try {
    L = await loadLeaflet();
  } catch {
    el.innerHTML = `<p class="hint" style="margin:0;padding:20px">แสดงแผนที่ไม่ได้ในขณะนี้</p>`;
    return;
  }

  const map = L.map(el, {
    center: [lat, lng],
    zoom: 16,
    // ปิดการซูมด้วยล้อเมาส์ ไม่งั้นผู้ใช้เลื่อนหน้าเว็บผ่านแผนที่แล้วจะโดนซูมแทน
    scrollWheelZoom: false,
    attributionControl: true,
  });

  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19,
    attribution: '&copy; ผู้ร่วมสร้าง OpenStreetMap',
  }).addTo(map);

  L.marker([lat, lng]).addTo(map).bindPopup(`<b>${esc(shop.name)}</b>`);

  // กดที่แผนที่หนึ่งครั้งเพื่อเปิดใช้งานการซูม — กันการซูมโดยไม่ตั้งใจ
  map.once("click", () => map.scrollWheelZoom.enable());
}

// ขอตำแหน่งปัจจุบันจากเบราว์เซอร์
function askLocation(timeoutMs = 8000) {
  return new Promise((resolve, reject) => {
    if (!navigator.geolocation) {
      return reject(new Error("เบราว์เซอร์นี้ไม่รองรับการระบุตำแหน่ง"));
    }
    navigator.geolocation.getCurrentPosition(
      (pos) => resolve({ lat: pos.coords.latitude, lng: pos.coords.longitude }),
      (err) => {
        const msg = {
          1: "คุณปฏิเสธการเข้าถึงตำแหน่ง — เปิดสิทธิ์ในเบราว์เซอร์แล้วลองใหม่",
          2: "หาตำแหน่งไม่ได้ กรุณาตรวจสอบ GPS หรือการเชื่อมต่อ",
          3: "ใช้เวลานานเกินไป กรุณาลองใหม่อีกครั้ง",
        }[err.code] || "ระบุตำแหน่งไม่สำเร็จ";
        reject(new Error(msg));
      },
      { enableHighAccuracy: true, timeout: timeoutMs, maximumAge: 60000 }
    );
  });
}

// ระยะทางในรูปแบบที่คนอ่านเข้าใจง่าย
const distanceText = (km) =>
  km == null ? "" : km < 1 ? `${Math.round(km * 1000)} ม.` : `${km.toFixed(1)} กม.`;

// ============================================================
// ใบเสร็จ
// ============================================================
const PAY_METHOD_TH = { promptpay: "พร้อมเพย์", card: "บัตรเครดิต/เดบิต", cash: "เงินสด" };
const PAY_KIND_TH = { deposit: "ค่ามัดจำ", balance: "ยอดคงเหลือ" };

function printReceipt(r) {
  const row = (label, value) =>
    value ? `<tr><th>${esc(label)}</th><td>${esc(String(value))}</td></tr>` : "";

  const voided =
    r.status === "refunded"
      ? `<div class="void">คืนเงินแล้ว — ใบเสร็จนี้เป็นโมฆะ</div>`
      : "";

  const html = `<!DOCTYPE html><html lang="th"><head><meta charset="UTF-8">
<title>ใบเสร็จ ${esc(r.receipt_no)}</title>
<style>
  @page { size: A5; margin: 14mm; }
  * { box-sizing: border-box; }
  body { font-family: 'IBM Plex Sans Thai','Tahoma',sans-serif; color:#14202f;
         font-size:13px; line-height:1.75; margin:0; }
  .head { display:flex; justify-content:space-between; align-items:flex-start;
          border-bottom:2px solid #0f294b; padding-bottom:10px; }
  .brand { font-size:19px; font-weight:700; color:#0f294b; letter-spacing:-.02em; }
  .sub { font-size:11px; color:#667; }
  .no { text-align:right; }
  .no b { font-size:15px; letter-spacing:.03em; }
  .shop { margin-top:14px; padding:10px 12px; background:#f4f7fb; border-radius:6px; }
  .shop b { display:block; font-size:14px; color:#0f294b; }
  table { width:100%; border-collapse:collapse; margin-top:14px; }
  th,td { text-align:left; padding:7px 0; vertical-align:top; border-bottom:1px dashed #d6dee9; }
  th { width:36%; font-weight:500; color:#667; }
  td { font-weight:500; }
  .total { display:flex; justify-content:space-between; align-items:baseline;
           margin-top:16px; padding-top:12px; border-top:2px solid #0f294b; }
  .total .big { font-size:22px; font-weight:700; color:#0f294b; }
  .void { margin-top:14px; padding:8px 12px; text-align:center; font-weight:600;
          color:#a8121f; border:2px dashed #a8121f; border-radius:6px; }
  .note { margin-top:16px; padding:9px 12px; background:#eef4fd;
          border-left:3px solid #1a63d8; font-size:11.5px; }
  footer { margin-top:20px; text-align:center; font-size:10.5px; color:#8894a6; }
</style></head><body>
  <div class="head">
    <div>
      <div class="brand">Bookvice</div>
      <div class="sub">ใบเสร็จรับเงิน / RECEIPT</div>
    </div>
    <div class="no">
      <div class="sub">เลขที่</div>
      <b>${esc(r.receipt_no)}</b>
      <div class="sub">${new Date(r.issued_at).toLocaleString("th-TH")}</div>
    </div>
  </div>

  <div class="shop">
    <b>${esc(r.shop_name)}</b>
    ${r.shop_address ? `<div class="sub">${esc(r.shop_address)}</div>` : ""}
    ${r.shop_phone ? `<div class="sub">โทร ${esc(r.shop_phone)}</div>` : ""}
  </div>

  <table>
    ${row("ผู้ชำระเงิน", r.customer_name)}
    ${row("รหัสการจอง", r.booking_code)}
    ${row("บริการ", r.service_name)}
    ${row("วันที่ใช้บริการ", `${thaiDate(r.booking_date)} ${shortTime(r.booking_time)} น.`)}
    ${row("ประเภทการชำระ", PAY_KIND_TH[r.kind] || r.kind)}
    ${row("ช่องทาง", PAY_METHOD_TH[r.method] || r.method)}
    ${row("เลขอ้างอิง", r.reference)}
    ${row("ค่าบริการทั้งหมด", `฿${baht(r.total_price)}`)}
  </table>

  <div class="total">
    <span>ยอดที่ชำระ</span>
    <span class="big">฿${baht(r.amount)}</span>
  </div>
  ${voided}

  <div class="note">
    เอกสารนี้ออกโดยระบบอัตโนมัติ ไม่ต้องมีลายเซ็น ·
    เก็บไว้เป็นหลักฐานในการเข้ารับบริการ
  </div>

  <footer>พิมพ์เมื่อ ${new Date().toLocaleString("th-TH")} · Bookvice</footer>
</body></html>`;

  openPrintWindow(html, 620, 800);
}
