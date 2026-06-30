# 🎬 Movie House

A full-stack movie browser with an AI-powered chatbot built with **Flask**, **Streamlit**, **SQLite**, and **Google Gemini**.

## 🚀 Live Demo

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://wimovie.streamlit.app/)

👉 **[https://wimovie.streamlit.app/](https://wimovie.streamlit.app/)**

> Enter your own [Gemini API Key](https://aistudio.google.com/app/apikey) (free) in the sidebar to enable the AI chatbot.

---

## Features

- 📽 **100 curated classic films** scraped from [ssr1.scrape.center](https://ssr1.scrape.center)
- 🔍 **Search & sort** by title, rating, or release year
- 🖼 **High-resolution posters** for every film
- 🤖 **Movie Bot** — Gemini-powered chatbot restricted to films in the collection
- ⚙️ **Self-serve API Key** — enter your Gemini key in the UI, no restart needed
- 🗄 **SQLite database** for persistent, queryable movie storage

## Project Structure

```
chatbot/
├── app.py              # Flask web app
├── streamlit_app.py    # Streamlit UI (deployed to Streamlit Cloud)
├── database.py         # SQLite helpers (init, seed, query)
├── movies.db           # SQLite database (auto-generated)
├── movies.json         # Source data (100 movies)
├── static/
│   └── robot.png       # Chatbot avatar
├── templates/
│   └── index.html      # Flask frontend (dark-theme movie grid + chat widget)
├── .env                # GEMINI_API_KEY (not committed)
└── requirements.txt
```

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Set Gemini API Key (optional)

Create `.env`:

```
GEMINI_API_KEY=your_key_here
```

Or enter it directly in the sidebar (⚙️ 設定).

### 3a. Run Flask app

```bash
python app.py
# → http://localhost:5000
```

### 3b. Run Streamlit app

```bash
streamlit run streamlit_app.py
# → http://localhost:8501
```

## Database Schema

```sql
CREATE TABLE movies (
    id          INTEGER PRIMARY KEY,
    name        TEXT,       -- original (Simplified Chinese + English)
    name_tw     TEXT,       -- Traditional Chinese
    score       REAL,       -- 0–10
    category    TEXT,
    release     TEXT,
    duration    TEXT,
    img_url     TEXT,
    poster_file TEXT        -- local filename: poster_001.jpg
);
```

## Tech Stack

| Layer     | Tech                        |
|-----------|-----------------------------|
| Scraping  | requests + BeautifulSoup    |
| Database  | SQLite (stdlib)             |
| Backend   | Flask 3                     |
| Frontend  | Vanilla HTML/CSS/JS         |
| Alt UI    | Streamlit                   |
| AI        | Google Gemini 2.5 Flash     |
| Images    | Pillow                      |
| Deploy    | Streamlit Cloud             |

## API Endpoints (Flask)

| Method | Path            | Description              |
|--------|-----------------|--------------------------|
| GET    | `/`             | Movie grid homepage      |
| GET    | `/poster/<file>`| Serve poster image       |
| POST   | `/chat`         | `{message}` → `{reply}` |
| GET    | `/api/config`   | Key status               |
| POST   | `/api/config`   | `{api_key}` → update key |
