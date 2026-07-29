"""
Integration tests for CPU metrics ingestion and retrieval endpoints.
"""
from datetime import datetime, timedelta, timezone


class TestIngestCPUMetric:
    def test_valid_ingest_returns_201(self, auth_client):
        payload = {
            "vm_id": "test-vm-001",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "cpu_percent": 55.0,
            "source": "test",
        }
        response = auth_client.post("/api/v1/metrics/cpu", json=payload)
        assert response.status_code == 201

    def test_ingest_returns_ingestion_id(self, auth_client):
        payload = {
            "vm_id": "test-vm-001",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "cpu_percent": 30.0,
            "source": "test",
        }
        response = auth_client.post("/api/v1/metrics/cpu", json=payload)
        data = response.json()
        assert "ingestion_id" in data

    def test_ingest_cpu_percent_too_high(self, auth_client):
        payload = {
            "vm_id": "test-vm-001",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "cpu_percent": 150.0,
            "source": "test",
        }
        response = auth_client.post("/api/v1/metrics/cpu", json=payload)
        assert response.status_code == 422

    def test_ingest_cpu_percent_negative(self, auth_client):
        payload = {
            "vm_id": "test-vm-001",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "cpu_percent": -10.0,
            "source": "test",
        }
        response = auth_client.post("/api/v1/metrics/cpu", json=payload)
        assert response.status_code == 422

    def test_ingest_unknown_vm(self, auth_client):
        payload = {
            "vm_id": "does-not-exist",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "cpu_percent": 50.0,
            "source": "test",
        }
        response = auth_client.post("/api/v1/metrics/cpu", json=payload)
        assert response.status_code == 404

    def test_ingest_updates_vm_live_state(self, auth_client):
        """Ingestion must keep current_cpu and the 24h average on the VM row
        in sync (previously only a separate legacy endpoint did this)."""
        payload = {
            "vm_id": "test-vm-001",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "cpu_percent": 77.5,
            "source": "test",
        }
        response = auth_client.post("/api/v1/metrics/cpu", json=payload)
        assert response.status_code == 201

        vm = auth_client.get("/api/v1/vms/test-vm-001").json()
        assert vm["current_cpu"] == 77.5
        assert vm["avg_cpu_24h"] is not None

    def test_legacy_ingest_endpoint_removed(self, auth_client):
        """POST /api/v1/metrics was consolidated into /api/v1/metrics/cpu."""
        payload = {
            "vm_id": "test-vm-001",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "cpu_percent": 50.0,
        }
        response = auth_client.post("/api/v1/metrics", json=payload)
        assert response.status_code in (404, 405)


class TestGetCPUMetrics:
    def test_get_metrics_returns_200(self, auth_client):
        response = auth_client.get("/api/v1/metrics/cpu/test-vm-001")
        assert response.status_code == 200

    def test_get_metrics_has_data(self, auth_client):
        response = auth_client.get("/api/v1/metrics/cpu/test-vm-001")
        data = response.json()
        assert data["total_records"] > 0
        assert len(data["metrics"]) > 0

    def test_get_metrics_limit(self, auth_client):
        response = auth_client.get("/api/v1/metrics/cpu/test-vm-001?limit=3")
        data = response.json()
        assert len(data["metrics"]) <= 3

    def test_get_metrics_limit_keeps_most_recent(self, auth_client):
        """Regression test: when the window holds more rows than `limit`,
        the endpoint must return the most recent rows, not the oldest slice.

        Ingests 5 metrics for test-vm-003 several hours in the past (well
        outside any other test's "now"-timestamped data, so this is immune
        to ordering/pollution from the rest of the suite) and scopes the
        query with start_time/end_time to that exact window.
        """
        base = datetime.now(timezone.utc) - timedelta(hours=3)
        for i in range(5):
            auth_client.post("/api/v1/metrics/cpu", json={
                "vm_id": "test-vm-003",
                "timestamp": (base - timedelta(minutes=i * 5)).isoformat(),
                "cpu_percent": 10.0 + i * 10,
                "source": "test",
            })

        response = auth_client.get(
            "/api/v1/metrics/cpu/test-vm-003",
            params={
                "start_time": (base - timedelta(minutes=25)).isoformat(),
                "end_time": (base + timedelta(minutes=5)).isoformat(),
                "limit": 3,
            },
        )
        data = response.json()["metrics"]
        assert len(data) == 3
        # i=0..2 (cpu 10/20/30) are the 3 most recent of the 5; returned
        # oldest-to-newest, i.e. 30.0 (i=2) first, 10.0 (i=0, most recent) last.
        assert [m["cpu_percent"] for m in data] == [30.0, 20.0, 10.0]
        timestamps = [m["timestamp"] for m in data]
        assert timestamps == sorted(timestamps)

    def test_get_metrics_unknown_vm(self, auth_client):
        response = auth_client.get("/api/v1/metrics/cpu/does-not-exist")
        assert response.status_code == 404

    def test_get_metrics_limit_bounds(self, auth_client):
        assert auth_client.get("/api/v1/metrics/cpu/test-vm-001?limit=0").status_code == 422
        assert auth_client.get("/api/v1/metrics/cpu/test-vm-001?limit=99999").status_code == 422

