import os
import random
import streamlit as st
from streamlit_float import float_init
from dotenv import load_dotenv
from database import init_db, seed_from_json, search_movies

load_dotenv()
init_db()
if not os.path.exists(os.path.join(os.path.dirname(__file__), "movies.db")):
    seed_from_json(os.path.join(os.path.dirname(__file__), "movies.json"))

POSTER_DIR = os.path.join(os.path.dirname(__file__), "..", "posters")

# ── Page config ───────────────────────────────────────────────────
st.set_page_config(
    page_title="🎬 Movie House",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="collapsed",
)

float_init(theme=False)

# ── Global styles ─────────────────────────────────────────────────
st.markdown("""
<style>
/* App background */
[data-testid="stAppViewContainer"] { background: #0d0d14; }
[data-testid="stSidebar"]          { background: #15151f; }
[data-testid="stHeader"]           { background: transparent; }

/* Hide Streamlit default top padding */
.block-container { padding-top: 2rem !important; }

/* Movie titles & text — 字體加大 */
h1, h2, h3 { color: #fff !important; }
h1          { font-size: 2.4rem !important; }
h2          { font-size: 1.6rem !important; }
h3          { font-size: 1.25rem !important; }
p, label, div, span { font-size: 1.05rem !important; color: #d4d8e2 !important; }

/* 小標 subtitle 加大一點 */
[data-testid="stMarkdownContainer"] p {
  font-size: 1.08rem !important;
  line-height: 1.65 !important;
}

/* Card title */
.card-title {
  font-size: 1rem; font-weight: 600; color: #fff;
  padding: 6px 4px 2px; line-height: 1.4; min-height: 2.6em;
  display: -webkit-box; -webkit-line-clamp: 2;
  -webkit-box-orient: vertical; overflow: hidden;
}
.card-meta  { font-size: .85rem; color: #9ca3af; padding: 0 4px 6px; }
.score-tag  { color: #fbbf24; font-weight: 700; }

/* ── Floating chat widget ── */
.chat-float-wrap {
  background: #15151f;
  border: 1px solid rgba(255,255,255,.08);
  border-radius: 20px;
  box-shadow: 0 20px 60px rgba(0,0,0,.55);
  overflow: hidden;
}
.chat-header {
  display: flex; align-items: center; gap: 10px;
  padding: 13px 16px;
  border-bottom: 1px solid rgba(255,255,255,.07);
  background: #1a1a2e;
}
.chat-bot-av {
  width: 48px; height: 48px; border-radius: 50%;
  background: linear-gradient(135deg, #6c63ff, #48cfad);
  display: flex; align-items: center; justify-content: center;
  font-size: 26px; flex-shrink: 0;
}
.chat-header-info h4 { margin: 0; font-size: .88rem; color: #fff !important; }
.chat-header-info p  { margin: 0; font-size: .7rem;  color: #48cfad !important; }
.online-dot {
  width: 8px; height: 8px; border-radius: 50%;
  background: #34d399; box-shadow: 0 0 6px #34d399;
  margin-left: auto;
}

/* Chat bubbles inside the float widget */
.chat-messages { padding: 12px 14px; max-height: 280px; overflow-y: auto; }
.bubble-user {
  background: linear-gradient(135deg, #6c63ff, #5a52d5);
  color: #fff; border-radius: 16px 16px 4px 16px;
  padding: 9px 13px; margin: 6px 0 6px auto;
  max-width: 82%; font-size: .84rem; line-height: 1.5;
  display: table; margin-left: auto;
}
.bubble-bot {
  background: #1e1e30; color: #d4d8e2;
  border: 1px solid rgba(255,255,255,.06);
  border-radius: 16px 16px 16px 4px;
  padding: 9px 13px; margin: 6px auto 6px 0;
  max-width: 82%; font-size: .84rem; line-height: 1.5;
  display: table;
}

/* Toggle button */
div[data-testid="stButton"] > button[kind="primary"] {
  background: linear-gradient(135deg, #6c63ff, #48cfad) !important;
  border: none !important;
  border-radius: 50% !important;
  width: 72px !important; height: 72px !important;
  font-size: 38px !important;
  box-shadow: 0 6px 28px rgba(108,99,255,.5) !important;
  padding: 0 !important;
  line-height: 1 !important;
}

/* Stacked input look */
[data-testid="stTextInput"] input {
  background: #1c1c2a !important;
  border: 1px solid rgba(255,255,255,.08) !important;
  color: #d4d8e2 !important;
  border-radius: 10px !important;
}
[data-testid="stTextInput"] input:focus {
  border-color: #6c63ff !important;
  box-shadow: 0 0 0 2px rgba(108,99,255,.2) !important;
}

/* Sidebar API key section */
[data-testid="stSidebar"] h2 { color: #fff !important; }
[data-testid="stSidebar"] p  { color: #9ca3af !important; }
</style>
""", unsafe_allow_html=True)

