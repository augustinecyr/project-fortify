"""
Integration tests for security summary endpoint.
"""


class TestSecuritySummary:
    def test_returns_200(self, client):
        response = client.get("/api/v1/security/summary")
        assert response.status_code == 200

    def test_has_required_fields(self, client):
        response = client.get("/api/v1/security/summary")
        data = response.json()
        for field in ["avg_security_score", "total_open_vulnerabilities",
                      "total_critical_vulnerabilities", "firewall_disabled_count",
                      "patch_lag_distribution", "vms"]:
            assert field in data, f"Missing field: {field}"

    def test_patch_lag_has_all_buckets(self, client):
        response = client.get("/api/v1/security/summary")
        data = response.json()
        lag = data["patch_lag_distribution"]
        for bucket in ["0_7_days", "8_30_days", "31_90_days", "90_plus_days"]:
            assert bucket in lag, f"Missing patch lag bucket: {bucket}"

    def test_avg_security_score_in_range(self, client):
        response = client.get("/api/v1/security/summary")
        data = response.json()
        assert 0 <= data["avg_security_score"] <= 100

    def test_vms_list_length(self, client):
        response = client.get("/api/v1/security/summary")
        data = response.json()
        assert len(data["vms"]) >= 3

    def test_total_vulnerabilities_correct(self, client):
        # Seeded VMs contribute at least 8 (vm-001: 2, vm-002: 6, vm-003: 0)
        response = client.get("/api/v1/security/summary")
        data = response.json()
        assert data["total_open_vulnerabilities"] >= 8

    def test_firewall_disabled_count(self, client):
        # Only vm-002 has firewall_enabled=False
        response = client.get("/api/v1/security/summary")
        data = response.json()
        assert data["firewall_disabled_count"] == 1