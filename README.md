# HairGraph Recommendation System

ระบบแนะนำทรงผมด้วย Graph Database สำหรับรายวิชา Graph Database / Advanced Database
พัฒนาด้วย **Streamlit + Neo4j Aura + Cypher** และ deploy ผ่าน **GitHub → Streamlit Community Cloud**

ดัดแปลงจากโปรเจ็คตัวอย่าง GraphBook ของอาจารย์ โดยเปลี่ยนข้อมูลเป็นชุดคน–ทรงผม
ชุดเดียวกับ notebook `033_HairStyle.ipynb`

## 1. แนวคิดของระบบ

ระบบใช้ Property Graph ดังนี้

```text
(Person {person_id, name})
(Style {style_id, name, image})                    image = ชื่อไฟล์ในโฟลเดอร์ images/
(Person)-[:LIKES {score}]->(Style)                 คนชอบทรงผม พร้อมคะแนน 1-10
(Person)-[:RECOMMENDED {score, rank}]->(Style)     ผลแนะนำที่บันทึกลง Aura
```

ข้อมูลตั้งต้น: คน 15 คน (P01–P15), ทรงผม 12 ทรง (H01–H12), ความชอบ 38 เส้น

จุดเด่นคือคำแนะนำอธิบายได้ (Explainable Recommendation) ว่าทรงผมถูกแนะนำเพราะ
1. คนที่ชอบทรงเดียวกับผู้ใช้ ชอบทรงนี้ด้วย
2. ทรงนี้เชื่อมมาจากทรงที่ผู้ใช้ชอบกี่ทรง
3. ทรงนี้มีคนชอบกี่คน
4. คะแนนความชอบเฉลี่ยดีแค่ไหน

สูตรคะแนน Hybrid:

```text
score = similar_people*3
      + shared_styles*2
      + popularity*0.20
      + avg_score*0.25
```

`avg_score` เต็ม 10 จึงใช้น้ำหนัก 0.25 (เทียบเท่า rating เต็ม 5 × 0.50 ของงานต้นแบบ)
สูตรนี้เป็น heuristic เพื่อการเรียนการสอน ไม่ใช่โมเดล ML ที่ผ่านการ optimize

## 2. โครงสร้างไฟล์

```text
tee/
├── app.py                  หน้าเว็บ Streamlit
├── neo4j_service.py        คำสั่ง Cypher ทั้งหมด + ข้อมูลตั้งต้น
├── requirements.txt
├── .gitignore
├── images/                 รูปทรงผม (H01.png ... H12.png) ชื่อไฟล์ = รหัสทรง
├── .streamlit/
│   └── secrets.toml.example
├── cypher/
│   ├── schema.cypher
│   ├── recommendation.cypher
│   └── save_recommended.cypher
└── docs/
    └── PROJECT_GUIDE_TH.md
```

## 3. เพิ่ม / ลบ / แก้ไขข้อมูล (CRUD)

เมนู **Manage Data** มี 3 แท็บ

| แท็บ | เพิ่ม | แก้ไข | ลบ |
|---|---|---|---|
| 👤 คน | รหัส + ชื่อ + เลือกทรงที่ชอบได้หลายทรงพร้อมคะแนน | ชื่อ + เพิ่ม/เอาทรงที่ชอบออก/แก้คะแนน | `DETACH DELETE` ลบความชอบของคนนั้นด้วย |
| 💇 ทรงผม | รหัส + ชื่อ + อัปโหลดรูป | ชื่อ + เปลี่ยนรูป | ลบ node + เลือกลบไฟล์รูปได้ |
| ❤️ ความชอบ | เลือกคน + ทรง + คะแนน | บันทึกคู่เดิมซ้ำ = แก้คะแนน | ลบเส้น `LIKES` |

รหัสเป็น primary key จึงไม่ให้แก้ ถ้าต้องการเปลี่ยนรหัสให้ลบแล้วเพิ่มใหม่
การลบต้องติ๊กยืนยันก่อนทุกครั้ง

## 4. รูปภาพทรงผม

- ไฟล์รูปเก็บในโฟลเดอร์ `images/` ใน git ส่วน Neo4j เก็บแค่ชื่อไฟล์ใน property `image`
- ตั้งชื่อไฟล์ตามรหัสทรง เช่น `H05.jpg` (รองรับ png, jpg, jpeg, webp)
- รูปตั้งต้น H01–H12 เป็นภาพประกอบที่วาดขึ้นใหม่ ใช้ได้เลย หรือเปลี่ยนเป็นรูปถ่ายจริงได้
  (ควรใช้รูปที่ถ่ายเองหรือรูปที่อนุญาตให้ใช้ฟรี)
