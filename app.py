"""หน้าเว็บ (Presentation layer) ของระบบแนะนำทรงผม

รันในเครื่อง:  streamlit run app.py
คำสั่ง Cypher ทั้งหมดอยู่ใน neo4j_service.py
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from neo4j_service import (
    ALLOWED_IMAGE_TYPES,
    DataError,
    create_person,
    create_style,
    delete_person,
    delete_style,
    get_all_likes,
    get_dashboard_metrics,
    get_people,
    get_profile,
    get_styles,
    graph_neighborhood,
    image_path,
    ping,
    recommend_styles,
    record_like,
    remove_like,
    save_recommendations,
    save_style_image,
    set_person_likes,
    search_styles,
    seed_demo_data,
    style_popularity,
    update_person,
    update_style,
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
      .no-image {
        aspect-ratio: 1 / 1; display:flex; align-items:center; justify-content:center;
        border: 1px dashed rgba(128,128,128,.45); border-radius: 12px; opacity:.6;
      }
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


def show_style_image(image: str | None, width: int | str = "stretch") -> None:
    """แสดงรูปทรงผมจากโฟลเดอร์ images/ ถ้าไม่มีไฟล์ให้แสดงกล่องแทน"""
    path = image_path(image)
    if path:
        st.image(str(path), width=width)
    else:
        st.markdown('<div class="no-image">ไม่มีรูป</div>', unsafe_allow_html=True)


def flash(message: str, clear_keys: list[str] | None = None) -> None:
    """เก็บข้อความแจ้งผลไว้ แล้วโหลดหน้าใหม่ (ข้อความจะแสดงหลังโหลดเสร็จ)

    clear_keys = key ของช่องกรอกที่ต้องการล้างค่า (เช่น หลังเพิ่มคนสำเร็จ)
    """
    for key in clear_keys or []:
        st.session_state.pop(key, None)
    st.session_state["flash"] = message
    st.rerun()


def likes_picker(styles: list[dict], key: str, current: dict[str, int] | None = None) -> dict[str, int]:
    """เลือกทรงผมได้หลายทรง แล้วให้คะแนนแต่ละทรง คืนค่าเป็น {รหัสทรง: คะแนน}

    current = ความชอบเดิม (ใช้ตอนแก้ไข จะเลือกไว้ให้ล่วงหน้าพร้อมคะแนนเดิม)
    """
    current = current or {}
    names = {h["style_id"]: h for h in styles}
    selected = st.multiselect(
        "ทรงผมที่ชอบ (เลือกได้หลายทรง)",
        options=list(names),
        default=[sid for sid in current if sid in names],
        format_func=lambda sid: f"{sid} — {names[sid]['name']}",
        key=f"{key}_styles",
    )
    result = {}
    # แสดงรูป + แถบคะแนนของทรงที่เลือก แถวละ 4 ทรง
    for start in range(0, len(selected), 4):
        cols = st.columns(4)
        for col, sid in zip(cols, selected[start:start + 4]):
            with col:
                show_style_image(names[sid].get("image"), width=110)
                result[sid] = st.slider(
                    names[sid]["name"], 1, 10, int(current.get(sid, 8)), key=f"{key}_score_{sid}"
                )
    return result


def show_flash() -> None:
    """แสดงข้อความที่เก็บไว้จาก flash() ครั้งเดียว"""
    message = st.session_state.pop("flash", None)
    if message:
        st.success(message)


def style_gallery(rows: list[dict], columns: int = 4, caption_key: str | None = None) -> None:
    """แสดงทรงผมเป็นตารางรูป (gallery)"""
    for start in range(0, len(rows), columns):
        cols = st.columns(columns)
        for col, row in zip(cols, rows[start:start + columns]):
            with col:
                show_style_image(row.get("image"))
                st.markdown(f"**{row['style']}**  \n`{row['style_id']}`")
                if caption_key:
                    st.caption(caption_key.format(**row))


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
        [
            "Dashboard",
            "Recommendations",
            "Style Search",
            "Like / Rate",
            "Manage Data",
            "Graph Explorer",
            "Admin / Setup",
        ],
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

show_flash()

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
        st.bar_chart(pop.set_index("style")["fans"], horizontal=True)

    st.divider()
    person_id = person_selector("dash_person")
    profile = get_profile(person_id)
    if profile:
        st.markdown(f"### {profile['name']} ({profile['person_id']})")
        st.write(f"ชอบ {len(profile['liked'])} ทรง")
        if profile["liked"]:
            style_gallery(profile["liked"], columns=6, caption_key="คะแนน {score}/10")
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
        # การ์ด 1 ใบ = รูปทางซ้าย + ชื่อ/คะแนน/เหตุผลทางขวา
        with st.container(border=True):
            left, right = st.columns([1, 4], vertical_alignment="center")
            with left:
                show_style_image(row.get("image"))
            with right:
                st.markdown(
                    f'<span class="score-pill">#{i} · score {row["score"]:.2f}</span>'
                    f'<h3 style="margin:.45rem 0 .1rem 0">{row["style"]}</h3>'
                    f'<div class="muted">{row["style_id"]}</div>',
                    unsafe_allow_html=True,
                )
                st.markdown(f"**เหตุผล:** {explain_reason(row)}")

# ---------------------------------------------------------------------------
elif page == "Style Search":
    st.subheader("🔎 ค้นหาทรงผม")
    keyword = st.text_input("ชื่อทรงหรือรหัส", placeholder="เช่น บ๊อบ, ลอน, H05")
    rows = search_styles(keyword)
    st.write(f"พบ {len(rows)} รายการ")
    for row in rows:
        row["liked_text"] = ", ".join(row["liked_by"]) or "-"
    style_gallery(
        rows,
        columns=4,
        caption_key="❤️ {fans} คน · เฉลี่ย {avg_score}/10 · {liked_text}",
    )

# ---------------------------------------------------------------------------
elif page == "Like / Rate":
    st.subheader("📝 บันทึกความชอบและให้คะแนน")
    person_id = person_selector("like_person")
    styles = get_styles()
    if not styles:
        st.info("ยังไม่มีทรงผม")
        st.stop()
    style_labels = {f"{h['style_id']} — {h['name']}": h for h in styles}

    left, right = st.columns([1, 2])
    with right:
        selected = style_labels[st.selectbox("ทรงผม", list(style_labels))]
        score = st.slider("คะแนนความชอบ", 1, 10, 8)
        c1, c2 = st.columns(2)
        if c1.button("บันทึกความชอบ", type="primary", width="stretch"):
            record_like(person_id, selected["style_id"], score)
            flash(f"บันทึก {person_id} ชอบ {selected['name']} คะแนน {score} แล้ว")
        if c2.button("ยกเลิกความชอบทรงนี้", width="stretch"):
            remove_like(person_id, selected["style_id"])
            flash(f"ลบความชอบ {selected['name']} ของ {person_id} แล้ว")
    with left:
        show_style_image(selected.get("image"))

    profile = get_profile(person_id)
    if profile and profile["liked"]:
        st.markdown("#### ทรงที่ชอบตอนนี้")
        style_gallery(profile["liked"], columns=6, caption_key="คะแนน {score}/10")

# ---------------------------------------------------------------------------
elif page == "Manage Data":
    st.subheader("🗂️ จัดการข้อมูล (เพิ่ม / แก้ไข / ลบ)")
    tab_person, tab_style, tab_like = st.tabs(["👤 คน", "💇 ทรงผม", "❤️ ความชอบ"])

    # ----- คน -----
    with tab_person:
        people = get_people()
        st.dataframe(pd.DataFrame(people), width="stretch", hide_index=True)
        action = st.radio("ต้องการ", ["เพิ่ม", "แก้ไข", "ลบ"], horizontal=True, key="person_action")

        if action == "เพิ่ม":
            # ไม่ใช้ st.form เพราะต้องการให้แถบคะแนนโผล่ทันทีที่เลือกทรงผม
            c1, c2 = st.columns([1, 2])
            new_id = c1.text_input("รหัส", placeholder="P16", key="new_person_id")
            new_name = c2.text_input("ชื่อ", key="new_person_name")
            new_likes = likes_picker(get_styles(), key="new_person")
            if st.button("เพิ่มคน", type="primary"):
                try:
                    pid = create_person(new_id, new_name)
                    set_person_likes(pid, new_likes)
                    # ล้างช่องกรอกทั้งหมดหลังเพิ่มสำเร็จ
                    clear = [k for k in st.session_state if str(k).startswith("new_person")]
                    flash(f"เพิ่ม {pid} พร้อมทรงที่ชอบ {len(new_likes)} ทรงแล้ว", clear)
                except DataError as exc:
                    st.warning(str(exc))

        elif people:
            labels = {f"{p['person_id']} — {p['name']}": p for p in people}
            chosen = labels[st.selectbox("เลือกคน", list(labels), key="person_pick")]

            if action == "แก้ไข":
                pid = chosen["person_id"]
                # key ผูกกับรหัส เพื่อให้ช่องต่าง ๆ เปลี่ยนตามคนที่เลือก
                name = st.text_input("ชื่อ", value=chosen["name"], key=f"edit_person_{pid}")
                profile = get_profile(pid)
                current = {x["style_id"]: x["score"] for x in profile["liked"]} if profile else {}
                edit_likes = likes_picker(get_styles(), key=f"edit_{pid}", current=current)
                st.caption(
                    "เอาทรงออกจากรายการ = ยกเลิกความชอบทรงนั้น · "
                    "รหัสเป็น primary key จึงแก้ไม่ได้ ถ้าต้องการเปลี่ยนรหัสให้ลบแล้วเพิ่มใหม่"
                )
                if st.button("บันทึกการแก้ไข", type="primary"):
                    try:
                        update_person(pid, name)
                        set_person_likes(pid, edit_likes)
                        flash(f"แก้ไข {pid} แล้ว (ชอบ {len(edit_likes)} ทรง)")
                    except DataError as exc:
                        st.warning(str(exc))
            else:
                st.warning("การลบจะลบความชอบ (LIKES) และผลแนะนำ (RECOMMENDED) ของคนนี้ทั้งหมดด้วย")
                confirm = st.checkbox(f"ยืนยันลบ {chosen['person_id']} — {chosen['name']}")
                if st.button("ลบคน", type="primary", disabled=not confirm):
                    try:
                        delete_person(chosen["person_id"])
                        flash(f"ลบ {chosen['person_id']} แล้ว")
                    except DataError as exc:
                        st.warning(str(exc))

    # ----- ทรงผม -----
    with tab_style:
        styles = get_styles()
        style_gallery(
            [{"style_id": h["style_id"], "style": h["name"], "image": h["image"]} for h in styles],
            columns=6,
        )
        st.info(
            "รูปเก็บเป็นไฟล์ในโฟลเดอร์ `images/` ของ git repo ส่วนใน Neo4j เก็บแค่ชื่อไฟล์ "
            "บน Streamlit Cloud ไฟล์ที่อัปโหลดจะหายเมื่อแอปรีสตาร์ท ให้ดาวน์โหลดไฟล์ที่อัปโหลดแล้ว "
            "นำไปใส่ใน `images/` แล้ว push ขึ้น GitHub เพื่อเก็บถาวร"
        )
        action = st.radio("ต้องการ", ["เพิ่ม", "แก้ไข", "ลบ"], horizontal=True, key="style_action")

        if action == "เพิ่ม":
            with st.form("add_style", clear_on_submit=True):
                c1, c2 = st.columns([1, 2])
                new_id = c1.text_input("รหัส", placeholder="H13")
                new_name = c2.text_input("ชื่อทรงผม")
                upload = st.file_uploader("รูปทรงผม", type=ALLOWED_IMAGE_TYPES)
                if st.form_submit_button("เพิ่มทรงผม", type="primary"):
                    try:
                        # สร้าง node ก่อน (เช็กรหัสซ้ำ) แล้วค่อยบันทึกรูป กันรูปไปทับของทรงเดิม
                        sid = create_style(new_id, new_name)
                        if upload:
                            filename = save_style_image(sid, upload.getvalue(), upload.name)
                            update_style(sid, new_name, filename)
                            st.session_state["last_upload"] = filename
                        flash(f"เพิ่ม {sid} แล้ว")
                    except DataError as exc:
                        st.warning(str(exc))

        elif styles:
            labels = {f"{h['style_id']} — {h['name']}": h for h in styles}
            chosen = labels[st.selectbox("เลือกทรงผม", list(labels), key="style_pick")]
            left, right = st.columns([1, 3])
            with left:
                show_style_image(chosen["image"])
                st.caption(chosen["image"] or "ไม่มีไฟล์")

            with right:
                if action == "แก้ไข":
                    name = st.text_input("ชื่อทรงผม", value=chosen["name"], key=f"edit_style_{chosen['style_id']}")
                    upload = st.file_uploader(
                        "เปลี่ยนรูป (ไม่เลือก = ใช้รูปเดิม)",
                        type=ALLOWED_IMAGE_TYPES,
                        key=f"upload_{chosen['style_id']}",
                    )
                    if st.button("บันทึกการแก้ไข", type="primary"):
                        try:
                            filename = None
                            if upload:
                                filename = save_style_image(chosen["style_id"], upload.getvalue(), upload.name)
                                st.session_state["last_upload"] = filename
                            update_style(chosen["style_id"], name, filename)
                            flash(f"แก้ไข {chosen['style_id']} แล้ว")
                        except DataError as exc:
                            st.warning(str(exc))
                else:
                    st.warning("การลบจะลบความชอบและผลแนะนำที่ชี้มาหาทรงนี้ทั้งหมดด้วย")
                    delete_file = st.checkbox("ลบไฟล์รูปในโฟลเดอร์ images/ ด้วย", value=True)
                    confirm = st.checkbox(f"ยืนยันลบ {chosen['style_id']} — {chosen['name']}")
                    if st.button("ลบทรงผม", type="primary", disabled=not confirm):
                        try:
                            delete_style(chosen["style_id"], delete_file)
                            flash(f"ลบ {chosen['style_id']} แล้ว")
                        except DataError as exc:
                            st.warning(str(exc))

        # ปุ่มดาวน์โหลดไฟล์ที่เพิ่งอัปโหลด เอาไปใส่ images/ ใน git
        last = st.session_state.get("last_upload")
        if last and image_path(last):
            st.download_button(
                f"⬇️ ดาวน์โหลด {last} ไปใส่ใน images/ ของ git",
                data=image_path(last).read_bytes(),
                file_name=last,
            )

    # ----- ความชอบ -----
    with tab_like:
        likes = get_all_likes()
        st.dataframe(pd.DataFrame(likes), width="stretch", hide_index=True)
        action = st.radio("ต้องการ", ["เพิ่ม / แก้คะแนน", "ลบ"], horizontal=True, key="like_action")

        if action == "เพิ่ม / แก้คะแนน":
            people = get_people()
            styles = get_styles()
            if people and styles:
                with st.form("upsert_like"):
                    p_labels = {f"{p['person_id']} — {p['name']}": p["person_id"] for p in people}
                    s_labels = {f"{h['style_id']} — {h['name']}": h["style_id"] for h in styles}
                    c1, c2 = st.columns(2)
                    pid = p_labels[c1.selectbox("คน", list(p_labels))]
                    sid = s_labels[c2.selectbox("ทรงผม", list(s_labels))]
                    score = st.slider("คะแนน", 1, 10, 8)
                    st.caption("ถ้าคู่นี้มีอยู่แล้วจะเป็นการแก้คะแนน (MERGE ไม่สร้างเส้นซ้ำ)")
                    if st.form_submit_button("บันทึก", type="primary"):
                        try:
                            record_like(pid, sid, score)
                            flash(f"บันทึก {pid} → {sid} คะแนน {score} แล้ว")
                        except DataError as exc:
                            st.warning(str(exc))
        elif likes:
            labels = {
                f"{x['person_id']} {x['person']} → {x['style_id']} {x['style']} ({x['score']})": x
                for x in likes
            }
            chosen = labels[st.selectbox("เลือกความชอบที่จะลบ", list(labels))]
            if st.button("ลบความชอบ", type="primary"):
                remove_like(chosen["person_id"], chosen["style_id"])
                flash("ลบความชอบแล้ว")

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
