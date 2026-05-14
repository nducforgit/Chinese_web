import streamlit as st
import streamlit.components.v1 as components
from google import genai
import os
import urllib.parse

os.environ["DATABASE_URL"] = st.secrets["DATABASE_URL"]
_gemini_key = st.secrets["GEMINI_API_KEY"]

from database import init_db, auto_seed, get_due_words, get_all_words, batch_update_reviews, delete_word, get_stats

_genai_client = genai.Client(api_key=_gemini_key) if _gemini_key else None

def _ai_html(text: str) -> str:
    import re
    text = re.sub(r'\n{2,}', '\n', text.strip())
    return text.replace('\n', '<br>')

GEMINI_MODELS = [
    "gemini-2.5-flash-lite",
    "gemini-2.0-flash-lite",
    "gemini-2.0-flash",
    "gemini-2.5-flash",
]

def ask_gemini(prompt: str) -> str:
    if not _genai_client:
        raise RuntimeError("Chưa có Gemini API Key — chạy lại start.py để nhập.")
    last_err = None
    for model_name in GEMINI_MODELS:
        try:
            response = _genai_client.models.generate_content(model=model_name, contents=prompt)
            return response.text
        except Exception as e:
            msg = str(e)
            if "429" in msg or "404" in msg or "quota" in msg.lower() or "not found" in msg.lower():
                last_err = e
                continue
            raise
    raise RuntimeError(
        "Hết quota hoặc không tìm thấy model khả dụng.\n"
        "Hãy lấy API key mới tại https://aistudio.google.com/app/apikey\n"
        f"(Chi tiết: {last_err})"
    )

st.set_page_config(
    page_title="Tiếng Trung - Mai Hương",
    page_icon="🌸",
    layout="wide"
)

# --- Khởi tạo (cache_resource = chỉ chạy 1 lần khi server start, không chạy lại mỗi render) ---
@st.cache_resource
def setup_db():
    init_db()
    auto_seed()

setup_db()

# --- PWA meta tags + icon ---
_icon_b64 = ""
_icon_path = os.path.join(os.path.dirname(__file__), "icon_b64.txt")
if os.path.exists(_icon_path):
    with open(_icon_path) as f:
        _icon_b64 = f.read().strip()

st.markdown(f"""
<link rel="apple-touch-icon" href="data:image/png;base64,{_icon_b64}">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="Tiếng Trung">
<meta name="mobile-web-app-capable" content="yes">
<meta name="theme-color" content="#f48fb1">
""", unsafe_allow_html=True)

# --- CSS giao diện hồng nhạt ---
st.markdown("""
<style>
    /* Nền tổng thể */
    .stApp {
        background-color: #fff0f5;
    }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #ffe0ec;
    }

    /* Tiêu đề chính */
    h1, h2, h3 {
        color: #c2185b !important;
    }

    /* Nút bấm */
    .stButton > button {
        background-color: #f48fb1;
        color: white;
        border: none;
        border-radius: 12px;
        font-weight: bold;
        transition: background-color 0.2s;
    }
    .stButton > button:hover {
        background-color: #e91e8c;
        color: white;
    }

    /* Text input */
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea {
        border: 2px solid #f48fb1;
        border-radius: 10px;
        background-color: #fff8fb;
    }

    /* Metric */
    [data-testid="stMetric"] {
        background-color: #fce4ec;
        border-radius: 12px;
        padding: 16px;
        border: 1px solid #f48fb1;
    }

    /* Expander */
    .streamlit-expanderHeader {
        background-color: #fce4ec;
        border-radius: 10px;
    }

    /* Progress bar */
    .stProgress > div > div > div {
        background-color: #e91e8c;
    }

    /* Info/success boxes */
    .stAlert {
        border-radius: 12px;
    }

    /* Card từ vựng */
    .flashcard {
        background: linear-gradient(135deg, #fce4ec, #fff0f5);
        border: 2px solid #f48fb1;
        border-radius: 20px;
        padding: 30px;
        text-align: center;
        margin: 20px 0;
        box-shadow: 0 4px 15px rgba(244,143,177,0.3);
    }
    .hanzi-big {
        font-size: 72px;
        color: #c2185b;
        font-weight: bold;
        line-height: 1.2;
    }
    .pinyin-text {
        font-size: 24px;
        color: #e91e8c;
        margin: 8px 0;
    }
    .meaning-text {
        font-size: 20px;
        color: #880e4f;
        margin-top: 10px;
    }
    .ai-result {
        background-color: #fce4ec;
        border-left: 4px solid #e91e8c;
        border-radius: 0 12px 12px 0;
        padding: 16px 20px;
        margin-top: 12px;
        color: #4a0020;
        line-height: 1.7;
    }

    /* ── MOBILE RESPONSIVE ── */
    @media (max-width: 768px) {
        /* Thu nhỏ padding tổng thể */
        .block-container {
            padding: 0.8rem 0.8rem 2rem !important;
        }

        /* Chữ Hán nhỏ hơn trên điện thoại */
        .hanzi-big {
            font-size: 52px !important;
        }
        .pinyin-text {
            font-size: 18px !important;
        }
        .meaning-text {
            font-size: 16px !important;
        }
        .flashcard {
            padding: 18px !important;
        }

        /* Nút bấm to hơn, dễ bấm ngón tay */
        .stButton > button {
            min-height: 48px !important;
            font-size: 15px !important;
        }

        /* Tiêu đề nhỏ hơn */
        h1 { font-size: 1.5rem !important; }
        h2 { font-size: 1.2rem !important; }
        h3 { font-size: 1rem !important; }

        /* Sidebar rộng hơn khi mở */
        [data-testid="stSidebar"] {
            min-width: 240px !important;
        }

        /* Radio buttons trong sidebar dễ bấm hơn */
        [data-testid="stSidebar"] label {
            font-size: 15px !important;
            padding: 6px 0 !important;
        }

        /* Input fields to hơn */
        .stTextInput > div > div > input,
        .stTextArea > div > div > textarea {
            font-size: 16px !important;
            min-height: 44px !important;
        }

        /* Tab labels */
        .stTabs [data-baseweb="tab"] {
            font-size: 13px !important;
            padding: 8px 12px !important;
        }
    }

    @media (max-width: 480px) {
        .hanzi-big { font-size: 42px !important; }
        .block-container { padding: 0.5rem 0.5rem 2rem !important; }
    }
</style>
""", unsafe_allow_html=True)