- วิธีเปลี่ยนรูปแบบถาวร: วางไฟล์ชื่อเดิมทับใน `images/` แล้ว `git add images` → commit → push
- อัปโหลดผ่านหน้าเว็บ: ในเครื่องจะบันทึกลง `images/` ทันที แต่บน Streamlit Cloud
  ไฟล์จะหายเมื่อแอปรีสตาร์ท ให้กดปุ่มดาวน์โหลดไฟล์ที่อัปโหลด แล้วนำไปใส่ `images/` และ push ขึ้น GitHub

## 5. Neo4j Aura

1. ใช้ AuraDB instance เดิมที่ใช้กับ notebook ได้เลย
2. เก็บค่า Connection URI, username และ password
3. อย่านำ password ไปใส่ในไฟล์ที่ commit ขึ้น GitHub

## 6. รันในเครื่อง

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
```

คัดลอกไฟล์ตัวอย่าง secrets แล้วใส่รหัสผ่านจริง

```bash
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
streamlit run app.py
```

## 7. ครั้งแรกที่เปิดระบบ

1. เข้าเมนู **Admin / Setup**
2. กด **สร้าง Constraint + ข้อมูลตั้งต้น** (ใช้ `MERGE` กดซ้ำได้ ถ้ามีข้อมูลจาก notebook อยู่แล้วก็ไม่ซ้ำ)
3. กด **บันทึกผลแนะนำลง Aura** ถ้าต้องการเห็นเส้น `RECOMMENDED` ใน Aura
4. ทดลอง Dashboard, Recommendations, Style Search, Like / Rate, Manage Data และ Graph Explorer

## 8. Deploy GitHub → Streamlit Community Cloud

1. push ไฟล์ทั้งหมดขึ้น GitHub **ยกเว้น `.streamlit/secrets.toml`**
2. เข้า Streamlit Community Cloud แล้วเลือก Create app
3. เลือก repository, branch `main` และ entrypoint = `app.py`
4. ใน Advanced settings → Secrets ใส่

```toml
[neo4j]
uri = "neo4j+s://YOUR_INSTANCE.databases.neo4j.io"
username = "YOUR_INSTANCE"
password = "YOUR_PASSWORD"
database = "YOUR_INSTANCE"
```

5. Deploy

## 9. ประเด็น Graph Database ที่ได้ฝึก

- Node, Label, Property
- Relationship, Direction และ property บนเส้น (`score`)
- Constraint และ Unique Key
- CRUD: `CREATE`/`MERGE ... ON CREATE`, `SET`, `DETACH DELETE`
- `MATCH`, `MERGE`, `OPTIONAL MATCH`, `WITH`, `UNWIND`, `EXISTS { }`, `COUNT { }`
- Graph traversal: คน → ทรงผม ← คนอื่น → ทรงผมใหม่
- Aggregation เช่น `count`, `avg`, `collect`
- Recommendation จาก topology ของกราฟ
- Parameterized Cypher
- Python Driver และ connection pooling
- Streamlit UI, Secrets และ cloud deployment

## 10. สิ่งที่เปลี่ยนจากโปรเจ็คต้นแบบ (GraphBook)

| GraphBook (อาจารย์) | HairGraph (ของฉัน) |
|---|---|
| `Student` | `Person` |
| `Book` | `Style` |
| `BORROWED {borrow_date, rating}` | `LIKES {score}` |
| เพื่อนที่เคยยืม (`FRIEND_OF`) | คนที่ชอบทรงเดียวกัน (traverse ผ่าน `LIKES`) |
| หมวดตรงความสนใจ (`INTERESTED_IN`) | ทรงที่ชอบที่เชื่อมมาถึง (`shared_styles`) |
| Book Search + Category | Style Search |
| Borrow / Rate | Like / Rate |
| - | Manage Data: เพิ่ม / แก้ไข / ลบ คน, ทรงผม, ความชอบ |
| - | รูปภาพทรงผมเก็บใน git (`images/`) |
| - | บันทึกผลแนะนำเป็นเส้น `RECOMMENDED` ลง Aura |
| - | กราฟทรงผมยอดนิยมใน Dashboard |
