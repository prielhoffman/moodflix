from __future__ import annotations

from datetime import date
from typing import Any, List, Optional

from app.schemas import (
    RecommendationInput,
    RecommendationOutput,
    BingePreference,
    Mood,
    EpisodeLengthPreference,
    WatchingContext,
)
from app.data import get_all_shows
from app.tmdb import search_tv_show
from app.embeddings import EMBED_DIM, embed_text
from app.models import Show
from app.shared import TMDB_TV_GENRE_ID_TO_NAME, shorten_text
from sqlalchemy.orm import Session


# -------------------- Safety --------------------
_ADULT_RATINGS = {"TV-MA"}


# -------------------- Mood → Genre soft mapping --------------------
_MOOD_GENRE_MAP = {
    Mood.CHILL: {"comedy", "slice of life", "lifestyle", "animation", "documentary", "design"},
    Mood.HAPPY: {"comedy", "romance", "family", "musical", "talent", "cooking"},
    Mood.FAMILIAR: {"sitcom", "procedural", "family", "animation", "reality"},
    Mood.FOCUSED: {"drama", "mystery", "historical", "legal", "medical", "competition"},
    Mood.ADRENALINE: {"action", "adventure", "sci-fi", "fantasy", "survival", "competition"},
    Mood.DARK: {"thriller", "crime", "horror", "psychological", "true crime"},
    Mood.CURIOUS: {"documentary", "travel", "culture", "anthology", "celebrity", "reality"},
}


def _coerce_genres(value: Any) -> list[str]:
    """
    Normalize genres from DB/static into list[str].
    - If list[int] (TMDB ids), map to names when possible.
    - If list[str], lower-case and keep.
    - Otherwise return empty list.
    """
    if not isinstance(value, list):
        return []

    out: list[str] = []
    for g in value:
        if isinstance(g, int):
            name = TMDB_TV_GENRE_ID_TO_NAME.get(g)
            if name:
                out.append(name)
        elif isinstance(g, str):
            if g.strip():
                out.append(g.strip())
    return out


def _build_short_summary(overview: str | None) -> str:
    return shorten_text(overview, fallback="No summary available.")


def _convert_show_row(row: Show) -> dict:
    genres = _coerce_genres(row.genres)

    return {
        "title": row.title,
        "recommendation_reason": None,
        "genres": genres,
        "short_summary": _build_short_summary(row.overview),
        # These fields don't exist in the current DB schema yet;
        # keep them as None so filters can treat them as "unknown".
        "content_rating": None,
        "average_episode_length": None,
        "number_of_seasons": None,
        "language": None,
        # Optional fields we can use as a fallback when TMDB enrichment is unavailable.
        "poster_url": row.poster_url,
        "tmdb_rating": row.vote_average,
        "tmdb_overview": row.overview,
        "first_air_date": row.first_air_date,
    }


def _load_shows_from_rows(rows: list[Show]) -> list[dict]:
    return [_convert_show_row(row) for row in rows]


def _load_shows_from_db(db: Session) -> list[dict]:
    rows = db.query(Show).all()
    return _load_shows_from_rows(rows)


def _fetch_candidate_rows(db: Session, query_vec: list[float], top_k: int) -> list[Show]:
    if len(query_vec) != EMBED_DIM:
        return []

    distance_expr = Show.embedding.cosine_distance(query_vec)
    return (
        db.query(Show)
        .filter(Show.embedding.isnot(None))
        .order_by(distance_expr.asc())
        .limit(top_k)
        .all()
    )


def _build_recommendation_reason(
    *,
    common_genres: set,
    binge_preference: BingePreference,
    seasons: int | None,
    episode_length: int | None,
    episode_length_pref: EpisodeLengthPreference,
    mood_matched: bool,
    mood: Mood,
) -> str | None:
    reasons = []

    if common_genres:
        reasons.append(
            f"Matches your interest in {', '.join(sorted(common_genres))}"
        )

    if seasons is not None:
        if binge_preference == BingePreference.SHORT_SERIES and seasons <= 3:
            reasons.append("Easy to finish in one season")
        elif binge_preference == BingePreference.BINGE and seasons > 3:
            reasons.append("Great for binge watching")

    if episode_length is not None:
        if episode_length_pref == EpisodeLengthPreference.SHORT and episode_length <= 30:
            reasons.append("Short, easy-to-watch episodes")
        elif episode_length_pref == EpisodeLengthPreference.LONG and episode_length > 30:
            reasons.append("Long, immersive episodes")
    else:
        # DB-backed shows currently don't have episode length populated.
        # If the user explicitly asked for SHORT/LONG, be honest about missing info.
        if episode_length_pref in (EpisodeLengthPreference.SHORT, EpisodeLengthPreference.LONG):
            reasons.append("Episode length info is unavailable")

    if mood_matched:
        if mood == Mood.CHILL:
            reasons.append("Relaxed and easy to watch")
        elif mood == Mood.HAPPY:
            reasons.append("Feel-good and uplifting")
        elif mood == Mood.FAMILIAR:
            reasons.append("Comforting and familiar vibe")
        elif mood == Mood.FOCUSED:
            reasons.append("Engaging and easy to focus on")
        elif mood == Mood.ADRENALINE:
            reasons.append("High-energy and exciting")
        elif mood == Mood.DARK:
            reasons.append("Darker, more intense tone")
        elif mood == Mood.CURIOUS:
            reasons.append("Great for curiosity and discovery")

    # Keep the response short, but allow the "unknown episode length" note to be included.
    if not reasons:
        return None

    top = reasons[:2]
    note = "Episode length info is unavailable"
    if note in reasons and note not in top:
        top.append(note)

    return ". ".join(top)


