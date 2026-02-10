from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import get_db
from app.models import User, WatchlistItem
from app.routers import auth, watchlist


def _make_test_client() -> TestClient:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    # Create only tables needed by auth/watchlist endpoints.
    User.__table__.create(bind=engine, checkfirst=True)
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
    return TestClient(app)


def _register(client: TestClient, email: str, password: str = "secret123"):
    return client.post("/auth/register", json={"email": email, "password": password})


def _login(client: TestClient, email: str, password: str = "secret123") -> str:
    res = client.post("/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200
    return res.json()["access_token"]


def _auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_add_show_to_watchlist_authorized():
    client = _make_test_client()
    _register(client, "watcher@example.com")
    token = _login(client, "watcher@example.com")

    res = client.post(
        "/watchlist/add",
        json={"title": "Stranger Things"},
        headers=_auth_header(token),
    )

    assert res.status_code == 200
    data = res.json()
    assert data["watchlist"] == [{"title": "Stranger Things"}]


def test_prevent_duplicate_watchlist_saves():
    client = _make_test_client()
    _register(client, "dupe-watch@example.com")
    token = _login(client, "dupe-watch@example.com")

    first = client.post(
        "/watchlist/add",
        json={"title": "Dark"},
        headers=_auth_header(token),
    )
    second = client.post(
        "/watchlist/add",
        json={"title": "Dark"},
        headers=_auth_header(token),
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["watchlist"] == [{"title": "Dark"}]


def test_list_watchlist_items():
    client = _make_test_client()
    _register(client, "list-watch@example.com")
    token = _login(client, "list-watch@example.com")

    client.post("/watchlist/add", json={"title": "Show A"}, headers=_auth_header(token))
    client.post("/watchlist/add", json={"title": "Show B"}, headers=_auth_header(token))

    res = client.get("/watchlist", headers=_auth_header(token))

    assert res.status_code == 200
    titles = [item["title"] for item in res.json()["watchlist"]]
    assert set(titles) == {"Show A", "Show B"}


def test_remove_item_from_watchlist():
    client = _make_test_client()
    _register(client, "remove-watch@example.com")
    token = _login(client, "remove-watch@example.com")

    client.post("/watchlist/add", json={"title": "The Office"}, headers=_auth_header(token))
    remove_res = client.post(
        "/watchlist/remove",
        json={"title": "The Office"},
        headers=_auth_header(token),
    )
    list_res = client.get("/watchlist", headers=_auth_header(token))

    assert remove_res.status_code == 200
    assert remove_res.json()["watchlist"] == []
    assert list_res.status_code == 200
    assert list_res.json()["watchlist"] == []


def test_watchlist_access_without_token_is_401():
    client = _make_test_client()

    get_res = client.get("/watchlist")
    add_res = client.post("/watchlist/add", json={"title": "No Auth Show"})
    remove_res = client.post("/watchlist/remove", json={"title": "No Auth Show"})

    assert get_res.status_code == 401
    assert add_res.status_code == 401
    assert remove_res.status_code == 401


def test_users_cannot_access_or_mutate_other_users_watchlists():
    client = _make_test_client()
    _register(client, "user-a@example.com")
    _register(client, "user-b@example.com")
    token_a = _login(client, "user-a@example.com")
    token_b = _login(client, "user-b@example.com")

    client.post("/watchlist/add", json={"title": "Private Show"}, headers=_auth_header(token_a))

    user_b_list = client.get("/watchlist", headers=_auth_header(token_b))
    user_b_remove = client.post(
        "/watchlist/remove",
        json={"title": "Private Show"},
        headers=_auth_header(token_b),
    )
    user_a_list_after = client.get("/watchlist", headers=_auth_header(token_a))

    assert user_b_list.status_code == 200
    assert user_b_list.json()["watchlist"] == []
    assert user_b_remove.status_code == 200
    assert user_b_remove.json()["watchlist"] == []
    assert user_a_list_after.status_code == 200
    assert user_a_list_after.json()["watchlist"] == [{"title": "Private Show"}]
