"""ชั้นติดต่อฐานข้อมูล (Database access layer)

ไฟล์นี้รวมทุกคำสั่ง Cypher ของระบบแนะนำทรงผมไว้ที่เดียว
app.py (หน้าเว็บ) จะเรียกใช้ฟังก์ชันจากไฟล์นี้ ไม่เขียน Cypher เอง

Graph model:
    (:Person)-[:LIKES {score}]->(:Style)          คนชอบทรงผม พร้อมคะแนน 1-10
    (:Person)-[:RECOMMENDED {score, rank}]->(:Style)  ผลแนะนำที่บันทึกลง Aura (สร้างจากหน้า Admin)
"""

from __future__ import annotations

from typing import Any

import streamlit as st
from neo4j import GraphDatabase, RoutingControl


# ---------------------------------------------------------------------------
# การเชื่อมต่อ
# ---------------------------------------------------------------------------

def _config() -> tuple[str, str, str, str | None]:
    """อ่านค่าเชื่อมต่อจาก Streamlit Secrets (ไม่เขียนรหัสผ่านไว้ในโค้ด)"""
    cfg = st.secrets["neo4j"]
    return (
        cfg["uri"],
        cfg["username"],
        cfg["password"],
        # ถ้าไม่ได้ใส่ database ใน secrets ให้เป็น None = ใช้ home database ของบัญชี
        cfg.get("database") or None,
    )


@st.cache_resource(show_spinner=False)
def get_driver():
    """สร้าง Driver ตัวเดียวแล้ว cache ไว้ ทุกหน้าใช้ร่วมกัน ไม่ต้องเชื่อมต่อใหม่ทุกครั้ง"""
    uri, username, password, _ = _config()
    driver = GraphDatabase.driver(uri, auth=(username, password))
    driver.verify_connectivity()
    return driver


def query(cypher: str, parameters: dict[str, Any] | None = None, *, write: bool = False) -> list[dict[str, Any]]:
    """รัน Cypher แบบส่ง parameter แล้วคืนผลเป็น list ของ dict

    write=True  ใช้กับคำสั่งที่แก้ข้อมูล (MERGE, SET, DELETE)
    write=False ใช้กับคำสั่งอ่านอย่างเดียว (MATCH ... RETURN)
    """
    _, _, _, database = _config()
    records, _, _ = get_driver().execute_query(
        cypher,
        parameters_=parameters or {},
        database_=database,
        routing_=RoutingControl.WRITE if write else RoutingControl.READ,
    )
    return [record.data() for record in records]


def ping() -> bool:
    """ทดสอบว่าเชื่อมต่อฐานข้อมูลได้"""
    rows = query("RETURN 1 AS ok")
    return bool(rows and rows[0]["ok"] == 1)


# ---------------------------------------------------------------------------
# Schema และข้อมูลตั้งต้น
# ---------------------------------------------------------------------------

def create_schema() -> None:
    """สร้าง constraint ให้รหัสคนและรหัสทรงผมห้ามซ้ำ (IF NOT EXISTS = รันซ้ำได้)"""
    statements = [
        "CREATE CONSTRAINT person_id_unique IF NOT EXISTS FOR (p:Person) REQUIRE p.person_id IS UNIQUE",
        "CREATE CONSTRAINT style_id_unique IF NOT EXISTS FOR (h:Style) REQUIRE h.style_id IS UNIQUE",
    ]
    for stmt in statements:
        query(stmt, write=True)


