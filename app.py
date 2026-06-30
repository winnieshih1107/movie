import os
import random
from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify, send_from_directory
from google import genai
from google.genai import types

load_dotenv()

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
POSTER_DIR = os.path.join(os.path.dirname(BASE_DIR), "posters")

app = Flask(__name__)

# ── Load movie data ──────────────────────────────────────────────
from database import init_db, seed_from_json, get_all_movies, get_all_categories, to_traditional, get_score_range
init_db()
if not os.path.exists(os.path.join(BASE_DIR, "movies.db")):
    seed_from_json(os.path.join(BASE_DIR, "movies.json"))
MOVIES = get_all_movies()
for _m in MOVIES:
    _m["category_tw"] = to_traditional(_m.get("category", ""))

CATEGORY_OPTIONS = [(c, to_traditional(c)) for c in get_all_categories()]
SCORE_LO, SCORE_HI = get_score_range()

MOVIE_LIST_TEXT = "\n".join(
    f"{m['id']}. {m['name_tw']}｜評分:{m['score']}｜{m['category']}｜{m.get('release','')}"
    for m in MOVIES
)

SYSTEM_PROMPT = f"""你是「Movie House」電影網站的專屬助手，名稱為 Movie Bot。
本網站收錄以下 100 部精選電影（繁體中文名稱）：

{MOVIE_LIST_TEXT}

回答規則：
1. 只能根據以上片單回答問題。
2. 若使用者詢問不在片單內的電影，請明確說明「此片不在我們的收藏清單中」，並建議他們瀏覽網站片單。
3. 回答請使用繁體中文，語氣友善、簡潔（2-4句），可適度加入 emoji。
4. 不可編造片單以外的資訊。
"""

# ── Gemini setup — 多模型自動切換 ─────────────────────────────────
GEMINI_KEY = os.getenv("GEMINI_API_KEY", "")
# 依優先順序嘗試，直到找到可用的
MODEL_CANDIDATES = [
    "gemini-2.5-flash-lite",
    "gemini-2.5-flash",
    "gemini-flash-lite-latest",
    "gemini-flash-latest",
]

gemini_client   = None
active_model    = None   # 快取目前可用的模型

FALLBACK = [
    "您好！我是 Movie Bot 🎬 可以幫您在片單中找到喜歡的電影，請問有什麼需要嗎？",
    "歡迎來到 Movie House！請問您想找什麼類型的電影？😊",
    "我只能回答關於本網站 100 部電影的問題，請問有什麼可以協助您的嗎？",
]

def init_gemini(api_key: str) -> bool:
    global gemini_client, active_model, GEMINI_KEY
    try:
        client = genai.Client(api_key=api_key)
        gemini_client = client
        active_model  = None
        GEMINI_KEY    = api_key
        # persist to .env (best-effort — read-only filesystems like Vercel
        # just keep the key in memory for the life of this process instead)
        try:
            env_path = os.path.join(BASE_DIR, ".env")
            with open(env_path, "w", encoding="utf-8") as f:
                f.write(f"GEMINI_API_KEY={api_key}\n")
        except OSError:
            pass
        print(f"✅ Gemini client ready")
        return True
    except Exception as e:
        print(f"⚠️  Gemini init failed: {e}")
        return False

if GEMINI_KEY:
    init_gemini(GEMINI_KEY)


def call_gemini(message: str) -> str | None:
    """Try each model in order; return text on first success, None on total failure."""
    global active_model

    candidates = ([active_model] + MODEL_CANDIDATES) if active_model else MODEL_CANDIDATES

    for model in candidates:
        try:
            resp = gemini_client.models.generate_content(
                model=model,
                contents=message,
                config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT),
            )
            reply = resp.text.strip()
            if active_model != model:
                print(f"✅ Switched to model: {model}")
                active_model = model
            return reply
        except Exception as e:
            err = str(e)
            if "RESOURCE_EXHAUSTED" in err or "429" in err:
                print(f"⚠️  {model} quota exhausted, trying next…")
                if active_model == model:
                    active_model = None
                continue
            if "UNAVAILABLE" in err or "503" in err:
                print(f"⚠️  {model} unavailable, trying next…")
                continue
            # unexpected error — stop trying
            print(f"❌ {model} error: {err[:120]}")
            return None

    return None   # all models exhausted


def get_reply(message: str) -> str:
    if gemini_client:
        result = call_gemini(message)
        if result:
            return result
        return "⚠️ 目前 AI 服務繁忙或配額已用完，請稍後再試！您可以先瀏覽上方的電影清單 🎬"
    return random.choice(FALLBACK)


# ── Routes ───────────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template(
        "index.html", movies=MOVIES, categories=CATEGORY_OPTIONS,
        score_lo=SCORE_LO, score_hi=SCORE_HI,
    )


@app.route("/poster/<path:filename>")
def poster(filename):
    return send_from_directory(POSTER_DIR, filename)


@app.route("/api/config", methods=["GET"])
def get_config():
    return jsonify({"has_key": bool(GEMINI_KEY), "key_preview": f"...{GEMINI_KEY[-6:]}" if GEMINI_KEY else ""})


@app.route("/api/config", methods=["POST"])
def set_config():
    data = request.get_json(silent=True) or {}
    new_key = data.get("api_key", "").strip()
    if not new_key:
        return jsonify({"ok": False, "error": "API Key 不可為空"}), 400
    ok = init_gemini(new_key)
    if ok:
        return jsonify({"ok": True, "message": "API Key 已儲存並套用 ✅"})
    return jsonify({"ok": False, "error": "Key 無效，請確認後重試"}), 400


@app.route("/chat", methods=["POST"])
def chat():
    data     = request.get_json(silent=True) or {}
    user_msg = data.get("message", "").strip()
    if not user_msg:
        return jsonify({"error": "empty message"}), 400
    return jsonify({"reply": get_reply(user_msg)})


if __name__ == "__main__":
    app.run(debug=True, use_reloader=False, port=5000)
