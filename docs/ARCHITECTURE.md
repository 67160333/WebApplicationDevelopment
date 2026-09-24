# สถาปัตยกรรมระบบ Bookvice

> เอกสารนี้อธิบายสถาปัตยกรรมที่ระบบ **เป็นอยู่จริง** ก่อน แล้วจึงเสนอแนวทาง
> แยกเป็น microservices พร้อมเหตุผลว่าทำไมตอนนี้ยังไม่ได้แยก

---

## 1. สรุปใน 30 วินาที

Bookvice เป็น **modular monolith** — แอปพลิเคชันเดียวที่แบ่งโค้ดภายในเป็นโมดูล
ตามขอบเขตธุรกิจไว้ชัดเจน รันด้วย Docker Compose 4 container

| ตัวเลขจากโค้ดจริง | ค่า |
|---|---|
| REST endpoint | 86 |
| ตารางฐานข้อมูล | 19 |
| โมดูล (router) | 12 |
| หน้าเว็บ | 20 |
| ชุดทดสอบอัตโนมัติ | 143 ข้อ (API 121 · ตรรกะหน้าเว็บ 22) |

---

## 2. สถาปัตยกรรมที่ใช้งานจริง

```mermaid
graph TB
    subgraph client["เครื่องผู้ใช้"]
        B["เบราว์เซอร์<br/>HTML · CSS · JavaScript"]
    end

    subgraph docker["Docker Compose network: bookvice-net"]
        W["<b>web</b><br/>nginx:alpine<br/>เสิร์ฟไฟล์หน้าเว็บ<br/>พอร์ต 3000"]
        A["<b>api</b><br/>FastAPI + Uvicorn<br/>86 endpoint<br/>พอร์ต 8000"]
        D[("<b>db</b><br/>PostgreSQL 16<br/>19 ตาราง")]
        P["<b>pgadmin</b><br/>เครื่องมือดูฐานข้อมูล<br/>พอร์ต 5050"]
    end

    subgraph ext["บริการภายนอก"]
        OSM["OpenStreetMap<br/>ภาพแผนที่"]
        OVP["Overpass API<br/>ค้นร้านรอบ ๆ"]
        RSD["Resend<br/>ส่งอีเมลรีเซ็ตรหัสผ่าน"]
        GF["Google Fonts"]
    end

    B -->|"HTTP"| W
    B -->|"REST + JWT"| A
    A -->|"SQLAlchemy"| D
    P -.->|"ดูข้อมูล"| D
    B -.-> OSM
    B -.-> OVP
    B -.-> GF
    A -.-> RSD
```

**จุดที่ควรสังเกต** — เบราว์เซอร์เรียก Overpass และ OpenStreetMap **โดยตรง**
ไม่ผ่านเซิร์ฟเวอร์เรา เพราะโฮสต์ที่ใช้เป็นแพ็กเกจฟรีที่ตื่นช้าอยู่แล้ว
การให้มันเป็นตัวกลางอีกทอดจะทำให้ช้าลงโดยไม่ได้อะไรกลับมา

---

## 3. โครงภายในของ api container

```mermaid
graph LR
    subgraph api["FastAPI application"]
        direction TB
        MW["CORS middleware"]
        SEC["security.py<br/>JWT · bcrypt · require_roles"]

        subgraph routers["routers/ — 12 โมดูล"]
            R1["auth · 6"]
            R2["users · 6"]
            R3["shops · 22"]
            R4["bookings · 16"]
            R5["payments · 5"]
            R6["matches · 12"]
            R7["images · 5"]
            R8["notifications · 4"]
            R9["staff · 5"]
            R10["watches · 3"]
            R11["gaps · 2"]
            R12["aliases"]
        end

        SCH["schemas.py<br/>Pydantic — ตรวจข้อมูลเข้า/ออก"]
        MOD["models.py<br/>SQLAlchemy — 19 ตาราง"]
    end

    MW --> SEC --> routers --> SCH --> MOD
```