# ข้อมูลชุดเดียวกับใน notebook 033_HairStyle (P01-P15, H01-H12)
PEOPLE = [
    {"person_id": "P01", "name": "ณรงค์ศักดิ์"},
    {"person_id": "P02", "name": "สมชาย"},
    {"person_id": "P03", "name": "สมหญิง"},
    {"person_id": "P04", "name": "ปรีชา"},
    {"person_id": "P05", "name": "กมลชนก"},
    {"person_id": "P06", "name": "ธนากร"},
    {"person_id": "P07", "name": "ศิริพร"},
    {"person_id": "P08", "name": "วิชัย"},
    {"person_id": "P09", "name": "นภัสสร"},
    {"person_id": "P10", "name": "อนุชา"},
    {"person_id": "P11", "name": "พิมพ์ชนก"},
    {"person_id": "P12", "name": "ชัยวัฒน์"},
    {"person_id": "P13", "name": "ญาดา"},
    {"person_id": "P14", "name": "ภาณุพงศ์"},
    {"person_id": "P15", "name": "อริสา"},
]

STYLES = [
    {"style_id": "H01", "name": "ซอยสั้นเลเยอร์"},
    {"style_id": "H02", "name": "บ๊อบสั้น"},
    {"style_id": "H03", "name": "บ๊อบยาว (Lob)"},
    {"style_id": "H04", "name": "ยาวตรงแสกกลาง"},
    {"style_id": "H05", "name": "ยาวดัดลอน"},
    {"style_id": "H06", "name": "หน้าม้าซีทรู"},
    {"style_id": "H07", "name": "รองทรงสูง"},
    {"style_id": "H08", "name": "เกรียนสั้น"},
    {"style_id": "H09", "name": "วูล์ฟคัท"},
    {"style_id": "H10", "name": "มัดจุกสูง"},
    {"style_id": "H11", "name": "ดัดโครงสร้าง"},
    {"style_id": "H12", "name": "ซอยสั้นแสกกลาง"},
]

# [รหัสคน, รหัสทรงผม, คะแนนความชอบ]
LIKES = [
    ["P01", "H02", 8], ["P01", "H05", 9], ["P01", "H11", 8],
    ["P02", "H04", 9], ["P02", "H01", 7],
    ["P03", "H09", 9], ["P03", "H03", 7],
    ["P04", "H02", 8], ["P04", "H06", 9],
    ["P05", "H03", 8], ["P05", "H05", 7], ["P05", "H10", 7],
    ["P06", "H09", 9], ["P06", "H12", 8],
    ["P07", "H02", 9], ["P07", "H06", 8],
    ["P08", "H05", 8], ["P08", "H03", 7], ["P08", "H07", 9], ["P08", "H02", 8],
    ["P09", "H10", 7], ["P09", "H06", 8],
    ["P10", "H05", 9], ["P10", "H12", 8], ["P10", "H08", 7],
    ["P11", "H01", 8], ["P11", "H02", 7],
    ["P12", "H05", 9], ["P12", "H09", 8], ["P12", "H12", 7], ["P12", "H11", 8],
    ["P13", "H04", 8], ["P13", "H11", 9],
    ["P14", "H09", 8], ["P14", "H08", 7], ["P14", "H12", 8],
    ["P15", "H05", 7], ["P15", "H04", 9],
]


def seed_demo_data() -> None:
    """ใส่ข้อมูลตั้งต้นทั้งหมด ใช้ MERGE จึงกดซ้ำได้ ไม่เกิด node/เส้นซ้ำ

    ถ้าเคยรัน notebook ใส่ข้อมูลไว้ใน Aura แล้ว ฟังก์ชันนี้จะแค่อัปเดตค่าเดิม
    """
    create_schema()

    # สร้าง/อัปเดต node คน
    query(
        """
        UNWIND $rows AS row
        MERGE (p:Person {person_id: row.person_id})
        SET p.name = row.name
        """,
        {"rows": PEOPLE},
        write=True,
    )

    # สร้าง/อัปเดต node ทรงผม
    query(
        """
        UNWIND $rows AS row
        MERGE (h:Style {style_id: row.style_id})
        SET h.name = row.name
        """,
        {"rows": STYLES},
        write=True,
    )

    # สร้างเส้น LIKES (row[0] = คน, row[1] = ทรงผม, row[2] = คะแนน)
    query(
        """
        UNWIND $rows AS row
        MATCH (p:Person {person_id: row[0]}), (h:Style {style_id: row[1]})
        MERGE (p)-[r:LIKES]->(h)
        SET r.score = row[2]
        """,
        {"rows": LIKES},
        write=True,
    )