# ── Session state defaults ─────────────────────────────────────────
if "chat_open"  not in st.session_state: st.session_state.chat_open  = False
if "messages"   not in st.session_state:
    st.session_state.messages = [{"role": "bot", "text": "您好！我是 Movie Bot 🎬 請問想找什麼電影？"}]
if "api_key"    not in st.session_state: st.session_state.api_key    = ""
if "gemini_ok"  not in st.session_state: st.session_state.gemini_ok  = False
if "selected"   not in st.session_state: st.session_state.selected   = None

# ── Sidebar: API Key settings only ────────────────────────────────
with st.sidebar:
    st.markdown("## ⚙️ 設定")
    st.markdown("---")
    st.markdown("**Gemini API Key**")
    st.markdown("<p style='font-size:.8rem'>在 aistudio.google.com 免費取得</p>", unsafe_allow_html=True)

    key_input = st.text_input(
        "API Key",
        value="",                       # 空白，讓使用者自行填入
        type="password",
        placeholder="貼上您的 API Key…",
        label_visibility="collapsed",
    )
    if st.button("套用", use_container_width=True):
        if key_input.strip():
            st.session_state.api_key   = key_input.strip()
            st.session_state.gemini_ok = False   # re-validate on next use
            st.success("✅ 已儲存")
        else:
            st.error("請填入 API Key")

    if st.session_state.api_key:
        st.markdown(
            f"<p style='font-size:.75rem;color:#48cfad'>已設定 …{st.session_state.api_key[-6:]}</p>",
            unsafe_allow_html=True,
        )

# ── Gemini helper ─────────────────────────────────────────────────
all_movies   = search_movies()
MOVIE_LIST   = "\n".join(
    f"{m['id']}. {m['name_tw']}｜評分:{m['score']}｜{m['category']}"
    for m in all_movies
)
SYSTEM_PROMPT = f"""你是「Movie House」電影網站的專屬助手 Movie Bot。
本網站收錄以下 100 部精選電影：
{MOVIE_LIST}
規則：只能依上述片單回答；詢問片單外電影需說「此片不在我們的收藏清單中」；用繁體中文回答，簡潔2-4句。"""

MODELS   = ["gemini-2.5-flash-lite", "gemini-2.5-flash", "gemini-flash-lite-latest"]
FALLBACK = ["我只能回答本站 100 部電影的問題，請問有什麼可以協助您的嗎？🎬",
            "請問您想找什麼類型的電影？我很樂意從片單中為您推薦！"]


def ask_gemini(question: str) -> str:
    key = st.session_state.get("api_key", "")
    if not key:
        return "⚠️ 請先在左側側欄輸入 Gemini API Key 以啟用 AI 功能。"
    try:
        from google import genai
        from google.genai import types
        client = genai.Client(api_key=key)
        for model in MODELS:
            try:
                resp = client.models.generate_content(
                    model=model,
                    contents=question,
                    config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT),
                )
                return resp.text.strip()
            except Exception as e:
                if "RESOURCE_EXHAUSTED" in str(e) or "UNAVAILABLE" in str(e):
                    continue
                break
    except Exception:
        pass
    return random.choice(FALLBACK)