`aliases.py` ไม่มี endpoint เป็นของตัวเอง — เป็นเส้นทางลัดที่ผูกกลับไปฟังก์ชันเดิม
เพื่อให้ URL ตรงกับรูปแบบที่โจทย์กำหนด โดยไม่ต้องเขียนตรรกะซ้ำสองชุด

---

## 4. ลำดับการทำงาน — ตัวอย่างการจองหนึ่งครั้ง

```mermaid
sequenceDiagram
    participant U as ผู้ใช้
    participant W as nginx
    participant A as FastAPI
    participant D as PostgreSQL

    U->>W: เปิด shop.html
    W-->>U: ไฟล์หน้าเว็บ
    U->>A: GET /api/shops/1
    A->>D: SELECT ร้าน บริการ ช่าง
    D-->>A: ข้อมูลร้าน
    A-->>U: JSON

    U->>A: GET /api/services/1/availability?date=...
    A->>D: อ่านคิวที่ถูกจองแล้ว + ตารางงานช่าง
    A->>A: คำนวณช่องเวลาว่าง<br/>หักวันหยุดประจำ · เพดาน 90 วัน
    A-->>U: รายการช่องเวลา

    U->>A: POST /api/bookings (Bearer token)
    A->>A: ตรวจ JWT · ตรวจเกณฑ์อายุ · ตรวจวันหยุด
    A->>D: INSERT booking (สถานะ รอชำระ)
    A-->>U: เลขที่การจอง

    Note over U,D: ช่องเวลายังไม่ถูกล็อก จนกว่าจะชำระมัดจำ

    U->>A: POST /api/payments (มัดจำ 20%)
    A->>D: ตรวจซ้ำว่ายังว่าง แล้ว INSERT payment
    A->>D: UPDATE booking → ยืนยันแล้ว
    A-->>U: ใบเสร็จ
```

---

## 5. ทำไมตอนนี้ยังเป็น monolith

การแยก microservices มีต้นทุนที่ต้องจ่ายก่อนได้ประโยชน์

| ต้นทุน | ผลกับโปรเจกต์นี้ |
|---|---|
| ธุรกรรมข้ามฐานข้อมูล | การจอง + การชำระเงินต้องอยู่ในธุรกรรมเดียวกัน ถ้าแยกฐานข้อมูลต้องทำ Saga pattern เอง |
| เครือข่ายระหว่าง service | เรียกในหน่วยความจำใช้เวลาระดับไมโครวินาที ข้ามเครือข่ายเป็นมิลลิวินาที และล้มเหลวได้ |
| จำนวน container | จาก 4 เป็น 10+ บนโฮสต์ฟรีที่ให้ container เดียว |
| การดูแล | ต้องมี service discovery · API gateway · distributed tracing |

**เกณฑ์ที่ใช้ตัดสิน** — ระบบนี้มีผู้ใช้หลักสิบ ทีมพัฒนาคนเดียว และ deploy พร้อมกันทั้งก้อน
ทั้งสามข้อคือเงื่อนไขที่ monolith เหมาะกว่า microservices

> แนวคิดนี้ตรงกับที่ Netflix อธิบายไว้ — Netflix แยก microservices เพราะมีผู้ใช้
> ระดับร้อยล้านและทีมหลายร้อยทีมที่ต้อง deploy อิสระจากกัน ไม่ใช่เพราะ microservices
> ดีกว่าโดยตัวมันเอง

**แต่โค้ดถูกวางไว้ให้แยกได้** — แต่ละโมดูลใน `routers/` มีขอบเขตข้อมูลของตัวเอง
และไม่เรียกฟังก์ชันข้ามโมดูลกันตรง ๆ ทำให้แยกออกมาได้โดยไม่ต้องรื้อ

---

## 6. แผนแยกเป็น microservices (ถ้าระบบโตขึ้น)

