from datetime import date
import json
import logging
import re
from pathlib import Path
from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from sqlalchemy import or_

from app.db import get_db
from app.embeddings import EMBED_DIM, embed_text
from app.models import Show
from app.schemas import SemanticSearchRequest, SemanticSearchResult, MoreLikeThisRequest
from app.shared import TMDB_TV_GENRE_ID_TO_NAME, shorten_text
from app.exceptions import (
    AppException,
    QUERY_REQUIRED,
    EMBEDDING_ERROR,
    SEARCH_FAILED,
    SHOW_NOT_FOUND,
    SHOW_NO_EMBEDDING,
)


router = APIRouter(prefix="/search", tags=["search"])
logger = logging.getLogger(__name__)

# Temporary debug: log semantic search for /search page flow (query "sitcom about a workplace").
_DEBUG_SEARCH_QUERY = "sitcom about a workplace"
_DEBUG_LOG_PATH = Path(__file__).resolve().parents[2] / "debug-8701ad.log"


def _debug_append_log(payload: dict) -> None:
    try:
        with open(_DEBUG_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")
    except Exception as e:
        logger.warning("[debug search] Failed to write debug log: %s", e)


def _short_overview(text: str | None) -> str:
    return shorten_text(text, fallback="No overview available.")


def normalize_genres(value) -> list[str]:
    if not isinstance(value, list):
        return []

    out: list[str] = []
    for g in value:
        if isinstance(g, int):
            out.append(TMDB_TV_GENRE_ID_TO_NAME.get(g, str(g)))
        elif isinstance(g, str):
            cleaned = g.strip()
            if cleaned:
                out.append(cleaned)
        else:
            out.append(str(g))
    return out


# Stopwords to exclude from explanation overlap logic (avoids "themes around 'about'").
_STOPWORDS = frozenset({
    "about", "the", "and", "for", "with", "that", "this", "like", "from", "into",
    "when", "what", "where", "who", "how", "some", "any", "have", "has", "had",
    "been", "being", "which", "were", "are", "was", "not", "just", "only", "more",
    "most", "other", "such", "than", "then", "them", "their", "there", "these",
    "they", "will", "would", "could", "should", "does", "done",
})


def _tokenize(text: str | None) -> set[str]:
    if not text:
        return set()
    return {t for t in re.findall(r"[a-z0-9]+", text.lower()) if len(t) > 2}


def _distance_bucket(distance: float | None) -> str:
    if distance is None:
        return "A relevant semantic match"
    if distance <= 0.18:
        return "A very close semantic match"
    if distance <= 0.26:
        return "A strong semantic match"
    if distance <= 0.36:
        return "A good semantic match"
    return "A related semantic match"


def _match_score_percent(distance: float | None) -> int:
    """
    Convert cosine distance (lower is better) to a simple percentage score.
    score = (1 - distance) * 100, clamped to [0, 100].
    """
    if distance is None:
        return 0
    score = (1.0 - distance) * 100.0
    if score < 0:
        return 0
    if score > 100:
        return 100
    return int(round(score))


# Hybrid retrieval: pool sizes for semantic and keyword sources before merge.
HYBRID_SEMANTIC_POOL_MULTIPLIER = 2  # fetch 2x top_k from vector search
HYBRID_KEYWORD_POOL_MULTIPLIER = 2  # fetch 2x top_k from keyword search
HYBRID_SEMANTIC_WEIGHT = 0.6  # weight for semantic similarity (1 - distance)
HYBRID_KEYWORD_WEIGHT = 0.4   # weight for keyword match score
DEFAULT_DISTANCE_WHEN_NO_SEMANTIC = 0.5  # used for keyword-only candidates in response
RELEVANCE_FLOOR_COMBINED_SCORE = 0.32  # exclude weak matches; may return fewer than top_k


def _query_terms(query: str) -> list[str]:
    """Tokenize query into words (alphanumeric, length > 2) for keyword matching. Excludes stopwords."""
    raw = [t for t in re.findall(r"[a-z0-9]+", query.lower()) if len(t) > 2]
    return [t for t in raw if t not in _STOPWORDS]


def _keyword_match_count(show: Show, terms: list[str]) -> int:
    """Count how many query terms appear in the show's title or overview."""
    title = (show.title or "").lower()
    overview = (show.overview or "").lower()
    return sum(1 for t in terms if t in title or t in overview)


def _fetch_keyword_candidates(db: Session, query: str, limit: int) -> list[tuple[Show, int]]:
    """
    Fetch shows that match any query term in title or overview (ILIKE).
    Return list of (Show, keyword_score) sorted by keyword_score desc, up to `limit` items.
    """
    terms = _query_terms(query)
    if not terms:
        return []
    # One OR per term: (title ILIKE %term% OR overview ILIKE %term%)
    clause = or_(
        *[
            or_(
                Show.title.ilike(f"%{t}%"),
                Show.overview.ilike(f"%{t}%"),
            )
            for t in terms
        ]
    )
    rows = db.query(Show).filter(clause).limit(limit * 3).all()  # over-fetch then re-rank
    scored = [(s, _keyword_match_count(s, terms)) for s in rows]
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:limit]


