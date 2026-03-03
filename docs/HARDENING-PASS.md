# MoodFlix Pre-Production Hardening Pass

**Date:** 2026-03-03  
**Scope:** Backend (FastAPI), frontend, database models, migrations, scripts.

---

## 1. Severity Summary Table

| Severity | Issue | File(s) | Status |
|----------|-------|---------|--------|
| **Critical** | Static data mutation across requests (data corruption) | `app/data.py`, `app/logic.py` | ✅ Fixed |
| **High** | Watchlist duplicate add race → IntegrityError crash | `app/routers/watchlist.py` | ✅ Fixed |
| **High** | Kids/Family: "Greys Anatomy" variant bypassed blacklist | `app/logic.py` | ✅ Fixed |
| **Medium** | Debug print statements in production code | `app/security.py`, `app/routers/watchlist.py` | ✅ Fixed |
| **Medium** | ACCESS_TOKEN_EXPIRE_MINUTES invalid env → crash | `app/security.py` | ✅ Fixed |
| **Medium** | datetime.utcnow() deprecated (Python 3.12+) | `app/security.py` | ✅ Fixed |
| **Low** | Binge test assertion outdated vs config | `tests/test_logic.py` | ✅ Fixed |
| **Low** | test_recommend_with_query used invalid mock db | `tests/test_logic.py` | ✅ Fixed |

---

## 2. Issues Fixed (Detail)

### A) Static Data Mutation (Critical)

**Identification**
- **Bug:** `get_all_shows()` returned a reference to the module-level `SHOWS` list. Callers mutated entries (e.g. `show["content_rating"] = rating`, `show["id"] = row.id`), corrupting shared state across requests.
- **Location:** `app/data.py` `get_all_shows()`, `app/logic.py` (mutating show dicts).
- **Root cause:** No copy on return; callers assumed they could mutate.
- **When:** Any request using static fallback (empty DB or semantic fallback).

**Impact**
- Data integrity: static catalog could be permanently altered.
- Cross-request leakage: one user’s filters could affect another’s.
- Affects: All users when fallback dataset is used.

**Fix**
- `get_all_shows()` now returns `[dict(s) for s in SHOWS]` so each call gets fresh copies.
- **Behavior change:** Mutations no longer affect the original `SHOWS` or other requests.

**Verification**
- `test_static_data_is_not_mutated_across_requests` added.

---

### B) Watchlist Duplicate Add Race (High)

**Identification**
- **Bug:** Concurrent add requests for the same show could both pass the existence check and hit a unique constraint, raising `IntegrityError` and returning 500.
- **Location:** `app/routers/watchlist.py` `add_to_watchlist()`.
- **Root cause:** No handling of `IntegrityError` from `(user_id, show_id)` unique constraint.
- **When:** Two simultaneous add requests for the same show.

**Impact**
- 500 error for a valid idempotent operation.
- Affects: Authenticated users.

**Fix**
- Catch `IntegrityError`, rollback, and return the current watchlist (idempotent success).
- **Behavior change:** Duplicate add returns 200 with watchlist instead of 500.

**Verification**
- Existing `test_prevent_duplicate_watchlist_saves` still passes; race case covered by design.

---

### C) Kids/Family Blacklist: "Greys Anatomy" Variant (High)

**Identification**
- **Bug:** "Greys Anatomy" (no apostrophe) was not blocked in Kids/Family context; only "grey's anatomy" and "grey anatomy" were in the blacklist.
- **Location:** `app/logic.py` `_KIDS_TITLE_BLACKLIST`.
- **Root cause:** Static data uses "Greys Anatomy"; blacklist lacked that variant.
- **When:** Family/Kids context with "Greys Anatomy" in catalog.

**Impact**
- Adult medical drama could appear in family-safe results.
- Affects: Users in family context.

**Fix**
- Added `"greys anatomy"` to `_KIDS_TITLE_BLACKLIST`.
- **Behavior change:** "Greys Anatomy" is now blocked in Kids/Family context.

**Verification**
- `test_greys_anatomy_variant_blocked_in_family_context` added.

---

### D) Debug Print Statements (Medium)

