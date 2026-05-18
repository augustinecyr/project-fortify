"""
Integration tests for OAuth2/JWT authentication.
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.auth.security import get_password_hash
from app.models.user import User

TEST_DB_URL = "postgresql+psycopg://fortify_user:fortify_pass@localhost:5432/fortify_test"
_engine = create_engine(TEST_DB_URL, pool_pre_ping=True)
_Session = sessionmaker(bind=_engine)

_TEST_USERNAME = "auth_test_user"
_TEST_PASSWORD = "authpass123"


@pytest.fixture(scope="session", autouse=True)
def seed_auth_user(setup_test_database):
    db = _Session()
    try:
        if not db.query(User).filter(User.username == _TEST_USERNAME).first():
            db.add(User(
                username=_TEST_USERNAME,
                hashed_password=get_password_hash(_TEST_PASSWORD),
                is_active=True,
            ))
            db.commit()
    finally:
        db.close()


class TestAuthToken:
    def test_login_returns_bearer_token(self, client):
        r = client.post(
            "/auth/token",
            data={"username": _TEST_USERNAME, "password": _TEST_PASSWORD},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert r.status_code == 200
        body = r.json()
        assert "access_token" in body
        assert body["token_type"] == "bearer"

    def test_wrong_password_returns_401(self, client):
        r = client.post(
            "/auth/token",
            data={"username": _TEST_USERNAME, "password": "wrongpassword"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert r.status_code == 401

    def test_unknown_user_returns_401(self, client):
        r = client.post(
            "/auth/token",
            data={"username": "nobody", "password": "anything"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        assert r.status_code == 401


class TestTokenProtection:
    def test_protected_route_rejects_missing_token(self, client):
        r = client.get("/api/v1/vms/summary")
        assert r.status_code == 401

    def test_valid_token_grants_access(self, client):
        token = client.post(
            "/auth/token",
            data={"username": _TEST_USERNAME, "password": _TEST_PASSWORD},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        ).json()["access_token"]

        r = client.get(
            "/api/v1/vms/summary",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 200
