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

# -------------------- TMDB Integration Tests --------------------


def test_tmdb_returns_none_does_not_break_logic(monkeypatch):
    """
    If TMDB returns None for all shows,
    recommendations should still work and all TMDB fields should be None.
    """

    def mock_search_tv_show(title):
        return None

    # Patch search_tv_show inside logic.py
    monkeypatch.setattr("app.logic.search_tv_show", mock_search_tv_show)

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

    assert results
    assert len(results) > 0

    for show in results:
        assert show.poster_url is None
        assert show.tmdb_rating is None
        assert show.tmdb_overview is None
        assert show.first_air_date is None


def test_tmdb_returns_valid_metadata(monkeypatch):
    """
    If TMDB returns valid metadata,
    it should be merged correctly into all results.
    """

    mocked_tmdb_data = {
        "poster_url": "https://example.com/poster.jpg",
        "rating": 8.5,
        "overview": "Test overview",
        "first_air_date": "2021-01-01",
    }

    def mock_search_tv_show(title):
        return mocked_tmdb_data

    # Patch search_tv_show inside logic.py
    monkeypatch.setattr("app.logic.search_tv_show", mock_search_tv_show)

    user_input = RecommendationInput(
        age=25,
        binge_preference=BingePreference.BINGE,
        preferred_genres=[],
        mood=Mood.HAPPY,
        language_preference=None,
        episode_length_preference=EpisodeLengthPreference.ANY,
        watching_context=WatchingContext.ALONE,
    )

    results = recommend_shows(user_input)

    assert results
    assert len(results) > 0

    for show in results:
        assert show.poster_url == mocked_tmdb_data["poster_url"]
        assert show.tmdb_rating == mocked_tmdb_data["rating"]
        assert show.tmdb_overview == mocked_tmdb_data["overview"]
        assert show.first_air_date == mocked_tmdb_data["first_air_date"]


def test_tmdb_enrichment_does_not_affect_existing_filters(monkeypatch):
    """
    TMDB enrichment should not affect existing business rules,
    such as excluding TV-MA content for family context.
    """

    def mock_search_tv_show(title):
        return {
            "poster_url": "https://example.com/poster.jpg",
            "rating": 9.0,
            "overview": "Overview",
            "first_air_date": "2022-01-01",
        }

    # Patch search_tv_show inside logic.py
    monkeypatch.setattr("app.logic.search_tv_show", mock_search_tv_show)

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

    assert results

    # Existing safety rule: no TV-MA in family context
    assert all(show.content_rating != "TV-MA" for show in results)