def recommend_shows(
    user_input: RecommendationInput,
    *,
    db: Optional[Session] = None,
    top_n: int = 10,
    candidate_top_k: int = 80,
) -> List[RecommendationOutput]:
    """
    Recommend shows based on user input.

    Data source priority:
    1) Postgres `shows` table (if db provided and has rows)
    2) Static dataset in app/data.py (fallback for empty DB or DB errors)
    """
    shows: list[dict] = []

    query_text = user_input.query.strip() if user_input.query else ""
    if query_text and db is not None:
        try:
            query_vec = embed_text(query_text)
            candidate_rows = _fetch_candidate_rows(db, query_vec, candidate_top_k)
            shows = _load_shows_from_rows(candidate_rows)
        except Exception:
            shows = []
    else:
        if db is not None:
            try:
                shows = _load_shows_from_db(db)
            except Exception:
                # Best-effort fallback: recommendations should still work even if DB is down.
                shows = []

    if not shows:
        shows = get_all_shows()

    scored: list[dict] = []

    for show in shows:
        # ---------- Hard filters (unchanged) ----------

        rating = show.get("content_rating")
        if rating:
            if user_input.watching_context == WatchingContext.FAMILY and rating in _ADULT_RATINGS:
                continue
            if user_input.age < 16 and rating in _ADULT_RATINGS:
                continue

        seasons = show.get("number_of_seasons")
        if seasons is not None:
            if user_input.binge_preference == BingePreference.SHORT_SERIES and seasons > 3:
                continue
            if user_input.binge_preference == BingePreference.BINGE and seasons <= 3:
                continue

        episode_length = show.get("average_episode_length")
        if user_input.episode_length_preference == EpisodeLengthPreference.SHORT:
            if episode_length is not None and episode_length > 30:
                continue
        if user_input.episode_length_preference == EpisodeLengthPreference.LONG:
            if episode_length is not None and episode_length <= 30:
                continue

        if user_input.language_preference:
            show_language = show.get("language")
            if show_language and show_language != user_input.language_preference:
                continue

        # ---------- Soft matching ----------

        score = 0

        user_genres = set(g.lower() for g in user_input.preferred_genres)
        show_genres = set(g.lower() for g in _coerce_genres(show.get("genres", [])))

        common_genres = user_genres & show_genres
        if common_genres:
            score += len(common_genres)

        # Mood soft signal
        mood_genres = _MOOD_GENRE_MAP.get(user_input.mood, set())
        mood_matched = bool(show_genres & mood_genres)

        if mood_matched:
            score += 1

        recommendation_reason = _build_recommendation_reason(
            common_genres=common_genres,
            binge_preference=user_input.binge_preference,
            seasons=seasons,
            episode_length=episode_length,
            episode_length_pref=user_input.episode_length_preference,
            mood_matched=mood_matched,
            mood=user_input.mood,
        )

        scored.append(
            {
                "score": score,
                "show": show,
                "recommendation_reason": recommendation_reason,
            }
        )

    scored.sort(key=lambda x: x["score"], reverse=True)
    top_scored = scored[: max(1, int(top_n))]

    outputs: list[RecommendationOutput] = []

    for item in top_scored:
        show = item["show"]
        recommendation_reason = item["recommendation_reason"]

        # ---------- TMDB Enrichment (best-effort / optional) ----------
        tmdb_data = search_tv_show(show["title"])

        # DB fallback fields (may be absent on static dataset)
        db_poster_url = show.get("poster_url")
        db_rating = show.get("tmdb_rating")
        db_overview = show.get("tmdb_overview")
        db_first_air_date: date | str | None = show.get("first_air_date")

        if isinstance(db_first_air_date, date):
            db_first_air_date_str = db_first_air_date.isoformat()
        else:
            db_first_air_date_str = db_first_air_date

        outputs.append(
            RecommendationOutput(
                title=show["title"],
                recommendation_reason=recommendation_reason,
                genres=_coerce_genres(show.get("genres", [])),
                short_summary=show.get("short_summary") or _build_short_summary(show.get("tmdb_overview")),
                content_rating=show.get("content_rating"),
                average_episode_length=show.get("average_episode_length"),
                number_of_seasons=show.get("number_of_seasons"),
                language=show.get("language"),

                # TMDB fields (may be None). Use DB values as a fallback where safe.
                poster_url=(
                    tmdb_data.get("poster_url")
                    if tmdb_data and tmdb_data.get("poster_url")
                    else db_poster_url
                ),
                tmdb_rating=(
                    tmdb_data.get("rating")
                    if tmdb_data and tmdb_data.get("rating") is not None
                    else db_rating
                ),
                tmdb_overview=(
                    tmdb_data.get("overview")
                    if tmdb_data and tmdb_data.get("overview")
                    else None
                ),
                first_air_date=(
                    tmdb_data.get("first_air_date")
                    if tmdb_data and tmdb_data.get("first_air_date")
                    else db_first_air_date_str
                ),
            )
        )

    return outputs
