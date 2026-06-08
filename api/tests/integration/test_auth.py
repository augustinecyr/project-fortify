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


class TestRBAC:
    """Role-based authorization: viewer < operator < admin."""

    # --- reads: every authenticated role is allowed ---
    def test_viewer_can_read(self, viewer_client):
        assert viewer_client.get("/api/v1/vms/summary").status_code == 200

    def test_me_reports_role(self, viewer_client):
        body = viewer_client.get("/auth/me").json()
        assert body["role"] == "viewer"

    # --- writes: viewer denied, operator allowed ---
    def test_viewer_cannot_update_vm(self, viewer_client):
        r = viewer_client.patch("/api/v1/vms/test-vm-001", json={"status": "online"})
        assert r.status_code == 403

    def test_operator_can_update_vm(self, operator_client):
        r = operator_client.patch("/api/v1/vms/test-vm-001", json={"status": "online"})
        assert r.status_code == 200

    def test_viewer_cannot_ingest_metric(self, viewer_client):
        r = viewer_client.post("/api/v1/metrics/cpu", json={
            "vm_id": "test-vm-001",
            "timestamp": "2026-06-06T00:00:00+00:00",
            "cpu_percent": 42.0,
            "source": "rbac-test",
        })
        assert r.status_code == 403

    def test_operator_can_ingest_metric(self, operator_client):
        r = operator_client.post("/api/v1/metrics/cpu", json={
            "vm_id": "test-vm-001",
            "timestamp": "2026-06-06T00:00:00+00:00",
            "cpu_percent": 42.0,
            "source": "rbac-test",
        })
        assert r.status_code == 201

    # --- admin-only: user management ---
    def test_operator_cannot_create_user(self, operator_client):
        r = operator_client.post("/auth/users", json={
            "username": "should_not_exist", "password": "password123", "role": "viewer",
        })
        assert r.status_code == 403

    def test_admin_can_create_user(self, auth_client):
        r = auth_client.post("/auth/users", json={
            "username": "rbac_made_user", "password": "password123", "role": "operator",
        })
        assert r.status_code in (201, 409)  # 409 if a prior run already created it

    def test_admin_rejects_invalid_role(self, auth_client):
        r = auth_client.post("/auth/users", json={
            "username": "bad_role_user", "password": "password123", "role": "superuser",
        })
        assert r.status_code == 400