def _build_fallback_match_reason(query: str, title: str, genres: list[str], overview: str | None, distance: float | None) -> str:
    query_tokens = _tokenize(query) - _STOPWORDS
    title_tokens = _tokenize(title)
    overview_tokens = _tokenize(overview)
    genre_tokens = _tokenize(" ".join(genres))

    overlap_title = query_tokens & title_tokens
    overlap_overview = query_tokens & overview_tokens
    overlap_genres = query_tokens & genre_tokens
    distance_phrase = _distance_bucket(distance)
    score = _match_score_percent(distance)
    prefix = f"Match Score: {score}% - {distance_phrase}"

    if overlap_genres:
        sample = sorted(overlap_genres)[0]
        return f"{prefix} that aligns with your {sample} vibe."
    if overlap_title:
        sample = sorted(overlap_title)[0]
        return f"{prefix} with title cues matching '{sample}'."
    if overlap_overview:
        sample = sorted(overlap_overview)[0]
        return f"{prefix} with themes around '{sample}'."
    if genres:
        top_genres = ", ".join(genres[:2])
        return f"{prefix} in genres like {top_genres}."
    return f"{prefix} based on plot and tone similarity."


@router.post("/semantic", response_model=List[SemanticSearchResult])
def semantic_search(payload: SemanticSearchRequest, db: Session = Depends(get_db)):
    """
    Hybrid search: semantic (pgvector) + keyword (title/overview ILIKE).
    Both candidate sets are merged, deduplicated by show id, and ranked by a combined score.
    """
    query = payload.query.strip()
    if not query:
        raise AppException(
            status_code=400,
            error_code=QUERY_REQUIRED,
            message="Query cannot be empty",
            details={},
        )

    top_k = min(int(payload.top_k or 10), 50)
    pool_size = max(top_k * HYBRID_SEMANTIC_POOL_MULTIPLIER, top_k * HYBRID_KEYWORD_POOL_MULTIPLIER, 20)

    # --- 1. Semantic candidates: top pool_size by vector similarity ---
    query_vec = embed_text(query)
    if len(query_vec) != EMBED_DIM:
        raise AppException(
            status_code=500,
            error_code=EMBEDDING_ERROR,
            message="Embedding failed; please try again.",
            details={},
        )
    distance_expr = Show.embedding.cosine_distance(query_vec).label("distance")
    try:
        semantic_rows = (
            db.query(Show, distance_expr)
            .filter(Show.embedding.isnot(None))
            .order_by(distance_expr.asc())
            .limit(pool_size)
            .all()
        )
    except Exception as e:
        logger.exception("Semantic search DB query failed")
        raise AppException(
            status_code=503,
            error_code=SEARCH_FAILED,
            message="Search is temporarily unavailable. Please try again later.",
            details={},
        ) from e

    # --- 2. Keyword candidates: top pool_size by term match in title/overview ---
    keyword_rows = _fetch_keyword_candidates(db, query, pool_size)
    terms = _query_terms(query)

    # --- 3. Merge by show id: keep best semantic distance and keyword score per show ---
    merged: dict[int, dict] = {}
    for show, distance in semantic_rows:
        d = float(distance) if distance is not None else float("inf")
        merged[show.id] = {
            "show": show,
            "semantic_distance": d,
            "keyword_score": _keyword_match_count(show, terms),
        }
    for show, kw_score in keyword_rows:
        if show.id not in merged:
            merged[show.id] = {
                "show": show,
                "semantic_distance": None,
                "keyword_score": kw_score,
            }
        else:
            merged[show.id]["keyword_score"] = max(merged[show.id]["keyword_score"], kw_score)

    # --- 4. Combined score and sort: higher = better ---
    def _combined_score(entry: dict) -> float:
        sem = entry["semantic_distance"]
        kw = entry["keyword_score"]
        semantic_score = (1.0 - sem) if sem is not None else 0.0
        keyword_norm = min(1.0, kw / max(1, len(terms))) if terms else 0.0
        return HYBRID_SEMANTIC_WEIGHT * semantic_score + HYBRID_KEYWORD_WEIGHT * keyword_norm

    sorted_entries = sorted(merged.values(), key=_combined_score, reverse=True)[:top_k]
    filtered_entries = [e for e in sorted_entries if _combined_score(e) >= RELEVANCE_FLOOR_COMBINED_SCORE]

    # --- 5. Build response: SemanticSearchResult with real or default distance ---
    results: list[SemanticSearchResult] = []
    for entry in filtered_entries:
        show = entry["show"]
        dist = entry["semantic_distance"]
        distance_value = dist if dist is not None else DEFAULT_DISTANCE_WHEN_NO_SEMANTIC
        first_air_date = show.first_air_date.isoformat() if isinstance(show.first_air_date, date) else None
        genres = normalize_genres(show.genres)
        match_reason = _build_fallback_match_reason(
            query=query,
            title=show.title,
            genres=genres,
            overview=show.overview,
            distance=dist,
        )
        results.append(
            SemanticSearchResult(
                id=show.id,
                title=show.title,
                genres=genres,
                overview=_short_overview(show.overview),
                poster_url=show.poster_url,
                vote_average=show.vote_average,
                first_air_date=first_air_date,
                distance=distance_value,
                ai_match_reason=match_reason,
            )
        )

    # #region agent log — debug /search/semantic final list returned to frontend
    if query.strip().lower() == _DEBUG_SEARCH_QUERY:
        try:
            final_list = [
                {"rank": i + 1, "title": r.title, "id": r.id, "distance": r.distance}
                for i, r in enumerate(results)
            ]
            _debug_append_log({
                "sessionId": "8701ad",
                "location": "routers/search.py:semantic_search",
                "message": "search flow: final list returned to frontend (hybrid)",
                "data": {"query": query, "ranked": final_list, "count": len(final_list)},
                "hypothesisId": "H2",
                "timestamp": __import__("time").time() * 1000,
            })
        except Exception as e:
            logger.warning("[debug search] final list log failed: %s", e)
    # #endregion

    return results


