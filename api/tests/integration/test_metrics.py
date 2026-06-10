"""
Integration tests for CPU metrics ingestion and retrieval endpoints.
"""
from datetime import datetime, timezone


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

    def test_get_metrics_unknown_vm(self, auth_client):
        response = auth_client.get("/api/v1/metrics/cpu/does-not-exist")
        assert response.status_code == 404

    def test_get_metrics_limit_bounds(self, auth_client):
        assert auth_client.get("/api/v1/metrics/cpu/test-vm-001?limit=0").status_code == 422
        assert auth_client.get("/api/v1/metrics/cpu/test-vm-001?limit=99999").status_code == 422

