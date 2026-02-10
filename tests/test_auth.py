from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import get_db
from app.models import User
from app.routers import auth
from app.security import create_access_token


def _make_test_client() -> TestClient:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    # Create only auth/watchlist-related tables for this test app.
    User.__table__.create(bind=engine, checkfirst=True)

    app = FastAPI()
    app.include_router(auth.router)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


def _register(client: TestClient, email: str, password: str = "secret123"):
    return client.post(
        "/auth/register",
        json={"email": email, "password": password},
    )


def _login(client: TestClient, email: str, password: str = "secret123"):
    return client.post(
        "/auth/login",
        json={"email": email, "password": password},
    )


def test_register_success():
    client = _make_test_client()

    res = _register(client, "user1@example.com")

    assert res.status_code == 200
    data = res.json()
    assert data["email"] == "user1@example.com"
    assert "id" in data
    assert "created_at" in data


def test_register_duplicate_email_rejected():
    client = _make_test_client()
    _register(client, "dupe@example.com")

    res = _register(client, "dupe@example.com")

    assert res.status_code == 400
    assert res.json()["detail"] == "Email already registered"


def test_login_success():
    client = _make_test_client()
    _register(client, "login-ok@example.com", "pw123456")

    res = _login(client, "login-ok@example.com", "pw123456")

    assert res.status_code == 200
    data = res.json()
    assert data["token_type"] == "bearer"
    assert isinstance(data["access_token"], str)
    assert data["access_token"]


def test_login_wrong_password_rejected():
    client = _make_test_client()
    _register(client, "login-fail@example.com", "correct-pass")

    res = _login(client, "login-fail@example.com", "wrong-pass")

    assert res.status_code == 401
    assert res.json()["detail"] == "Invalid credentials"


def test_auth_me_with_valid_token_returns_user():
    client = _make_test_client()
    _register(client, "me@example.com", "pw123456")
    login_res = _login(client, "me@example.com", "pw123456")
    token = login_res.json()["access_token"]

    res = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert res.status_code == 200
    assert res.json()["email"] == "me@example.com"


def test_auth_me_without_token_returns_401():
    client = _make_test_client()

    res = client.get("/auth/me")

    assert res.status_code == 401


def test_auth_me_with_invalid_or_expired_token_returns_401():
    client = _make_test_client()
    _register(client, "expired@example.com", "pw123456")

    # Create a token that is already expired.
    expired_token = create_access_token({"user_id": 1, "email": "expired@example.com"}, expires_minutes=-1)

    expired_res = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    invalid_res = client.get(
        "/auth/me",
        headers={"Authorization": "Bearer not-a-real-jwt"},
    )

    assert expired_res.status_code == 401
    assert invalid_res.status_code == 401