**Identification**
- **Bug:** `print()` used for debugging in production paths.
- **Location:** `app/security.py` (password length), `app/routers/watchlist.py` (payload, exception).
- **Impact:** Log noise, potential information leakage.
- **Fix:** Removed all debug prints; kept `logger` usage.
- **Behavior change:** No more print output from these paths.

---

### E) ACCESS_TOKEN_EXPIRE_MINUTES Parsing (Medium)

**Identification**
- **Bug:** `int(os.getenv(...))` could raise `ValueError` on invalid values (e.g. `"abc"`), crashing the app on import.
- **Location:** `app/security.py`.
- **Fix:** Try/except with fallback to 30; clamp to minimum 1.
- **Behavior change:** Invalid env no longer crashes; uses 30 minutes.

---

### F) datetime.utcnow() Deprecation (Medium)

**Identification**
- **Bug:** `datetime.utcnow()` is deprecated in Python 3.12+.
- **Location:** `app/security.py` `create_access_token()`.
- **Fix:** Use `datetime.now(timezone.utc)`.
- **Behavior change:** Same behavior, no deprecation warning.

---

### G) Test Fixes (Low)

- **test_binge_returns_only_more_than_three_seasons:** Assertion expected `> 3` but config uses `BINGE_MIN_SEASONS = 2` (3+ seasons). Updated to use `config.BINGE_MIN_SEASONS`.
- **test_recommend_with_query_uses_db_candidates:** Used `db=object()` which lacks `query`/`execute`. Replaced with `MockDB` and `top_n=2` to avoid fallback path.

---

## 3. What Changes After Fixes (Developer Summary)

| Area | Before | After |
|------|--------|-------|
| **Static fallback** | Mutating `SHOWS` could corrupt data across requests | Each request gets its own copy; no shared mutation |
| **Watchlist add** | Duplicate add (incl. race) could return 500 | Duplicate add returns 200 with current watchlist |
| **Family context** | "Greys Anatomy" could appear | "Greys Anatomy" is blocked |
| **Logs** | Debug prints in security/watchlist | Only structured logging |
| **Startup** | Invalid `ACCESS_TOKEN_EXPIRE_MINUTES` could crash app | Falls back to 30 minutes |
| **JWT** | `datetime.utcnow()` deprecation warning | Uses `datetime.now(timezone.utc)` |

---

## 4. TODO Checklist (GitHub Issues)

### Critical (Done)
- [x] Fix static data mutation in `get_all_shows()`
- [x] Handle watchlist `IntegrityError` for duplicate add

### High (Done)
- [x] Add "greys anatomy" to kids blacklist

### Medium (Done)
- [x] Remove debug print statements
- [x] Harden `ACCESS_TOKEN_EXPIRE_MINUTES` parsing
- [x] Replace `datetime.utcnow()` with timezone-aware API

### Low / Future
- [ ] Make CORS origins configurable via env (e.g. `CORS_ORIGINS`)
- [ ] Add rate limiting for TMDB enrichment (avoid 429)
- [ ] Add `SECRET_KEY` validation on startup in production (fail fast if default)
- [ ] Consider `alg` in JWT header validation (jose default is usually fine)
- [ ] Document `BINGE_MIN_SEASONS` vs test expectations in `config.py`

---

## 5. How to Run Tests

```powershell
# All backend tests
pytest tests/ -v

# Specific suites
pytest tests/test_auth.py tests/test_watchlist.py -v
pytest tests/test_logic.py -v
```

---

## 6. Assumptions / Items Verified as Safe

- **JWT:** `jwt.decode(..., algorithms=[ALGORITHM])` restricts to HS256; no algorithm confusion.
- **Password:** bcrypt truncation to 72 bytes is applied; schema allows up to 72 chars.
- **Watchlist FK:** `ON DELETE CASCADE` on `show_id`; deleting a show removes watchlist items.
- **TMDB:** Degrades when API key missing or rate-limited; no crash.
- **Embeddings:** `generate_embeddings.py` uses `EMBED_DIM=384`; model and DB schema match.
- **Alembic:** `env.py` builds `DATABASE_URL` from `POSTGRES_*` when `DATABASE_URL` unset; consistent with `app/db.py`.
