"""หน้าเว็บ (Presentation layer) ของระบบแนะนำทรงผม

รันในเครื่อง:  streamlit run app.py
คำสั่ง Cypher ทั้งหมดอยู่ใน neo4j_service.py
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from neo4j_service import (
    add_person,
    get_dashboard_metrics,
    get_people,
    get_profile,
    get_styles,
    graph_neighborhood,
    ping,
    recommend_styles,
    record_like,
    remove_like,
    save_recommendations,
    search_styles,
    seed_demo_data,
    style_popularity,
)

st.set_page_config(
    page_title="HairGraph Recommender",
    page_icon="💇",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
      .block-container {padding-top: 1.3rem; padding-bottom: 2rem;}
      .hero {
        padding: 1.4rem 1.6rem; border-radius: 22px;
        background: linear-gradient(120deg, #1e1b4b 0%, #4c1d95 55%, #be185d 100%);
        color: white; margin-bottom: 1rem;
      }
      .hero h1 {margin:0; font-size:2.15rem;}
      .hero p {opacity:.88; margin:.35rem 0 0 0;}
      .style-card {
        padding: 1rem 1.1rem; border: 1px solid rgba(128,128,128,.25);
        border-radius: 16px; margin-bottom: .75rem;
      }
      .score-pill {
        display:inline-block; padding:.2rem .55rem; border-radius:999px;
        background:#6C4AB6; color:white; font-size:.8rem; font-weight:700;
      }
      .muted {opacity:.72; font-size:.9rem;}
    </style>
    """,
    unsafe_allow_html=True,
)


def require_connection() -> None:
    """ตรวจการเชื่อมต่อก่อนแสดงหน้าเว็บ ถ้าไม่ได้ให้บอกวิธีตั้งค่า Secrets"""
    try:
        if not ping():
            raise RuntimeError("Neo4j did not return a healthy response")
    except Exception as exc:
        st.error("ยังเชื่อมต่อ Neo4j Aura ไม่สำเร็จ")
        st.code(
            '[neo4j]\nuri = "neo4j+s://YOUR_INSTANCE.databases.neo4j.io"\n'
            'username = "YOUR_INSTANCE"\npassword = "YOUR_PASSWORD"\ndatabase = "YOUR_INSTANCE"',
            language="toml",
        )
        st.caption("ให้นำค่าด้านบนไปใส่ใน Streamlit Secrets และห้าม commit password ลง GitHub")
        st.exception(exc)
        st.stop()


def person_selector(key: str = "person") -> str:
    """dropdown เลือกผู้ใช้ คืนค่าเป็นรหัสคน เช่น P01"""
    people = get_people()
    if not people:
        st.info("ยังไม่มีข้อมูล กรุณาไปหน้า Admin / Setup แล้วกดสร้างข้อมูลตั้งต้น")
        st.stop()
    labels = {f"{x['person_id']} — {x['name']}": x["person_id"] for x in people}
    chosen = st.selectbox("เลือกผู้ใช้", list(labels), key=key)
    return labels[chosen]


def explain_reason(row: dict) -> str:
    """แปลงตัวเลขจาก Cypher เป็นประโยคเหตุผลที่คนอ่านเข้าใจ"""
    parts = []
    if row.get("similar_people", 0):
        names = ", ".join(row.get("similar_names") or [])
        parts.append(f"คนที่ชอบคล้ายคุณ {row['similar_people']} คนชอบทรงนี้" + (f" ({names})" if names else ""))
    if row.get("shared_styles", 0):
        styles = ", ".join(row.get("shared_names") or [])
        parts.append(f"เชื่อมมาจากทรงที่คุณชอบ {row['shared_styles']} ทรง" + (f" ({styles})" if styles else ""))
    if row.get("popularity", 0):
        parts.append(f"มีคนชอบทั้งหมด {row['popularity']} คน")
    if row.get("avg_score", 0):
        parts.append(f"คะแนนเฉลี่ย {row['avg_score']:.2f}/10")
    return " • ".join(parts) or "แนะนำจากความนิยมโดยรวม"


require_connection()

with st.sidebar:
    st.markdown("## 💇 HairGraph")
    st.caption("Neo4j Aura + Streamlit")
    page = st.radio(
        "เมนู",
        ["Dashboard", "Recommendations", "Style Search", "Like / Rate", "Graph Explorer", "Admin / Setup"],
    )
    st.divider()
    st.caption("Graph Database Project")

