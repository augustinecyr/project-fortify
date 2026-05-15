"""
Integration tests for VM endpoints.
"""


class TestGetAllVMs:
    def test_returns_200(self, client):
        response = client.get("/api/v1/vms")
        assert response.status_code == 200

    def test_total_matches_seeded_count(self, client):
        response = client.get("/api/v1/vms")
        data = response.json()
        assert data["total"] == 3

    def test_vms_list_present(self, client):
        response = client.get("/api/v1/vms")
        data = response.json()
        assert "vms" in data
        assert len(data["vms"]) == 3


class TestGetVMsSummary:
    def test_returns_200(self, client):
        response = client.get("/api/v1/vms/summary")
        assert response.status_code == 200

    def test_has_fleet_aggregates(self, client):
        response = client.get("/api/v1/vms/summary")
        data = response.json()
        assert "total_vms" in data
        assert "fleet_health_score" in data
        assert "fleet_security_score" in data

    def test_total_vms_correct(self, client):
        response = client.get("/api/v1/vms/summary")
        data = response.json()
        assert data["total_vms"] == 3

    def test_vms_list_in_summary(self, client):
        response = client.get("/api/v1/vms/summary")
        data = response.json()
        assert "vms" in data
        assert len(data["vms"]) == 3


class TestGetVMDetails:
    def test_returns_200(self, client):
        response = client.get("/api/v1/vms/test-vm-001")
        assert response.status_code == 200

    def test_has_expected_fields(self, client):
        response = client.get("/api/v1/vms/test-vm-001")
        data = response.json()
        for field in ["vm_id", "name", "status", "health_score", "security_score",
                      "current_cpu", "current_memory", "current_disk"]:
            assert field in data, f"Missing field: {field}"

    def test_unknown_vm_returns_error(self, client):
        # vms.py returns ({"error": "..."}, 404) — FastAPI serialises as a list
        response = client.get("/api/v1/vms/does-not-exist")
        data = response.json()
        assert isinstance(data, list)
        assert "error" in data[0]


class TestPatchVM:
    def test_partial_update_accepted(self, client):
        response = client.patch("/api/v1/vms/test-vm-001", json={"current_cpu": 75.0})
        assert response.status_code == 200

    def test_patch_unknown_vm_returns_404(self, client):
        response = client.patch("/api/v1/vms/does-not-exist", json={"current_cpu": 50.0})
        assert response.status_code == 404