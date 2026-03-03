from __future__ import annotations

import logging
import math
import os
import random
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from typing import Any, List, Optional

import app.tmdb as tmdb_adapter
from app.schemas import (
    RecommendationInput,
    RecommendationOutput,
    BingePreference,
    Mood,
    EpisodeLengthPreference,
    WatchingContext,
)
from app.data import get_all_shows
from app.tmdb import get_tv_details_cached
from app.embeddings import EMBED_DIM, embed_text
from app.models import Show
from app.shared import TMDB_TV_GENRE_ID_TO_NAME, shorten_text
from app import config
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def _int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        value = int(raw)
        return value if value > 0 else default
    except ValueError:
        return default


TMDB_ENRICH_MAX_WORKERS = _int_env("TMDB_ENRICH_MAX_WORKERS", 5)


# -------------------- Safety --------------------
_ADULT_RATINGS = {"TV-MA", "TV-14", "R", "NC-17", "PG-13"}

# Family context: only these ratings allowed (strict whitelist).
_FAMILY_SAFE_RATINGS = {"G", "PG", "TV-G", "TV-PG", "TV-Y", "TV-Y7", "TV-Y7-FV"}

# Genres to exclude when watching with family (violence, horror, adult themes).
_FAMILY_UNSAFE_GENRES = {"crime", "horror", "thriller", "true crime", "war"}

# Genres to boost when in Family context (clean, age-appropriate).
_FAMILY_FRIENDLY_GENRES = {"animation", "family", "comedy"}

# For relaxed Family fallback: "all ages" content must have at least one of these.
_FAMILY_FALLBACK_GENRES = {"animation", "family", "comedy", "documentary"}

# TMDB genre IDs to block for Kids/Family (DB stores genre_ids as integers).
_ADULT_GENRE_IDS = {80, 9648, 10768, 10763}  # Crime, Mystery, War, News

# Keywords in title/overview that indicate adult content (case-insensitive).
_KIDS_KEYWORD_BLOCKLIST = {
    "murder", "criminal", "victim", "sexual", "investigation", "police",
    "blood", "terrorist", "drug",
}

# Title substrings that indicate shows to block in Kids/Family context (case-insensitive).
_KIDS_TITLE_BLACKLIST = {
    "law & order",
    "grey's anatomy",
    "grey anatomy",
    "csi:",
    "criminal minds",
    "ncis",
    "svu",
    "the walking dead",
    "game of thrones",
    "breaking bad",
    "squid game",
}


# Kids/Family safety: show must have at least one of these genre IDs (or pass exception rule).
_KIDS_SAFE_GENRE_IDS = {10751, 10762, 16}  # Family, Kids, Animation
_KIDS_EXCEPTION_GENRE_IDS = {99, 35}       # Documentary, Comedy (allowed only without Drama/Crime)
_KIDS_EXCLUDED_IF_EXCEPTION = {18, 80}     # Drama, Crime
_FAMILY_GENRE_ID = 10751


# -------------------- Mood → Genre soft mapping --------------------
# Mood is the star: these genres get the mood boost. e.g. Happy prioritizes comedy & animation over drama.
_MOOD_GENRE_MAP = {
    # Keep CHILL and FAMILIAR anchored around mainstream comfort genres.
    Mood.CHILL: {"comedy", "sitcom", "reality", "lifestyle", "family", "romance"},
    # Happy: comedy and animation first; no heavy drama.
    Mood.HAPPY: {"comedy", "animation", "romance", "family", "musical", "reality"},
    Mood.FAMILIAR: {"sitcom", "procedural", "family", "comedy", "reality", "animation"},
    Mood.FOCUSED: {"drama", "mystery", "historical", "legal", "medical", "competition"},
    Mood.ADRENALINE: {"action", "adventure", "sci-fi", "fantasy", "survival", "competition"},
    # Dark: thriller, horror, psychological (exclude generic 'crime' to avoid light procedurals like The Rookie).
    Mood.DARK: {"thriller", "horror", "psychological", "true crime"},
    Mood.CURIOUS: {"documentary", "travel", "culture", "anthology", "celebrity", "reality"},
}