def tts_button(hanzi: str):
    """Phát âm qua Google TTS audio (ưu tiên) → Web Speech API (dự phòng).
    Dùng components.html() để tránh CSP của trang chủ và giới hạn Safari."""
    safe = hanzi.replace("\\", "\\\\").replace("'", "\\'")
    encoded = urllib.parse.quote(hanzi)
    tts_url = f"https://translate.google.com/translate_tts?ie=UTF-8&q={encoded}&tl=zh-CN&client=tw-ob"
    components.html(f"""
    <html><body style="margin:0;padding:0;background:transparent;">
    <button id="b"
        style="background:none;border:none;font-size:22px;cursor:pointer;
               padding:4px 8px;border-radius:8px;line-height:1;"
        title="Phát âm">🔊</button>
    <script>
    document.getElementById('b').onclick = function() {{
        var text = '{safe}';

        // Cả hai được gọi ĐỒNG BỘ ngay trong sự kiện bấm
        // (iOS Safari sẽ hủy quyền audio nếu gọi bất đồng bộ sau .catch)

        // Primary: Google Translate TTS (mp3 trực tiếp, không cần quyền, hoạt động trên iOS Safari)
        // audio.play() gọi đồng bộ trong handler tap — iOS Safari cho phép
        var audio = new Audio('{tts_url}');
        audio.play().catch(function() {{
            // Fallback: Web Speech API (chạy async khi audio fail)
            try {{
                var ss = (window.parent && window.parent.speechSynthesis) || window.speechSynthesis;
                var SU = (window.parent && window.parent.SpeechSynthesisUtterance) || SpeechSynthesisUtterance;
                if (ss && SU) {{
                    ss.cancel();
                    var u = new SU(text);
                    u.lang = 'zh-CN'; u.rate = 0.9;
                    ss.speak(u);
                }}
            }} catch(e) {{}}
        }});
    }};
    </script>
    </body></html>
    """, height=44)

# --- Sidebar ---
with st.sidebar:
    st.markdown("## 🌸 Xin chào, **Mai Hương**!")
    st.markdown("---")
    page = st.radio(
        "Chọn chức năng",
        ["🏠 Dashboard",
         "📘 HSK 2 — Sơ cấp",
         "📗 HSK 3 — Trung sơ cấp",
         "📕 HSK 4 — Trung cấp",
         "📝 Bài tập luyện tập",
         "📋 Danh sách từ",
         "🈯 Dịch câu",
         "✍️ Đặt câu & Kiểm tra ngữ pháp"],
        label_visibility="collapsed"
    )
    st.markdown("---")
    st.success("🤖 Gemini AI đã kết nối ✓")