@router.post("/more-like-this", response_model=List[SemanticSearchResult])
def more_like_this(payload: MoreLikeThisRequest, db: Session = Depends(get_db)):
    show = db.query(Show).filter(Show.id == payload.show_id).first()
    if show is None:
        raise AppException(
            status_code=404,
            error_code=SHOW_NOT_FOUND,
            message="Show not found",
            details={"show_id": payload.show_id},
        )
    if show.embedding is None:
        raise AppException(
            status_code=400,
            error_code=SHOW_NO_EMBEDDING,
            message="Show does not have an embedding",
            details={"show_id": payload.show_id},
        )

    top_k = min(int(payload.top_k or 10), 50)
    distance_expr = Show.embedding.cosine_distance(show.embedding).label("distance")

    rows = (
        db.query(Show, distance_expr)
        .filter(Show.embedding.isnot(None))
        .filter(Show.id != show.id)
        .order_by(distance_expr.asc())
        .limit(top_k)
        .all()
    )

    results: list[SemanticSearchResult] = []
    for row, distance in rows:
        first_air_date = row.first_air_date.isoformat() if isinstance(row.first_air_date, date) else None
        results.append(
            SemanticSearchResult(
                id=row.id,
                title=row.title,
                genres=normalize_genres(row.genres),
                overview=_short_overview(row.overview),
                poster_url=row.poster_url,
                vote_average=row.vote_average,
                first_air_date=first_air_date,
                distance=float(distance) if distance is not None else float("inf"),
            )
        )

    results.sort(key=lambda r: r.distance)
    return results