```mermaid
graph TB
    C["เบราว์เซอร์"]
    GW["<b>API Gateway</b><br/>ตรวจ JWT · จัดเส้นทาง · จำกัดอัตราเรียก"]

    subgraph svc["Services"]
        S1["<b>Identity Service</b><br/>สมัคร · เข้าสู่ระบบ · โปรไฟล์<br/>auth · users"]
        S2["<b>Catalog Service</b><br/>ร้าน · บริการ · ช่าง · รูป<br/>shops · staff · images"]
        S3["<b>Booking Service</b><br/>ช่องเวลาว่าง · จอง · เลื่อนนัด<br/>bookings · watches · gaps"]
        S4["<b>Payment Service</b><br/>มัดจำ · คืนเงิน · ใบเสร็จ<br/>payments"]
        S5["<b>Community Service</b><br/>ก๊วน · โพสต์หาคน<br/>matches"]
        S6["<b>Notification Service</b><br/>แจ้งเตือน · อีเมล<br/>notifications"]
    end

    subgraph data["ฐานข้อมูลแยกตาม service"]
        D1[("identity_db")]
        D2[("catalog_db")]
        D3[("booking_db")]
        D4[("payment_db")]
        D5[("community_db")]
    end

    MQ["<b>Message Broker</b><br/>RabbitMQ / Redis Streams"]

    C --> GW
    GW --> S1 & S2 & S3 & S4 & S5
    S1 --> D1
    S2 --> D2
    S3 --> D3
    S4 --> D4
    S5 --> D5

    S3 -.->|"BookingCreated"| MQ
    S4 -.->|"PaymentCompleted"| MQ
    S5 -.->|"MatchJoined"| MQ
    MQ -.-> S6
    MQ -.->|"PaymentCompleted<br/>→ ล็อกช่องเวลา"| S3
```

### ขอบเขตของแต่ละ service มาจากไหน

แบ่งตาม **สิ่งที่เปลี่ยนแปลงด้วยเหตุผลเดียวกัน** ไม่ใช่แบ่งตามตาราง

| Service | ตารางที่เป็นเจ้าของ | เหตุผลที่แยกเป็นก้อนนี้ |
|---|---|---|
| Identity | users · token_blacklist · password_reset_tokens · app_secrets | ทุก service ต้องใช้ แต่ไม่มี service ไหนแก้ |
| Catalog | shops · services · staff · categories · shop_images · shop_closures · favorites | อ่านบ่อยมาก เขียนน้อย เหมาะกับการทำแคชแยก |
| Booking | bookings · slot_watches | ตรรกะซับซ้อนที่สุดและเปลี่ยนบ่อยที่สุด |
| Payment | payments | ต้องแยกเพื่อความปลอดภัยและการตรวจสอบย้อนหลัง |
| Community | match_requests · match_joins · match_interests | ฟีเจอร์เสริม ล่มแล้วการจองยังทำงานได้ |
| Notification | notifications | ไม่มีใครเรียกตรง ๆ รับ event อย่างเดียว |

### ปัญหาที่ต้องแก้ตอนแยก

1. **การจองกับการชำระเงินต้องสอดคล้องกัน**
   ปัจจุบันอยู่ในธุรกรรมเดียวกันของ PostgreSQL เมื่อแยกแล้วต้องใช้ Saga —
   Payment Service ยิง event `PaymentCompleted` แล้ว Booking Service ค่อยล็อกช่องเวลา
   ถ้าล็อกไม่สำเร็จต้องยิง `RefundRequested` กลับ

2. **หน้าจองต้องใช้ข้อมูลจากสาม service**
   ร้าน (Catalog) + ช่องเวลา (Booking) + สถานะชำระเงิน (Payment)
   แก้ด้วย API Gateway ที่รวมผลลัพธ์ หรือทำ Backend-for-Frontend

3. **ข้อมูลที่ใช้ร่วมกัน**
   Booking Service ต้องรู้ชื่อร้าน — ไม่ควรเรียก Catalog ทุกครั้ง
   ใช้วิธีคัดลอกเฉพาะฟิลด์ที่ต้องใช้มาเก็บไว้ แล้วอัปเดตเมื่อได้รับ event

---

## 7. ข้อมูลอ้างอิงประกอบ

- Netflix — [10 things you can learn from Netflix's architecture](https://dev.to/somadevtoo/10-things-you-can-learn-from-netflixs-architecture-1bnn)
- Martin Fowler — [MonolithFirst](https://martinfowler.com/bliki/MonolithFirst.html)
