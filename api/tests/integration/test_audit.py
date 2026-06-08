"""
Integration tests for the persisted audit trail and the /api/v1/audit endpoint.
"""

# Credentials match the role users seeded in conftest.py
_ADMIN = ("suite_admin", "suitepass123")
_OPERATOR = ("suite_operator", "operatorpass123")
_VIEWER = ("suite_viewer", "viewerpass123")


def _token(client, creds):
    r = client.post(
        "/auth/token",
        data={"username": creds[0], "password": creds[1]},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    return r.json()["access_token"]


def _auth(tok):
    return {"Authorization": f"Bearer {tok}"}


class TestAuditAccess:
    def test_viewer_cannot_read_audit(self, client):
        tok = _token(client, _VIEWER)
        assert client.get("/api/v1/audit", headers=_auth(tok)).status_code == 403

    def test_operator_can_read_audit(self, client):
        tok = _token(client, _OPERATOR)
        r = client.get("/api/v1/audit", headers=_auth(tok))
        assert r.status_code == 200
        body = r.json()
        assert {"total", "limit", "offset", "entries"} <= body.keys()


class TestAuditCapture:
    def test_login_is_persisted(self, client):
        # Logging in emits an auth_success event that must be queryable.
        _token(client, _OPERATOR)
        tok = _token(client, _ADMIN)
        r = client.get(
            "/api/v1/audit",
            headers=_auth(tok),
            params={"event": "auth_success", "actor": "suite_operator"},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["total"] >= 1
        assert all(e["event"] == "auth_success" for e in body["entries"])
        assert all(e["actor"] == "suite_operator" for e in body["entries"])

    def test_authz_denial_is_persisted(self, client):
        # A viewer hitting an operator-only route is denied AND recorded.
        viewer = _token(client, _VIEWER)
        denied = client.delete("/api/v1/ai/cache", headers=_auth(viewer))
        assert denied.status_code == 403

        admin = _token(client, _ADMIN)
        r = client.get(
            "/api/v1/audit",
            headers=_auth(admin),
            params={"event": "authz_denied", "actor": "suite_viewer"},
        )
        assert r.json()["total"] >= 1

    def test_pagination_caps_limit(self, client):
        tok = _token(client, _ADMIN)
        # limit above the 200 cap is rejected by validation
        assert client.get("/api/v1/audit", headers=_auth(tok),
                          params={"limit": 500}).status_code == 422
        # a valid limit is echoed back
        r = client.get("/api/v1/audit", headers=_auth(tok), params={"limit": 5})
        assert r.json()["limit"] == 5
        assert len(r.json()["entries"]) <= 5
