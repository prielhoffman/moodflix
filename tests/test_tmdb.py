import importlib
import os
import pytest
import requests

import app.tmdb as tmdb


# -------------------- Helpers --------------------

class MockResponse:
    """
    Simple mock response object for requests.get
    """

    def __init__(self, json_data, status_code=200):
        self._json_data = json_data
        self.status_code = status_code

    def json(self):
        return self._json_data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError("HTTP error")


# -------------------- Tests --------------------

@pytest.fixture(autouse=True)
def setup_tmdb_cache_and_key(monkeypatch):
    # Keep tests deterministic regardless of local environment.
    monkeypatch.setattr(tmdb, "TMDB_API_KEY", "test-key")
    tmdb.clear_tmdb_cache()
    yield
    tmdb.clear_tmdb_cache()


def test_no_results_returns_none(monkeypatch):
    """
    When TMDB returns an empty results list,
    search_tv_show should return None and not crash.
    """

    def mock_get(*args, **kwargs):
        return MockResponse({"results": []})

    monkeypatch.setattr(tmdb.requests, "get", mock_get)

    result = tmdb.search_tv_show("asdasd_qwe_12345")

    assert result is None


def test_no_poster_returns_none_poster_url(monkeypatch):
    """
    When poster_path is None,
    poster_url should be None and not raise errors.
    """

    def mock_get(*args, **kwargs):
        return MockResponse(
            {
                "results": [
                    {
                        "id": 123,
                        "poster_path": None,
                        "overview": "Test overview",
                        "vote_average": 7.5,
                        "first_air_date": "2020-01-01",
                    }
                ]
            }
        )

    monkeypatch.setattr(tmdb.requests, "get", mock_get)

    result = tmdb.search_tv_show("Test Show")

    assert result is not None
    assert result["poster_url"] is None


def test_valid_result_structure(monkeypatch):
    """
    When TMDB returns a valid result,
    the returned dictionary should contain valid types.
    """

    def mock_get(*args, **kwargs):
        return MockResponse(
            {
                "results": [
                    {
                        "id": 456,
                        "poster_path": "/poster.jpg",
                        "overview": "Some overview",
                        "vote_average": 8.3,
                        "first_air_date": "2019-05-10",
                    }
                ]
            }
        )

    monkeypatch.setattr(tmdb.requests, "get", mock_get)

    result = tmdb.search_tv_show("Valid Show")

    assert result is not None

    assert isinstance(result["tmdb_id"], int)

    assert result["poster_url"] is None or isinstance(result["poster_url"], str)

    assert result["rating"] is None or isinstance(result["rating"], float)

    assert result["overview"] is None or isinstance(result["overview"], str)

    assert result["first_air_date"] is None or isinstance(result["first_air_date"], str)


def test_network_failure_returns_none(monkeypatch):
    """
    When requests.get raises an exception,
    search_tv_show should return None and not crash.
    """

    def mock_get(*args, **kwargs):
        raise requests.RequestException("Network error")

    monkeypatch.setattr(tmdb.requests, "get", mock_get)

    result = tmdb.search_tv_show("Network Failure Show")

    assert result is None