# ── Main: hero ────────────────────────────────────────────────────
st.markdown("# 🎬 Movie House")
st.markdown("<p style='color:#6b7280;margin-top:-10px'>100 部手選經典電影</p>", unsafe_allow_html=True)

col_s, col_sort, col_cnt = st.columns([3, 2, 1])
with col_s:
    query = st.text_input("search", placeholder="🔍 搜尋電影名稱…", label_visibility="collapsed")
with col_sort:
    sort = st.selectbox("sort", ["預設排序", "評分高→低", "評分低→高", "最新年份"], label_visibility="collapsed")
sort_map = {"預設排序": "id", "評分高→低": "score_desc", "評分低→高": "score_asc", "最新年份": "year_desc"}

movies = search_movies(query, sort_map[sort])
with col_cnt:
    st.markdown(f"<p style='color:#6b7280;padding-top:8px'>{len(movies)} 部</p>", unsafe_allow_html=True)

# ── Detail expander ────────────────────────────────────────────────
if st.session_state.selected:
    m = st.session_state.selected
    with st.expander(f"📽 {m['name_tw']}", expanded=True):
        c1, c2 = st.columns([1, 2])
        with c1:
            p = os.path.join(POSTER_DIR, m["poster_file"])
            if os.path.exists(p):
                st.image(p, use_container_width=True)
        with c2:
            st.markdown(f"### {m['name_tw']}")
            st.markdown(f"⭐ **{m['score']}**　🎭 {m['category']}")
            st.markdown(f"📅 {m['release']}　⏱ {m['duration']}")
        if st.button("✕ 關閉"):
            st.session_state.selected = None
            st.rerun()

# ── Movie grid ────────────────────────────────────────────────────
COLS = 5
for i in range(0, len(movies), COLS):
    row  = movies[i: i + COLS]
    cols = st.columns(COLS)
    for col, m in zip(cols, row):
        with col:
            p = os.path.join(POSTER_DIR, m["poster_file"])
            if os.path.exists(p):
                st.image(p, use_container_width=True)
            st.markdown(
                f'<div class="card-title">{m["name_tw"]}</div>'
                f'<div class="card-meta"><span class="score-tag">★ {m["score"]}</span>　'
                f'{(m["category"] or "").split("/")[0].strip()}</div>',
                unsafe_allow_html=True,
            )
            if st.button("詳情", key=f"d_{m['id']}"):
                st.session_state.selected = m
                st.rerun()

if not movies:
    st.info("找不到符合的電影，請嘗試其他關鍵字。")

# ── Floating chat widget (bottom-right) ───────────────────────────
chat_float = st.container()
with chat_float:
    if st.session_state.chat_open:
        # Chat panel
        msgs_html = "".join(
            f'<div class="bubble-{"user" if m["role"]=="user" else "bot"}">{m["text"]}</div>'
            for m in st.session_state.messages
        )
        st.markdown(f"""
        <div class="chat-float-wrap">
          <div class="chat-header">
            <div class="chat-bot-av">🤖</div>
            <div class="chat-header-info">
              <h4>Movie Bot</h4>
              <p>{"✅ AI 已連線" if st.session_state.api_key else "請設定 API Key"}</p>
            </div>
            <div class="online-dot"></div>
          </div>
          <div class="chat-messages" id="chat-scroll">{msgs_html}</div>
        </div>
        """, unsafe_allow_html=True)

        user_input = st.text_input(
            "chat_input", placeholder="輸入訊息…",
            label_visibility="collapsed", key="chat_text_input",
        )
        c1, c2 = st.columns([5, 1])
        with c1:
            send = st.button("送出", use_container_width=True)
        with c2:
            if st.button("✕"):
                st.session_state.chat_open = False
                st.rerun()

        if send and user_input:
            st.session_state.messages.append({"role": "user", "text": user_input})
            with st.spinner(""):
                reply = ask_gemini(user_input)
            st.session_state.messages.append({"role": "bot", "text": reply})
            st.rerun()

    else:
        # Toggle button
        if st.button("🤖", type="primary", key="open_chat"):
            st.session_state.chat_open = True
            st.rerun()

chat_float.float("top: 68px; right: 28px; width: 360px; z-index: 9999;")
