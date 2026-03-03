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
        binge_preference=BingePreference.BINGE,
        preferred_genres=[],
        mood=Mood.FOCUSED,
        language_preference=None,
        episode_length_preference=EpisodeLengthPreference.ANY,
        watching_context=WatchingContext.FAMILY,
    )

    results = recommend_shows(user_input, age=35)

    assert all(show.content_rating != "TV-MA" for show in results)


def test_child_age_excludes_adult_content():
    user_input = RecommendationInput(
        binge_preference=BingePreference.BINGE,
        preferred_genres=[],
        mood=Mood.FOCUSED,
        language_preference=None,
        episode_length_preference=EpisodeLengthPreference.ANY,
        watching_context=WatchingContext.ALONE,
    )

    results = recommend_shows(user_input, age=10)

    assert all(show.content_rating != "TV-MA" for show in results)


# ---------- Binge preference ----------

def test_short_series_returns_only_up_to_three_seasons():
    user_input = RecommendationInput(
        binge_preference=BingePreference.SHORT_SERIES,
        preferred_genres=[],
        mood=Mood.FOCUSED,
        language_preference=None,
        episode_length_preference=EpisodeLengthPreference.ANY,
        watching_context=WatchingContext.ALONE,
    )

    results = recommend_shows(user_input, age=30)

    assert results
    assert all(show.number_of_seasons <= 3 for show in results)


def test_binge_returns_only_more_than_min_seasons():
    """BINGE requires > config.BINGE_MIN_SEASONS (2), so 3+ seasons pass."""
    from app import config

    user_input = RecommendationInput(
        binge_preference=BingePreference.BINGE,
        preferred_genres=[],
        mood=Mood.FOCUSED,
        language_preference=None,
        episode_length_preference=EpisodeLengthPreference.ANY,
        watching_context=WatchingContext.ALONE,
    )

    results = recommend_shows(user_input, age=30)

    assert results
    for show in results:
        if show.number_of_seasons is not None:
            assert show.number_of_seasons > config.BINGE_MIN_SEASONS, (
                f"Show {show.title} has {show.number_of_seasons} seasons, "
                f"expected > {config.BINGE_MIN_SEASONS}"
            )


# ---------- Episode length ----------

def test_short_episode_preference_filters_long_episodes():
    user_input = RecommendationInput(
        binge_preference=BingePreference.BINGE,
        preferred_genres=[],
        mood=Mood.FOCUSED,
        language_preference=None,
        episode_length_preference=EpisodeLengthPreference.SHORT,
        watching_context=WatchingContext.ALONE,
    )

    results = recommend_shows(user_input, age=30)

    assert results
    assert all(show.average_episode_length <= 30 for show in results)


def test_long_episode_preference_filters_short_episodes():
    user_input = RecommendationInput(
        binge_preference=BingePreference.BINGE,
        preferred_genres=[],
        mood=Mood.FOCUSED,
        language_preference=None,
        episode_length_preference=EpisodeLengthPreference.LONG,
        watching_context=WatchingContext.ALONE,
    )

    results = recommend_shows(user_input, age=30)

    assert results
    assert all(show.average_episode_length > 30 for show in results)


# ---------- Soft matching ----------

def test_genre_matching_does_not_eliminate_valid_shows():
    user_input = RecommendationInput(
        binge_preference=BingePreference.BINGE,
        preferred_genres=["comedy"],
        mood=Mood.FOCUSED,
        language_preference=None,
        episode_length_preference=EpisodeLengthPreference.ANY,
        watching_context=WatchingContext.ALONE,
    )

    results = recommend_shows(user_input, age=30)

    assert results
    assert any("comedy" in show.genres for show in results)


# ---------- Recommendation reason ----------

def test_recommendation_reason_is_generated_on_clear_match():
    user_input = RecommendationInput(
        binge_preference=BingePreference.BINGE,
        preferred_genres=["comedy"],
        mood=Mood.CHILL,
        language_preference=None,
        episode_length_preference=EpisodeLengthPreference.SHORT,
        watching_context=WatchingContext.ALONE,
    )

    results = recommend_shows(user_input, age=30)

    assert results
    assert any(show.recommendation_reason for show in results)


# ---------- Mood-based logic ----------

