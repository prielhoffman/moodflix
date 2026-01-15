import pytest

from app.schemas import (
    RecommendationInput,
    BingePreference,
    ContentIntensity,
    EpisodeLengthPreference,
    WatchingContext,
)
from app.logic import recommend_shows


# ---------- Safety rules ----------

def test_family_context_excludes_adult_content():
    user_input = RecommendationInput(
        age=35,
        binge_preference=BingePreference.BINGE,
        preferred_genres=[],
        content_intensity=ContentIntensity.MODERATE,
        language_preference=None,
        episode_length_preference=EpisodeLengthPreference.ANY,
        watching_context=WatchingContext.FAMILY,
    )

    results = recommend_shows(user_input)

    assert all(show.content_rating != "TV-MA" for show in results)


def test_child_age_excludes_adult_content():
    user_input = RecommendationInput(
        age=10,
        binge_preference=BingePreference.BINGE,
        preferred_genres=[],
        content_intensity=ContentIntensity.MODERATE,
        language_preference=None,
        episode_length_preference=EpisodeLengthPreference.ANY,
        watching_context=WatchingContext.ALONE,
    )

    results = recommend_shows(user_input)

    assert all(show.content_rating != "TV-MA" for show in results)


# ---------- Binge preference ----------

def test_short_series_returns_only_up_to_three_seasons():
    user_input = RecommendationInput(
        age=30,
        binge_preference=BingePreference.SHORT_SERIES,
        preferred_genres=[],
        content_intensity=ContentIntensity.MODERATE,
        language_preference=None,
        episode_length_preference=EpisodeLengthPreference.ANY,
        watching_context=WatchingContext.ALONE,
    )

    results = recommend_shows(user_input)

    assert results
    assert all(show.number_of_seasons <= 3 for show in results)


def test_binge_returns_only_more_than_three_seasons():
    user_input = RecommendationInput(
        age=30,
        binge_preference=BingePreference.BINGE,
        preferred_genres=[],
        content_intensity=ContentIntensity.MODERATE,
        language_preference=None,
        episode_length_preference=EpisodeLengthPreference.ANY,
        watching_context=WatchingContext.ALONE,
    )

    results = recommend_shows(user_input)

    assert results
    assert all(show.number_of_seasons > 3 for show in results)


# ---------- Episode length ----------

def test_short_episode_preference_filters_long_episodes():
    user_input = RecommendationInput(
        age=30,
        binge_preference=BingePreference.BINGE,
        preferred_genres=[],
        content_intensity=ContentIntensity.MODERATE,
        language_preference=None,
        episode_length_preference=EpisodeLengthPreference.SHORT,
        watching_context=WatchingContext.ALONE,
    )

    results = recommend_shows(user_input)

    assert results
    assert all(show.average_episode_length <= 30 for show in results)


def test_long_episode_preference_filters_short_episodes():
    user_input = RecommendationInput(
        age=30,
        binge_preference=BingePreference.BINGE,
        preferred_genres=[],
        content_intensity=ContentIntensity.MODERATE,
        language_preference=None,
        episode_length_preference=EpisodeLengthPreference.LONG,
        watching_context=WatchingContext.ALONE,
    )

    results = recommend_shows(user_input)

    assert results
    assert all(show.average_episode_length > 30 for show in results)


# ---------- Soft matching ----------

def test_genre_matching_does_not_eliminate_valid_shows():
    user_input = RecommendationInput(
        age=30,
        binge_preference=BingePreference.BINGE,
        preferred_genres=["comedy"],
        content_intensity=ContentIntensity.MODERATE,
        language_preference=None,
        episode_length_preference=EpisodeLengthPreference.ANY,
        watching_context=WatchingContext.ALONE,
    )

    results = recommend_shows(user_input)

    # Should still return shows even if not all are comedies
    assert results
    assert any("comedy" in show.genres for show in results)


# ---------- Recommendation reason ----------

def test_recommendation_reason_is_generated_on_clear_match():
    user_input = RecommendationInput(
        age=30,
        binge_preference=BingePreference.BINGE,
        preferred_genres=["comedy"],
        content_intensity=ContentIntensity.LIGHT,
        language_preference=None,
        episode_length_preference=EpisodeLengthPreference.SHORT,
        watching_context=WatchingContext.ALONE,
    )

    results = recommend_shows(user_input)

    assert results
    assert any(show.recommendation_reason for show in results)
