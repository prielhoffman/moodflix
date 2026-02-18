from datetime import date
import logging
import re
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.embeddings import EMBED_DIM, embed_text
from app.models import Show
from app.schemas import SemanticSearchRequest, SemanticSearchResult, MoreLikeThisRequest
from app.shared import TMDB_TV_GENRE_ID_TO_NAME, shorten_text


router = APIRouter(prefix="/search", tags=["search"])
logger = logging.getLogger(__name__)

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


def _build_fallback_match_reason(query: str, title: str, genres: list[str], overview: str | None, distance: float | None) -> str:
    query_tokens = _tokenize(query)
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
    Semantic search over shows using pgvector cosine distance.
    Lower distance = more similar.
    """
    query = payload.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="query cannot be empty")

    top_k = min(int(payload.top_k or 10), 50)

    query_vec = embed_text(query)
    if len(query_vec) != EMBED_DIM:
        raise HTTPException(
            status_code=500,
            detail=f"Embedding dim mismatch: got {len(query_vec)} expected {EMBED_DIM}",
        )

    # Cosine distance is appropriate for normalized embeddings (lower = more similar).
    distance_expr = Show.embedding.cosine_distance(query_vec).label("distance")

    try:
        rows = (
            db.query(Show, distance_expr)
            .filter(Show.embedding.isnot(None))
            .order_by(distance_expr.asc())
            .limit(top_k)
            .all()
        )
    except Exception as e:
        logger.exception("Semantic search DB query failed")
        raise HTTPException(status_code=500, detail=f"Semantic search DB query failed: {e}") from e

    results: list[SemanticSearchResult] = []
    for show, distance in rows:
        distance_value = float(distance) if distance is not None else float("inf")
        first_air_date = show.first_air_date.isoformat() if isinstance(show.first_air_date, date) else None
        genres = normalize_genres(show.genres)
        match_reason = _build_fallback_match_reason(
            query=query,
            title=show.title,
            genres=genres,
            overview=show.overview,
            distance=distance_value if distance is not None else None,
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

    # Defensive sort (DB should already order, but helps with mocks/tests).
    results.sort(key=lambda r: r.distance)
    return results


@router.post("/more-like-this", response_model=List[SemanticSearchResult])
def more_like_this(payload: MoreLikeThisRequest, db: Session = Depends(get_db)):
    show = db.query(Show).filter(Show.id == payload.show_id).first()
    if show is None:
        raise HTTPException(status_code=404, detail="Show not found")
    if show.embedding is None:
        raise HTTPException(status_code=400, detail="Show does not have an embedding")

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

