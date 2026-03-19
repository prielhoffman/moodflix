# Database: Migrations & Reset (Local Development)

Use this when **FastAPI runs locally** (uvicorn) and **PostgreSQL runs in Docker**. Schema is managed by **Alembic**; there is no `Base.metadata.create_all()` on startup.

---

## 1. DATABASE_URL / POSTGRES_HOST

- When the **backend runs on your machine** (e.g. `uvicorn app.api:app`), it must connect to Postgres via **localhost** (or `127.0.0.1`), because the container exposes port 5432 to the host.
- In your **`.env`** (copy from `.env.example` if needed), set:

  ```env
  POSTGRES_HOST=localhost
  POSTGRES_USER=postgres
  POSTGRES_PASSWORD=postgres
  POSTGRES_DB=moodflix
  POSTGRES_PORT=5432
  ```

  Or a single URL:

  ```env
  DATABASE_URL=postgresql://postgres:postgres@localhost:5432/moodflix
  ```

- **Do not** use `POSTGRES_HOST=db` when running uvicorn on your machine; `db` is the Docker service name and only works from inside the Docker network.

---

## 2. Exact terminal commands

All commands assume you are in the project root and (if you use a venv) that it is activated.

### Restart the PostgreSQL Docker container

```powershell
docker compose restart db
```

Or stop and start clean (container only; data volume is kept):

```powershell
docker compose stop db
docker compose up -d db
```

### Check current migration state

```powershell
alembic current
```

### Apply all migrations (upgrade to head)

```powershell
alembic upgrade head
```

### Generate a new migration (after changing SQLAlchemy models)

```powershell
alembic revision --autogenerate -m "describe_your_change"
```

Then review the new file under `alembic/versions/` and apply it:

```powershell
alembic upgrade head
```

### Reset the database (development only)

This **destroys all data** in the `moodflix` database and reapplies migrations from scratch.

**Option A – Drop and recreate the database (recommended for a clean reset):**

```powershell
# Connect to default postgres DB and drop moodflix (replace password if different)
docker exec -it moodflix-db psql -U postgres -c "DROP DATABASE IF EXISTS moodflix;"
docker exec -it moodflix-db psql -U postgres -c "CREATE DATABASE moodflix;"

# Re-run all migrations
alembic upgrade head
```

**Option B – Downgrade all then upgrade (only if you have no migration conflicts):**

```powershell
alembic downgrade base
alembic upgrade head
```

**Option C – Nuclear: remove the Postgres volume and recreate the container (all data in the volume is lost):**

```powershell
docker compose down
docker volume rm moodflix_postgres_data
docker compose up -d db
# Wait a few seconds for Postgres to be ready, then:
alembic upgrade head
```

---

## 3. If schema mismatch is detected

- **Symptom:** Errors about missing columns/tables or wrong types when the app runs.
- **Cause:** Database is behind the migrations (or migrations were never run).
- **Fix:** Run `alembic upgrade head` so the DB matches the migration chain. If you prefer a clean slate, use the reset commands above, then `alembic upgrade head`.

After any model change, add a new migration with `alembic revision --autogenerate -m "..."`, then run `alembic upgrade head`.

---

## 4. Verify and seed the `shows` table

Recommendations use the **static fallback** when the `shows` table is **empty or under-seeded** (fewer than 50 rows). This ensures a sufficient candidate pool for scoring; otherwise a DB with 1–2 rows (e.g. from favorites add-by-title) would return only 1–2 recommendations. **Favorites** (API: /watchlist) still works: adding by **title** creates a minimal row in `shows` (Option A). If you want recommendations to be DB-backed (and have `show_id` in responses), seed `shows` with at least 50 rows (200+ recommended for production-like behavior).

### Check if `shows` has rows

```powershell
docker exec -it moodflix-db psql -U postgres -d moodflix -c "SELECT COUNT(*) FROM shows;"
```

### Seed `shows` from TMDB (optional)

Requires `TMDB_API_KEY` in `.env`. The ingest script fetches popular TV shows from TMDB and inserts them into `shows`:

```powershell
python -m scripts.ingest_tmdb
```

- **TMDB_API_KEY** is required (get a free key from [themoviedb.org](https://www.themoviedb.org/settings/api)).
- **TMDB_PAGES** in `.env` controls how many pages to fetch (default 2 ≈ 40 shows; use 5+ for 100+, 10 for 200+).
- Run from project root with venv activated; the script uses the same DB connection as the backend.

Then (optional) generate embeddings for semantic search:

```powershell
python -m scripts.generate_embeddings
```

Use `--force` to regenerate all embeddings, or `--limit N` to process only N shows.

### Verify show and embedding counts

Check total rows and how many have embeddings (semantic search only uses rows with non-null `embedding`):

```powershell
docker exec -it moodflix-db psql -U postgres -d moodflix -c "SELECT COUNT(*), COUNT(embedding) FROM shows;"
```

Or with a direct connection (e.g. `psql -U postgres -d moodflix`):

```sql
SELECT COUNT(*), COUNT(embedding) FROM shows;
```

If `COUNT(embedding)` is much smaller than `COUNT(*)`, run `python -m scripts.generate_embeddings` so recommendations with a search query return more than one result.

### If you see "Show not found" when adding by `show_id`

That means the given `show_id` is not in `shows`. Either:

- **Option A (current behavior):** Add by **title** instead of `show_id`; the backend will create a minimal `Show` row and then the favorites item.
- **Option B:** Seed the DB first (`python -m scripts.ingest_tmdb`) so recommendations return shows that exist in `shows`, and the frontend sends `show_id`.
