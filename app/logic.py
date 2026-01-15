from typing import List

from app.schemas import (
    RecommendationInput,
    RecommendationOutput,
    BingePreference,
    ContentIntensity,
    EpisodeLengthPreference,
    WatchingContext,
)
from app.data import get_all_shows


_ADULT_RATINGS = {"TV-MA"}

_INTENSITY_GENRE_MAP = {
    ContentIntensity.LIGHT: {"comedy", "family", "animation", "documentary"},
    ContentIntensity.MODERATE: {"drama", "mystery", "adventure"},
    ContentIntensity.DARK: {"thriller", "crime", "horror"},
}


def _build_recommendation_reason(
    *,
    common_genres: set,
    binge_preference: BingePreference,
    seasons: int,
    episode_length: int | None,
    episode_length_pref: EpisodeLengthPreference,
    intensity_matched: bool,
    intensity: ContentIntensity,
) -> str | None:
    """
    Build a short, user-friendly recommendation reason
    using the strongest 1–2 matching signals.
    """
    reasons = []

    # 1. Genre overlap (highest priority)
    if common_genres:
        reasons.append(
            f"Matches your interest in {', '.join(sorted(common_genres))}"
        )

    # 2. Binge / commitment
    if binge_preference == BingePreference.SHORT_SERIES and seasons <= 3:
        reasons.append("Easy to finish in a few days")
    elif binge_preference == BingePreference.BINGE and seasons > 3:
        reasons.append("Great for binge watching")

    # 3. Episode length
    if episode_length is not None:
        if episode_length_pref == EpisodeLengthPreference.SHORT and episode_length <= 30:
            reasons.append("Short, easy-to-watch episodes")
        elif episode_length_pref == EpisodeLengthPreference.LONG and episode_length > 30:
            reasons.append("Long, immersive episodes")

    # 4. Content intensity
    if intensity_matched:
        if intensity == ContentIntensity.LIGHT:
            reasons.append("Light and easy to watch")
        elif intensity == ContentIntensity.DARK:
            reasons.append("Darker, more intense tone")
        elif intensity == ContentIntensity.MODERATE:
            reasons.append("Balanced tone with engaging storytelling")

    return ". ".join(reasons[:2]) if reasons else None


def recommend_shows(user_input: RecommendationInput) -> List[RecommendationOutput]:
    shows = get_all_shows()
    results = []

    for show in shows:
        # ---------- Hard filters ----------

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

        intensity_genres = _INTENSITY_GENRE_MAP.get(user_input.content_intensity, set())
        intensity_matched = bool(show_genres & intensity_genres)
        if intensity_matched:
            score += 1

        recommendation_reason = _build_recommendation_reason(
            common_genres=common_genres,
            binge_preference=user_input.binge_preference,
            seasons=seasons,
            episode_length=episode_length,
            episode_length_pref=user_input.episode_length_preference,
            intensity_matched=intensity_matched,
            intensity=user_input.content_intensity,
        )

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
                ),
            }
        )

    results.sort(key=lambda x: x["score"], reverse=True)
    return [item["show"] for item in results]
