# 📺 MoodFlix

MoodFlix is a full‑stack project that recommends **TV shows** based on a user’s **mood** and **watching preferences**. It also supports **accounts + per‑user watchlists**, and can optionally enrich recommendations with **TMDB metadata**.

An **AI layer** provides **local embeddings** (sentence-transformers) stored in **pgvector** for semantic search and vector-based similarity in recommendations.

---

## 🖥️ Tech Stack

- **Backend**: FastAPI, SQLAlchemy, Alembic
- **Database**: PostgreSQL (Docker) + pgvector
- **Frontend**: React + Vite
- **Auth**: JWT (Bearer tokens)
- **AI**: Local embeddings (sentence-transformers) + pgvector storage
- **Infrastructure**: Alembic for schema migrations; pgvector extension auto-initialized on first DB connection (`app/db.py`)

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
  - Watchlist items reference the `shows` table via `show_id` (FK); add/remove by `show_id` (title supported for legacy/remove)
- **DB‑backed shows**
  - Recommendations prefer the `shows` table in Postgres (fallback to `app/data.py` if DB is empty)
  - `shows` stores TMDB metadata (content_rating, number_of_seasons, average_episode_length, original_language) for faster reads and fewer API calls
- **TMDB enrichment (optional, best‑effort)**
  - Posters/ratings/overviews/dates are fetched from TMDB when `TMDB_API_KEY` is set
  - Fetched metadata is persisted to the DB (write-through) so future requests use local data first
  - If TMDB is down/rate‑limited/misconfigured, recommendations still work (TMDB fields fall back to DB or `null`)
- **Semantic search**
  - `POST /search/semantic` performs pgvector cosine search over embeddings (HNSW index for performance)
  - `POST /search/more-like-this` returns similar shows by `show_id`
- **Embeddings generation (batch script)**
  - `scripts/generate_embeddings.py` generates local embeddings and stores them in `shows.embedding` (`vector(384)`)
- **Graceful handling of missing API keys**
  - Server starts without `TMDB_API_KEY`

---

## 📐 Recent Improvements & Architecture

### Database Schema Evolution

- **Watchlist refactor**  
  The watchlist now uses a **foreign key to the `shows` table** (`show_id`) instead of storing only a title string. This ensures a stable link to the catalog, avoids duplicates by show, and allows the API to accept `show_id` for add/remove (with optional title for backward compatibility). The `title` column is kept as an optional denormalized field for display.

- **Shows table expansion**  
  The `shows` table has been extended with TMDB-derived metadata columns: **`content_rating`**, **`average_episode_length`**, **`number_of_seasons`**, and **`original_language`**. These are populated by the write-through enrichment flow so recommendations and filtering can read from the database first and reduce dependency on the TMDB API.

### Search Optimization

- **Semantic search performance**  
  Vector similarity search uses an **HNSW index** on `shows.embedding` with **`vector_cosine_ops`** (pgvector). This avoids full table scans on `ORDER BY embedding <=> query_vector` and reduces latency for:
  - `POST /search/semantic` (natural-language search)
  - `POST /search/more-like-this` (similar shows by `show_id`)
  - Semantic candidate retrieval inside the recommendation pipeline when a `query` is provided.

### Data Enrichment Strategy

- **Write-through cache / persistence**  
  When TMDB is used to enrich a show (e.g. content rating, seasons, episode length, language), the app **persists that data to the local `shows` table** after each fetch. Subsequent requests for the same show read these fields from the database first; TMDB is only called when data is missing or when additional fields (e.g. poster, overview) are needed. This reduces API latency and external dependency while keeping the catalog up to date as enrichment runs.

### Infrastructure

- **pgvector extension**  
  The **pgvector** extension is ensured on every new database connection via a pool listener in `app/db.py`. The app can rely on vector support without depending on a one-off migration or manual setup.

- **Migrations**  
  **Alembic** is used for all schema changes (watchlist `show_id`, shows metadata columns, HNSW index, etc.). Run `alembic upgrade head` after pulling or when deploying.

### User Registration & Age-Based Recommendations

- **Registration fields**  
  Users now provide **full_name**, **date_of_birth**, **email**, and **password** when registering. `date_of_birth` is validated (must be in the past; age 13–120).

- **Recommendations without age input**  
  The recommendations form no longer asks for age. For **authenticated** users, age is inferred from `date_of_birth` and used for content filtering. For **unauthenticated** users, age filtering is skipped (treated as adult).

### Bug Fixes & Safety

- **Kids / family filtering**  
  Filtering logic for family and kids contexts has been tightened. A **title blacklist** (`_KIDS_TITLE_BLACKLIST`) blocks known adult-oriented titles in kids/family mode, in addition to genre-based and keyword-based rules, improving safety for age-restricted use cases.

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
alembic upgrade head
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

### 4) Run migrations (full_name + date_of_birth)

After pulling the latest changes, run:

```bash
alembic upgrade head
```

This adds `full_name` and `date_of_birth` to the `users` table. Existing users are backfilled with defaults (email prefix as full_name, `1990-01-01` as date_of_birth).

**Verify the new flow:**
1. Register a new user with full name, date of birth, email, and password.
2. Log in and open the recommendations page — the form no longer asks for age.
3. Get recommendations (age is inferred from your date of birth for content filtering).
4. Log out and get recommendations — they work without age filtering (treated as adult).

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

## Demo without TMDB

You can demo recommendations without TMDB and without seeded Postgres content:

- Leave `TMDB_API_KEY` unset.
- Start the backend normally.
- Call `POST /recommend`.

When the `shows` table is empty (or DB is unavailable), the app falls back to a curated static dataset in `app/data.py` with diverse genres, languages, content ratings, season counts, and episode lengths.

Example payloads that should return multiple recommendations from fallback data:

```bash
curl -X POST http://127.0.0.1:8000/recommend ^
  -H "Content-Type: application/json" ^
  -d "{\"age\":28,\"mood\":\"chill\",\"preferred_genres\":[\"comedy\",\"slice of life\"],\"binge_preference\":\"short_series\",\"episode_length_preference\":\"short\",\"watching_context\":\"alone\"}"
```

```bash
curl -X POST http://127.0.0.1:8000/recommend ^
  -H "Content-Type: application/json" ^
  -d "{\"age\":30,\"mood\":\"adrenaline\",\"preferred_genres\":[\"action\",\"thriller\"],\"binge_preference\":\"binge\",\"episode_length_preference\":\"long\",\"watching_context\":\"partner\"}"
```

```bash
curl -X POST http://127.0.0.1:8000/recommend ^
  -H "Content-Type: application/json" ^
  -d "{\"age\":12,\"mood\":\"happy\",\"preferred_genres\":[\"family\",\"animation\"],\"binge_preference\":\"short_series\",\"episode_length_preference\":\"short\",\"watching_context\":\"family\"}"
```

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
