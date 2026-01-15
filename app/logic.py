from typing import List

from schemas import (
    RecommendationInput,
    RecommendationOutput,
    BingePreference,
    ContentIntensity,
    EpisodeLengthPreference,
    WatchingContext,
)
from data import get_all_shows


# Simple content rating hierarchy for safety checks
_ADULT_RATINGS = {"TV-MA"}
_TEEN_RATINGS = {"TV-14"}
_KIDS_RATINGS = {"TV-G", "TV-Y", "TV-Y7", "TV-PG"}


# Soft mapping between content intensity and genres
_INTENSITY_GENRE_MAP = {
    ContentIntensity.LIGHT: {"comedy", "family", "animation", "documentary"},
    ContentIntensity.MODERATE: {"drama", "mystery", "adventure"},
    ContentIntensity.DARK: {"thriller", "crime", "horror"},
}


def recommend_shows(user_input: RecommendationInput) -> List[RecommendationOutput]:
    shows = get_all_shows()
    results = []

    for show in shows:
        # ---------- Hard filters ----------

        rating = show.get("content_rating")

        # Age & watching context safety
        if rating:
            # Family context → no adult-only content
            if user_input.watching_context == WatchingContext.FAMILY:
                if rating in _ADULT_RATINGS:
                    continue
            # Age-based restrictions
            if user_input.age < 13 and rating in _ADULT_RATINGS:
                continue
            if user_input.age < 16 and rating in _ADULT_RATINGS:
                continue

        # Binge preference
        seasons = show.get("number_of_seasons")
        if user_input.binge_preference == BingePreference.ONE_SEASON and seasons > 3:
            continue
        if user_input.binge_preference == BingePreference.BINGE and seasons <= 3:
            continue

        # Episode length preference
        episode_length = show.get("average_episode_length")
        if user_input.episode_length_preference == EpisodeLengthPreference.SHORT:
            if episode_length is not None and episode_length > 30:
                continue
        if user_input.episode_length_preference == EpisodeLengthPreference.LONG:
            if episode_length is not None and episode_length <= 30:
                continue

        # Language preference
        if user_input.language_preference:
            if show.get("language") != user_input.language_preference:
                continue

        # ---------- Soft matching ----------

        score = 0
        reasons = []

        # Genre overlap
        user_genres = set(g.lower() for g in user_input.preferred_genres)
        show_genres = set(g.lower() for g in show.get("genres", []))
        common_genres = user_genres & show_genres
        if common_genres:
            score += len(common_genres)
            reasons.append(f"Matches genres: {', '.join(sorted(common_genres))}")

        # Content intensity match
        intensity_genres = _INTENSITY_GENRE_MAP.get(user_input.content_intensity, set())
        if show_genres & intensity_genres:
            score += 1
            reasons.append(f"Fits a {user_input.content_intensity.value} tone")

        # Commitment explanation
        if user_input.binge_preference == BingePreference.SHORT_SERIES and seasons <= 3:
            reasons.append("Short commitment series")
        elif user_input.binge_preference == BingePreference.BINGE and seasons > 3:
            reasons.append("Great for binge watching")

        results.append(
            {
                "score": score,
                "show": RecommendationOutput(
                    title=show["title"],
                    recommendation_reason="; ".join(reasons[:2]) if reasons else None,
                    genres=show["genres"],
                    short_summary=show["short_summary"],
                    content_rating=show["content_rating"],
                    average_episode_length=show["average_episode_length"],
                    number_of_seasons=show["number_of_seasons"],
                    language=show["language"],
                ),
            }
        )

    # Sort by score (highest first)
    results.sort(key=lambda x: x["score"], reverse=True)

    return [item["show"] for item in results]
