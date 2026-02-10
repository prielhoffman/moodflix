# 📺 MoodFlix

MoodFlix is a full‑stack project that recommends **TV shows** based on a user’s **mood** and **watching preferences**. It also supports **accounts + per‑user watchlists**, and can optionally enrich recommendations with **TMDB metadata**.

There is also an optional AI layer: you can generate **local embeddings** for shows and store them in **pgvector** (to enable semantic search and vector ranking later).

---

## 🖥️ Tech Stack

- **Backend**: FastAPI, SQLAlchemy, Alembic
- **Database**: PostgreSQL (Docker) + pgvector
- **Frontend**: React + Vite
- **Auth**: JWT (Bearer tokens)
- **AI**: Local embeddings (sentence-transformers) + pgvector storage

---

## ✨ Current Features (Implemented)

- **User authentication**
  - `POST /auth/register`, `POST /auth/login`, `GET /auth/me`
- **Recommendations**
  - `POST /recommend` returns **top N (default 10)** shows ranked by existing scoring logic
  - Optional `query` field enables semantic candidate retrieval before scoring
  - Includes short **explanations** (“why this was recommended”)
- **Watchlist (per user)**
  - `GET /watchlist`, `POST /watchlist/add`, `POST /watchlist/remove` (JWT required)
- **DB‑backed shows**
  - Recommendations prefer the `shows` table in Postgres (fallback to `app/data.py` if DB is empty)
- **TMDB enrichment (optional, best‑effort)**
  - Posters/ratings/overviews/dates are fetched from TMDB when `TMDB_API_KEY` is set
  - If TMDB is down/rate‑limited/misconfigured, recommendations still work (TMDB fields become `null`)
- **Semantic search**
  - `POST /search/semantic` performs pgvector cosine search over embeddings
  - `POST /search/more-like-this` returns similar shows by `show_id`
- **Embeddings generation (batch script)**
  - `scripts/generate_embeddings.py` generates local embeddings and stores them in `shows.embedding` (`vector(384)`)
- **Graceful handling of missing API keys**
  - Server starts without `TMDB_API_KEY`

---

## 📁 Project Structure (High Level)

```
app/                  # FastAPI app, routers, business logic
  api.py              # FastAPI app + routes
  logic.py            # Recommendation engine (DB-backed + fallback)
  models.py           # SQLAlchemy models (User, WatchlistItem, Show)
  schemas.py          # Pydantic schemas (API contracts)
  tmdb.py             # TMDB enrichment adapter (optional / best-effort)

alembic/              # DB migrations
scripts/              # One-off utilities (ingest, embeddings generation)
frontend/             # React + Vite UI
tests/                # pytest suite
docker/               # Docker init scripts (pgvector extension)
```

---

## 💻 Setup Instructions

### Prerequisites

- **Python 3.12.x** (recommended)
- Node.js (for the frontend)
- Docker Desktop (for Postgres + pgvector)

### 1) Start Postgres (with pgvector)

From the repo root:

```bash
docker compose up -d db
```

### 2) Backend setup & run

```bash
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

uvicorn app.api:app --reload
```

Backend URLs:
- API: `http://127.0.0.1:8000`
- Swagger: `http://127.0.0.1:8000/docs`

### 3) Frontend setup & run

```bash
cd frontend
npm install
npm run dev
```

Frontend URL:
- `http://localhost:5173`

---

## 🔎 Environment Variables

Copy the template and create your local `.env`:

```bash
cp .env.example .env
```

PowerShell:

```powershell
Copy-Item .env.example .env
```

The `.env.example` file contains all variables used by backend runtime, docker compose defaults, auth, TMDB caching/enrichment, and optional frontend API base URL.

### Database (used by backend + Alembic)

The backend supports either:
- `DATABASE_URL` (preferred when set), or
- `POSTGRES_*` variables (fallback)

Using `POSTGRES_*`:

```env
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=moodflix
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
```

Optional direct connection string:

```env
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/moodflix
```

### Auth / JWT

```env
SECRET_KEY=change-me
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

### TMDB (optional)

```env
TMDB_API_KEY=your_tmdb_key
```

If missing, the backend still starts and `/recommend` still works (TMDB fields will be `null`).

### Embeddings (local, no API keys)

Embeddings are generated locally via `sentence-transformers` — no API key required.

### Frontend (optional)

```env
VITE_API_BASE_URL=http://127.0.0.1:8000
```

---

## 🤖 AI / Embeddings (pgvector)

Embeddings are generated via a **batch script** (not an API endpoint yet). They are stored in:
- `shows.embedding` as `vector(384)` (pgvector)

The script:
- builds input text: `Title / Genres / Overview`
- batches requests (default batch size 100)
- runs locally (no paid APIs)
- commits after each batch

### Generate embeddings

```powershell
.\.venv\Scripts\python scripts\generate_embeddings.py --batch-size 100

# Optional flags:
#   --limit 200
#   --force
#   --batch-size 50
```

---

## 🗺️ Roadmap / Planned Features

- **Semantic search** over shows using embeddings
- **Vector ranking** (pgvector similarity search) combined with existing scoring
- **Personalization** via watch history and explicit feedback (“helped / didn’t help”)
- **Production hardening**
  - config cleanup, logging, safer secrets handling, better error reporting
- **CI/CD**
  - automated tests, linting, and container builds
- **UI improvements**
  - more polished browsing experience, better auth UX, richer show details

---

## 📋 Developer Notes

### Test `/recommend`

- Use Swagger at `http://127.0.0.1:8000/docs`, or:

```bash
curl -X POST http://127.0.0.1:8000/recommend ^
  -H "Content-Type: application/json" ^
  -d "{\"age\":25,\"mood\":\"chill\",\"binge_preference\":\"binge\"}"
```

### Run tests

```bash
pytest
```

### Run frontend tests

```bash
cd frontend
npm test
```

### Debug endpoint status

Debug-only endpoint(s) were removed from the backend and temporary frontend click-debug listeners were removed from the app shell.

### Swagger docs

- `http://127.0.0.1:8000/docs` shows request/response shapes for all endpoints and supports trying requests interactively.
