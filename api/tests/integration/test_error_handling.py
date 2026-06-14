"""
Integration tests for API error semantics:
- consistent error envelope + correlation id (X-Request-ID)
- global DB-error handlers (OperationalError -> 503, IntegrityError -> 409)
- generic unhandled errors -> 500 without leaking internals
- /api/v1/status -> 503 when the database is unreachable
- AI cache-clear failure -> generic 500 (no raw exception echoed)
"""
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError, OperationalError

from app.main import app
from app.db.database import get_db

# Same test database the suite uses (see conftest). Recreated here so a fake
# session can delegate real reads while forcing a commit to fail.
_TEST_DB_URL = "postgresql+psycopg://fortify_user:fortify_pass@localhost:5432/fortify_test"
_real_session = sessionmaker(
    autocommit=False, autoflush=False,
    bind=create_engine(_TEST_DB_URL, pool_pre_ping=True),
)

_FORM = {"Content-Type": "application/x-www-form-urlencoded"}


class _RaisingDB:
    """Stands in for a Session whose every query/execute fails — i.e. the DB
    is unreachable."""
    def __init__(self, exc):
        self._exc = exc

    def query(self, *a, **k):
        raise self._exc

    def execute(self, *a, **k):
        raise self._exc

    def rollback(self):
        pass

    def close(self):
        pass


class _CommitFailDB:
    """Delegates reads to a real session but raises on commit — simulates a
    concurrent insert losing the race on a unique constraint (TOCTOU)."""
    def __init__(self, real, exc):
        self._real = real
        self._exc = exc

    def commit(self):
        raise self._exc

    def __getattr__(self, name):
        return getattr(self._real, name)


def _override_raising(exc):
    def _gen():
        yield _RaisingDB(exc)
    return _gen


def _override_commit_fail(exc):
    def _gen():
        real = _real_session()
        try:
            yield _CommitFailDB(real, exc)
        finally:
            real.close()
    return _gen


class TestCorrelationId:
    def test_request_id_header_on_success(self, client):
        r = client.get("/")
        assert r.status_code == 200
        assert r.headers.get("X-Request-ID")


class TestSystemStatus:
    def test_status_503_when_db_down(self, client):
        app.dependency_overrides[get_db] = _override_raising(
            OperationalError("SELECT 1", {}, Exception("connection refused"))
        )
        r = client.get("/api/v1/status")
        assert r.status_code == 503
        body = r.json()
        assert body["database"] == "disconnected"
        assert body["status"] == "degraded"
        # raw driver text must never reach the client
        assert "connection refused" not in str(body)


class TestGlobalDbHandlers:
    def test_db_unavailable_returns_503(self, client):
        app.dependency_overrides[get_db] = _override_raising(
            OperationalError("SELECT", {}, Exception("server closed the connection"))
        )
        r = client.post(
            "/auth/token",
            data={"username": "anyone", "password": "whatever"},
            headers=_FORM,
        )
        assert r.status_code == 503
        body = r.json()
        assert "dependency" in body["detail"].lower()
        assert body["request_id"]
        assert r.headers.get("X-Request-ID")
        assert "server closed" not in str(body)

    def test_integrity_error_returns_409(self, auth_client):
        # Logged in as admin via the normal override; now force commit to fail.
        app.dependency_overrides[get_db] = _override_commit_fail(
            IntegrityError("INSERT", {}, Exception("duplicate key"))
        )
        r = auth_client.post(
            "/auth/users",
            json={"username": "race_user", "password": "racepass123", "role": "viewer"},
        )
        assert r.status_code == 409
        body = r.json()
        assert body["request_id"]
        assert "duplicate key" not in str(body)


class TestUnhandledError:
    def test_unexpected_error_returns_generic_500(self):
        app.dependency_overrides[get_db] = _override_raising(ValueError("boom internal detail"))
        try:
            with TestClient(app, raise_server_exceptions=False) as c:
                r = c.post(
                    "/auth/token",
                    data={"username": "x", "password": "y"},
                    headers=_FORM,
                )
            assert r.status_code == 500
            body = r.json()
            assert body["detail"] == "An unexpected error occurred."
            assert body["request_id"]
            assert "boom internal detail" not in str(body)
        finally:
            app.dependency_overrides.clear()


class TestCacheClearFailure:
    def test_cache_clear_failure_is_generic_500(self, auth_client):
        with patch("app.routers.ai.get_redis_client", side_effect=RuntimeError("redis down at 10.0.0.5")):
            r = auth_client.delete("/api/v1/ai/cache")
        assert r.status_code == 500
        body = r.json()
        assert body["detail"] == "Failed to clear AI cache."
        assert "10.0.0.5" not in str(body)
