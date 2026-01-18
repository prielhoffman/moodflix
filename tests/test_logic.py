import pytest

from app.schemas import (
    RecommendationInput,
    BingePreference,
    Mood,
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
        mood=Mood.FOCUSED,
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
        mood=Mood.FOCUSED,
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
        mood=Mood.FOCUSED,
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
        mood=Mood.FOCUSED,
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
        mood=Mood.FOCUSED,
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
        mood=Mood.FOCUSED,
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
        mood=Mood.FOCUSED,
        language_preference=None,
        episode_length_preference=EpisodeLengthPreference.ANY,
        watching_context=WatchingContext.ALONE,
    )

    results = recommend_shows(user_input)

    assert results
    assert any("comedy" in show.genres for show in results)


# ---------- Recommendation reason ----------

def test_recommendation_reason_is_generated_on_clear_match():
    user_input = RecommendationInput(
        age=30,
        binge_preference=BingePreference.BINGE,
        preferred_genres=["comedy"],
        mood=Mood.CHILL,
        language_preference=None,
        episode_length_preference=EpisodeLengthPreference.SHORT,
        watching_context=WatchingContext.ALONE,
    )

    results = recommend_shows(user_input)

    assert results
    assert any(show.recommendation_reason for show in results)


# ---------- Mood-based logic ----------

def test_mood_is_soft_signal_does_not_filter_results():
    """
    Mood should not eliminate valid shows.
    Results should still be returned even if some shows do not match the mood.
    """
    user_input = RecommendationInput(
        age=30,
        binge_preference=BingePreference.BINGE,
        preferred_genres=[],
        mood=Mood.ADRENALINE,
        language_preference=None,
        episode_length_preference=EpisodeLengthPreference.ANY,
        watching_context=WatchingContext.ALONE,
    )

    results = recommend_shows(user_input)

    assert results


def test_mood_match_affects_ranking_order():
    """
    Shows that match the selected mood should generally
    appear earlier than those that do not.
    """
    user_input = RecommendationInput(
        age=30,
        binge_preference=BingePreference.BINGE,
        preferred_genres=[],
        mood=Mood.CHILL,
        language_preference=None,
        episode_length_preference=EpisodeLengthPreference.ANY,
        watching_context=WatchingContext.ALONE,
    )

    results = recommend_shows(user_input)

    assert len(results) >= 1
    assert results[0].recommendation_reason

    assert any(
        phrase in results[0].recommendation_reason.lower()
        for phrase in ["relaxed", "easy", "chill"]
    )



def test_recommendation_reason_mentions_mood_when_matched():
    """
    When a show matches the selected mood,
    the recommendation_reason should include
    a mood-related explanation.
    """
    user_input = RecommendationInput(
        age=30,
        binge_preference=BingePreference.BINGE,
        preferred_genres=[],
        mood=Mood.HAPPY,
        language_preference=None,
        episode_length_preference=EpisodeLengthPreference.ANY,
        watching_context=WatchingContext.ALONE,
    )

    results = recommend_shows(user_input)

    assert results
    assert any(
        show.recommendation_reason
        and any(
            keyword in show.recommendation_reason.lower()
            for keyword in ["uplifting", "feel-good", "happy"]
        )
        for show in results
    )