# ============================================================
# DASHBOARD
# ============================================================
if page == "🏠 Dashboard":
    st.markdown("# 🌸 Học Tiếng Trung cùng Mai Hương")
    st.markdown("---")

    stats = get_stats()
    col1, col2, col3 = st.columns(3)
    col1.metric("🗂️ Tổng số từ", stats["total"])
    col2.metric("📅 Cần ôn hôm nay", stats["due"])
    col3.metric("✅ Học hôm nay", stats["learned"])

    st.markdown("### 🎓 Tiến độ theo cấp HSK")
    h2 = get_stats("HSK2")
    h3 = get_stats("HSK3")
    h4 = get_stats("HSK4")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("#### 📘 HSK 2")
        st.metric("Tổng từ", h2["total"])
        st.metric("Cần ôn", h2["due"])
        st.metric("Đã học", h2["learned"])
        if h2["total"]:
            st.progress(h2["learned"] / h2["total"])
    with c2:
        st.markdown("#### 📗 HSK 3")
        st.metric("Tổng từ", h3["total"])
        st.metric("Cần ôn", h3["due"])
        st.metric("Đã học", h3["learned"])
        if h3["total"]:
            st.progress(h3["learned"] / h3["total"])
    with c3:
        st.markdown("#### 📕 HSK 4")
        st.metric("Tổng từ", h4["total"])
        st.metric("Cần ôn", h4["due"])
        st.metric("Đã học", h4["learned"])
        if h4["total"]:
            st.progress(h4["learned"] / h4["total"])

    st.markdown("---")
    if stats["due"] > 0:
        st.info(f"💪 Mai Hương có **{stats['due']} từ** cần ôn tập hôm nay!")
    elif stats["total"] == 0:
        st.info("🌱 Hãy bắt đầu bằng cách thêm từ mới nhé!")
    else:
        st.success("🎉 Tuyệt vời! Mai Hương đã hoàn thành ôn tập hôm nay!")

    with st.expander("📲 Cài app lên iPhone"):
        st.markdown("""
        1. Mở **Safari** trên iPhone (bắt buộc phải là Safari)
        2. Truy cập URL ngrok của app
        3. Bấm nút **Chia sẻ** (biểu tượng 􀈂 ở giữa thanh dưới)
        4. Kéo xuống → chọn **"Thêm vào màn hình chính"**
        5. Đặt tên **Tiếng Trung** → bấm **Thêm**

        App sẽ xuất hiện trên màn hình chính như app thật, mở toàn màn hình! 🌸
        """)

    st.markdown("### 📚 Hướng dẫn sử dụng")
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("""
        - **📘 HSK 2** — Bài tập 261 từ vựng cấp HSK 2 (sơ cấp)
        - **📗 HSK 3** — Bài tập 306 từ vựng cấp HSK 3 (trung sơ cấp)
        - **📕 HSK 4** — Bài tập 652 từ vựng cấp HSK 4 (trung cấp)
        - **📋 Danh sách từ** — Xem toàn bộ từ, lọc theo cấp HSK
        """)
    with col_b:
        st.markdown("""
        - **🈯 Dịch câu** — Dịch Việt → Trung hoặc Trung → Việt bằng AI
        - **✍️ Đặt câu & Kiểm tra ngữ pháp** — AI kiểm tra câu tiếng Trung
        - Mỗi trang HSK có 2 tab: **Ôn 10 từ** + **Đặt 10 câu**
        - Hệ thống dùng thuật toán **SM-2** lên lịch ôn tập tự động
        """)


# ============================================================
# HSK 2 / 3 / 4 — Trang luyện tập theo cấp độ
# ============================================================

HSK_PAGES = {
    "📘 HSK 2 — Sơ cấp": ("HSK2", "📘 HSK 2 — Sơ cấp", "Trình độ HSK 2: từ vựng & câu nền tảng đời sống hằng ngày."),
    "📗 HSK 3 — Trung sơ cấp": ("HSK3", "📗 HSK 3 — Trung sơ cấp", "Trình độ HSK 3: mở rộng giao tiếp, học tập, công việc."),
    "📕 HSK 4 — Trung cấp": ("HSK4", "📕 HSK 4 — Trung cấp", "Trình độ HSK 4: từ vựng nâng cao, xã hội & học thuật."),
}

