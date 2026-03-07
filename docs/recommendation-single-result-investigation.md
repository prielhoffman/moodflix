# Recommendation pipeline: why only one result is returned

**Note:** A fix was applied (see [REGRESSION-ANALYSIS-SINGLE-RECOMMENDATION.md](REGRESSION-ANALYSIS-SINGLE-RECOMMENDATION.md)): when the DB has fewer than 50 rows, the system now uses the static fallback instead of the DB. This prevents the "1 result" issue when the DB is under-seeded (e.g. 1 row from watchlist add-by-title).

## Diagnostics (form flow: only 1 recommendation)

After submitting the recommendations form, check server logs for these lines to find the exact bottleneck:

1. **Path and query**
   - `query_text length=0` → form flow (semantic path will NOT run).
   - `CHOSEN PATH=db_full_scan` or `fallback` → correct for form flow.

2. **DB and load**
   - `DB raw: SELECT COUNT(*) FROM shows => N` → backend sees N rows. If N < 50, the under-seeded fallback should kick in (static catalog). If N is 1 and you still get only 1 result, the fix may not be applied, or the app is connected to a different DB (check `DB connection target: host=... database=...` and your `.env`).
   - `_load_shows_from_db returned len(shows)=N` → candidate pool size before filtering. If this is 1 but raw COUNT is large, there is a bug in `_load_shows_from_db` (it has no `.limit()`; inspect if needed).

3. **Filtering**
   - `candidates_after_filtering=N | rejection counts: {...}` → which rules removed candidates. If one key (e.g. `binge`, `zero_trust_rating`) is much larger than others, that filter is the bottleneck.

**Fixes by finding:**
- **DB COUNT is 1** → Wrong DB. Fix `DATABASE_URL` / `POSTGRES_*` so the app uses the same DB you seeded.
- **Raw COUNT large but _load_shows_from_db returns 1** → Bug in loader (no limit in code; check for session/transaction issues).
- **Rejection counts: `binge` dominant** → Most shows have `number_of_seasons` ≤ 3; BINGE filter drops them. Fix: set `BINGE_MIN_SEASONS = 2` in `app/config.py` so 3-season shows pass (see config and logic).
- **Rejection counts: `zero_trust_rating` dominant** → Guest + family-safe requested; most shows lack family-safe rating. Fix: ensure form does not send `guest_family_safe: true` by default, or relax zero-trust for adults.

---

## 1) How candidates are selected (DB vs fallback)

- **When the request includes a non-empty `query`** (e.g. home search "Find shows"):
  - The query is embedded and **semantic search** runs: `_fetch_candidate_rows(db, query_vec, candidate_top_k)`.
  - That function returns **only** rows where `Show.embedding.isnot(None)`, ordered by cosine distance, **limit `candidate_top_k`** (default 80).
  - So the candidate pool is **at most 80 shows that have a non-null embedding**. If the DB has many rows but only one (or few) have embeddings populated, the pool is 1 (or very small) **before any filtering**.
  - **Fallback:** If `db_with_embedding < SEMANTIC_MIN_EMBEDDINGS` (50) or semantic returns fewer than `top_n` candidates, we fall back to full DB scan; if that yields nothing, we use static fallback.

- **When there is no `query`** (e.g. preference form "Get recommendations"):
  - We load **all** shows from the DB: `_load_shows_from_db(db)` (no embedding filter).
  - **Under-seeded fallback:** If the DB has **fewer than 50 rows** (`SEMANTIC_MIN_EMBEDDINGS`), we use the static dataset instead. This prevents the "1 result" bug when the DB has only 1–2 rows (e.g. from watchlist add-by-title).
  - So the candidate pool is either the full `shows` table (when ≥ 50 rows) or the static dataset (~50 shows).

- **Fallback** (general):
  - If the candidate list is empty (DB error, no rows, or under-seeded), we use the static dataset: `get_all_shows()` (~50–100 shows).

So: **DB vs fallback** is “DB when we have enough rows (≥ 50 for form flow; sufficient embeddings for semantic path), else static fallback”. The critical distinction is **with-query** (semantic, embedding-limited) vs **no-query** (full DB load with under-seeded check).

---

## 2) Filtering (genre, mood, binge, etc.)

Filtering happens in a single loop over the candidate list. A show is **dropped** (not added to `candidate_items`) if any of the following apply:

