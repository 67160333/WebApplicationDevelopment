/* ============================================================
   GlowGo — Mock Data Layer
   ในโปรเจกต์จริงข้อมูลนี้จะมาจาก REST API / ฐานข้อมูล
   ที่นี่ใช้เป็น mock data เพื่อให้แอปรันได้จริงแบบ static
   ============================================================ */

const CATEGORIES = [
  { id: "nails",   name: "ทำเล็บ",        icon: "💅" },
  { id: "spa",     name: "สปา & นวด",     icon: "💆" },
  { id: "hair",    name: "ทำผม",          icon: "💇" },
  { id: "skin",    name: "ดูแลผิว/ตรวจผิว", icon: "🧖" },
  { id: "lash",    name: "ต่อขนตา/คิ้ว",   icon: "👁️" },
  { id: "clinic",  name: "คลินิกความงาม",  icon: "🏥" },
];

const ZONES = ["สยาม", "อารีย์", "ลาดพร้าว", "ทองหล่อ", "บางนา", "รังสิต"];

const SHOPS = [
  {
    id: "s1",
    name: "Bloom Nail Studio",
    category: "nails",
    zone: "สยาม",
    rating: 4.8,
    reviewCount: 312,
    priceFrom: 350,
    certified: true,
    image: "💅",
    about: "ร้านทำเล็บสไตล์มินิมอล อุปกรณ์ผ่านการฆ่าเชื้อทุกครั้ง มีช่างมืออาชีพ 6 คน",
    services: [
      { name: "ทาสีเจล", price: 350, duration: 60 },
      { name: "ต่อเล็บ PVC", price: 690, duration: 120 },
      { name: "เพนต์ลาย", price: 250, duration: 45 },
    ],
    reviews: [
      { user: "มายด์", rating: 5, text: "สีสวยมาก อยู่ทน ช่างใจดี", verified: true },
      { user: "ฟ้า", rating: 5, text: "ร้านสะอาด จองง่าย ไม่ต้องรอ", verified: true },
      { user: "นุ่น", rating: 4, text: "ดีค่ะ แต่คิวค่อนข้างแน่น", verified: true },
    ],
  },
  {
    id: "s2",
    name: "Serene Spa & Massage",
    category: "spa",
    zone: "ทองหล่อ",
    rating: 4.9,
    reviewCount: 528,
    priceFrom: 800,
    certified: true,
    image: "💆",
    about: "สปาหรูใจกลางทองหล่อ นวดแผนไทย & อโรมา บรรยากาศผ่อนคลาย",
    services: [
      { name: "นวดไทย 60 นาที", price: 800, duration: 60 },
      { name: "นวดอโรมา 90 นาที", price: 1400, duration: 90 },
      { name: "ขัดผิว + นวด", price: 1900, duration: 120 },
    ],
    reviews: [
      { user: "แพร", rating: 5, text: "ผ่อนคลายสุด ๆ พนักงานมืออาชีพ", verified: true },
      { user: "โบว์", rating: 5, text: "ราคาคุ้ม บรรยากาศดีมาก", verified: true },
    ],
  },
  {
    id: "s3",
    name: "Glow Skin Clinic",
    category: "skin",
    zone: "อารีย์",
    rating: 4.7,
    reviewCount: 190,
    priceFrom: 500,
    certified: true,
    image: "🧖",
    about: "คลินิกดูแลผิวโดยแพทย์ผิวหนัง มีบริการตรวจวิเคราะห์ผิวฟรีก่อนทำ",
    services: [
      { name: "ตรวจวิเคราะห์ผิว", price: 500, duration: 30 },
      { name: "ทรีตเมนต์หน้าใส", price: 1200, duration: 60 },
      { name: "เลเซอร์รอยสิว", price: 2500, duration: 45 },
    ],
    reviews: [
      { user: "มิ้น", rating: 5, text: "หมอให้คำแนะนำดี ผิวดีขึ้นจริง", verified: true },
      { user: "เจน", rating: 4, text: "ผลลัพธ์ดี แต่ต้องจองล่วงหน้า", verified: true },
    ],
  },
  {
    id: "s4",
    name: "The Hair Bar",
    category: "hair",
    zone: "ลาดพร้าว",
    rating: 4.6,
    reviewCount: 245,
    priceFrom: 450,
    certified: false,
    image: "💇",
    about: "ร้านทำผมทันสมัย ทำสี ดัด ยืด โดยช่างที่ผ่านการอบรม",
    services: [
      { name: "ตัด + สระไดร์", price: 450, duration: 60 },
      { name: "ทำสีผม", price: 1800, duration: 150 },
      { name: "ยืดผม", price: 2200, duration: 180 },
    ],
    reviews: [
      { user: "ปาล์ม", rating: 5, text: "ช่างเก่ง ตัดตรงปก", verified: true },
      { user: "อาย", rating: 4, text: "ทำสีสวย แต่ใช้เวลานาน", verified: false },
    ],
  },
  {
    id: "s5",
    name: "Lash Lounge",
    category: "lash",
    zone: "บางนา",
    rating: 4.8,
    reviewCount: 156,
    priceFrom: 590,
    certified: true,
    image: "👁️",
    about: "ต่อขนตา สักคิ้ว โดยผู้เชี่ยวชาญ ใช้ผลิตภัณฑ์นำเข้า ปลอดภัย",
    services: [
      { name: "ต่อขนตาแบบธรรมชาติ", price: 590, duration: 90 },
      { name: "ต่อขนตา Volume", price: 990, duration: 120 },
      { name: "สักคิ้ว 3 มิติ", price: 3500, duration: 120 },
    ],
    reviews: [
      { user: "ก้อย", rating: 5, text: "ขนตาเป็นธรรมชาติมาก ติดทน", verified: true },
    ],
  },
  {
    id: "s6",
    name: "Pure Beauty Clinic",
    category: "clinic",
    zone: "รังสิต",
    rating: 4.5,
    reviewCount: 98,
    priceFrom: 1000,
    certified: true,
    image: "🏥",
    about: "คลินิกความงามครบวงจร ฉีดวิตามินผิว ดูแลรูปหน้า โดยแพทย์",
    services: [
      { name: "ฉีดวิตามินผิว", price: 1500, duration: 30 },
      { name: "ทรีตเมนต์ยกกระชับ", price: 3000, duration: 60 },
    ],
    reviews: [
      { user: "ตาล", rating: 5, text: "แพทย์ดูแลดี ปลอดภัย", verified: true },
      { user: "พลอย", rating: 4, text: "บริการดี ราคาสมเหตุผล", verified: true },
    ],
  },
];

// เวลาที่ว่างให้จอง (mock) ต่อร้านต่อวัน
const TIME_SLOTS = [
  "10:00", "11:00", "12:00", "13:00",
  "14:00", "15:00", "16:00", "17:00", "18:00",
];

// helper: ดึงร้านตาม id
function getShopById(id) {
  return SHOPS.find((s) => s.id === id);
}

// helper: ดึงชื่อหมวดหมู่
function getCategoryName(id) {
  const c = CATEGORIES.find((c) => c.id === id);
  return c ? c.name : id;
}