st.markdown(
    """
    <div class="hero">
      <h1>💇 HairGraph Recommendation System</h1>
      <p>ระบบแนะนำทรงผมด้วย Graph Database ที่อธิบายเหตุผลของคำแนะนำได้</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
if page == "Dashboard":
    st.subheader("ภาพรวมระบบ")
    m = get_dashboard_metrics()
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("People", m.get("people", 0))
    c2.metric("Hair styles", m.get("styles", 0))
    c3.metric("LIKES relationships", m.get("likes", 0))
    c4.metric("RECOMMENDED saved", m.get("recommended", 0))

    st.markdown("### ทรงผมยอดนิยม")
    pop = pd.DataFrame(style_popularity())
    if not pop.empty:
        # แสดงชื่อทรงแทนรหัสบนแกน
        st.bar_chart(pop.set_index("style")["fans"], horizontal=True)

    st.divider()
    person_id = person_selector("dash_person")
    profile = get_profile(person_id)
    if profile:
        left, right = st.columns([1, 2])
        with left:
            st.markdown(f"### {profile['name']}")
            st.write(f"**รหัส:** {profile['person_id']}")
            st.write(f"**จำนวนทรงที่ชอบ:** {len(profile['liked'])} ทรง")
        with right:
            st.markdown("### ทรงที่ชอบ")
            if profile["liked"]:
                st.dataframe(pd.DataFrame(profile["liked"]), width="stretch", hide_index=True)
            else:
                st.info("ยังไม่ได้ชอบทรงไหน")

# ---------------------------------------------------------------------------
elif page == "Recommendations":
    st.subheader("✨ ทรงผมที่แนะนำ")
    person_id = person_selector("rec_person")
    top_n = st.slider("จำนวนคำแนะนำ", 3, 12, 6)
    rows = recommend_styles(person_id, top_n)

    st.caption(
        "คะแนน = คนที่ชอบคล้ายกัน × 3 + ทรงที่เชื่อมมาถึง × 2 + จำนวนคนชอบ × 0.20 + คะแนนเฉลี่ย × 0.25"
    )
    if not rows:
        st.info("ยังไม่มีคำแนะนำสำหรับผู้ใช้นี้")
    for i, row in enumerate(rows, start=1):
        st.markdown(
            f"""
            <div class="style-card">
              <span class="score-pill">#{i} · score {row['score']:.2f}</span>
              <h3 style="margin:.55rem 0 .2rem 0">{row['style']}</h3>
              <div class="muted">{row['style_id']}</div>
              <p><b>เหตุผล:</b> {explain_reason(row)}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

# ---------------------------------------------------------------------------
elif page == "Style Search":
    st.subheader("🔎 ค้นหาทรงผม")
    keyword = st.text_input("ชื่อทรงหรือรหัส", placeholder="เช่น บ๊อบ, ลอน, H05")
    rows = search_styles(keyword)
    st.write(f"พบ {len(rows)} รายการ")
    if rows:
        df = pd.DataFrame(rows)
        df["liked_by"] = df["liked_by"].apply(lambda x: ", ".join(x))
        st.dataframe(df, width="stretch", hide_index=True)

# ---------------------------------------------------------------------------
elif page == "Like / Rate":
    st.subheader("📝 บันทึกความชอบและให้คะแนน")

    with st.expander("➕ เพิ่มผู้ใช้ใหม่"):
        c1, c2 = st.columns([1, 2])
        new_id = c1.text_input("รหัส", placeholder="P16")
        new_name = c2.text_input("ชื่อ")
        if st.button("เพิ่มผู้ใช้", width="stretch"):
            if new_id.strip() and new_name.strip():
                add_person(new_id, new_name)
                st.success(f"เพิ่ม {new_id.strip().upper()} แล้ว")
                st.rerun()
            else:
                st.warning("กรอกรหัสและชื่อให้ครบ")

    person_id = person_selector("like_person")
    styles = get_styles()
    if not styles:
        st.info("ยังไม่มีทรงผม")
        st.stop()
    style_labels = {f"{h['style_id']} — {h['name']}": h["style_id"] for h in styles}
    selected = st.selectbox("ทรงผม", list(style_labels))
    score = st.slider("คะแนนความชอบ", 1, 10, 8)

    c1, c2 = st.columns(2)
    if c1.button("บันทึกความชอบ", type="primary", width="stretch"):
        record_like(person_id, style_labels[selected], score)
        st.success("บันทึกความสัมพันธ์ LIKES แล้ว")
    if c2.button("ยกเลิกความชอบทรงนี้", width="stretch"):
        remove_like(person_id, style_labels[selected])
        st.success("ลบความสัมพันธ์ LIKES แล้ว")

    profile = get_profile(person_id)
    if profile and profile["liked"]:
        st.markdown("#### ทรงที่ชอบตอนนี้")
        st.dataframe(pd.DataFrame(profile["liked"]), width="stretch", hide_index=True)

# ---------------------------------------------------------------------------
elif page == "Graph Explorer":
    st.subheader("🕸️ Graph Explorer")
    person_id = person_selector("graph_person")
    rows = graph_neighborhood(person_id)
    if not rows:
        st.info("ยังไม่มี neighborhood graph")
    else:
        # สร้างกราฟด้วยภาษา DOT ของ Graphviz
        # คน = ฟ้า, ทรงผม = เขียว, ตัวเราเอง = ส้ม, เส้น RECOMMENDED = ม่วงเส้นประ
        dot = ["digraph G {", 'rankdir="LR";', 'node [shape=box, style="rounded,filled"];']
        seen_nodes = set()
        for r in rows:
            for nid, label, name, key in [
                (r["source_id"], r["source_label"], r["source_name"], r["source_key"]),
                (r["target_id"], r["target_label"], r["target_name"], r["target_key"]),
            ]:
                if nid not in seen_nodes:
                    if key == person_id:
                        color = "#F2A07B"
                    elif label == "Person":
                        color = "#BFDBFE"
                    else:
                        color = "#BBF7D0"
                    safe_name = str(name).replace('"', "'")
                    dot.append(f'"{nid}" [label="{safe_name}\\n{key}", fillcolor="{color}"];')
                    seen_nodes.add(nid)
            if r["relationship"] == "RECOMMENDED":
                dot.append(
                    f'"{r["source_id"]}" -> "{r["target_id"]}" '
                    f'[label="RECOMMENDED", color="#6C4AB6", fontcolor="#6C4AB6", style=dashed, penwidth=2];'
                )
            else:
                dot.append(f'"{r["source_id"]}" -> "{r["target_id"]}" [label="LIKES {r["score"]}"];')
        dot.append("}")
        st.graphviz_chart("\n".join(dot), width="stretch")
        st.caption("เส้นประสีม่วงจะขึ้นหลังจากกด 'บันทึกผลแนะนำลง Aura' ในหน้า Admin / Setup")
        with st.expander("ดูข้อมูล edge ที่ใช้วาดกราฟ"):
            st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)

