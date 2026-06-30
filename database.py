import sqlite3
import json
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "movies.db")


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


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


def search_movies(query: str = "", sort: str = "id"):
    order = {
        "score_desc": "score DESC",
        "score_asc":  "score ASC",
        "year_desc":  "CAST(SUBSTR(release,1,4) AS INTEGER) DESC",
    }.get(sort, "id ASC")

    sql = f"SELECT * FROM movies WHERE name_tw LIKE ? OR name LIKE ? ORDER BY {order}"
    pattern = f"%{query}%"
    with get_conn() as conn:
        return [dict(r) for r in conn.execute(sql, (pattern, pattern)).fetchall()]


if __name__ == "__main__":
    init_db()
    json_path = os.path.join(os.path.dirname(__file__), "movies.json")
    seed_from_json(json_path)
    rows = get_all_movies()
    print(f"Total rows: {len(rows)}")
    print("Sample:", rows[0]["name_tw"], "|", rows[0]["score"])
