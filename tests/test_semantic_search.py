from datetime import date

from fastapi.testclient import TestClient

from app.api import app
from app.db import get_db
from app.routers import search as search_router


class FakeShow:
    def __init__(self, *, id, title, genres=None, overview=None, poster_url=None, vote_average=None, first_air_date=None):
        self.id = id
        self.title = title
        self.genres = genres
        self.overview = overview
        self.poster_url = poster_url
        self.vote_average = vote_average
        self.first_air_date = first_air_date


class _FakeQuery:
    def __init__(self, rows):
        self._rows = rows

    def filter(self, *_args, **_kwargs):
        return self

    def order_by(self, *_args, **_kwargs):
        return self

    def limit(self, *_args, **_kwargs):
        return self

    def all(self):
        return self._rows


class FakeDB:
    def __init__(self, rows):
        self._rows = rows

    def query(self, *_args, **_kwargs):
        return _FakeQuery(self._rows)


def test_semantic_search_returns_sorted_by_distance(monkeypatch):
    # Mock embeddings so no model download is required
    monkeypatch.setattr(search_router, "embed_text", lambda _q: [0.0] * 384)

    rows = [
        (FakeShow(id=1, title="B", genres=["comedy"], overview="bbb", first_air_date=date(2020, 1, 1)), 0.6),
        (FakeShow(id=2, title="A", genres=[35, 18], overview="aaa", first_air_date=date(2021, 1, 1)), 0.2),
        (FakeShow(id=3, title="C", genres=["crime"], overview="ccc", first_air_date=None), 0.9),
    ]

    app.dependency_overrides[get_db] = lambda: (yield FakeDB(rows))

    client = TestClient(app)
    res = client.post("/search/semantic", json={"query": "detective show", "top_k": 10})
    assert res.status_code == 200

    data = res.json()
    assert [item["id"] for item in data] == [2, 1, 3]
    assert [item["distance"] for item in data] == sorted([0.2, 0.6, 0.9])
    assert data[0]["genres"] == ["comedy", "drama"]

    app.dependency_overrides.clear()


def test_semantic_search_empty_embeddings_returns_empty_list(monkeypatch):
    monkeypatch.setattr(search_router, "embed_text", lambda _q: [0.0] * 384)

    app.dependency_overrides[get_db] = lambda: (yield FakeDB([]))

    client = TestClient(app)
    res = client.post("/search/semantic", json={"query": "anything", "top_k": 10})
    assert res.status_code == 200
    assert res.json() == []

    app.dependency_overrides.clear()

