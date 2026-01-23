from typing import List

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


def _build_recommendation_reason(
    *,
    common_genres: set,
    binge_preference: BingePreference,
    seasons: int,
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

    if binge_preference == BingePreference.SHORT_SERIES and seasons <= 3:
        reasons.append("Easy to finish in one season")
    elif binge_preference == BingePreference.BINGE and seasons > 3:
        reasons.append("Great for binge watching")

    if episode_length is not None:
        if episode_length_pref == EpisodeLengthPreference.SHORT and episode_length <= 30:
            reasons.append("Short, easy-to-watch episodes")
        elif episode_length_pref == EpisodeLengthPreference.LONG and episode_length > 30:
            reasons.append("Long, immersive episodes")

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

    return ". ".join(reasons[:2]) if reasons else None


def recommend_shows(user_input: RecommendationInput) -> List[RecommendationOutput]:
    shows = get_all_shows()
    results = []

    for show in shows:
        # ---------- Hard filters (unchanged) ----------

        rating = show.get("content_rating")
        if rating:
            if user_input.watching_context == WatchingContext.FAMILY and rating in _ADULT_RATINGS:
                continue
            if user_input.age < 16 and rating in _ADULT_RATINGS:
                continue

        seasons = show.get("number_of_seasons")
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
            if show.get("language") != user_input.language_preference:
                continue

        # ---------- Soft matching ----------

        score = 0

        user_genres = set(g.lower() for g in user_input.preferred_genres)
        show_genres = set(g.lower() for g in show.get("genres", []))

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

        # ---------- TMDB Enrichment ----------
        # Fetch external metadata for this show
        tmdb_data = search_tv_show(show["title"])

        results.append(
            {
                "score": score,
                "show": RecommendationOutput(
                    title=show["title"],
                    recommendation_reason=recommendation_reason,
                    genres=show["genres"],
                    short_summary=show["short_summary"],
                    content_rating=show["content_rating"],
                    average_episode_length=show["average_episode_length"],
                    number_of_seasons=show["number_of_seasons"],
                    language=show["language"],

                    # TMDB fields (may be None)
                    poster_url=tmdb_data.get("poster_url") if tmdb_data else None,
                    tmdb_rating=tmdb_data.get("rating") if tmdb_data else None,
                    tmdb_overview=tmdb_data.get("overview") if tmdb_data else None,
                    first_air_date=tmdb_data.get("first_air_date") if tmdb_data else None,
                ),
            }
        )

    results.sort(key=lambda x: x["score"], reverse=True)

    return [item["show"] for item in results]
