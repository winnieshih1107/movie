import shutil
import sqlite3
import json
import os

_BUNDLED_DB = os.path.join(os.path.dirname(__file__), "movies.db")

if os.environ.get("VERCEL"):
    # Vercel's deployment filesystem is read-only — copy the bundled,
    # pre-seeded DB into /tmp (the only writable path) on cold start.
    DB_PATH = "/tmp/movies.db"
    if not os.path.exists(DB_PATH) and os.path.exists(_BUNDLED_DB):
        shutil.copyfile(_BUNDLED_DB, DB_PATH)
else:
    DB_PATH = _BUNDLED_DB


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# Seed data stores genre names in Simplified Chinese; map to Traditional for display.
S2T_GENRES = {
    "传记": "傳記", "冒险": "冒險", "剧情": "劇情", "动作": "動作", "动画": "動畫",
    "历史": "歷史", "古装": "古裝", "喜剧": "喜劇", "奇幻": "奇幻", "家庭": "家庭",
    "悬疑": "懸疑", "惊悚": "驚悚", "战争": "戰爭", "歌舞": "歌舞", "武侠": "武俠",
    "灾难": "災難", "爱情": "愛情", "犯罪": "犯罪", "科幻": "科幻", "纪录片": "紀錄片",
    "西部": "西部", "音乐": "音樂",
}


def to_traditional(text: str) -> str:
    if not text:
        return text
    for simp, trad in S2T_GENRES.items():
        text = text.replace(simp, trad)
    return text


def init_db():
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS movies (
                id          INTEGER PRIMARY KEY,
                name        TEXT NOT NULL,
                name_tw     TEXT NOT NULL,
                score       REAL,
                category    TEXT,
                release     TEXT,
                duration    TEXT,
                img_url     TEXT,
                poster_file TEXT
            )
        """)
        conn.commit()


def seed_from_json(json_path: str):
    with open(json_path, encoding="utf-8") as f:
        movies = json.load(f)

    with get_conn() as conn:
        conn.execute("DELETE FROM movies")
        conn.executemany(
            """INSERT INTO movies
               (id, name, name_tw, score, category, release, duration, img_url, poster_file)
               VALUES (:id, :name, :name_tw, :score, :category, :release, :duration, :img_url, :poster_file)""",
            [
                {
                    "id":          m["id"],
                    "name":        m.get("name", ""),
                    "name_tw":     m.get("name_tw", m.get("name", "")),
                    "score":       float(m["score"]) if m.get("score") else None,
                    "category":    m.get("category", ""),
                    "release":     m.get("release", ""),
                    "duration":    m.get("duration", ""),
                    "img_url":     m.get("img_url", ""),
                    "poster_file": f"poster_{m['id']:03d}.jpg",
                }
                for m in movies
            ],
        )
        conn.commit()
    print(f"✅ Seeded {len(movies)} movies into {DB_PATH}")


def get_all_movies():
    with get_conn() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM movies ORDER BY id").fetchall()]


def get_all_categories():
    with get_conn() as conn:
        rows = conn.execute("SELECT DISTINCT category FROM movies WHERE category IS NOT NULL").fetchall()
    cats = set()
    for r in rows:
        for c in (r["category"] or "").split("/"):
            c = c.strip()
            if c:
                cats.add(c)
    return sorted(cats)


def search_movies(query: str = "", sort: str = "id", category: str = "",
                   min_score: float = 0.0, max_score: float = 10.0):
    order = {
        "score_desc": "score DESC",
        "score_asc":  "score ASC",
        "year_desc":  "CAST(SUBSTR(release,1,4) AS INTEGER) DESC",
    }.get(sort, "id ASC")

    conditions = ["(name_tw LIKE ? OR name LIKE ?)"]
    params = [f"%{query}%", f"%{query}%"]

    if category:
        conditions.append("category LIKE ?")
        params.append(f"%{category}%")

    if min_score:
        conditions.append("score >= ?")
        params.append(min_score)

    if max_score and max_score < 10.0:
        conditions.append("score <= ?")
        params.append(max_score)

    sql = f"SELECT * FROM movies WHERE {' AND '.join(conditions)} ORDER BY {order}"
    with get_conn() as conn:
        return [dict(r) for r in conn.execute(sql, params).fetchall()]


if __name__ == "__main__":
    init_db()
    json_path = os.path.join(os.path.dirname(__file__), "movies.json")
    seed_from_json(json_path)
    rows = get_all_movies()
    print(f"Total rows: {len(rows)}")
    print("Sample:", rows[0]["name_tw"], "|", rows[0]["score"])