if page in HSK_PAGES:
    import random

    level, title, subtitle = HSK_PAGES[page]
    st.markdown(f"# {title}")
    st.caption(subtitle)
    st.markdown("---")

    s = get_stats(level)
    m1, m2, m3 = st.columns(3)
    m1.metric("🗂️ Tổng từ", s["total"])
    m2.metric("📅 Cần ôn", s["due"])
    m3.metric("✅ Đã học", s["learned"])

    tab1, tab2 = st.tabs(["📖 Ôn 10 từ", "✍️ Đặt 10 câu"])

    # ----------------------------------------------------------
    # TAB 1: ÔN 10 TỪ — chỉ trong cấp HSK hiện tại
    # ----------------------------------------------------------
    with tab1:
        st.markdown(f"### 📖 Ôn 10 từ {level} — Điền nghĩa tiếng Việt")
        st.markdown("Nhìn vào chữ Hán và pinyin, điền nghĩa tiếng Việt vào ô bên cạnh.")

        all_words = get_all_words(level)
        session_key = f"vocab_session_{level}"
        submitted_key = f"vocab_submitted_{level}"
        results_key = f"vocab_results_{level}"

        if len(all_words) == 0:
            st.info(f"Chưa có từ nào ở cấp {level}.")
        else:
            if session_key not in st.session_state or st.button("🔄 Lấy 10 từ mới", key=f"refresh_vocab_{level}"):
                due = get_due_words(level)
                pool = due if len(due) >= 10 else all_words
                st.session_state[session_key] = random.sample(pool, min(10, len(pool)))
                st.session_state[submitted_key] = False
                st.session_state[results_key] = {}
                st.rerun()

            words_today = st.session_state[session_key]
            submitted = st.session_state.get(submitted_key, False)

            if not submitted:
                with st.form(f"vocab_form_{level}"):
                    for i, w in enumerate(words_today):
                        col_word, col_spk, col_input = st.columns([2, 1, 3])
                        with col_word:
                            st.markdown(f"""
                            <div style='background:#fce4ec;border-radius:10px;padding:10px 14px;margin:4px 0'>
                                <span style='font-size:28px;color:#c2185b;font-weight:bold'>{w['hanzi']}</span>
                                <span style='color:#e91e8c;margin-left:10px'>{w['pinyin']}</span>
                            </div>
                            """, unsafe_allow_html=True)
                        with col_spk:
                            tts_button(w['hanzi'])
                        with col_input:
                            st.text_input(
                                f"Nghĩa #{i+1}",
                                key=f"ans_{level}_{w['id']}",
                                placeholder="Nhập nghĩa tiếng Việt...",
                                label_visibility="collapsed"
                            )

                    submit_btn = st.form_submit_button("✅ Kiểm tra kết quả", use_container_width=True)

                if submit_btn:
                    results = {}
                    pairs = []
                    for w in words_today:
                        user_ans = st.session_state.get(f"ans_{level}_{w['id']}", "").strip().lower()
                        correct = w["meaning"].lower()
                        keywords = [k.strip() for k in correct.replace(",", "/").split("/")]
                        is_correct = bool(user_ans) and any(
                            k in user_ans or user_ans in k for k in keywords if k
                        )
                        results[w["id"]] = {
                            "user": st.session_state.get(f"ans_{level}_{w['id']}", "").strip(),
                            "correct": w["meaning"],
                            "is_correct": is_correct,
                            "hanzi": w["hanzi"],
                            "pinyin": w["pinyin"],
                        }
                        pairs.append((w["id"], 5 if is_correct else 1))
                    batch_update_reviews(pairs)
                    st.session_state[results_key] = results
                    st.session_state[submitted_key] = True
                    st.rerun()

            else:
                results = st.session_state[results_key]
                correct_count = sum(1 for r in results.values() if r["is_correct"])
                total = len(results)
                score_pct = correct_count / total * 100

                if score_pct == 100:
                    st.balloons()
                    st.success(f"🎊 Xuất sắc! Mai Hương đúng **{correct_count}/{total}** từ {level}!")
                elif score_pct >= 70:
                    st.success(f"👏 Tốt lắm! Mai Hương đúng **{correct_count}/{total}** từ {level}!")
                else:
                    st.warning(f"💪 Cố lên! Mai Hương đúng **{correct_count}/{total}** từ {level}. Luyện thêm nhé!")

                st.progress(score_pct / 100)
                st.markdown("---")
                st.markdown("#### Kết quả chi tiết:")

                for r in results.values():
                    icon = "✅" if r["is_correct"] else "❌"
                    bg = "#e8f5e9" if r["is_correct"] else "#fce4ec"
                    border = "#66bb6a" if r["is_correct"] else "#e91e8c"
                    rc1, rc2 = st.columns([6, 1])
                    with rc1:
                        st.markdown(f"""
                        <div style='background:{bg};border-left:4px solid {border};border-radius:0 10px 10px 0;padding:10px 16px;margin:6px 0'>
                            {icon} <strong style='font-size:20px;color:#c2185b'>{r['hanzi']}</strong>
                            <span style='color:#e91e8c;margin-left:8px'>{r['pinyin']}</span><br>
                            <span style='color:#555'>Bạn trả lời: <em>{r['user'] or '(để trống)'}</em></span><br>
                            <span style='color:#2e7d32'><strong>Đáp án: {r['correct']}</strong></span>
                        </div>
                        """, unsafe_allow_html=True)
                    with rc2:
                        tts_button(r['hanzi'])

                if st.button("🔄 Làm lại với 10 từ mới", use_container_width=True, key=f"redo_vocab_{level}"):
                    due = get_due_words(level)
                    pool = due if len(due) >= 10 else get_all_words(level)
                    st.session_state[session_key] = random.sample(pool, min(10, len(pool)))
                    st.session_state[submitted_key] = False
                    st.session_state[results_key] = {}
                    st.rerun()

    # ----------------------------------------------------------
    # TAB 2: ĐẶT 10 CÂU — chủ đề và yêu cầu phù hợp cấp HSK
    # ----------------------------------------------------------
    with tab2:
        st.markdown(f"### ✍️ Đặt 10 câu {level}")
        st.markdown(f"Đặt câu tiếng Trung theo chủ đề bên dưới, dùng từ vựng cấp **{level}**, AI sẽ kiểm tra ngữ pháp.")

        topics_by_level = {
            "HSK2": [
                "Giới thiệu bản thân",
                "Gia đình của bạn",
                "Sở thích của bạn",
                "Hoạt động hằng ngày",
                "Thời tiết hôm nay",
                "Món ăn bạn thích",
                "Bạn của bạn",
                "Số đếm và thời gian",
                "Mua sắm cơ bản",
                "Cảm xúc hôm nay",
            ],
            "HSK3": [
                "Mô tả công việc / trường lớp của bạn",
                "Một kỷ niệm đáng nhớ",
                "Kế hoạch cuối tuần và lý do",
                "So sánh hai địa điểm bạn từng đến",
                "Thói quen tốt và thói quen xấu",
                "Mô tả tính cách của một người",
                "Một vấn đề bạn từng giải quyết",
                "Sở thích nấu ăn / món ăn yêu thích",
                "Lời khuyên cho người mới học tiếng Trung",
                "Mục tiêu trong năm nay",
            ],
            "HSK4": [
                "Quan điểm của bạn về mạng xã hội",
                "Lợi ích và hạn chế của làm việc từ xa",
                "So sánh cuộc sống thành thị và nông thôn",
                "Ảnh hưởng của công nghệ đến giáo dục",
                "Kể lại một sự kiện quan trọng trong đời",
                "Bạn nghĩ gì về biến đổi khí hậu?",
                "Ưu nhược điểm của du học",
                "Mô tả văn hoá truyền thống bạn yêu thích",
                "Cách giảm áp lực trong cuộc sống",
                "Bạn nghĩ thành công là gì?",
            ],
        }
        topics_key = f"sentence_topics_{level}"
        results_sk = f"sentence_grammar_results_{level}"

        if topics_key not in st.session_state:
            st.session_state[topics_key] = topics_by_level[level].copy()
        if results_sk not in st.session_state:
            st.session_state[results_sk] = {}

        for i, topic in enumerate(st.session_state[topics_key]):
            col_topic, col_check = st.columns([3, 1])

            with col_topic:
                st.markdown(f"**{i+1}. {topic}**")
                user_sentence = st.text_input(
                    f"Câu {i+1}",
                    key=f"sent_{level}_{i}",
                    placeholder="Viết câu tiếng Trung của bạn...",
                    label_visibility="collapsed"
                )

            with col_check:
                st.markdown("<div style='margin-top:24px'></div>", unsafe_allow_html=True)
                if st.button("🔍 Kiểm tra", key=f"check_{level}_{i}", use_container_width=True):
                    if not user_sentence.strip():
                        st.warning("Hãy nhập câu trước nhé!")
                    elif not _gemini_key:
                        st.error("Chưa có Gemini API Key — chạy lại start.py để nhập.")
                    else:
                        with st.spinner("Đang kiểm tra..."):
                            prompt = f"""Kiểm tra ngữ pháp câu tiếng Trung sau (cấp độ {level}, chủ đề: {topic}):

"{user_sentence}"

Phân tích ngắn gọn:
1. Đúng/Sai ngữ pháp?
2. Nếu sai: chỉ lỗi + câu đúng
3. Câu này có phù hợp trình độ {level} không? (gợi ý từ vựng/ngữ pháp {level} có thể dùng thêm)
4. Nhận xét 1-2 dòng (khuyến khích người học)

Trả lời bằng tiếng Việt, ngắn gọn."""
                            try:
                                st.session_state[results_sk][i] = ask_gemini(prompt)
                            except Exception as e:
                                st.session_state[results_sk][i] = f"Lỗi: {e}"

            if i in st.session_state[results_sk]:
                result_text = st.session_state[results_sk][i]
                st.markdown(f'<div class="ai-result">{_ai_html(result_text)}</div>', unsafe_allow_html=True)

            st.markdown("<hr style='border:1px solid #f8bbd0;margin:8px 0'>", unsafe_allow_html=True)

        if st.button("🔄 Làm lại (xóa câu đã viết)", use_container_width=True, key=f"reset_sentences_{level}"):
            for i in range(10):
                if f"sent_{level}_{i}" in st.session_state:
                    del st.session_state[f"sent_{level}_{i}"]
            st.session_state[results_sk] = {}
            st.rerun()


