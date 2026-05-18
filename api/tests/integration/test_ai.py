"""
Integration tests for AI insights endpoints.

Groq is mocked at the router boundary (app.routers.ai.query_llm)
so no real LLM calls are made during tests.
Redis cache_get/cache_set are already patched to no-ops in conftest.py.
"""
from unittest.mock import patch

MOCK_FLEET_INSIGHTS = {
    "fleet_summary": "Fleet is operating within normal parameters.",
    "anomalies": [
        {
            "vm_id": "test-vm-002",
            "vm_name": "db-server-test-02",
            "explanation": "High CPU and disk usage detected.",
            "severity": "warning",
        }
    ],
    "recommendations": [
        {
            "priority": "high",
            "title": "Address high disk usage",
            "description": "test-vm-002 disk at 91%.",
            "affected_vms": ["test-vm-002"],
        }
    ],
    "predictions": [
        {
            "vm_id": "test-vm-002",
            "vm_name": "db-server-test-02",
            "prediction": "Disk may reach capacity within 7 days.",
            "timeframe": "within 7 days",
        }
    ],
}

MOCK_VM_ANALYSIS = {
    "health_explanation": "VM is under high load.",
    "anomaly_explanation": "CPU spike detected in last 24 hours.",
    "risk_level": "medium",
    "recommended_actions": ["Scale up instance", "Review running processes"],
    "prediction": "Performance may degrade within 48 hours.",
}


class TestFleetInsights:
    def test_returns_200(self, auth_client):
        with patch("app.routers.ai.query_llm", return_value=MOCK_FLEET_INSIGHTS):
            response = auth_client.get("/api/v1/ai/insights")
        assert response.status_code == 200

    def test_has_required_fields(self, auth_client):
        with patch("app.routers.ai.query_llm", return_value=MOCK_FLEET_INSIGHTS):
            response = auth_client.get("/api/v1/ai/insights")
        data = response.json()
        for field in ["fleet_summary", "anomalies", "recommendations",
                      "predictions", "analysis_timestamp", "model_used", "vm_count"]:
            assert field in data, f"Missing field: {field}"

    def test_vm_count_correct(self, auth_client):
        with patch("app.routers.ai.query_llm", return_value=MOCK_FLEET_INSIGHTS):
            response = auth_client.get("/api/v1/ai/insights")
        data = response.json()
        assert data["vm_count"] >= 3

    def test_is_not_fallback(self, auth_client):
        with patch("app.routers.ai.query_llm", return_value=MOCK_FLEET_INSIGHTS):
            response = auth_client.get("/api/v1/ai/insights")
        data = response.json()
        assert data["is_fallback"] is False

    def test_returns_fallback_when_groq_unavailable(self, auth_client):
        with patch("app.routers.ai.query_llm", return_value=None), \
             patch("app.routers.ai.cache_get", return_value=None):
            response = auth_client.get("/api/v1/ai/insights")
        assert response.status_code == 200
        data = response.json()
        assert data["is_fallback"] is True


class TestVMAnalysis:
    def test_returns_200(self, auth_client):
        with patch("app.routers.ai.query_llm", return_value=MOCK_VM_ANALYSIS):
            response = auth_client.get("/api/v1/ai/vm-analysis/test-vm-001")
        assert response.status_code == 200

    def test_has_required_fields(self, auth_client):
        with patch("app.routers.ai.query_llm", return_value=MOCK_VM_ANALYSIS):
            response = auth_client.get("/api/v1/ai/vm-analysis/test-vm-001")
        data = response.json()
        for field in ["vm_id", "vm_name", "analysis_timestamp", "model_used", "is_fallback"]:
            assert field in data, f"Missing field: {field}"

    def test_vm_id_matches(self, auth_client):
        with patch("app.routers.ai.query_llm", return_value=MOCK_VM_ANALYSIS):
            response = auth_client.get("/api/v1/ai/vm-analysis/test-vm-001")
        data = response.json()
        assert data["vm_id"] == "test-vm-001"

    def test_unknown_vm_returns_404(self, auth_client):
        with patch("app.routers.ai.query_llm", return_value=MOCK_VM_ANALYSIS):
            response = auth_client.get("/api/v1/ai/vm-analysis/does-not-exist")
        assert response.status_code == 404

    def test_returns_fallback_when_groq_unavailable(self, auth_client):
        with patch("app.routers.ai.query_llm", return_value=None), \
             patch("app.routers.ai.cache_get", return_value=None):
            response = auth_client.get("/api/v1/ai/vm-analysis/test-vm-001")
        assert response.status_code == 200
        data = response.json()
        assert data["is_fallback"] is True


class TestClearAICache:
    def test_returns_200(self, auth_client):
        with patch("app.routers.ai.get_redis_client") as mock_redis:
            mock_redis.return_value.keys.return_value = []
            response = auth_client.delete("/api/v1/ai/cache")
        assert response.status_code == 200

    def test_returns_cleared_count(self, auth_client):
        with patch("app.routers.ai.get_redis_client") as mock_redis:
            mock_redis.return_value.keys.return_value = []
            response = auth_client.delete("/api/v1/ai/cache")
        data = response.json()
        assert "cleared" in data