def test_mood_is_soft_signal_does_not_filter_results():
    """
    Mood should not eliminate valid shows.
    Results should still be returned even if some shows do not match the mood.
    """
    user_input = RecommendationInput(
        binge_preference=BingePreference.BINGE,
        preferred_genres=[],
        mood=Mood.ADRENALINE,
        language_preference=None,
        episode_length_preference=EpisodeLengthPreference.ANY,
        watching_context=WatchingContext.ALONE,
    )

    results = recommend_shows(user_input, age=30)

    assert results


def test_mood_match_affects_ranking_order():
    """
    Shows that match the selected mood should generally
    appear earlier than those that do not.
    At least one result should have a mood-related recommendation reason.
    """
    user_input = RecommendationInput(
        binge_preference=BingePreference.BINGE,
        preferred_genres=[],
        mood=Mood.CHILL,
        language_preference=None,
        episode_length_preference=EpisodeLengthPreference.ANY,
        watching_context=WatchingContext.ALONE,
    )

    results = recommend_shows(user_input, age=30)

    assert len(results) >= 1
    assert any(
        r.recommendation_reason
        and any(
            phrase in r.recommendation_reason.lower()
            for phrase in ["relaxed", "easy", "chill"]
        )
        for r in results
    )



def test_recommendation_reason_mentions_mood_when_matched():
    """
    When a show matches the selected mood,
    the recommendation_reason should include
    a mood-related explanation.
    """
    user_input = RecommendationInput(
        binge_preference=BingePreference.BINGE,
        preferred_genres=[],
        mood=Mood.HAPPY,
        language_preference=None,
        episode_length_preference=EpisodeLengthPreference.ANY,
        watching_context=WatchingContext.ALONE,
    )

    results = recommend_shows(user_input, age=30)

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

    def mock_get_tv_details_cached(title, **_kwargs):
        return None

    # Patch TMDB adapter function inside logic.py
    monkeypatch.setattr("app.logic.get_tv_details_cached", mock_get_tv_details_cached)

    user_input = RecommendationInput(
        binge_preference=BingePreference.BINGE,
        preferred_genres=[],
        mood=Mood.CHILL,
        language_preference=None,
        episode_length_preference=EpisodeLengthPreference.ANY,
        watching_context=WatchingContext.ALONE,
    )

    results = recommend_shows(user_input, age=30)

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

    def mock_get_tv_details_cached(title, **_kwargs):
        return mocked_tmdb_data

    # Patch TMDB adapter function inside logic.py
    monkeypatch.setattr("app.logic.get_tv_details_cached", mock_get_tv_details_cached)

    user_input = RecommendationInput(
        binge_preference=BingePreference.BINGE,
        preferred_genres=[],
        mood=Mood.HAPPY,
        language_preference=None,
        episode_length_preference=EpisodeLengthPreference.ANY,
        watching_context=WatchingContext.ALONE,
    )

    results = recommend_shows(user_input, age=25)

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

    def mock_get_tv_details_cached(title, **_kwargs):
        return {
            "poster_url": "https://example.com/poster.jpg",
            "rating": 9.0,
            "overview": "Overview",
            "first_air_date": "2022-01-01",
        }

    # Patch TMDB adapter function inside logic.py
    monkeypatch.setattr("app.logic.get_tv_details_cached", mock_get_tv_details_cached)

    user_input = RecommendationInput(
        binge_preference=BingePreference.BINGE,
        preferred_genres=[],
        mood=Mood.FOCUSED,
        language_preference=None,
        episode_length_preference=EpisodeLengthPreference.ANY,
        watching_context=WatchingContext.FAMILY,
    )

    results = recommend_shows(user_input, age=35)

    assert results

    # Existing safety rule: no TV-MA in family context
    assert all(show.content_rating != "TV-MA" for show in results)