# ============================================================
# DANH SÁCH TỪ
# ============================================================
elif page == "📋 Danh sách từ":
    st.markdown("# 📋 Danh sách từ vựng")
    st.markdown("---")

    level_filter = st.radio(
        "Lọc theo cấp độ:",
        ["Tất cả", "HSK 2", "HSK 3", "HSK 4"],
        horizontal=True
    )
    level_map = {"Tất cả": None, "HSK 2": "HSK2", "HSK 3": "HSK3", "HSK 4": "HSK4"}
    words = get_all_words(level_map[level_filter])

    if not words:
        st.info("Chưa có từ nào ở cấp này.")
    else:
        search = st.text_input("🔍 Tìm kiếm", placeholder="Nhập chữ Hán, pinyin hoặc nghĩa...")
        if search:
            words = [w for w in words if
                     search.lower() in w["hanzi"].lower() or
                     search.lower() in w["pinyin"].lower() or
                     search.lower() in w["meaning"].lower()]

        st.markdown(f"**{len(words)} từ**")
        for w in words:
            badge = f"`{w.get('hsk_level', '?')}`"
            with st.expander(f"{badge} **{w['hanzi']}** ({w['pinyin']}) — {w['meaning']}"):
                tts_button(w['hanzi'])
                if w["example_zh"]:
                    st.write(f"Ví dụ: *{w['example_zh']}*")
                if w["example_vn"]:
                    st.write(f"Nghĩa: *{w['example_vn']}*")
                st.write(f"Ôn tiếp theo: `{w['next_review'][:10]}`  |  Đã ôn: `{w['repetitions']} lần`  |  Chu kỳ: `{w['interval']} ngày`")
                if st.button("🗑️ Xóa", key=f"del_{w['id']}"):
                    delete_word(w["id"])
                    st.rerun()


# ============================================================
# DỊCH CÂU
# ============================================================
elif page == "🈯 Dịch câu":
    st.markdown("# 🈯 Dịch câu")
    st.markdown("---")

    direction = st.radio("Chiều dịch:", ["🇻🇳 Việt → 🇨🇳 Trung", "🇨🇳 Trung → 🇻🇳 Việt"], horizontal=True)

    if direction == "🇻🇳 Việt → 🇨🇳 Trung":
        placeholder = "Nhập câu tiếng Việt cần dịch..."
        lang_hint = "Dịch câu tiếng Việt sau sang tiếng Trung (cung cấp: chữ Hán, pinyin, và giải thích ngắn):"
    else:
        placeholder = "Nhập câu tiếng Trung cần dịch... (e.g. 我喜欢学习汉语)"
        lang_hint = "Dịch câu tiếng Trung sau sang tiếng Việt (cung cấp: bản dịch tiếng Việt, pinyin của câu gốc, và giải thích ngắn về từ quan trọng):"

    text_input = st.text_area("Nhập câu cần dịch:", placeholder=placeholder, height=100)

    if st.button("🌸 Dịch ngay", use_container_width=True):
        if not text_input.strip():
            st.warning("Vui lòng nhập câu cần dịch.")
        elif not _gemini_key:
            st.error("Chưa có Gemini API Key — chạy lại start.py để nhập.")
        else:
            with st.spinner("Đang dịch..."):
                prompt = f"""{lang_hint}

"{text_input}"

Trả lời bằng tiếng Việt, rõ ràng và dễ hiểu cho người học tiếng Trung."""
                try:
                    st.markdown(f'<div class="ai-result">{_ai_html(ask_gemini(prompt))}</div>', unsafe_allow_html=True)
                except Exception as e:
                    st.error(f"Lỗi: {e}")


