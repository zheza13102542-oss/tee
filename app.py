"""หน้าเว็บ (Presentation layer) ของระบบแนะนำทรงผม

รันในเครื่อง:  streamlit run app.py
คำสั่ง Cypher ทั้งหมดอยู่ใน neo4j_service.py
"""

from __future__ import annotations

import html

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
    page_title="HairGraph Barber & Salon",
    page_icon="💈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# หน้าตาเว็บแบบร้านตัดผม
#   สี: กรมท่า (ป้ายร้าน) + แดงเสาตัดผม + ทองเหลือง (กรอบกระจก/ป้าย)
#   ฟอนต์: ตั้งไว้ใน .streamlit/config.toml (Chonburi = หัวข้อแบบป้ายร้าน, Anuphan = เนื้อหา)
# ---------------------------------------------------------------------------
st.markdown(
    """
    <style>
      :root {
        --navy: #1B2A41;
        --red: #B3261E;
        --brass: #C9A24B;
        --paper: #FBFCFD;
        --line: #D5DCE4;
        --soft: #5B6878;
      }
      .block-container {padding-top: 3.4rem; padding-bottom: 3rem; max-width: 1180px;}

      /* ----- ป้ายร้าน (hero) + เสาตัดผมหมุน ----- */
      .shop-sign {
        display: flex; gap: 1.6rem; align-items: stretch;
        background: var(--navy); color: #F4EEE2;
        border-radius: 18px; padding: 1.4rem 1.8rem 1.4rem 1.4rem;
        outline: 1px solid rgba(201,162,75,.55); outline-offset: -9px;
        margin-bottom: 1.4rem;
      }
      .pole {
        width: 26px; flex: none; border-radius: 13px;
        border-top: 9px solid var(--brass); border-bottom: 9px solid var(--brass);
        background: repeating-linear-gradient(-45deg,
          var(--red) 0 12px, #F7F8FA 12px 24px, #2457A6 24px 36px, #F7F8FA 36px 48px);
        animation: pole-spin 2.6s linear infinite;
        box-shadow: inset -5px 0 8px rgba(0,0,0,.25), inset 4px 0 6px rgba(255,255,255,.35);
      }
      @keyframes pole-spin { to { background-position: 0 -67.88px; } }
      @media (prefers-reduced-motion: reduce) { .pole { animation: none; } }
      .shop-sign h1 {
        font-family: "Chonburi", serif; font-weight: 400;
        font-size: 2.35rem; line-height: 1.15; margin: 0; padding: 0; color: #F4EEE2;
      }
      .shop-sign .since { color: var(--brass); font-size: .95rem; letter-spacing: .04em; margin: 0 0 .3rem 0; }
      .shop-sign .tagline { margin: .45rem 0 0 0; color: #CBD4E0; font-size: 1.02rem; max-width: 52ch; }

      /* ----- รูปทรงผม = กระจกโค้งแบบร้านทำผม ----- */
      [data-testid="stImage"] img {
        border-radius: 999px 999px 14px 14px;
        aspect-ratio: 4 / 5; object-fit: cover;
        border: 3px solid #fff; box-shadow: 0 0 0 1px var(--line);
      }
      .no-image {
        aspect-ratio: 4 / 5; display: flex; align-items: center; justify-content: center;
        border: 1.5px dashed var(--line); border-radius: 999px 999px 14px 14px; color: var(--soft);
      }
      .style-name { font-weight: 600; font-size: 1.02rem; margin-top: .35rem; line-height: 1.35; }
      .style-code { color: var(--soft); font-size: .85rem; }

      /* ----- การ์ดแนะนำ = รายการในเมนูร้าน (ชื่อ ....... คะแนน) ----- */
      .menu-head { display: flex; align-items: baseline; gap: .6rem; }
      .menu-no {
        font-family: "Chonburi", serif; color: var(--red); font-size: 1.05rem; flex: none;
      }
      .menu-name { font-family: "Chonburi", serif; font-size: 1.55rem; line-height: 1.25; }
      .menu-dots { flex: 1; border-bottom: 2px dotted #9AA6B5; transform: translateY(-.35rem); min-width: 2rem; }
      .menu-score { font-family: "Chonburi", serif; font-size: 1.55rem; color: var(--navy); flex: none; }
      .menu-code { color: var(--soft); font-size: .88rem; margin: .1rem 0 .7rem 0; }
      .reasons { margin: 0; padding-left: 1.1rem; color: #2E3B4E; }
      .reasons li { margin: .15rem 0; }
      .reasons li::marker { color: var(--brass); content: "✂  "; }

      /* ----- ตัวเลขสรุป ----- */
      [data-testid="stMetric"] {
        background: var(--paper); border: 1px solid var(--line);
        border-top: 4px solid var(--red); border-radius: 12px; padding: .8rem 1rem;
      }
      [data-testid="stMetricValue"] { font-family: "Chonburi", serif; }

      /* ----- แถบเมนูด้านข้าง ----- */
      [data-testid="stSidebar"] .brand {
        font-family: "Chonburi", serif; font-size: 1.6rem; color: #F4EEE2; margin: 0; line-height: 1.2;
      }
      [data-testid="stSidebar"] .brand-sub { color: var(--brass); margin: .1rem 0 .4rem 0; font-size: .95rem; }
      [data-testid="stSidebar"] [role="radiogroup"] label { padding: .3rem 0; }
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
                st.markdown(
                    f'<div class="style-name">{html.escape(str(row["style"]))}</div>'
                    f'<div class="style-code">{html.escape(str(row["style_id"]))}</div>',
                    unsafe_allow_html=True,
                )
                if caption_key:
                    st.caption(caption_key.format(**row))


def explain_parts(row: dict) -> list[str]:
    """แปลงตัวเลขจาก Cypher เป็นเหตุผลทีละข้อ (ใช้แสดงเป็นรายการในการ์ดแนะนำ)"""
    return explain_reason(row).split(" • ")


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
    st.markdown(
        '<p class="brand">💈 HairGraph</p><p class="brand-sub">Barber &amp; Salon</p>',
        unsafe_allow_html=True,
    )
    # ค่าของเมนูยังเป็นชื่อภาษาอังกฤษเดิม (โค้ดด้านล่างใช้เทียบ) แต่แสดงเป็นภาษาไทย
    MENU_TH = {
        "Dashboard": "หน้าร้าน",
        "Recommendations": "แนะนำทรงผม",
        "Style Search": "ค้นหาทรงผม",
        "Like / Rate": "ให้คะแนนทรงผม",
        "Manage Data": "จัดการข้อมูล",
        "Graph Explorer": "กราฟความสัมพันธ์",
        "Admin / Setup": "ตั้งค่าระบบ",
    }
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
        format_func=lambda p: MENU_TH[p],
    )
    st.divider()
    st.caption("Graph Database Project")

st.markdown(
    """
    <div class="shop-sign">
      <div class="pole" aria-hidden="true"></div>
      <div>
        <p class="since">Barber &amp; Salon · Neo4j Aura</p>
        <h1>HairGraph</h1>
        <p class="tagline">ร้านที่รู้ว่าคุณน่าจะชอบทรงไหน จากคนที่ชอบทรงเดียวกับคุณ และบอกเหตุผลได้ทุกคำแนะนำ</p>
      </div>
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
    c1.metric("ลูกค้าในระบบ", m.get("people", 0))
    c2.metric("ทรงผมในร้าน", m.get("styles", 0))
    c3.metric("ความชอบ (LIKES)", m.get("likes", 0))
    c4.metric("ผลแนะนำที่บันทึก", m.get("recommended", 0))

    st.markdown("### ทรงผมยอดนิยม")
    pop = pd.DataFrame(style_popularity())
    if not pop.empty:
        st.bar_chart(
            pop.rename(columns={"style": "ทรงผม", "fans": "จำนวนคนชอบ"}),
            x="ทรงผม", y="จำนวนคนชอบ", horizontal=True, color="#1B2A41",
            sort="-จำนวนคนชอบ",   # ทรงที่คนชอบมากสุดอยู่บนสุด
        )

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
    st.subheader("ทรงผมที่แนะนำ")
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
                # แบบรายการในเมนูร้าน: No.1  ชื่อทรง ............ คะแนน
                reasons = "".join(f"<li>{html.escape(p)}</li>" for p in explain_parts(row))
                st.markdown(
                    f'<div class="menu-head">'
                    f'<span class="menu-no">No.{i}</span>'
                    f'<span class="menu-name">{html.escape(str(row["style"]))}</span>'
                    f'<span class="menu-dots"></span>'
                    f'<span class="menu-score">{row["score"]:.2f}</span>'
                    f'</div>'
                    f'<div class="menu-code">{html.escape(str(row["style_id"]))} · คะแนนแนะนำ</div>'
                    f'<ul class="reasons">{reasons}</ul>',
                    unsafe_allow_html=True,
                )

# ---------------------------------------------------------------------------
elif page == "Style Search":
    st.subheader("ค้นหาทรงผม")
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
    st.subheader("บันทึกความชอบและให้คะแนน")
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
    st.subheader("จัดการข้อมูล (เพิ่ม / แก้ไข / ลบ)")
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
    st.subheader("กราฟความสัมพันธ์")
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
                        color = "#F4B4AE"   # ตัวเอง = แดงอ่อน (สีเสาตัดผม)
                    elif label == "Person":
                        color = "#C9D6EA"   # คน = กรมท่าอ่อน
                    else:
                        color = "#EADCB3"   # ทรงผม = ทองเหลืองอ่อน
                    safe_name = str(name).replace('"', "'")
                    dot.append(f'"{nid}" [label="{safe_name}\\n{key}", fillcolor="{color}"];')
                    seen_nodes.add(nid)
            if r["relationship"] == "RECOMMENDED":
                dot.append(
                    f'"{r["source_id"]}" -> "{r["target_id"]}" '
                    f'[label="RECOMMENDED", color="#B3261E", fontcolor="#B3261E", style=dashed, penwidth=2];'
                )
            else:
                dot.append(f'"{r["source_id"]}" -> "{r["target_id"]}" [label="LIKES {r["score"]}"];')
        dot.append("}")
        st.graphviz_chart("\n".join(dot), width="stretch")
        st.caption("เส้นประสีแดงจะขึ้นหลังจากกด 'บันทึกผลแนะนำลง Aura' ในหน้า Admin / Setup")
        with st.expander("ดูข้อมูล edge ที่ใช้วาดกราฟ"):
            st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)

# ---------------------------------------------------------------------------
elif page == "Admin / Setup":
    st.subheader("ตั้งค่าระบบ")
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