_LOW_PRIORITY_GENRES = {"talk", "talk-show", "talk show", "variety", "news"}
_KIDS_GENRES = {"kids", "children", "children's", "preschool"}
_ENGLISH_HINTS = {"en", "english"}
_FOREIGN_INTENT_HINTS = {
    "korean",
    "k-drama",
    "kdrama",
    "japanese",
    "anime",
    "spanish",
    "french",
    "german",
    "hindi",
    "arabic",
    "foreign",
    "subtitled",
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


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def _normalize_from_range(value: float | None, min_v: float, max_v: float, fallback: float = 0.0) -> float:
    if value is None:
        return fallback
    if max_v <= min_v:
        return _clamp01(value)
    return _clamp01((value - min_v) / (max_v - min_v))


def _normalize_rating(vote_average: float | None) -> float:
    if vote_average is None:
        return 0.0
    return _clamp01(vote_average / 10.0)


def _normalize_vote_count(vote_count: float | None, min_v: float, max_v: float) -> float:
    if vote_count is None:
        return 0.0
    # Log scale so massive franchises do not completely dominate.
    value = math.log1p(max(0.0, vote_count))
    return _normalize_from_range(value, min_v, max_v, fallback=0.0)


def _normalize_lang(value: str | None) -> str | None:
    if not value:
        return None
    return value.strip().lower()


def _is_english_language(value: str | None) -> bool:
    lang = _normalize_lang(value)
    return bool(lang and lang in _ENGLISH_HINTS)


def _has_foreign_intent(user_input: RecommendationInput) -> bool:
    if user_input.language_preference and not _is_english_language(user_input.language_preference):
        return True
    q = (user_input.query or "").lower()
    return any(hint in q for hint in _FOREIGN_INTENT_HINTS)


def _get_genre_ids(genres_raw: Any) -> set[int]:
    """Extract set of TMDB genre IDs from raw genres (list of ints or names)."""
    if not isinstance(genres_raw, list):
        return set()
    ids: set[int] = set()
    name_to_id = {v: k for k, v in TMDB_TV_GENRE_ID_TO_NAME.items()}
    for g in genres_raw:
        if isinstance(g, int):
            ids.add(g)
        elif isinstance(g, str) and g.strip():
            key = g.strip().lower()
            if key in name_to_id:
                ids.add(name_to_id[key])
    return ids


def _show_passes_kids_safety_filter(genres_raw: Any) -> bool:
    """True if show has Family/Kids/Animation, or Documentary/Comedy without Drama/Crime."""
    ids = _get_genre_ids(genres_raw)
    if ids & _KIDS_SAFE_GENRE_IDS:
        return True
    if (99 in ids or 35 in ids) and not (ids & _KIDS_EXCLUDED_IF_EXCEPTION):
        return True
    return False


def _show_has_family_kids_animation(genres_raw: Any) -> bool:
    """True if show has at least one of Family (10751), Kids (10762), Animation (16)."""
    return bool(_get_genre_ids(genres_raw) & _KIDS_SAFE_GENRE_IDS)


def _genres_contain_adult_ids(genres_raw: Any) -> bool:
    """True if genres list (IDs or names) contains any adult genre ID. DB stores IDs as ints."""
    if not isinstance(genres_raw, list):
        return False
    for g in genres_raw:
        if isinstance(g, int) and g in _ADULT_GENRE_IDS:
            return True
        if isinstance(g, str):
            # Map name back to ID via shared dict (inverse lookup)
            for gid, name in TMDB_TV_GENRE_ID_TO_NAME.items():
                if name == g.lower() and gid in _ADULT_GENRE_IDS:
                    return True
    return False


def _text_contains_blocked_keywords(text: str | None) -> bool:
    """True if title or overview contains any Kids blocklist keyword."""
    if not text or not isinstance(text, str):
        return False
    lower = text.lower()
    return any(kw in lower for kw in _KIDS_KEYWORD_BLOCKLIST)


def _title_in_kids_blacklist(title: str | None) -> bool:
    """True if title matches any blacklisted show (partial, case-insensitive)."""
    if not title or not isinstance(title, str):
        return False
    lower = title.lower()
    return any(bl in lower for bl in _KIDS_TITLE_BLACKLIST)


def _is_english_text(text: str | None) -> bool:
    """Heuristic: text is mostly ASCII (English). Non-ASCII ratio < threshold."""
    if not text or not isinstance(text, str):
        return True
    try:
        ascii_count = sum(1 for c in text if ord(c) < 128)
        return (ascii_count / len(text)) >= config.ENGLISH_ASCII_RATIO_MIN
    except (ZeroDivisionError, TypeError):
        return True


def _requests_kids_content(user_input: RecommendationInput) -> bool:
    preferred = {g.strip().lower() for g in user_input.preferred_genres if g and g.strip()}
    if preferred & (_KIDS_GENRES | {"animation", "family", "cartoon"}):
        return True
    query = (user_input.query or "").lower()
    return any(token in query for token in ("kids", "children", "family", "cartoon", "animated"))


def _normalize_content_rating(rating: str | None) -> str | None:
    """Normalize content rating for comparison (e.g. TV-G, tv-g -> TV-G)."""
    if not rating or not isinstance(rating, str):
        return None
    return rating.strip().upper()


def _default_rating_for_trusted_show(show: dict) -> str | None:
    """
    When a show has no content_rating (e.g. from local DB), return 'PG' only if it has
    Animation or Comedy genre, so it can pass zero-trust for Kids/Family.
    """
    if show.get("content_rating"):
        return None
    genres = {g.lower() for g in _coerce_genres(show.get("genres", []))}
    if genres & {"animation", "comedy"}:
        return "PG"
    return None


def _convert_show_row(row: Show) -> dict:
    genres = _coerce_genres(row.genres)

    return {
        "id": row.id,
        "tmdb_id": row.tmdb_id,
        "title": row.title,
        "recommendation_reason": None,
        "genres": genres,
        "short_summary": _build_short_summary(row.overview),
        "content_rating": getattr(row, "content_rating", None),
        "average_episode_length": getattr(row, "average_episode_length", None),
        "number_of_seasons": getattr(row, "number_of_seasons", None),
        "language": getattr(row, "original_language", None),
        "original_language": getattr(row, "original_language", None),
        "poster_url": row.poster_url,
        "popularity": row.popularity,
        "vote_count": row.vote_count,
        "tmdb_rating": row.vote_average,
        "vote_average": row.vote_average,
        "tmdb_overview": row.overview,
        "first_air_date": row.first_air_date,
    }


def _load_shows_from_rows(rows: list[Show]) -> list[dict]:
    return [_convert_show_row(row) for row in rows]


def _persist_tmdb_to_show(db: Optional[Session], show_id: Optional[int], tmdb_data: dict) -> None:
    """
    Write-through: persist TMDB metadata to the shows table so future requests
    can read from DB instead of calling the API. Updates fields when tmdb_data
    has values (so DB stays in sync with the last TMDB fetch).
    """
    if db is None or show_id is None or not tmdb_data:
        return
    row = db.query(Show).filter(Show.id == show_id).first()
    if row is None:
        return
    updated = False
    if tmdb_data.get("content_rating") is not None:
        val = (tmdb_data["content_rating"] or "").strip() or None
        if row.content_rating != val:
            row.content_rating = val
            updated = True
    if tmdb_data.get("average_episode_length") is not None:
        if row.average_episode_length != tmdb_data["average_episode_length"]:
            row.average_episode_length = tmdb_data["average_episode_length"]
            updated = True
    if tmdb_data.get("number_of_seasons") is not None:
        if row.number_of_seasons != tmdb_data["number_of_seasons"]:
            row.number_of_seasons = tmdb_data["number_of_seasons"]
            updated = True
    if tmdb_data.get("original_language") is not None:
        val = (tmdb_data["original_language"] or "").strip() or None
        if row.original_language != val:
            row.original_language = val
            updated = True
    if updated:
        db.commit()


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

    # Lead with mood when the show got a mood boost so it's visible in the reason.
    if mood_matched:
        mood_name = mood.value.replace("_", " ").capitalize()
        reasons.append(f"Perfect for your {mood_name} mood!")

    if common_genres:
        reasons.append(
            f"Matches your interest in {', '.join(sorted(common_genres))}"
        )

    if seasons is not None:
        if binge_preference == BingePreference.SHORT_SERIES and seasons <= config.SHORT_SERIES_MAX_SEASONS:
            reasons.append("Easy to finish in one season")
        elif binge_preference == BingePreference.BINGE and seasons > config.BINGE_MIN_SEASONS:
            reasons.append("Great for binge watching")

    if episode_length is not None:
        if episode_length_pref == EpisodeLengthPreference.SHORT and episode_length <= config.SHORT_EPISODE_MAX_MINUTES:
            reasons.append("Short, easy-to-watch episodes")
        elif episode_length_pref == EpisodeLengthPreference.LONG and episode_length > config.LONG_EPISODE_MIN_MINUTES:
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

    top = reasons[: config.MAX_RECOMMENDATION_REASONS]
    note = "Episode length info is unavailable"
    if note in reasons and note not in top:
        top.append(note)

    return ". ".join(top)


def recommend_shows(
    user_input: RecommendationInput,
    *,
    db: Optional[Session] = None,
    age: Optional[int] = None,
    top_n: Optional[int] = None,
    candidate_top_k: Optional[int] = None,
) -> List[RecommendationOutput]:
    """
    Recommend shows based on user input.

    Age is inferred from authenticated user's date_of_birth when available.
    When age is None (unauthenticated), defaults to 18 (adult) so age filtering is skipped.

    Data source priority:
    1) Postgres `shows` table (if db provided and has rows)
    2) Static dataset in app/data.py (fallback for empty DB or DB errors)
    """
    if top_n is None:
        top_n = config.DEFAULT_TOP_N
    if candidate_top_k is None:
        candidate_top_k = config.DEFAULT_CANDIDATE_TOP_K

    # Unauthenticated: use 18 (adult) so we don't restrict content by age.
    user_age = age if age is not None else 18

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

    foreign_intent = _has_foreign_intent(user_input)
    kids_intent = _requests_kids_content(user_input)
    # Family context and age-based flags before building user_genres.
    is_family_context = user_input.watching_context == WatchingContext.FAMILY
    effective_max_age = config.FAMILY_CONTEXT_EFFECTIVE_AGE if is_family_context else user_age
    is_kids_or_family = effective_max_age < config.KIDS_CUTOFF_AGE or is_family_context
    # Zero-trust: require explicit family-safe rating when age < 18 or Kids/Family context.
    zero_trust_rating = (user_age < 18) or is_family_context or kids_intent

    # Auto-genre injection: ensure kids/family when under 13 or Family context.
    user_genres = {g.lower() for g in user_input.preferred_genres if g and g.strip()}
    if is_kids_or_family:
        user_genres = user_genres | {"kids", "family"}
    wants_reality = "reality" in user_genres
    candidate_items: list[dict] = []

    for show in shows:
        # ---------- Hard filters ----------

        rating_raw = show.get("content_rating")
        rating = _normalize_content_rating(rating_raw)
        if not rating and zero_trust_rating:
            default_pg = _default_rating_for_trusted_show(show)
            if default_pg:
                rating = default_pg
                show["content_rating"] = rating
        if zero_trust_rating:
            # Zero-trust: only allow shows with an explicit rating in _FAMILY_SAFE_RATINGS.
            title = show.get("title") or "Unknown"
            if not rating or rating not in _FAMILY_SAFE_RATINGS:
                logger.info("Blocking [%s] because rating is missing or not family-safe.", title)
                continue
            logger.info("Allowing [%s] with rating [%s].", title, rating)
        else:
            # Non-family: block adult ratings below configured age.
            if rating and rating in _ADULT_RATINGS and effective_max_age < config.ADULT_RATING_MIN_AGE:
                continue

        show_genres = {g.lower() for g in _coerce_genres(show.get("genres", []))}

        # Kids/Family: block by TMDB genre IDs (DB stores IDs; static may use names).
        if is_kids_or_family and _genres_contain_adult_ids(show.get("genres", [])):
            continue

        # Kids/Family: block by keywords in title or overview.
        if is_kids_or_family:
            if _text_contains_blocked_keywords(show.get("title")):
                continue
            if _text_contains_blocked_keywords(show.get("overview") or show.get("tmdb_overview")):
                continue

        # Kids/Family: hard-coded title blacklist (Law & Order, Grey's Anatomy, etc.).
        if is_kids_or_family and _title_in_kids_blacklist(show.get("title")):
            continue

        # Kids/Family safety filter: must have Family/Kids/Animation, or Documentary/Comedy without Drama/Crime.
        if is_kids_or_family and not _show_passes_kids_safety_filter(show.get("genres", [])):
            continue

        # Family context: exclude crime, horror, thriller, true crime, war (by name).
        if is_family_context and (show_genres & _FAMILY_UNSAFE_GENRES):
            continue
        if user_age >= config.EXCLUDE_KIDS_GENRE_MIN_AGE and not kids_intent:
            if show_genres & _KIDS_GENRES:
                continue

        seasons = show.get("number_of_seasons")
        if seasons is not None:
            if user_input.binge_preference == BingePreference.SHORT_SERIES and seasons > config.SHORT_SERIES_MAX_SEASONS:
                continue
            if user_input.binge_preference == BingePreference.BINGE and seasons <= config.BINGE_MIN_SEASONS:
                continue

        episode_length = show.get("average_episode_length")
        if user_input.episode_length_preference == EpisodeLengthPreference.SHORT:
            if episode_length is not None and episode_length > config.SHORT_EPISODE_MAX_MINUTES:
                continue
        if user_input.episode_length_preference == EpisodeLengthPreference.LONG:
            if episode_length is not None and episode_length <= config.LONG_EPISODE_MIN_MINUTES:
                continue

        if user_input.language_preference:
            show_language = _normalize_lang(show.get("language") or show.get("original_language"))
            preferred_lang = _normalize_lang(user_input.language_preference)
            if show_language and preferred_lang and show_language != preferred_lang:
                continue

        common_genres = user_genres & show_genres

        # Strict genre enforcement:
        # if user selected genres, candidate must match at least one.
        if user_genres and not common_genres:
            continue

        # If reality is requested, enforce actual reality content
        # (exclude talk/variety-only matches).
        if wants_reality:
            if "reality" not in show_genres:
                continue
            if (show_genres & _LOW_PRIORITY_GENRES) and "reality" not in show_genres:
                continue

        mood_genres = _MOOD_GENRE_MAP.get(user_input.mood, set())
        mood_matched = bool(show_genres & mood_genres)

        recommendation_reason = _build_recommendation_reason(
            common_genres=common_genres,
            binge_preference=user_input.binge_preference,
            seasons=seasons,
            episode_length=episode_length,
            episode_length_pref=user_input.episode_length_preference,
            mood_matched=mood_matched,
            mood=user_input.mood,
        )

        candidate_items.append(
            {
                "show": show,
                "show_genres": show_genres,
                "common_genres": common_genres,
                "mood_matched": mood_matched,
                "recommendation_reason": recommendation_reason,
            }
        )

    # Family context: debug small pool and ensure minimum results via relaxed fallback.
    if is_family_context and len(candidate_items) < config.FAMILY_MIN_RESULTS:
        excluded_by_rating = 0
        excluded_by_genre_unsafe = 0
        excluded_by_user_genre = 0
        for show in shows:
            r = _normalize_content_rating(show.get("content_rating"))
            if not r or r not in _FAMILY_SAFE_RATINGS:
                excluded_by_rating += 1
                continue
            sg = {g.lower() for g in _coerce_genres(show.get("genres", []))}
            if sg & _FAMILY_UNSAFE_GENRES:
                excluded_by_genre_unsafe += 1
                continue
            if user_genres and not (user_genres & sg):
                excluded_by_user_genre += 1
                continue
        logger.info(
            "Family context: candidate pool=%d (target >= %d). Exclusions: rating=%d, unsafe_genre=%d, user_genre_mismatch=%d. Total shows=%d.",
            len(candidate_items),
            config.FAMILY_MIN_RESULTS,
            excluded_by_rating,
            excluded_by_genre_unsafe,
            excluded_by_user_genre,
            len(shows),
        )
        # Build relaxed fallback: Animation, Comedy, or Documentary without TV-MA/R, no unsafe genres.
        fallback: list[dict] = []
        seen_ids: set = set()
        for show in shows:
            rid = show.get("tmdb_id") or show.get("title")
            if rid in seen_ids:
                continue
            r = _normalize_content_rating(show.get("content_rating")) or _default_rating_for_trusted_show(show)
            if r and not show.get("content_rating"):
                show["content_rating"] = r
            if not r or r not in _FAMILY_SAFE_RATINGS:
                continue
            if _genres_contain_adult_ids(show.get("genres", [])):
                continue
            if _text_contains_blocked_keywords(show.get("title")) or _text_contains_blocked_keywords(show.get("overview") or show.get("tmdb_overview")):
                continue
            if _title_in_kids_blacklist(show.get("title")):
                continue
            if not _show_passes_kids_safety_filter(show.get("genres", [])):
                continue
            sg = {g.lower() for g in _coerce_genres(show.get("genres", []))}
            if sg & _FAMILY_UNSAFE_GENRES:
                continue
            if not (sg & _FAMILY_FALLBACK_GENRES):
                continue
            if user_input.language_preference:
                sl = _normalize_lang(show.get("language") or show.get("original_language"))
                pl = _normalize_lang(user_input.language_preference)
                if sl and pl and sl != pl:
                    continue
            seasons = show.get("number_of_seasons")
            if seasons is not None:
                if user_input.binge_preference == BingePreference.SHORT_SERIES and seasons > config.SHORT_SERIES_MAX_SEASONS:
                    continue
                if user_input.binge_preference == BingePreference.BINGE and seasons <= config.BINGE_MIN_SEASONS:
                    continue
            ep = show.get("average_episode_length")
            if user_input.episode_length_preference == EpisodeLengthPreference.SHORT and ep is not None and ep > config.SHORT_EPISODE_MAX_MINUTES:
                continue
            if user_input.episode_length_preference == EpisodeLengthPreference.LONG and ep is not None and ep <= config.LONG_EPISODE_MIN_MINUTES:
                continue
            if wants_reality and "reality" not in sg:
                continue
            mood_matched = bool(sg & _MOOD_GENRE_MAP.get(user_input.mood, set()))
            common = user_genres & sg
            reason = _build_recommendation_reason(
                common_genres=common,
                binge_preference=user_input.binge_preference,
                seasons=seasons,
                episode_length=ep,
                episode_length_pref=user_input.episode_length_preference,
                mood_matched=mood_matched,
                mood=user_input.mood,
            )
            fallback.append({
                "show": show,
                "show_genres": sg,
                "common_genres": common,
                "mood_matched": mood_matched,
                "recommendation_reason": reason,
            })
            seen_ids.add(rid)
        if not candidate_items and fallback:
            candidate_items = fallback
            logger.info("Family context: using relaxed fallback pool (%d candidates).", len(candidate_items))
        elif candidate_items and len(candidate_items) < config.FAMILY_MIN_RESULTS:
            existing_ids = {item["show"].get("tmdb_id") or item["show"].get("title") for item in candidate_items}
            for item in fallback:
                if len(candidate_items) >= config.FAMILY_MIN_RESULTS:
                    break
                sid = item["show"].get("tmdb_id") or item["show"].get("title")
                if sid not in existing_ids:
                    candidate_items.append(item)
                    existing_ids.add(sid)
            logger.info("Family context: backfilled to %d candidates (min %d).", len(candidate_items), config.FAMILY_MIN_RESULTS)

    popularity_values: list[float] = []
    vote_count_logs: list[float] = []
    for item in candidate_items:
        show = item["show"]
        pop_raw = show.get("popularity")
        if isinstance(pop_raw, (int, float)):
            popularity_values.append(float(pop_raw))
        vote_count_raw = show.get("vote_count")
        if isinstance(vote_count_raw, (int, float)):
            vote_count_logs.append(math.log1p(max(0.0, float(vote_count_raw))))

    popularity_min = min(popularity_values) if popularity_values else 0.0
    popularity_max = max(popularity_values) if popularity_values else 1.0
    vote_count_min = min(vote_count_logs) if vote_count_logs else 0.0
    vote_count_max = max(vote_count_logs) if vote_count_logs else 1.0

    scored: list[dict] = []
    for item in candidate_items:
        show = item["show"]
        show_genres = item["show_genres"]
        common_genres = item["common_genres"]

        vote_average_raw = show.get("tmdb_rating")
        if vote_average_raw is None:
            vote_average_raw = show.get("vote_average")
        vote_average = float(vote_average_raw) if isinstance(vote_average_raw, (int, float)) else None

        popularity_raw = show.get("popularity")
        popularity = float(popularity_raw) if isinstance(popularity_raw, (int, float)) else None

        vote_count_raw = show.get("vote_count")
        vote_count = float(vote_count_raw) if isinstance(vote_count_raw, (int, float)) else None

        rating_norm = _normalize_rating(vote_average)
        popularity_norm = _normalize_from_range(popularity, popularity_min, popularity_max, fallback=0.0)
        vote_count_norm = _normalize_vote_count(vote_count, vote_count_min, vote_count_max)

        # Mainstream hit signal: popularity is primary, vote_count supports global recognition.
        popularity_signal = (popularity_norm * config.POPULARITY_NORM_WEIGHT) + (vote_count_norm * config.VOTE_COUNT_NORM_WEIGHT)
        base_score = (rating_norm * config.RATING_WEIGHT) + (popularity_signal * (1.0 - config.RATING_WEIGHT))

        # Mood is required and the primary ranking factor (MoodFlix identity).
        final_score = base_score
        if item["mood_matched"]:
            final_score *= config.MOOD_BOOST_MULTIPLIER

        # Genre is optional: lighter multiplier when user selected genres and show matches.
        genre_score = 1.0
        if user_genres and common_genres:
            genre_score = config.GENRE_BASE_MULTIPLIER + min(
                config.GENRE_EXTRA_CAP, config.GENRE_EXTRA_PER_MATCH * (len(common_genres) - 1)
            )
        final_score *= genre_score

        # Family context: boost animation, family, comedy (clean sitcoms, MasterChef-style, etc.).
        if is_family_context and (show_genres & _FAMILY_FRIENDLY_GENRES):
            final_score *= config.FAMILY_FRIENDLY_BOOST_MULTIPLIER

        # Kids/Family: strong penalty for popular shows that lack Family/Kids/Animation tag.
        if is_kids_or_family and not _show_has_family_kids_animation(show.get("genres", [])):
            final_score *= config.KIDS_WITHOUT_FAMILY_PENALTY

        # Extra anti talk/variety bias for chill/familiar/happy reality expectations.
        if user_input.mood in {Mood.CHILL, Mood.HAPPY, Mood.FAMILIAR} and (show_genres & _LOW_PRIORITY_GENRES):
            final_score *= config.TALK_VARIETY_PENALTY

        # Dark mood: penalize dramedies and light procedurals (comedy/family + crime).
        if user_input.mood == Mood.DARK and (show_genres & {"comedy", "family"}):
            final_score *= config.DARK_COMEDY_FAMILY_PENALTY

        # English priority: original_language missing in DB; use title/overview heuristic.
        show_language = _normalize_lang(show.get("original_language") or show.get("language"))
        title_eng = _is_english_text(show.get("title"))
        overview_eng = _is_english_text(show.get("overview") or show.get("tmdb_overview"))
        if not user_input.language_preference and not foreign_intent:
            if _is_english_language(show_language):
                final_score *= config.ENGLISH_BOOST
            elif title_eng and overview_eng:
                # Assume English when title/overview are mostly ASCII.
                final_score *= config.ENGLISH_HEURISTIC_BOOST
            elif show_language:
                if popularity_signal < config.NON_ENGLISH_PENALTY_POPULARITY_THRESHOLD and rating_norm < config.NON_ENGLISH_PENALTY_RATING_THRESHOLD:
                    final_score *= config.NON_ENGLISH_STRONG_PENALTY
                else:
                    final_score *= config.NON_ENGLISH_SLIGHT_PENALTY
            elif not title_eng or not overview_eng:
                # Non-ASCII text suggests non-English; slight penalty.
                final_score *= config.NON_ASCII_PENALTY

        # Entropy: ±RANKING_NOISE_FRACTION so same mood does not always yield identical top 10.
        noise = 1.0 + random.uniform(
            -config.RANKING_NOISE_FRACTION,
            config.RANKING_NOISE_FRACTION,
        )
        final_score = max(0.0, final_score * noise)

        scored.append(
            {
                "score": final_score,
                "show": show,
                "recommendation_reason": item["recommendation_reason"],
            }
        )

    scored.sort(key=lambda x: x["score"], reverse=True)
    # In Family mode, take extra buffer so after output rating filter we still hit min results.
    take = max(1, int(top_n) * config.FAMILY_BUFFER_MULTIPLIER) if is_family_context else max(1, int(top_n))
    top_scored = scored[: take]

    tmdb_before = tmdb_adapter.get_cache_counters()
    if len(top_scored) <= 1:
        tmdb_enriched = [
            get_tv_details_cached(
                item["show"]["title"],
                tmdb_id=item["show"].get("tmdb_id"),
            )
            for item in top_scored
        ]
    else:
        max_workers = min(TMDB_ENRICH_MAX_WORKERS, len(top_scored))

        def _enrich(item: dict) -> dict | None:
            show = item["show"]
            return get_tv_details_cached(
                show["title"],
                tmdb_id=show.get("tmdb_id"),
            )

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # executor.map preserves input order.
            tmdb_enriched = list(executor.map(_enrich, top_scored))

    tmdb_after = tmdb_adapter.get_cache_counters()
    cache_hits = max(0, tmdb_after["hits"] - tmdb_before["hits"])
    network_fetches = max(0, tmdb_after["misses"] - tmdb_before["misses"])
    if top_scored:
        logger.debug(
            "TMDB enrichment cache stats: total=%d cache_hits=%d network_fetches=%d",
            len(top_scored),
            cache_hits,
            network_fetches,
        )

    # Write-through: persist TMDB metadata to DB so future requests read locally
    for item, tmdb_data in zip(top_scored, tmdb_enriched):
        if tmdb_data and item["show"].get("id"):
            _persist_tmdb_to_show(db, item["show"]["id"], tmdb_data)

    outputs: list[RecommendationOutput] = []

    def _resolved_seasons_and_episode_length(show: dict, tmdb_data: dict | None) -> tuple[int | None, int | None]:
        """Use DB first, then TMDB fallback (write-through: DB may already have persisted data)."""
        td = tmdb_data or {}
        seasons = show.get("number_of_seasons")
        if seasons is None:
            seasons = td.get("number_of_seasons")
        ep_len = show.get("average_episode_length")
        if ep_len is None:
            ep_len = td.get("average_episode_length")
        return seasons, ep_len

    def _apply_post_enrichment_binge_episode_filters(
        resolved_seasons: int | None,
        resolved_ep_length: int | None,
    ) -> bool:
        """True if show passes binge and episode-length filters using enriched data."""
        if user_input.binge_preference == BingePreference.SHORT_SERIES and resolved_seasons is not None:
            if resolved_seasons > config.SHORT_SERIES_MAX_SEASONS:
                return False
        if user_input.binge_preference == BingePreference.BINGE and resolved_seasons is not None:
            if resolved_seasons <= config.BINGE_MIN_SEASONS:
                return False
        if user_input.episode_length_preference == EpisodeLengthPreference.SHORT and resolved_ep_length is not None:
            if resolved_ep_length > config.SHORT_EPISODE_MAX_MINUTES:
                return False
        if user_input.episode_length_preference == EpisodeLengthPreference.LONG and resolved_ep_length is not None:
            if resolved_ep_length <= config.LONG_EPISODE_MIN_MINUTES:
                return False
        return True

    def _build_output(item: dict, tmdb_data: dict | None, show: dict) -> RecommendationOutput | None:
        """Build one RecommendationOutput from item + tmdb_data; apply filters; return None if dropped."""
        # Prefer DB (show), then TMDB fallback
        resolved_rating = _normalize_content_rating(
            show.get("content_rating") or (tmdb_data or {}).get("content_rating")
        )
        if resolved_rating:
            show["content_rating"] = resolved_rating
        title = show.get("title") or "Unknown"
        if zero_trust_rating:
            if not resolved_rating or resolved_rating not in _FAMILY_SAFE_RATINGS:
                logger.info("Blocking [%s] because rating is missing.", title)
                return None
            logger.info("Allowing [%s] with rating [%s].", title, resolved_rating)
        resolved_seasons, resolved_ep_length = _resolved_seasons_and_episode_length(show, tmdb_data)
        if resolved_seasons is not None:
            show["number_of_seasons"] = resolved_seasons
        if resolved_ep_length is not None:
            show["average_episode_length"] = resolved_ep_length
        if not _apply_post_enrichment_binge_episode_filters(resolved_seasons, resolved_ep_length):
            logger.info("Dropping [%s] after enrichment: binge/episode length mismatch.", title)
            return None
        show_genres = {g.lower() for g in _coerce_genres(show.get("genres", []))}
        common_genres = user_genres & show_genres
        mood_matched = bool(show_genres & _MOOD_GENRE_MAP.get(user_input.mood, set()))
        recommendation_reason = _build_recommendation_reason(
            common_genres=common_genres,
            binge_preference=user_input.binge_preference,
            seasons=resolved_seasons,
            episode_length=resolved_ep_length,
            episode_length_pref=user_input.episode_length_preference,
            mood_matched=mood_matched,
            mood=user_input.mood,
        )
        db_poster_url = show.get("poster_url")
        db_rating = show.get("tmdb_rating")
        db_overview = show.get("tmdb_overview")
        db_first_air_date: date | str | None = show.get("first_air_date")
        if isinstance(db_first_air_date, date):
            db_first_air_date_str = db_first_air_date.isoformat()
        else:
            db_first_air_date_str = db_first_air_date
        return RecommendationOutput(
            id=show.get("id"),
            title=show["title"],
            recommendation_reason=recommendation_reason,
            genres=_coerce_genres(show.get("genres", [])),
            short_summary=show.get("short_summary") or _build_short_summary(show.get("tmdb_overview")),
            content_rating=resolved_rating or show.get("content_rating"),
            average_episode_length=show.get("average_episode_length"),
            number_of_seasons=show.get("number_of_seasons"),
            language=show.get("language"),
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

    for item, tmdb_data in zip(top_scored, tmdb_enriched):
        if is_family_context and len(outputs) >= int(top_n):
            continue
        show = item["show"]
        out = _build_output(item, tmdb_data, show)
        if out is not None:
            outputs.append(out)

    # Refill from scored list if post-enrichment filters dropped too many.
    refill_idx = take
    while len(outputs) < int(top_n) and refill_idx < len(scored):
        item = scored[refill_idx]
        refill_idx += 1
        show = item["show"]
        tmdb_data = get_tv_details_cached(
            show.get("title"),
            tmdb_id=show.get("tmdb_id"),
        )
        if tmdb_data and show.get("id"):
            _persist_tmdb_to_show(db, show["id"], tmdb_data)
        out = _build_output(item, tmdb_data, show)
        if out is not None:
            outputs.append(out)
        if len(outputs) >= int(top_n):
            break
    if refill_idx > take and outputs:
        logger.debug("Post-enrichment refill: used %d extra candidates to reach top_n.", refill_idx - take)
    outputs = outputs[: int(top_n)]

    # Clean fallback: if Kids/Family and too few results, fill remaining slots only with Family (10751) shows.
    if is_kids_or_family and len(outputs) < int(top_n):
        output_titles = {o.title for o in outputs}
        family_only: list[dict] = []
        for show in shows:
            if show.get("title") in output_titles:
                continue
            ids = _get_genre_ids(show.get("genres", []))
            if _FAMILY_GENRE_ID not in ids:
                continue
            r = _normalize_content_rating(show.get("content_rating")) or _default_rating_for_trusted_show(show)
            if r and not show.get("content_rating"):
                show["content_rating"] = r
            if not r or r not in _FAMILY_SAFE_RATINGS:
                continue
            if _genres_contain_adult_ids(show.get("genres", [])):
                continue
            if _text_contains_blocked_keywords(show.get("title")) or _text_contains_blocked_keywords(show.get("overview") or show.get("tmdb_overview")):
                continue
            if _title_in_kids_blacklist(show.get("title")):
                continue
            sg = {g.lower() for g in _coerce_genres(show.get("genres", []))}
            if sg & _FAMILY_UNSAFE_GENRES:
                continue
            family_only.append(show)
        # Sort by popularity descending, take enough to fill to top_n.
        family_only.sort(key=lambda s: (float(s.get("popularity") or 0), float(s.get("vote_count") or 0)), reverse=True)
        need = int(top_n) - len(outputs)
        for show in family_only[:need]:
            tmdb_data = get_tv_details_cached(show.get("title"), tmdb_id=show.get("tmdb_id"))
            if tmdb_data and show.get("id"):
                _persist_tmdb_to_show(db, show["id"], tmdb_data)
            resolved_rating = _normalize_content_rating(
                (tmdb_data or {}).get("content_rating") or show.get("content_rating")
            ) or _default_rating_for_trusted_show(show)
            if resolved_rating and (tmdb_data or {}).get("content_rating"):
                show["content_rating"] = resolved_rating
            title = show.get("title") or "Unknown"
            if not resolved_rating or resolved_rating not in _FAMILY_SAFE_RATINGS:
                logger.info("Blocking [%s] because rating is missing.", title)
                continue
            logger.info("Allowing [%s] with rating [%s].", title, resolved_rating)
            db_first_air_date = show.get("first_air_date")
            if isinstance(db_first_air_date, date):
                db_first_air_date_str = db_first_air_date.isoformat()
            else:
                db_first_air_date_str = db_first_air_date
            outputs.append(
                RecommendationOutput(
                    id=show.get("id"),
                    title=show["title"],
                    recommendation_reason="Family-friendly pick.",
                    genres=_coerce_genres(show.get("genres", [])),
                    short_summary=show.get("short_summary") or _build_short_summary(show.get("tmdb_overview")),
                    content_rating=resolved_rating or show.get("content_rating"),
                    average_episode_length=show.get("average_episode_length"),
                    number_of_seasons=show.get("number_of_seasons"),
                    language=show.get("language"),
                    poster_url=(tmdb_data or {}).get("poster_url") if tmdb_data else show.get("poster_url"),
                    tmdb_rating=(tmdb_data or {}).get("rating") if tmdb_data else show.get("tmdb_rating"),
                    tmdb_overview=(tmdb_data or {}).get("overview") if tmdb_data else show.get("tmdb_overview"),
                    first_air_date=(tmdb_data or {}).get("first_air_date") if tmdb_data else db_first_air_date_str,
                )
            )
            if len(outputs) >= int(top_n):
                break
        if len(outputs) > int(top_n):
            outputs = outputs[: int(top_n)]
        if family_only:
            logger.info("Kids/Family: filled remaining slots with Family-genre fallback (used %d of %d).", min(need, len(family_only)), len(family_only))

    return outputs
