"""
Integration tests for optimization recommendations endpoint.
"""

VALID_SEVERITIES = {"info", "warning", "critical"}
VALID_TYPES = {"downsize", "scale_up", "disk_cleanup", "review_offline"}


class TestOptimizationRecommendations:
    def test_returns_200(self, client):
        response = client.get("/api/v1/optimization/recommendations")
        assert response.status_code == 200

    def test_has_required_top_level_fields(self, client):
        response = client.get("/api/v1/optimization/recommendations")
        data = response.json()
        assert "recommendations" in data
        assert "total_recommendations" in data
        assert "fleet_summary" in data

    def test_total_matches_list_length(self, client):
        response = client.get("/api/v1/optimization/recommendations")
        data = response.json()
        assert data["total_recommendations"] == len(data["recommendations"])

    def test_recommendation_fields(self, client):
        response = client.get("/api/v1/optimization/recommendations")
        data = response.json()
        for rec in data["recommendations"]:
            assert "vm_id" in rec
            assert "vm_name" in rec
            assert "recommendation_type" in rec
            assert "reason" in rec
            assert "severity" in rec

    def test_severity_values_valid(self, client):
        response = client.get("/api/v1/optimization/recommendations")
        data = response.json()
        for rec in data["recommendations"]:
            assert rec["severity"] in VALID_SEVERITIES

    def test_recommendation_type_values_valid(self, client):
        response = client.get("/api/v1/optimization/recommendations")
        data = response.json()
        for rec in data["recommendations"]:
            assert rec["recommendation_type"] in VALID_TYPES

    def test_fleet_summary_has_utilization(self, client):
        response = client.get("/api/v1/optimization/recommendations")
        data = response.json()
        summary = data["fleet_summary"]
        assert "avg_cpu" in summary
        assert "avg_memory" in summary
        assert "avg_disk" in summary

    def test_seeded_data_generates_recommendations(self, client):
        # vm-002: cpu=88 (scale_up), disk=91 (disk_cleanup)
        # vm-003: offline + uptime=0 (review_offline), cpu=5 (downsize)
        response = client.get("/api/v1/optimization/recommendations")
        data = response.json()
        assert data["total_recommendations"] >= 3
