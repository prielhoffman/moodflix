from datetime import date
import logging
import json
import time as _time
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.embeddings import EMBED_DIM, embed_text
from app.models import Show
from app.schemas import SemanticSearchRequest, SemanticSearchResult


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


def _debug_log(message: str, data: dict, *, hypothesis_id: str, run_id: str = "pre-fix") -> None:
    try:
        payload = {
            "id": f"log_{int(_time.time() * 1000)}_{hypothesis_id}",
            "timestamp": int(_time.time() * 1000),
            "location": "app/routers/search.py",
            "message": message,
            "data": data,
            "runId": run_id,
            "hypothesisId": hypothesis_id,
        }
        with open(r"c:\Users\Owner\Desktop\Github-Projects\MoodFlix\.cursor\debug.log", "a", encoding="utf-8") as f:
            f.write(json.dumps(payload) + "\n")
    except Exception:
        pass


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
    # region agent log
    _debug_log(
        "semantic_search_entry",
        {"query_raw": payload.query, "top_k": payload.top_k},
        hypothesis_id="H1",
    )
    # endregion agent log

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
        # region agent log
        _debug_log(
            "semantic_search_db_query_start",
            {"top_k": top_k},
            hypothesis_id="H2",
        )
        # endregion agent log
        rows = (
            db.query(Show, distance_expr)
            .filter(Show.embedding.isnot(None))
            .order_by(distance_expr.asc())
            .limit(top_k)
            .all()
        )
        # region agent log
        _debug_log(
            "semantic_search_db_query_done",
            {"rows_count": len(rows)},
            hypothesis_id="H2",
        )
        # endregion agent log
    except Exception as e:
        # region agent log
        _debug_log(
            "semantic_search_db_query_error",
            {"error": str(e)},
            hypothesis_id="H2",
        )
        # endregion agent log
        logger.exception("Semantic search DB query failed")
        raise HTTPException(status_code=500, detail=f"Semantic search DB query failed: {e}") from e

    results: list[SemanticSearchResult] = []
    for show, distance in rows:
        first_air_date = show.first_air_date.isoformat() if isinstance(show.first_air_date, date) else None
        genres = normalize_genres(show.genres)
        # region agent log
        _debug_log(
            "semantic_search_row_genres",
            {"show_id": getattr(show, "id", None), "genres_type": type(genres).__name__, "genres_value": genres},
            hypothesis_id="H3",
        )
        # endregion agent log

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

