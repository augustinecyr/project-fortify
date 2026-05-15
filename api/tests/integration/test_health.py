"""
Integration tests for health check and VM health scoring endpoints.
"""


class TestSystemHealth:
    def test_health_check(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    def test_system_status(self, client):
        response = client.get("/api/v1/status")
        assert response.status_code == 200
        data = response.json()
        assert data["database"] == "connected"


class TestVMHealthScore:
    def test_health_score_returns_200(self, client):
        response = client.get("/api/v1/health/test-vm-001")
        assert response.status_code == 200

    def test_health_score_range(self, client):
        response = client.get("/api/v1/health/test-vm-001")
        data = response.json()
        assert 0 <= data["health_score"] <= 100

    def test_health_score_has_components(self, client):
        response = client.get("/api/v1/health/test-vm-001")
        data = response.json()
        assert "components" in data
        assert "anomaly_score" in data["components"]
        assert "stability_score" in data["components"]
        assert "historical_score" in data["components"]

    def test_health_score_has_anomaly_details(self, client):
        response = client.get("/api/v1/health/test-vm-001")
        data = response.json()
        assert "anomaly_details" in data
        assert "anomaly_count" in data["anomaly_details"]
        assert "total_points" in data["anomaly_details"]

    def test_health_score_unknown_vm(self, client):
        response = client.get("/api/v1/health/does-not-exist")
        assert response.status_code == 404
