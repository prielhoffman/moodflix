from __future__ import annotations

import logging
import math
import os
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
_FAMILY_MIN_RESULTS = 10

# TMDB genre IDs to block for Kids/Family (DB stores genre_ids as integers).
_ADULT_GENRE_IDS = {80, 9648, 10768, 10763}  # Crime, Mystery, War, News

# Keywords in title/overview that indicate adult content (case-insensitive).
_KIDS_KEYWORD_BLOCKLIST = {
    "murder", "criminal", "victim", "sexual", "investigation", "police",
    "blood", "terrorist", "drug",
}

# Hard-coded title blacklist for Kids/Family (partial match, case-insensitive).
_KIDS_TITLE_BLACKLIST = {
    "law & order",
    "grey's anatomy",
    "greys anatomy",
    "stranger things",
    "the rookie",
    "supernatural",
}

# Kids/Family safety: show must have at least one of these genre IDs (or pass exception rule).
_KIDS_SAFE_GENRE_IDS = {10751, 10762, 16}  # Family, Kids, Animation
_KIDS_EXCEPTION_GENRE_IDS = {99, 35}       # Documentary, Comedy (allowed only without Drama/Crime)
_KIDS_EXCLUDED_IF_EXCEPTION = {18, 80}     # Drama, Crime
_FAMILY_GENRE_ID = 10751