# ---------------------------------------------------------------------------
elif page == "Admin / Setup":
    st.subheader("⚙️ Setup ข้อมูล")
    st.markdown(
        """
        **Graph schema**
        - `(:Person)-[:LIKES {score}]->(:Style)` คนชอบทรงผม พร้อมคะแนน 1–10
        - `(:Person)-[:RECOMMENDED {score, rank}]->(:Style)` ผลแนะนำที่บันทึกลงฐานข้อมูล
        """
    )

    st.markdown("#### 1) สร้างข้อมูลตั้งต้น")
    st.warning("ปุ่มนี้ไม่ลบข้อมูลเดิม และใช้ MERGE จึงกดซ้ำได้ (ถ้าเคยรัน notebook ไว้แล้วก็กดได้)")
    if st.button("สร้าง Constraint + ข้อมูลตั้งต้น (P01–P15, H01–H12)", type="primary", width="stretch"):
        with st.spinner("กำลังสร้างข้อมูล..."):
            seed_demo_data()
        st.success("สร้างข้อมูลเรียบร้อยแล้ว")

    st.markdown("#### 2) บันทึกผลแนะนำลง Aura")
    st.caption(
        "ผลแนะนำปกติคำนวณตอนเปิดหน้าเว็บ ไม่ได้อยู่ในฐานข้อมูล ปุ่มนี้จะสร้างเส้น RECOMMENDED "
        "ให้ทุกคน เพื่อเปิดดูใน Neo4j Aura ได้ (กดใหม่ทุกครั้งที่ข้อมูลความชอบเปลี่ยน)"
    )
    save_n = st.number_input("จำนวนทรงที่บันทึกต่อคน", 1, 10, 3)
    if st.button("บันทึกผลแนะนำลง Aura", width="stretch"):
        with st.spinner("กำลังคำนวณ..."):
            total = save_recommendations(int(save_n))
        st.success(f"สร้างเส้น RECOMMENDED {total} เส้น")
        st.code(
            "MATCH path = (:Person {person_id:'P01'})-[:LIKES|RECOMMENDED]->(:Style)\nRETURN path",
            language="cypher",
        )
        st.caption("นำ query ด้านบนไปรันใน Aura → Query เพื่อดูกราฟ")