def test_recommend_with_query_uses_db_candidates(monkeypatch):
    class DummyShow:
        def __init__(self, id, title, genres=None, overview=None):
            self.id = id
            self.tmdb_id = id + 1000
            self.title = title
            self.genres = genres or []
            self.overview = overview or ""
            self.poster_url = None
            self.vote_average = 8.0
            self.first_air_date = None
            self.popularity = 1.0
            self.vote_count = 100
            self.content_rating = "TV-14"
            self.number_of_seasons = 5  # passes BINGE filter (>3)

    # Ensure no model download during test
    monkeypatch.setattr("app.logic.embed_text", lambda _q: [0.0] * 384)
    # Avoid DB write when persisting TMDB metadata (we pass a dummy db)
    monkeypatch.setattr("app.logic._persist_tmdb_to_show", lambda _db, _sid, _data: None)
    # Return safe metadata so both shows pass post-enrichment filters
    monkeypatch.setattr(
        "app.logic.get_tv_details_cached",
        lambda title, **_: {"content_rating": "TV-14", "poster_url": None, "rating": 8.0, "overview": "x", "first_air_date": "2020-01-01"},
    )

    candidates = [
        DummyShow(1, "Alpha", genres=[35, 18], overview="alpha overview"),
        DummyShow(2, "Beta", genres=["crime"], overview="beta overview"),
    ]

    monkeypatch.setattr("app.logic._fetch_candidate_rows", lambda _db, _vec, _k: candidates)

    user_input = RecommendationInput(
        binge_preference=BingePreference.BINGE,
        preferred_genres=[],  # empty so both Alpha and Beta pass genre filter
        mood=Mood.HAPPY,
        language_preference=None,
        episode_length_preference=EpisodeLengthPreference.ANY,
        watching_context=WatchingContext.ALONE,
        query="funny workplace comedy",
    )

    class MockDB:
        """Minimal mock so recommend_shows doesn't crash on db.query/execute."""

        def execute(self, *args):
            return _MockResult(100)

        def query(self, *args):
            return self

        filter = lambda self, *args: self
        count = lambda self: 100
        first = lambda self: None

        def get_bind(self):
            return type("MockURL", (), {"host": "test", "database": "test", "url": None})()

    class _MockResult:
        def __init__(self, val):
            self._val = val

        def scalar(self):
            return self._val

    db = MockDB()

    results = recommend_shows(user_input, db=db, age=30, top_n=2)

    assert results
    result_titles = {show.title for show in results}
    assert result_titles == {"Alpha", "Beta"}, f"Expected Alpha and Beta, got {result_titles}"


def test_static_data_is_not_mutated_across_requests():
    """
    get_all_shows() returns copies; mutating results must not affect other requests.
    Regression test for data corruption when using static fallback.
    """
    from app.data import get_all_shows

    s1 = get_all_shows()
    s2 = get_all_shows()
    assert s1 is not s2
    assert s1[0] is not s2[0]
    s1[0]["content_rating"] = "MUTATED"
    assert "MUTATED" not in str(s2[0].get("content_rating"))


def test_greys_anatomy_variant_blocked_in_family_context():
    """
    "Greys Anatomy" (no apostrophe) must be blocked in Kids/Family context
    alongside "Grey's Anatomy" - same show, different spelling.
    """
    user_input = RecommendationInput(
        binge_preference=BingePreference.BINGE,
        preferred_genres=[],
        mood=Mood.CHILL,
        language_preference=None,
        episode_length_preference=EpisodeLengthPreference.ANY,
        watching_context=WatchingContext.FAMILY,
    )
    results = recommend_shows(user_input, age=35)
    titles_lower = [s.title.lower() for s in results]
    assert "greys anatomy" not in titles_lower
    assert "grey's anatomy" not in titles_lower


def test_tmdb_cache_reuses_network_results_across_consecutive_recommend_calls(monkeypatch):
    import app.tmdb as tmdb

    monkeypatch.setattr(tmdb, "TMDB_API_KEY", "test-key")
    tmdb.clear_tmdb_cache()

    calls = {"count": 0}

    def mock_uncached(title, *, year=None):
        calls["count"] += 1
        return {
            "tmdb_id": 1000 + calls["count"],
            "poster_url": f"https://example.com/{title}.jpg",
            "overview": "cached overview",
            "rating": 8.0,
            "first_air_date": "2020-01-01",
        }

    monkeypatch.setattr("app.tmdb._search_tv_show_uncached", mock_uncached)

    user_input = RecommendationInput(
        binge_preference=BingePreference.BINGE,
        preferred_genres=[],
        mood=Mood.CHILL,
        language_preference=None,
        episode_length_preference=EpisodeLengthPreference.ANY,
        watching_context=WatchingContext.ALONE,
    )

    results1 = recommend_shows(user_input, top_n=3, age=30)
    results2 = recommend_shows(user_input, top_n=3, age=30)

    assert len(results1) == 3
    assert len(results2) == 3
    # Only one network call per unique title; second recommend call should hit cache.
    assert calls["count"] == 3
