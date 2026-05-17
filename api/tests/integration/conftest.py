"""
Shared fixtures for integration tests.

Database strategy:
- Uses a separate 'fortify_test' PostgreSQL database.
- Tables are created fresh at session start and dropped at session end.
- Seed data (3 VMs + CPU metrics) is inserted once per session.

Redis strategy:
- cache_get / cache_set are patched to no-ops for the full test session.
- This prevents stale cache hits from masking live DB results.

Usage:
    pytest api/tests/integration/ -v
"""
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.db.database import Base, get_db
from app.db.models import VirtualMachine, CPUMetric
from app.models.user import User
from app.auth.security import get_password_hash

_SUITE_USER = "suite_admin"
_SUITE_PASS = "suitepass123"

# ---------------------------------------------------------------------------
# Test database — separate from dev DB, never touches fortify
# ---------------------------------------------------------------------------
TEST_DB_URL = "postgresql+psycopg://fortify_user:fortify_pass@localhost:5432/fortify_test"

test_engine = create_engine(TEST_DB_URL, pool_pre_ping=True)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


# ---------------------------------------------------------------------------
# Session-scoped: create tables once, drop after all tests finish
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


# ---------------------------------------------------------------------------
# Session-scoped: seed 3 VMs + CPU metrics once for the full test run
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session", autouse=True)
def seed_test_data(setup_test_database):
    db = TestingSessionLocal()
    try:
        vms = [
            VirtualMachine(
                vm_id="test-vm-001",
                name="web-server-test-01",
                status="online",
                host="host-01",
                os_version="Ubuntu 22.04 LTS",
                health_score=85,
                security_score=78,
                current_cpu=42.5,
                current_memory=61.0,
                current_disk=38.0,
                memory_total_mb=8192,
                memory_used_mb=5000,
                disk_total_gb=100,
                disk_used_gb=38,
                open_vulnerabilities=2,
                critical_vulnerabilities=0,
                firewall_enabled=True,
                ssh_key_auth=True,
                disk_encryption=False,
                alert_count=1,
                anomaly_detected=False,
                avg_cpu_24h=40.0,
                peak_cpu_24h=78.0,
                uptime_hours=240.0,
                last_patch_date=datetime.now(timezone.utc) - timedelta(days=15),
            ),
            VirtualMachine(
                vm_id="test-vm-002",
                name="db-server-test-02",
                status="online",
                host="host-02",
                os_version="Ubuntu 20.04 LTS",
                health_score=62,
                security_score=55,
                current_cpu=88.0,
                current_memory=79.0,
                current_disk=91.0,
                memory_total_mb=16384,
                memory_used_mb=12900,
                disk_total_gb=200,
                disk_used_gb=182,
                open_vulnerabilities=6,
                critical_vulnerabilities=2,
                firewall_enabled=False,
                ssh_key_auth=True,
                disk_encryption=True,
                alert_count=4,
                anomaly_detected=True,
                avg_cpu_24h=85.0,
                peak_cpu_24h=98.0,
                uptime_hours=720.0,
                last_patch_date=datetime.now(timezone.utc) - timedelta(days=60),
            ),
            VirtualMachine(
                vm_id="test-vm-003",
                name="worker-test-03",
                status="offline",
                host="host-01",
                os_version="Ubuntu 22.04 LTS",
                health_score=45,
                security_score=90,
                current_cpu=5.0,
                current_memory=20.0,
                current_disk=15.0,
                memory_total_mb=4096,
                memory_used_mb=820,
                disk_total_gb=50,
                disk_used_gb=8,
                open_vulnerabilities=0,
                critical_vulnerabilities=0,
                firewall_enabled=True,
                ssh_key_auth=True,
                disk_encryption=True,
                alert_count=0,
                anomaly_detected=False,
                avg_cpu_24h=8.0,
                peak_cpu_24h=22.0,
                uptime_hours=0.0,
                last_patch_date=datetime.now(timezone.utc) - timedelta(days=3),
            ),
        ]
        db.add_all(vms)
        db.flush()

        # Add 10 CPU metrics for test-vm-001 and test-vm-002
        now = datetime.now(timezone.utc)
        metrics = []
        for i in range(10):
            metrics.append(CPUMetric(
                vm_id="test-vm-001",
                timestamp=now - timedelta(minutes=i * 5),
                cpu_percent=40.0 + i,
                source="test",
            ))
            metrics.append(CPUMetric(
                vm_id="test-vm-002",
                timestamp=now - timedelta(minutes=i * 5),
                cpu_percent=85.0 + (i % 5),
                source="test",
            ))
        db.add_all(metrics)

        if not db.query(User).filter(User.username == _SUITE_USER).first():
            db.add(User(
                username=_SUITE_USER,
                hashed_password=get_password_hash(_SUITE_PASS),
                is_active=True,
            ))

        db.commit()
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Function-scoped: DB override + Redis patch for every test
# ---------------------------------------------------------------------------
@pytest.fixture()
def client():
    """
    TestClient with:
    - get_db overridden to use the test database
    - cache_get patched to always return None (cache miss)
    - cache_set patched to no-op
    """
    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    with patch("app.utils.redis_client.cache_get", return_value=None), \
         patch("app.utils.redis_client.cache_set", return_value=None):
        with TestClient(app) as c:
            yield c

    app.dependency_overrides.clear()


@pytest.fixture()
def auth_client(client):
    """TestClient pre-loaded with a valid Bearer token for protected routes."""
    token = client.post(
        "/auth/token",
        data={"username": _SUITE_USER, "password": _SUITE_PASS},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    ).json()["access_token"]
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client