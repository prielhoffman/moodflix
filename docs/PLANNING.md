# MoodFlix Planning

**Canonical planning and design reference.** This file covers why we're building MoodFlix, how we think about the project, key decisions, and the planning steps (Step 1–9). All changes and suggestions align with these goals unless explicitly discussed.

---

## Step 1 – Project Goal Definition

### 1. Goal Statement

| Dimension | Definition |
|-----------|------------|
| **Why** | Hands-on experience with in-demand tools/patterns, stronger GitHub portfolio, higher chance of technical interviews |
| **Who** | Users who want to find a TV show *as quickly as possible* without endless browsing |
| **Value** | Mood-based recommendations + constraints (age from DOB, time, commitment) + semantic AI search from free-text descriptions |

---

### 2. Success Metrics (Checklist)

#### User Flow

- [ ] **1-minute flow**: Register → Top 10 recommendations → Save at least one to watchlist
- [ ] **Search relevance**: Each search returns 1–2 recommendations that feel clearly relevant to user intent
- [ ] **UX**: Fast response times, clear flow, non-confusing

#### Portfolio

- [ ] Clean repository structure
- [ ] Clear documentation
- [ ] Simple local setup (Docker + DB + migrations)
- [ ] Basic automated tests and CI

---

### 3. Current Project Alignment

#### What Already Aligns

| Goal | Current State |
|------|---------------|
| Mood-based recommendations | [app/logic.py](../app/logic.py) – mood, binge_preference, genres, watching_context, episode_length |
| Age from DOB | [app/schemas.py](../app/schemas.py) – `date_of_birth` in `UserCreate`; age inferred for authenticated users |
| Semantic AI search | `POST /search/semantic` (pgvector), optional `query` in `POST /recommend` |
| Top 10 recommendations | `POST /recommend` returns top N (default 10) |
| Watchlist | `GET/POST /watchlist` with JWT; add by `show_id` |
| Docker + DB | [docker-compose.yml](../docker-compose.yml) – db service; [docker/initdb/](../docker/) – pgvector |
| Migrations | Alembic with 10+ versions |
| Tests | pytest (backend), Vitest (frontend) |
| CI | [.github/workflows/ci.yml](../.github/workflows/ci.yml) – backend tests, frontend tests + build |

#### Potential Gaps / Friction Points

| Metric | Gap | Notes |
|--------|-----|-------|
| **1-minute flow** | Registration has 4 fields (full_name, date_of_birth, email, password); preference form has mood + binge + optional advanced (genres, language, episode length, context) | Could streamline: e.g. minimal registration, or "quick start" with defaults |
| **1-minute flow** | Home → Recommend requires explicit navigation; no "guest" path that skips registration | Unauthenticated users get recommendations but cannot save to watchlist |
| **Search relevance** | No explicit validation that semantic search returns 1–2 "clearly relevant" results | Quality depends on embeddings + catalog; may need tuning or user feedback loop |
| **Simple setup** | Backend/frontend run separately (venv + npm); [frontend/Dockerfile](../frontend/Dockerfile) exists but untracked | docker-compose has db only; full Docker stack could simplify "one command" setup |
| **CI** | Backend tests run without DB in CI | Some tests may skip or mock DB; worth confirming coverage |

---

### 4. Roadmap (MVP / V2 / V3)

#### MVP (Job-Ready)

- **Auth + Profile:** Registration/Login (JWT) with full_name, date_of_birth, email, password
- **Recommendations (Mood + Constraints):** Input form + engine returning Top N shows
- **Explainability:** Each recommendation includes a short "Why this?" (1–2 reasons)
- **Watchlist:** Save from results, view watchlist, remove items
- **Semantic Search:** Free-text search with pgvector (natural-language descriptions)
- **Stable Data Layer:** PostgreSQL + Alembic + optional TMDB enrichment (write-through cache)
- **Demo Readiness:** Docker Compose (db + backend + frontend), pytest + Vitest, CI

#### V2 (Nice-to-Have)

- **"More Like This":** Vector similarity recommendations (backend exists; add frontend UI)
- **User Preferences:** Persistent settings (genres/language/max length) with auto-fill
- **Feedback:** Simple Like/Dislike for future re-ranking
- **Recommendation Logs:** Session tracking (input/results/latency)
- **Systematic CI:** Expanded test coverage + GitHub Actions

#### V3 (Future)

- **Personalized Ranking:** History-based re-ranking
- **A/B Testing:** Comparing algorithm versions via logs
- **Advanced Caching:** Redis, rate limiting
- **Observability:** Metrics, tracing, dashboards
- **Production Deployment:** Cloud infrastructure (CD, secrets, monitoring)

---

### 5. Recommended Next Steps (For Later Planning)

1. **Step 2** – Define explicit planning steps (e.g. UX flow, API contracts, data model) that reference Step 1.
2. **Gap review** – When prioritizing work, use the gaps above (1-minute flow, search relevance, setup simplicity) to decide what to tackle first.

---

### 6. Decision Rule for Future Suggestions

When proposing changes:

- **Do** align with: fast time-to-first-recommendation, mood + constraints, semantic search, portfolio quality.
- **Avoid** unless discussed: features that add friction (e.g. long onboarding, extra required fields), scope creep beyond "find a show quickly," or complexity that hurts setup/tests/docs.
