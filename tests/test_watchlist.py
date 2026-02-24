from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import get_db
from app.models import User, WatchlistItem, Show
from app.routers import auth, watchlist


def _make_test_client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    # Create tables: User, Show (for watchlist FK), WatchlistItem
    User.__table__.create(bind=engine, checkfirst=True)
    Show.__table__.create(bind=engine, checkfirst=True)
    WatchlistItem.__table__.create(bind=engine, checkfirst=True)

    app = FastAPI()
    app.include_router(auth.router)
    app.include_router(watchlist.router)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    return client, TestingSessionLocal


def _register(client: TestClient, email: str, password: str = "secret123"):
    return client.post("/auth/register", json={"email": email, "password": password})


def _login(client: TestClient, email: str, password: str = "secret123") -> str:
    res = client.post("/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200
    return res.json()["access_token"]


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _seed_show(session_factory, show_id: int = 1, title: str = "Stranger Things", poster_url: str | None = None):
    """Insert a show for tests that use show_id."""
    db = session_factory()
    try:
        existing = db.query(Show).filter(Show.id == show_id).first()
        if existing:
            return
        db.add(Show(id=show_id, tmdb_id=1000 + show_id, title=title, poster_url=poster_url))
        db.commit()
    finally:
        db.close()


def test_add_show_to_watchlist_authorized():
    client, session_factory = _make_test_client()
    _seed_show(session_factory, 1, "Stranger Things")
    _register(client, "watcher@example.com")
    token = _login(client, "watcher@example.com")

    res = client.post(
        "/watchlist/add",
        json={"show_id": 1},
        headers=_auth_header(token),
    )

    assert res.status_code == 200
    data = res.json()
    assert data["watchlist"] == [{"show_id": 1, "title": "Stranger Things", "poster_url": None}]


def test_prevent_duplicate_watchlist_saves():
    client, session_factory = _make_test_client()
    _seed_show(session_factory, 1, "Dark")
    _register(client, "dupe-watch@example.com")
    token = _login(client, "dupe-watch@example.com")

    first = client.post(
        "/watchlist/add",
        json={"show_id": 1},
        headers=_auth_header(token),
    )
    second = client.post(
        "/watchlist/add",
        json={"show_id": 1},
        headers=_auth_header(token),
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["watchlist"] == [{"show_id": 1, "title": "Dark", "poster_url": None}]


def test_list_watchlist_items():
    client, session_factory = _make_test_client()
    _seed_show(session_factory, 1, "Show A")
    _seed_show(session_factory, 2, "Show B")
    _register(client, "list-watch@example.com")
    token = _login(client, "list-watch@example.com")

    client.post("/watchlist/add", json={"show_id": 1}, headers=_auth_header(token))
    client.post("/watchlist/add", json={"show_id": 2}, headers=_auth_header(token))

    res = client.get("/watchlist", headers=_auth_header(token))

    assert res.status_code == 200
    titles = [item["title"] for item in res.json()["watchlist"]]
    assert set(titles) == {"Show A", "Show B"}


def test_remove_item_from_watchlist():
    client, session_factory = _make_test_client()
    _seed_show(session_factory, 1, "The Office")
    _register(client, "remove-watch@example.com")
    token = _login(client, "remove-watch@example.com")

    client.post("/watchlist/add", json={"show_id": 1}, headers=_auth_header(token))
    remove_res = client.post(
        "/watchlist/remove",
        json={"show_id": 1},
        headers=_auth_header(token),
    )
    list_res = client.get("/watchlist", headers=_auth_header(token))

    assert remove_res.status_code == 200
    assert remove_res.json()["watchlist"] == []
    assert list_res.status_code == 200
    assert list_res.json()["watchlist"] == []


def test_remove_by_title_legacy():
    """Remove by title still works (for legacy items or backward compatibility)."""
    client, session_factory = _make_test_client()
    _seed_show(session_factory, 1, "Legacy Show")
    _register(client, "legacy@example.com")
    token = _login(client, "legacy@example.com")
    client.post("/watchlist/add", json={"show_id": 1}, headers=_auth_header(token))
    remove_res = client.post(
        "/watchlist/remove",
        json={"title": "Legacy Show"},
        headers=_auth_header(token),
    )
    assert remove_res.status_code == 200
    assert remove_res.json()["watchlist"] == []


def test_watchlist_access_without_token_is_401():
    client, _ = _make_test_client()

    get_res = client.get("/watchlist")
    add_res = client.post("/watchlist/add", json={"show_id": 1})
    remove_res = client.post("/watchlist/remove", json={"show_id": 1})

    assert get_res.status_code == 401
    assert add_res.status_code == 401
    assert remove_res.status_code == 401


def test_users_cannot_access_or_mutate_other_users_watchlists():
    client, session_factory = _make_test_client()
    _seed_show(session_factory, 1, "Private Show")
    _register(client, "user-a@example.com")
    _register(client, "user-b@example.com")
    token_a = _login(client, "user-a@example.com")
    token_b = _login(client, "user-b@example.com")

    client.post("/watchlist/add", json={"show_id": 1}, headers=_auth_header(token_a))

    user_b_list = client.get("/watchlist", headers=_auth_header(token_b))
    user_b_remove = client.post(
        "/watchlist/remove",
        json={"show_id": 1},
        headers=_auth_header(token_b),
    )
    user_a_list_after = client.get("/watchlist", headers=_auth_header(token_a))

    assert user_b_list.status_code == 200
    assert user_b_list.json()["watchlist"] == []
    assert user_b_remove.status_code == 200
    assert user_b_remove.json()["watchlist"] == []
    assert user_a_list_after.status_code == 200
    assert user_a_list_after.json()["watchlist"] == [{"show_id": 1, "title": "Private Show", "poster_url": None}]