# ---------------------------------------------------------------------------
# อ่านข้อมูลสำหรับหน้าเว็บ
# ---------------------------------------------------------------------------

def get_people() -> list[dict[str, Any]]:
    """รายชื่อคนทั้งหมด ใช้ทำ dropdown เลือกผู้ใช้"""
    return query(
        "MATCH (p:Person) RETURN p.person_id AS person_id, p.name AS name ORDER BY p.person_id"
    )


def get_styles() -> list[dict[str, Any]]:
    """รายชื่อทรงผมทั้งหมด"""
    return query(
        "MATCH (h:Style) RETURN h.style_id AS style_id, h.name AS name ORDER BY h.style_id"
    )


def get_dashboard_metrics() -> dict[str, int]:
    """ตัวเลขสรุปหน้า Dashboard

    ใช้ COUNT { } แยกกันแต่ละตัว ถ้ายังไม่มีเส้นประเภทไหนเลยก็ได้ 0 (ไม่ทำให้ทั้งแถวหาย)
    """
    rows = query(
        """
        RETURN
            COUNT { (:Person) } AS people,
            COUNT { (:Style) } AS styles,
            COUNT { ()-[:LIKES]->() } AS likes,
            COUNT { ()-[:RECOMMENDED]->() } AS recommended
        """
    )
    return rows[0] if rows else {"people": 0, "styles": 0, "likes": 0, "recommended": 0}


def get_profile(person_id: str) -> dict[str, Any] | None:
    """ข้อมูลคน 1 คน พร้อมรายการทรงที่ชอบ"""
    rows = query(
        """
        MATCH (p:Person {person_id:$person_id})
        OPTIONAL MATCH (p)-[r:LIKES]->(h:Style)
        WITH p, r, h
        ORDER BY r.score DESC, h.style_id
        RETURN p.person_id AS person_id, p.name AS name,
               collect({style_id: h.style_id, style: h.name, score: r.score}) AS liked
        """,
        {"person_id": person_id},
    )
    if not rows:
        return None
    row = rows[0]
    # ถ้ายังไม่ชอบทรงไหนเลย collect จะได้ dict ที่ค่าเป็น null ให้กรองทิ้ง
    row["liked"] = [x for x in row["liked"] if x.get("style_id")]
    return row


def style_popularity() -> list[dict[str, Any]]:
    """ทรงผมแต่ละทรงมีคนชอบกี่คน และคะแนนเฉลี่ยเท่าไร (ทรงที่ไม่มีคนชอบก็แสดง)"""
    return query(
        """
        MATCH (h:Style)
        OPTIONAL MATCH (:Person)-[r:LIKES]->(h)
        RETURN h.style_id AS style_id, h.name AS style,
               count(r) AS fans,
               round(coalesce(avg(r.score), 0) * 100) / 100.0 AS avg_score
        ORDER BY fans DESC, avg_score DESC, style_id
        """
    )


# ---------------------------------------------------------------------------
# ระบบแนะนำทรงผม
# ---------------------------------------------------------------------------

