from datetime import date
import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.embeddings import EMBED_DIM, embed_text
from app.models import Show
from app.schemas import SemanticSearchRequest, SemanticSearchResult, MoreLikeThisRequest


router = APIRouter(prefix="/search", tags=["search"])
logger = logging.getLogger(__name__)

_TMDB_TV_GENRE_ID_TO_NAME: dict[int, str] = {
    10759: "action",
    16: "animation",
    35: "comedy",
    80: "crime",
    99: "documentary",
    18: "drama",
    10751: "family",
    10762: "kids",
    9648: "mystery",
    10763: "news",
    10764: "reality",
    10765: "sci-fi",
    10766: "soap",
    10767: "talk",
    10768: "war",
    37: "western",
}


def _short_overview(text: str | None) -> str:
    if text and text.strip():
        t = text.strip()
        return t if len(t) <= 220 else t[:217].rstrip() + "..."
    return "No overview available."


def normalize_genres(value) -> list[str]:
    if not isinstance(value, list):
        return []

    out: list[str] = []
    for g in value:
        if isinstance(g, int):
            out.append(_TMDB_TV_GENRE_ID_TO_NAME.get(g, str(g)))
        elif isinstance(g, str):
            cleaned = g.strip()
            if cleaned:
                out.append(cleaned)
        else:
            out.append(str(g))
    return out


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
        first_air_date = show.first_air_date.isoformat() if isinstance(show.first_air_date, date) else None
        genres = normalize_genres(show.genres)

        results.append(
            SemanticSearchResult(
                id=show.id,
                title=show.title,
                genres=genres,
                overview=_short_overview(show.overview),
                poster_url=show.poster_url,
                vote_average=show.vote_average,
                first_air_date=first_air_date,
                distance=float(distance) if distance is not None else float("inf"),
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