# ============================================================
# ĐẶT CÂU & KIỂM TRA NGỮ PHÁP
# ============================================================
elif page == "✍️ Đặt câu & Kiểm tra ngữ pháp":
    st.markdown("# ✍️ Đặt câu & Kiểm tra ngữ pháp")
    st.markdown("---")

    st.markdown("Nhập một câu tiếng Trung — AI sẽ kiểm tra ngữ pháp, chỉ ra lỗi và gợi ý cách viết đúng.")

    user_sentence = st.text_area(
        "Câu tiếng Trung của Mai Hương:",
        placeholder="e.g. 我很喜欢吃越南食物。",
        height=100
    )

    topic = st.text_input(
        "Chủ đề muốn đặt câu (không bắt buộc):",
        placeholder="e.g. gia đình, du lịch, thức ăn..."
    )

    col1, col2 = st.columns(2)

    with col1:
        if st.button("🔍 Kiểm tra ngữ pháp", use_container_width=True):
            if not user_sentence.strip():
                st.warning("Vui lòng nhập câu cần kiểm tra.")
            elif not _gemini_key:
                st.error("Chưa có Gemini API Key — chạy lại start.py để nhập.")
            else:
                with st.spinner("Đang kiểm tra..."):
                    prompt = f"""Hãy kiểm tra ngữ pháp câu tiếng Trung sau của một người học tiếng Trung tên Mai Hương:

"{user_sentence}"

Hãy phân tích:
1. Câu này đúng hay sai ngữ pháp?
2. Nếu sai, chỉ ra lỗi cụ thể và giải thích tại sao
3. Đưa ra câu đúng (nếu cần sửa)
4. Giải thích cấu trúc ngữ pháp được dùng
5. Gợi ý câu tương tự để luyện tập

Trả lời bằng tiếng Việt, thân thiện và khuyến khích người học."""
                    try:
                        st.markdown(f'<div class="ai-result">{_ai_html(ask_gemini(prompt))}</div>', unsafe_allow_html=True)
                    except Exception as e:
                        st.error(f"Lỗi: {e}")

    with col2:
        if st.button("💡 Gợi ý câu mẫu", use_container_width=True):
            if not _gemini_key:
                st.error("Chưa có Gemini API Key — chạy lại start.py để nhập.")
            else:
                with st.spinner("Đang tạo câu mẫu..."):
                    topic_text = f"về chủ đề: {topic}" if topic else "về chủ đề thông dụng hàng ngày"
                    prompt = f"""Hãy tạo 5 câu tiếng Trung mẫu {topic_text} phù hợp cho người học trung cấp.

Với mỗi câu, cung cấp:
- Câu tiếng Trung (chữ Hán)
- Pinyin
- Nghĩa tiếng Việt
- Ghi chú ngữ pháp ngắn (nếu có điểm đáng chú ý)

Trình bày rõ ràng, dễ học."""
                    try:
                        st.markdown(f'<div class="ai-result">{_ai_html(ask_gemini(prompt))}</div>', unsafe_allow_html=True)
                    except Exception as e:
                        st.error(f"Lỗi: {e}")