RECOMMEND_CYPHER = """
// เริ่มจากคนที่ต้องการคำแนะนำ และทรงผมทุกทรงที่เขายังไม่ได้ชอบ
MATCH (u:Person {person_id:$person_id})
MATCH (h:Style)
WHERE NOT EXISTS { (u)-[:LIKES]->(h) }

// 1) Collaborative signal: คนที่ชอบทรงเดียวกับ u และชอบทรง h ด้วย
//    u -> ทรงที่ชอบ (shared) <- คนอื่น (o) -> h
OPTIONAL MATCH (u)-[:LIKES]->(shared:Style)<-[:LIKES]-(o:Person)-[:LIKES]->(h)
WHERE o <> u
WITH h,
     count(DISTINCT o) AS similar_people,
     [x IN collect(DISTINCT o.name) WHERE x IS NOT NULL][0..3] AS similar_names,
     count(DISTINCT shared) AS shared_styles,
     [x IN collect(DISTINCT shared.name) WHERE x IS NOT NULL] AS shared_names

// 2) Popularity + score signal: ทรง h มีคนชอบกี่คน คะแนนเฉลี่ยเท่าไร
OPTIONAL MATCH (:Person)-[l:LIKES]->(h)
WITH h, similar_people, similar_names, shared_styles, shared_names,
     count(l) AS popularity,
     avg(l.score) AS avg_score

// 3) รวมเป็นคะแนนเดียว (สูตรแบบเดียวกับงานอาจารย์ ปรับให้เข้ากับข้อมูลทรงผม)
WITH h, similar_people, similar_names, shared_styles, shared_names,
     popularity, coalesce(avg_score, 0.0) AS avg_score,
     (similar_people * 3.0) +
     (shared_styles * 2.0) +
     (popularity * 0.20) +
     (coalesce(avg_score, 0.0) * 0.25) AS score

// ตัดทรงที่ไม่มีหลักฐานอะไรเลย (ไม่มีใครชอบ)
WHERE similar_people > 0 OR popularity > 0

RETURN h.style_id AS style_id, h.name AS style,
       similar_people, similar_names, shared_styles, shared_names,
       popularity, round(avg_score * 100) / 100.0 AS avg_score,
       round(score * 100) / 100.0 AS score
ORDER BY score DESC, h.style_id
LIMIT $limit
"""


def recommend_styles(person_id: str, limit: int = 6) -> list[dict[str, Any]]:
    """แนะนำทรงผมแบบอธิบายเหตุผลได้ (Explainable Hybrid Recommendation)

    score = similar_people × 3     (คนที่ชอบคล้ายกันกี่คนชอบทรงนี้)
          + shared_styles × 2      (ทรงที่เราชอบกี่ทรงเชื่อมมาถึงทรงนี้)
          + popularity × 0.20      (ทั้งระบบมีคนชอบกี่คน)
          + avg_score × 0.25       (คะแนนเฉลี่ยเต็ม 10 เทียบ rating เต็ม 5 × 0.5 ของงานอาจารย์)

    คนใหม่ที่ยังไม่ชอบทรงไหนเลย จะได้คำแนะนำจากความนิยม (popularity + avg_score) แทน
    """
    return query(RECOMMEND_CYPHER, {"person_id": person_id, "limit": int(limit)})


def save_recommendations(top_n: int = 3) -> int:
    """คำนวณผลแนะนำของทุกคน แล้วบันทึกเป็นเส้น RECOMMENDED ลง Aura

    ปกติผลแนะนำคำนวณตอนเปิดหน้าเว็บเท่านั้น ไม่ได้อยู่ในฐานข้อมูล
    ฟังก์ชันนี้ทำให้เปิดดูใน Neo4j Aura ได้ (ต้องกดใหม่ทุกครั้งที่ข้อมูล LIKES เปลี่ยน)
    """
    # ลบผลแนะนำเก่าก่อน
    query("MATCH ()-[r:RECOMMENDED]->() DELETE r", write=True)

    rows = []
    for person in get_people():
        for rank, rec in enumerate(recommend_styles(person["person_id"], top_n), start=1):
            rows.append({
                "person_id": person["person_id"],
                "style_id": rec["style_id"],
                "score": rec["score"],
                "rank": rank,
            })

    if rows:
        query(
            """
            UNWIND $rows AS row
            MATCH (p:Person {person_id: row.person_id}), (h:Style {style_id: row.style_id})
            MERGE (p)-[r:RECOMMENDED]->(h)
            SET r.score = row.score, r.rank = row.rank
            """,
            {"rows": rows},
            write=True,
        )
    return len(rows)