# -------------------- Mood → Genre soft mapping --------------------
_MOOD_GENRE_MAP = {
    # Keep CHILL and FAMILIAR anchored around mainstream comfort genres.
    Mood.CHILL: {"comedy", "sitcom", "reality", "lifestyle", "family", "romance", "drama"},
    Mood.HAPPY: {"comedy", "romance", "family", "musical", "reality", "animation"},
    Mood.FAMILIAR: {"sitcom", "procedural", "family", "comedy", "reality", "animation"},
    Mood.FOCUSED: {"drama", "mystery", "historical", "legal", "medical", "competition"},
    Mood.ADRENALINE: {"action", "adventure", "sci-fi", "fantasy", "survival", "competition"},
    Mood.DARK: {"thriller", "crime", "horror", "psychological", "true crime"},
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
    """Heuristic: text is mostly ASCII (English). Non-ASCII ratio < 20%."""
    if not text or not isinstance(text, str):
        return True
    try:
        ascii_count = sum(1 for c in text if ord(c) < 128)
        return (ascii_count / len(text)) >= 0.8
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


def _convert_show_row(row: Show) -> dict:
    genres = _coerce_genres(row.genres)

    return {
        "tmdb_id": row.tmdb_id,
        "title": row.title,
        "recommendation_reason": None,
        "genres": genres,
        "short_summary": _build_short_summary(row.overview),
        # These fields don't exist in the current DB schema yet;
        # keep them as None so filters can treat them as "unknown".
        "content_rating": None,
        "average_episode_length": None,
        "number_of_seasons": None,
        "language": getattr(row, "original_language", None),
        "original_language": getattr(row, "original_language", None),
        # Optional fields we can use as a fallback when TMDB enrichment is unavailable.
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
    top_n: int = 20,
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

    foreign_intent = _has_foreign_intent(user_input)
    kids_intent = _requests_kids_content(user_input)
    # Family context and age-based flags before building user_genres.
    is_family_context = user_input.watching_context == WatchingContext.FAMILY
    effective_max_age = 12 if is_family_context else user_input.age
    is_kids_or_family = effective_max_age < 13 or is_family_context

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

        if is_family_context:
            # Exclude only explicit adult ratings; allow no rating (fallback to general audience) or family-safe.
            if rating and rating in _ADULT_RATINGS:
                continue
            if rating and rating not in _FAMILY_SAFE_RATINGS:
                continue
        else:
            # Non-family: block adult ratings for under-16 (use effective age if we ever reuse it).
            if rating and rating in _ADULT_RATINGS and effective_max_age < 16:
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
        if user_input.age >= 21 and not kids_intent:
            if show_genres & _KIDS_GENRES:
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
    if is_family_context and len(candidate_items) < _FAMILY_MIN_RESULTS:
        excluded_by_rating = 0
        excluded_by_genre_unsafe = 0
        excluded_by_user_genre = 0
        for show in shows:
            r = _normalize_content_rating(show.get("content_rating"))
            if r and (r in _ADULT_RATINGS or r not in _FAMILY_SAFE_RATINGS):
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
            _FAMILY_MIN_RESULTS,
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
            r = _normalize_content_rating(show.get("content_rating"))
            if r and r in _ADULT_RATINGS:
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
                if user_input.binge_preference == BingePreference.SHORT_SERIES and seasons > 3:
                    continue
                if user_input.binge_preference == BingePreference.BINGE and seasons <= 3:
                    continue
            ep = show.get("average_episode_length")
            if user_input.episode_length_preference == EpisodeLengthPreference.SHORT and ep is not None and ep > 30:
                continue
            if user_input.episode_length_preference == EpisodeLengthPreference.LONG and ep is not None and ep <= 30:
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
        elif candidate_items and len(candidate_items) < _FAMILY_MIN_RESULTS:
            existing_ids = {item["show"].get("tmdb_id") or item["show"].get("title") for item in candidate_items}
            for item in fallback:
                if len(candidate_items) >= _FAMILY_MIN_RESULTS:
                    break
                sid = item["show"].get("tmdb_id") or item["show"].get("title")
                if sid not in existing_ids:
                    candidate_items.append(item)
                    existing_ids.add(sid)
            logger.info("Family context: backfilled to %d candidates (min %d).", len(candidate_items), _FAMILY_MIN_RESULTS)

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
        popularity_signal = (popularity_norm * 0.75) + (vote_count_norm * 0.25)
        base_score = (rating_norm * 0.4) + (popularity_signal * 0.6)

        # Strong genre multiplier for user-selected genres.
        genre_score = 1.0
        if user_genres and common_genres:
            genre_score = 2.0 + min(0.6, 0.15 * (len(common_genres) - 1))

        final_score = genre_score * base_score

        # Light mood boost within the already genre-filtered pool.
        if item["mood_matched"]:
            final_score *= 1.04

        # Family context: boost animation, family, comedy (clean sitcoms, MasterChef-style, etc.).
        if is_family_context and (show_genres & _FAMILY_FRIENDLY_GENRES):
            final_score *= 1.18

        # Kids/Family: strong penalty for popular shows that lack Family/Kids/Animation tag.
        if is_kids_or_family and not _show_has_family_kids_animation(show.get("genres", [])):
            final_score *= 0.1

        # Extra anti talk/variety bias for chill/familiar/happy reality expectations.
        if user_input.mood in {Mood.CHILL, Mood.HAPPY, Mood.FAMILIAR} and (show_genres & _LOW_PRIORITY_GENRES):
            final_score *= 0.92

        # English priority: original_language missing in DB; use title/overview heuristic.
        show_language = _normalize_lang(show.get("original_language") or show.get("language"))
        title_eng = _is_english_text(show.get("title"))
        overview_eng = _is_english_text(show.get("overview") or show.get("tmdb_overview"))
        if not user_input.language_preference and not foreign_intent:
            if _is_english_language(show_language):
                final_score *= 1.15
            elif title_eng and overview_eng:
                # Assume English when title/overview are mostly ASCII.
                final_score *= 1.12
            elif show_language:
                if popularity_signal < 0.90 and rating_norm < 0.88:
                    final_score *= 0.72
                else:
                    final_score *= 0.95
            elif not title_eng or not overview_eng:
                # Non-ASCII text suggests non-English; slight penalty.
                final_score *= 0.92

        scored.append(
            {
                "score": final_score,
                "show": show,
                "recommendation_reason": item["recommendation_reason"],
            }
        )

    scored.sort(key=lambda x: x["score"], reverse=True)
    # In Family mode, take extra buffer so after output rating filter we still hit min results.
    take = max(1, int(top_n) * 2) if is_family_context else max(1, int(top_n))
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

    outputs: list[RecommendationOutput] = []

    for item, tmdb_data in zip(top_scored, tmdb_enriched):
        show = item["show"]
        recommendation_reason = item["recommendation_reason"]

        # Post-enrichment safety: for Kids/Family, remove TV-MA, TV-14, R even if passed pre-filter.
        if is_kids_or_family:
            resolved_rating = _normalize_content_rating(
                (tmdb_data or {}).get("content_rating") or show.get("content_rating")
            )
            if resolved_rating and resolved_rating in _ADULT_RATINGS:
                continue
            if is_family_context and len(outputs) >= int(top_n):
                continue

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
            r = _normalize_content_rating(show.get("content_rating"))
            if r and r in _ADULT_RATINGS:
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
            resolved_rating = _normalize_content_rating(
                (tmdb_data or {}).get("content_rating") or show.get("content_rating")
            )
            if resolved_rating and resolved_rating in _ADULT_RATINGS:
                continue
            db_first_air_date = show.get("first_air_date")
            if isinstance(db_first_air_date, date):
                db_first_air_date_str = db_first_air_date.isoformat()
            else:
                db_first_air_date_str = db_first_air_date
            outputs.append(
                RecommendationOutput(
                    title=show["title"],
                    recommendation_reason="Family-friendly pick.",
                    genres=_coerce_genres(show.get("genres", [])),
                    short_summary=show.get("short_summary") or _build_short_summary(show.get("tmdb_overview")),
                    content_rating=show.get("content_rating"),
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