- **Rating**: Zero-trust / family: only family-safe ratings allowed; otherwise adult ratings blocked by age.
- **Kids/Family**: Adult genre IDs, blocked keywords in title/overview, title blacklist, and “kids safety” rule (must have Family/Kids/Animation, or Documentary/Comedy without Drama/Crime).
- **Family context**: Exclude crime, horror, thriller, true crime, war.
- **Adults without kids intent**: Exclude kids/children/preschool genres.
- **Binge preference**:
  - `SHORT_SERIES`: drop if `number_of_seasons > 3`.
  - `BINGE`: drop if `number_of_seasons <= 3` (need **more than 3** seasons). Only applied when `number_of_seasons` is not `None`.
- **Episode length**: SHORT/LONG preferences drop shows that don’t match (when episode length is present).
- **Language**: If the user set a language, drop shows that don’t match.
- **Strict genre**: If the user selected **any** `preferred_genres`, the show must match **at least one** of them (`if user_genres and not common_genres: continue`). So with genres selected, only shows that have one of those genres pass.
- **Reality**: If “reality” is in preferred genres, require the show to have “reality” and apply talk/variety rules.

Mood is **not** a hard filter: it only affects **ranking** (mood-matched shows get a score boost). So filtering can shrink the pool a lot; mood doesn’t remove candidates.

---

## 3) Why you might get only one result

### A) Semantic path (request **has** a `query`) — most likely

- Candidates come **only** from `_fetch_candidate_rows`, which returns **only shows with non-null `embedding`**.
- If the `shows` table was seeded from TMDB but **embeddings were never (or barely) populated**, then:
  - `db_shows_with_embedding` can be 1 (or very low).
  - The candidate pool is **1 (or a few)** before any filtering.
  - After scoring and `top_n`, you get **one (or a few) recommendations**.

So: **only one result often means only one (or very few) DB row has an embedding** when the user triggers the semantic path (e.g. home search with a query).

### B) No-query path (preference form only) — possible but less likely

- We start with the full DB (or fallback) list.
- **Strict genre + binge + language + kids/family** can leave very few candidates.
- If the DB is small or filters are strict, you can end up with **one candidate** after the loop; then you get one result.

There is **no** watchlist-based filtering in this logic; we do not exclude already-saved shows.

---

## 4) What is **not** limiting results to 1

- **`top_n`**: Not ignored. Default 20; we take `scored[: take]` with `take = max(1, int(top_n))` (or 2× for family), then `outputs[: int(top_n)]`. So we never force “exactly 1”; we only **cap** at `top_n`. If there is only 1 item in `scored`, we return 1.
- **Slicing**: There is no `results[:1]` or similar that would cap to one. The only slices are by `take` and by `top_n` as above.
- **Early return / break**: No early return that would truncate the list to one; the only `break` is in refill/backfill loops when we’ve reached `top_n`.
- **Overwriting**: The list is built by appending; we don’t overwrite the full list with a single item.

So the single result is because **the pipeline only has one (or very few) candidates** (either from the semantic path with almost no embeddings, or from heavy filtering on the no-query path), not because we slice or return “top 1” by mistake.

---

## 5) Debug logging added (temporary)

In `app/logic.py`, the following **temporary** logs were added so you can see exactly where the pipeline narrows:

1. **Source and DB size**
   - **With query**: `[recommend] source=db+semantic: total_db_shows=…, db_shows_with_embedding=…, candidate_top_k=…, candidates_returned=…`
   - **No query**: `[recommend] source=db: total_db_shows=…` (or warning if load failed and we fall back).
   - **Fallback used**: `[recommend] source=fallback: total_fallback_shows=…`

2. **Before filtering**: `[recommend] candidates_before_filtering=… (top_n=…)`

3. **After filtering**: `[recommend] candidates_after_filtering=…`

4. **Before return**: `[recommend] final_result_count=… (requested top_n=…)`

**How to use them**

- Reproduce the “only one recommendation” request (same route: form vs home search, and same payload: with/without `query`).
- Check server logs (e.g. uvicorn stdout) for the `[recommend]` lines.

Interpretation:

- If you see **`candidates_returned=1`** (or very small) and **`db_shows_with_embedding=1`** (or very small) → the semantic path is used and **lack of embeddings** is the cause; fix by populating embeddings for more (or all) shows.
- If you see **`candidates_before_filtering`** large but **`candidates_after_filtering=1`** → the no-query path is used and **filtering** is the cause; then relax or debug filters (genre, binge, language, kids/family) as needed.

No behavior of the recommendation logic was changed; only logging was added.