# ============================================================
# BÀI TẬP LUYỆN TẬP
# ============================================================
elif page == "📝 Bài tập luyện tập":
    import random as _rnd

    st.markdown("# 📝 Bài tập luyện tập")
    st.markdown("---")

    ex_level = st.radio("Cấp độ:", ["HSK2", "HSK3", "HSK4"], horizontal=True, key="ex_lvl")
    all_ex = get_all_words(ex_level)

    if len(all_ex) < 4:
        st.info(f"Cần ít nhất 4 từ ở cấp {ex_level}.")
    else:
        tab_fill, tab_mc, tab_match = st.tabs([
            "✏️ Điền từ vào chỗ trống",
            "🔤 Chọn đáp án đúng",
            "🔗 Ghép từ với nghĩa",
        ])

        def _show_score(n_ok, total):
            pct = n_ok / total
            if pct == 1:
                st.balloons()
                st.success(f"🎊 Xuất sắc! Mai Hương đúng **{n_ok}/{total}**!")
            elif pct >= 0.7:
                st.success(f"👏 Tốt lắm! **{n_ok}/{total}** câu đúng!")
            else:
                st.warning(f"💪 Cố lên! **{n_ok}/{total}** câu đúng. Luyện thêm nhé!")
            st.progress(pct)
            st.markdown("---")

        def _result_card(icon, bg, border, hanzi, pinyin, label_u, user_val, label_c, correct_val):
            col_card, col_spk = st.columns([11, 1])
            with col_card:
                st.markdown(f"""
                <div style='background:{bg};border-left:4px solid {border};
                            border-radius:0 10px 10px 0;padding:10px 16px;margin:6px 0'>
                    {icon} <strong style='font-size:20px;color:#c2185b'>{hanzi}</strong>
                    <span style='color:#e91e8c;margin-left:8px'>{pinyin}</span><br>
                    <span style='color:#555'>{label_u}: <em>{user_val or "(để trống)"}</em></span><br>
                    <span style='color:#2e7d32'><strong>{label_c}: {correct_val}</strong></span>
                </div>
                """, unsafe_allow_html=True)
            with col_spk:
                tts_button(hanzi)

        # ──────────────────────────────────────────────────────
        # TAB 1: ĐIỀN TỪ VÀO CHỖ TRỐNG
        # ──────────────────────────────────────────────────────
        with tab_fill:
            st.markdown("### ✏️ Điền từ vào chỗ trống")
            st.caption("Đọc nghĩa tiếng Việt và pinyin gợi ý → điền chữ Hán đúng.")

            WF = f"fw_{ex_level}"; SF = f"fs_{ex_level}"; RF = f"fr_{ex_level}"

            if WF not in st.session_state or st.button("🔄 Bài mới", key=f"fn_{ex_level}"):
                st.session_state[WF] = _rnd.sample(all_ex, min(10, len(all_ex)))
                st.session_state[SF] = False
                st.session_state[RF] = {}
                st.rerun()

            fw = st.session_state[WF]

            if not st.session_state.get(SF, False):
                with st.form(f"fill_{ex_level}"):
                    for i, w in enumerate(fw):
                        c1, c2 = st.columns([3, 2])
                        with c1:
                            st.markdown(f"""
                            <div style='background:#fce4ec;border-radius:10px;padding:10px 14px;margin:4px 0'>
                                <span style='color:#880e4f'><strong>{i+1}. {w['meaning']}</strong></span><br>
                                <span style='color:#e91e8c;font-size:13px'>🔤 {w['pinyin']}</span>
                            </div>
                            """, unsafe_allow_html=True)
                        with c2:
                            st.text_input("_", key=f"fa_{ex_level}_{w['id']}",
                                          placeholder="Nhập chữ Hán...",
                                          label_visibility="collapsed")
                    btn_f = st.form_submit_button("✅ Kiểm tra kết quả", use_container_width=True)

                if btn_f:
                    res = {}
                    for w in fw:
                        ans = st.session_state.get(f"fa_{ex_level}_{w['id']}", "").strip()
                        res[w['id']] = {"hanzi": w['hanzi'], "pinyin": w['pinyin'],
                                        "meaning": w['meaning'], "user": ans,
                                        "ok": ans == w['hanzi']}
                    st.session_state[RF] = res
                    st.session_state[SF] = True
                    st.rerun()

            else:
                res = st.session_state[RF]
                _show_score(sum(r['ok'] for r in res.values()), len(res))
                for r in res.values():
                    icon = "✅" if r['ok'] else "❌"
                    bg = "#e8f5e9" if r['ok'] else "#fce4ec"
                    border = "#66bb6a" if r['ok'] else "#e91e8c"
                    _result_card(icon, bg, border, r['hanzi'], r['pinyin'],
                                 "Bạn điền", r['user'], "Đáp án", r['hanzi'])
                if st.button("🔄 Làm lại", key=f"fr_redo_{ex_level}", use_container_width=True):
                    st.session_state[WF] = _rnd.sample(all_ex, min(10, len(all_ex)))
                    st.session_state[SF] = False
                    st.session_state[RF] = {}
                    st.rerun()

        # ──────────────────────────────────────────────────────
        # TAB 2: CHỌN ĐÁP ÁN ĐÚNG
        # ──────────────────────────────────────────────────────
        with tab_mc:
            st.markdown("### 🔤 Chọn đáp án đúng")
            st.caption("Nhìn chữ Hán và pinyin → chọn nghĩa tiếng Việt đúng trong 4 đáp án.")

            WM = f"mw_{ex_level}"; SM = f"ms_{ex_level}"; RM = f"mr_{ex_level}"; OM = f"mo_{ex_level}"

            if WM not in st.session_state or st.button("🔄 Bài mới", key=f"mn_{ex_level}"):
                batch = _rnd.sample(all_ex, min(10, len(all_ex)))
                st.session_state[WM] = batch
                st.session_state[SM] = False
                st.session_state[RM] = {}
                opts_map = {}
                for w in batch:
                    wrong_pool = [x for x in all_ex if x['id'] != w['id']]
                    wrongs = _rnd.sample(wrong_pool, min(3, len(wrong_pool)))
                    opts = [w['meaning']] + [x['meaning'] for x in wrongs]
                    _rnd.shuffle(opts)
                    opts_map[w['id']] = opts
                st.session_state[OM] = opts_map
                st.rerun()

            mw = st.session_state[WM]
            opts_map = st.session_state.get(OM, {})

            if not st.session_state.get(SM, False):
                with st.form(f"mc_{ex_level}"):
                    for i, w in enumerate(mw):
                        col_h, col_spk = st.columns([8, 1])
                        with col_h:
                            st.markdown(f"""
                            <div style='background:#fce4ec;border-radius:10px;padding:10px 16px;margin:8px 0'>
                                <span style='font-size:30px;color:#c2185b;font-weight:bold'>{w['hanzi']}</span>
                                <span style='color:#e91e8c;margin-left:10px;font-size:16px'>{w['pinyin']}</span>
                            </div>
                            """, unsafe_allow_html=True)
                        with col_spk:
                            st.markdown("<div style='margin-top:14px'></div>", unsafe_allow_html=True)
                            tts_button(w['hanzi'])
                        opts = opts_map.get(w['id'], [w['meaning']])
                        st.radio("_", options=opts, key=f"mc_{ex_level}_{w['id']}",
                                 label_visibility="collapsed")
                        st.markdown("<hr style='border:1px solid #f8bbd0;margin:4px 0'>",
                                    unsafe_allow_html=True)
                    btn_m = st.form_submit_button("✅ Kiểm tra kết quả", use_container_width=True)

                if btn_m:
                    res2 = {}
                    for w in mw:
                        chosen = st.session_state.get(f"mc_{ex_level}_{w['id']}", "")
                        res2[w['id']] = {"hanzi": w['hanzi'], "pinyin": w['pinyin'],
                                         "correct": w['meaning'], "user": chosen,
                                         "ok": chosen == w['meaning']}
                    st.session_state[RM] = res2
                    st.session_state[SM] = True
                    st.rerun()

            else:
                res2 = st.session_state[RM]
                _show_score(sum(r['ok'] for r in res2.values()), len(res2))
                for r in res2.values():
                    icon = "✅" if r['ok'] else "❌"
                    bg = "#e8f5e9" if r['ok'] else "#fce4ec"
                    border = "#66bb6a" if r['ok'] else "#e91e8c"
                    _result_card(icon, bg, border, r['hanzi'], r['pinyin'],
                                 "Bạn chọn", r['user'], "Đáp án", r['correct'])
                if st.button("🔄 Làm lại", key=f"mc_redo_{ex_level}", use_container_width=True):
                    del st.session_state[WM]
                    st.rerun()

        # ──────────────────────────────────────────────────────
        # TAB 3: GHÉP TỪ VỚI NGHĨA
        # ──────────────────────────────────────────────────────
        with tab_match:
            st.markdown("### 🔗 Ghép từ với nghĩa")
            st.caption("Chọn nghĩa tiếng Việt đúng cho từng chữ Hán trong danh sách.")

            WG = f"gw_{ex_level}"; SG = f"gs_{ex_level}"; RG = f"gr_{ex_level}"; MG = f"gml_{ex_level}"

            if WG not in st.session_state or st.button("🔄 Bài mới", key=f"gn_{ex_level}"):
                batch3 = _rnd.sample(all_ex, min(8, len(all_ex)))
                st.session_state[WG] = batch3
                st.session_state[SG] = False
                st.session_state[RG] = {}
                meanings = [w['meaning'] for w in batch3]
                _rnd.shuffle(meanings)
                st.session_state[MG] = meanings
                st.rerun()

            gw = st.session_state[WG]
            gm = st.session_state.get(MG, [])

            if not st.session_state.get(SG, False):
                with st.form(f"match_{ex_level}"):
                    st.markdown("**Chọn nghĩa đúng cho từng từ:**")
                    choices = ["— Chọn nghĩa —"] + gm
                    for i, w in enumerate(gw):
                        c_w, c_s, c_sel = st.columns([2, 1, 4])
                        with c_w:
                            st.markdown(f"""
                            <div style='background:#fce4ec;border-radius:10px;
                                        padding:8px 12px;margin:4px 0;text-align:center'>
                                <span style='font-size:24px;color:#c2185b;font-weight:bold'>{w['hanzi']}</span><br>
                                <span style='color:#e91e8c;font-size:12px'>{w['pinyin']}</span>
                            </div>
                            """, unsafe_allow_html=True)
                        with c_s:
                            st.markdown("<div style='margin-top:12px'></div>", unsafe_allow_html=True)
                            tts_button(w['hanzi'])
                        with c_sel:
                            st.markdown("<div style='margin-top:8px'></div>", unsafe_allow_html=True)
                            st.selectbox("_", options=choices,
                                         key=f"gm_{ex_level}_{w['id']}",
                                         label_visibility="collapsed")
                    btn_g = st.form_submit_button("✅ Kiểm tra kết quả", use_container_width=True)

                if btn_g:
                    res3 = {}
                    for w in gw:
                        chosen = st.session_state.get(f"gm_{ex_level}_{w['id']}", "")
                        res3[w['id']] = {"hanzi": w['hanzi'], "pinyin": w['pinyin'],
                                         "correct": w['meaning'], "user": chosen,
                                         "ok": chosen == w['meaning']}
                    st.session_state[RG] = res3
                    st.session_state[SG] = True
                    st.rerun()

            else:
                res3 = st.session_state[RG]
                _show_score(sum(r['ok'] for r in res3.values()), len(res3))
                for r in res3.values():
                    icon = "✅" if r['ok'] else "❌"
                    bg = "#e8f5e9" if r['ok'] else "#fce4ec"
                    border = "#66bb6a" if r['ok'] else "#e91e8c"
                    _result_card(icon, bg, border, r['hanzi'], r['pinyin'],
                                 "Bạn chọn", r['user'], "Đáp án", r['correct'])
                if st.button("🔄 Làm lại", key=f"match_redo_{ex_level}", use_container_width=True):
                    del st.session_state[WG]
                    st.rerun()