# ---------------------------------------------------------------------------
# ค้นหา / บันทึกข้อมูล
# ---------------------------------------------------------------------------

def search_styles(keyword: str = "") -> list[dict[str, Any]]:
    """ค้นหาทรงผมจากชื่อหรือรหัส พร้อมจำนวนคนชอบและรายชื่อคนที่ชอบ"""
    return query(
        """
        MATCH (h:Style)
        WHERE $keyword = ''
           OR toLower(h.name) CONTAINS toLower($keyword)
           OR toLower(h.style_id) CONTAINS toLower($keyword)
        OPTIONAL MATCH (p:Person)-[r:LIKES]->(h)
        RETURN h.style_id AS style_id, h.name AS style,
               count(r) AS fans,
               round(coalesce(avg(r.score), 0) * 100) / 100.0 AS avg_score,
               collect(p.name) AS liked_by
        ORDER BY h.style_id
        """,
        {"keyword": keyword.strip()},
    )


def add_person(person_id: str, name: str) -> None:
    """เพิ่มคนใหม่ (ถ้ารหัสมีอยู่แล้วจะอัปเดตชื่อแทน)"""
    query(
        """
        MERGE (p:Person {person_id:$person_id})
        SET p.name = $name
        """,
        {"person_id": person_id.strip().upper(), "name": name.strip()},
        write=True,
    )


def record_like(person_id: str, style_id: str, score: int) -> None:
    """บันทึกว่าคนนี้ชอบทรงนี้ด้วยคะแนนเท่าไร (ชอบซ้ำ = อัปเดตคะแนน ไม่สร้างเส้นซ้ำ)"""
    query(
        """
        MATCH (p:Person {person_id:$person_id}), (h:Style {style_id:$style_id})
        MERGE (p)-[r:LIKES]->(h)
        SET r.score = $score
        """,
        {"person_id": person_id, "style_id": style_id, "score": int(score)},
        write=True,
    )


def remove_like(person_id: str, style_id: str) -> None:
    """ยกเลิกความชอบ (ลบเส้น LIKES)"""
    query(
        """
        MATCH (:Person {person_id:$person_id})-[r:LIKES]->(:Style {style_id:$style_id})
        DELETE r
        """,
        {"person_id": person_id, "style_id": style_id},
        write=True,
    )


def graph_neighborhood(person_id: str, limit: int = 60) -> list[dict[str, Any]]:
    """ดึงเส้นรอบตัวคนนี้ 2 ทอด ใช้วาดกราฟในหน้า Graph Explorer

    ทอดที่ 1: คนนี้ -> ทรงที่ชอบ / ทรงที่ถูกแนะนำ
    ทอดที่ 2: ทรงนั้น <- คนอื่นที่ชอบทรงเดียวกัน
    """
    return query(
        """
        MATCH (u:Person {person_id:$person_id})
        OPTIONAL MATCH p=(u)-[:LIKES|RECOMMENDED*1..2]-(x)
        WITH u, collect(p)[0..$limit] AS paths
        UNWIND paths AS p
        UNWIND relationships(p) AS r
        WITH DISTINCT startNode(r) AS s, r, endNode(r) AS t
        RETURN elementId(s) AS source_id, labels(s)[0] AS source_label,
               coalesce(s.name, s.person_id) AS source_name,
               coalesce(s.person_id, s.style_id) AS source_key,
               type(r) AS relationship, r.score AS score,
               elementId(t) AS target_id, labels(t)[0] AS target_label,
               coalesce(t.name, t.style_id) AS target_name,
               coalesce(t.person_id, t.style_id) AS target_key
        LIMIT $limit
        """,
        {"person_id": person_id, "limit": int(limit)},
    )
