import os
import streamlit as st
from dotenv import load_dotenv
from database import init_db, seed_from_json, search_movies

load_dotenv()
init_db()
if not os.path.exists("movies.db"):
    seed_from_json("movies.json")

# ── Page config ──────────────────────────────────────────────────
st.set_page_config(
    page_title="🎬 Movie House",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
  [data-testid="stAppViewContainer"] { background:#0d0d14; }
  [data-testid="stSidebar"]          { background:#15151f; }
  .movie-card {
    background:#1c1c2a; border:1px solid rgba(255,255,255,.07);
    border-radius:14px; overflow:hidden; cursor:pointer;
    transition:transform .2s;
  }
  .card-title {
    font-size:.85rem; font-weight:600; color:#fff;
    padding:8px 10px 2px; line-height:1.4; min-height:2.6em;
    display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical; overflow:hidden;
  }
  .card-meta  { font-size:.75rem; color:#9ca3af; padding:0 10px 10px; }
  .score-tag  { color:#fbbf24; font-weight:700; }
  .user-msg   { background:#6c63ff; color:#fff; border-radius:16px 16px 4px 16px; padding:10px 14px; margin:4px 0; display:inline-block; max-width:80%; }
  .bot-msg    { background:#1e1e30; color:#d4d8e2; border:1px solid rgba(255,255,255,.07); border-radius:16px 16px 16px 4px; padding:10px 14px; margin:4px 0; display:inline-block; max-width:80%; }
  h1, h2, h3 { color:#fff !important; }
</style>
""", unsafe_allow_html=True)

# ── Gemini init ──────────────────────────────────────────────────
def build_gemini(api_key: str):
    try:
        from google import genai
        from google.genai import types
        client = genai.Client(api_key=api_key)
        return client, types
    except Exception:
        return None, None

POSTER_DIR = os.path.join(os.path.dirname(__file__), "..", "posters")

# ── Sidebar ──────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🤖 Movie Bot")
    st.markdown("---")

    # API Key input
    api_key = st.text_input(
        "Gemini API Key",
        value=os.getenv("GEMINI_API_KEY", ""),
        type="password",
        placeholder="AIzaSy… 或其他格式",
        help="在 aistudio.google.com 免費取得",
    )

    gemini_client, gtypes = (None, None)
    if api_key:
        gemini_client, gtypes = build_gemini(api_key)
        if gemini_client:
            st.success("✅ AI 已連線")
        else:
            st.error("❌ API Key 無效")

    st.markdown("---")
    st.markdown("### 💬 聊天")

    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "bot", "text": "您好！我是 Movie Bot 🎬 請問想找什麼電影？"}
        ]

    # Chat history display
    chat_container = st.container()
    with chat_container:
        for msg in st.session_state.messages:
            if msg["role"] == "user":
                st.markdown(f'<div style="text-align:right"><span class="user-msg">{msg["text"]}</span></div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div><span class="bot-msg">{msg["text"]}</span></div>', unsafe_allow_html=True)

    # Build movie list for system prompt
    all_movies = search_movies()
    MOVIE_LIST = "\n".join(
        f"{m['id']}. {m['name_tw']}｜評分:{m['score']}｜{m['category']}"
        for m in all_movies
    )
    SYSTEM_PROMPT = f"""你是「Movie House」電影網站的專屬助手 Movie Bot。
本網站收錄以下 100 部精選電影：
{MOVIE_LIST}
規則：只能依上述片單回答；詢問片單外電影需說「此片不在我們的收藏清單中」；用繁體中文回答，簡潔2-4句。"""

    MODELS = ["gemini-2.5-flash-lite", "gemini-2.5-flash", "gemini-flash-lite-latest"]
    FALLBACK_REPLIES = [
        "我只能回答本站 100 部電影的問題，請問有什麼可以協助您的嗎？",
        "請問您想找什麼類型的電影？我很樂意從片單中為您推薦！🎬",
    ]

    def ask_gemini(question: str) -> str:
        if not gemini_client:
            return "⚠️ 請先在上方填入 Gemini API Key 以啟用 AI 功能。"
        import random
        for model in MODELS:
            try:
                resp = gemini_client.models.generate_content(
                    model=model,
                    contents=question,
                    config=gtypes.GenerateContentConfig(system_instruction=SYSTEM_PROMPT),
                )
                return resp.text.strip()
            except Exception as e:
                if "RESOURCE_EXHAUSTED" in str(e) or "UNAVAILABLE" in str(e):
                    continue
                break
        return random.choice(FALLBACK_REPLIES)

    user_input = st.chat_input("輸入問題…")
    if user_input:
        st.session_state.messages.append({"role": "user", "text": user_input})
        with st.spinner("思考中…"):
            reply = ask_gemini(user_input)
        st.session_state.messages.append({"role": "bot", "text": reply})
        st.rerun()

# ── Main: Movie grid ─────────────────────────────────────────────
st.markdown("# 🎬 Movie House")
st.markdown("100 部手選經典電影")

col_s, col_sort, col_count = st.columns([3, 2, 1])
with col_s:
    query = st.text_input("", placeholder="🔍 搜尋電影名稱…", label_visibility="collapsed")
with col_sort:
    sort = st.selectbox("", ["預設排序", "評分高→低", "評分低→高", "最新年份"],
                        label_visibility="collapsed")
sort_map = {"預設排序": "id", "評分高→低": "score_desc", "評分低→高": "score_asc", "最新年份": "year_desc"}

movies = search_movies(query, sort_map[sort])
with col_count:
    st.markdown(f"<p style='color:#6b7280;padding-top:8px'>{len(movies)} 部</p>", unsafe_allow_html=True)

# ── Detail modal via session state ───────────────────────────────
if "selected" not in st.session_state:
    st.session_state.selected = None

if st.session_state.selected:
    m = st.session_state.selected
    with st.expander(f"📽 {m['name_tw']}", expanded=True):
        c1, c2 = st.columns([1, 2])
        with c1:
            poster_path = os.path.join(POSTER_DIR, m["poster_file"])
            if os.path.exists(poster_path):
                st.image(poster_path, use_container_width=True)
            else:
                st.markdown("🎬")
        with c2:
            st.markdown(f"### {m['name_tw']}")
            st.markdown(f"**⭐ 評分：** {m['score']}")
            st.markdown(f"**🎭 類型：** {m['category']}")
            st.markdown(f"**📅 上映：** {m['release']}")
            st.markdown(f"**⏱ 片長：** {m['duration']}")
        if st.button("✕ 關閉"):
            st.session_state.selected = None
            st.rerun()

# ── Grid ─────────────────────────────────────────────────────────
COLS = 5
for i in range(0, len(movies), COLS):
    row = movies[i: i + COLS]
    cols = st.columns(COLS)
    for col, m in zip(cols, row):
        with col:
            poster_path = os.path.join(POSTER_DIR, m["poster_file"])
            if os.path.exists(poster_path):
                st.image(poster_path, use_container_width=True)
            else:
                st.markdown("🎬")
            st.markdown(
                f'<div class="card-title">{m["name_tw"]}</div>'
                f'<div class="card-meta"><span class="score-tag">★ {m["score"]}</span>　{(m["category"] or "").split("/")[0].strip()}</div>',
                unsafe_allow_html=True,
            )
            if st.button("詳情", key=f"btn_{m['id']}"):
                st.session_state.selected = m
                st.rerun()

if not movies:
    st.info("找不到符合的電影，請嘗試其他關鍵字。")
