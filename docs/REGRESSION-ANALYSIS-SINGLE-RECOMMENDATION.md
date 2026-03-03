# Regression Analysis: POST /recommend Returns Only One Show

**Date:** 2026-03-03  
**Symptom:** Form flow (no query) returns 1 show instead of 10. DB has 1 row with synthetic `tmdb_id`.

---

## 1. Execution Path Trace

```
Request: POST /recommend
  └─ Body: { mood, binge_preference, ... }  // query = "" (form flow)
  └─ api.py recommend() → recommend_shows(input_data, db=db, age=age)

recommend_shows():
  ├─ query_text = (input_data.query or "").strip()  → ""
  ├─ query_text and db  → FALSE (no semantic path)
  └─ else branch (form flow):
       ├─ shows = _load_shows_from_db(db)  → 1 row (Stranger Things)
       ├─ source_path = "db_full_scan"
       ├─ if not shows  → FALSE (we have 1 show)
       └─ [BEFORE FIX] no fallback; shows stays at 1

  ├─ candidates_before_filtering = 1
  ├─ Filtering loop: 1 candidate → 1 candidate_item
  ├─ Scoring: 1 scored item
  ├─ outputs[:top_n]  → 1 output
  └─ Return: [RecommendationOutput(Stranger Things)]
```

**Bottleneck:** Candidate pool size is 1 because `_load_shows_from_db(db)` returns 1 row. The DB has only 1 row.

---

## 2. Root Cause

**The DB has only 1 row.** That row was created by the watchlist flow, not by `ingest_tmdb.py`:

| Evidence | Meaning |
|----------|---------|
| `tmdb_id = -523530012` | Synthetic ID from `_synthetic_tmdb_id_for_title()` in `app/routers/watchlist.py` |
| `id = 1` | First (and only) row in `shows` |
| `title = "Stranger Things"` | Matches static fallback catalog |

**Sequence that produced the 1-row DB:**

1. DB was empty (fresh volume, or `docker compose down -v`).
2. User submitted recommendation form → `_load_shows_from_db()` returned [].
3. Fallback: `shows = get_all_shows()` (50 static shows).
4. User received 10 recommendations from static pool.
5. User saved "Stranger Things" to watchlist.
6. `_get_or_create_show_by_title("Stranger Things")` created a new `Show` row with synthetic `tmdb_id`.
7. DB now has 1 row.
8. Next recommendation: `_load_shows_from_db()` returns 1 row → 1 result.

**Commit that introduced the behavior:** `542ff20` – "Watchlist: auto-create minimal Show on add-by-title to support fallback recommendations"

That commit added `_get_or_create_show_by_title()`, which creates a `Show` row when adding from static fallback. Once one show is saved, the DB is no longer empty, so the next request uses the DB (1 row) instead of static fallback (50 shows).

---

## 3. Git History (Relevant Commits)

| Commit | Change | Impact |
|--------|--------|--------|
| `542ff20` | `_get_or_create_show_by_title()` + id resolution in logic | Creates Show row on watchlist add from static; enables "1-row trap" |
| `2a40eaa` | "Make TMDB optional and switch recommendations to DB with fallback" | DB-first, fallback when empty |
| `857e2f5` | Add shows table and TMDB ingest script | ingest_tmdb.py populates DB |

**Faulty commit:** `542ff20` did not introduce a logic bug per se; it added a feature that, when combined with an empty DB, creates a state where the DB has 1 row and form flow returns 1 result. The missing piece is: **use static fallback when DB is under-seeded**, not only when it is empty.

---

## 4. DB Lifecycle

| Question | Answer |
|----------|--------|
| Is Docker volume persistent? | Yes. `postgres_data` volume persists across `docker compose down` unless `-v` is used. |
| Was volume recreated? | Likely. `docker compose down -v` or fresh clone would create empty DB. |
| Is ingest_tmdb.py mandatory? | For 200+ shows, yes. Without it, DB stays empty until watchlist creates rows. |
| Did static fallback mask empty DB? | Yes. When DB was empty, we used static (50 shows). Saving one show created 1 row; next request used DB (1 row) instead of static. |

---

## 5. Logic Expectations (Verified)

| Expectation | Status |
|-------------|--------|
| `query == ""` → full DB scan (no semantic) | ✅ Correct path |
| Embeddings do not affect form flow | ✅ Form flow uses `_load_shows_from_db()` |
| Static fallback when DB empty | ✅ `if not shows: shows = get_all_shows()` |
| Static fallback when DB has 1 row | ❌ **Missing** – we used 1 row as pool |

---

## 6. Fix Applied

**Patch:** In form flow, when `_load_shows_from_db()` returns fewer than `SEMANTIC_MIN_EMBEDDINGS` (50) rows, use static fallback.

**File:** `app/logic.py`  
**Location:** `else` branch (form flow, lines 551–567)

**Behavior change:**
- Before: DB with 1 row → 1 candidate → 1 result.
- After: DB with &lt; 50 rows → static fallback (50 shows) → up to `top_n` results.

---

## 7. Verification Commands

### A) Confirm DB row count

```powershell
docker exec moodflix-db psql -U postgres -d moodflix -c "SELECT COUNT(*) FROM shows;"
```

### B) Test API (with fix, under-seeded DB)

```powershell
# Get token (replace with your credentials)
$login = Invoke-RestMethod -Uri "http://localhost:8000/auth/login" -Method POST -ContentType "application/json" -Body '{"email":"user@example.com","password":"yourpassword"}'
$token = $login.access_token

# Request recommendations (form flow, no query)
$body = '{"mood":"chill","binge_preference":"binge","preferred_genres":[],"watching_context":"alone","episode_length_preference":"any"}'
$headers = @{ "Authorization" = "Bearer $token"; "Content-Type" = "application/json" }
$resp = Invoke-RestMethod -Uri "http://localhost:8000/recommend" -Method POST -Headers $headers -Body $body

# Expect 10 results (or up to top_n)
$resp.Count
```

### C) Seed DB for production-like behavior

```powershell
# Set TMDB_API_KEY in .env, then:
python scripts/ingest_tmdb.py

# Verify
docker exec moodflix-db psql -U postgres -d moodflix -c "SELECT COUNT(*) FROM shows;"
# Expect 40+ (2 pages × 20 per page)
```

### D) Run tests

```powershell
pytest tests/test_logic.py -v -k "family_context or binge or static_data"
```

---

## 8. Summary

| Item | Value |
|------|-------|
| **Root cause** | DB has 1 row (from watchlist add-by-title). Form flow uses DB when non-empty; 1 row → 1 result. |
| **Faulty commit** | `542ff20` (introduced create-on-add; exposed missing under-seeded fallback) |
| **Fix** | Use static fallback when DB has &lt; 50 rows in form flow |
| **Seeding** | Run `ingest_tmdb.py` for 200+ shows; optional for form flow after fix |
