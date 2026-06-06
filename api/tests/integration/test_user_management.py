"""
Integration tests for the user-management lifecycle endpoints:
list, update (role / is_active), admin password reset, and self password change.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.user import User

_ADMIN = ("suite_admin", "suitepass123")
_OPERATOR = ("suite_operator", "operatorpass123")
_VIEWER = ("suite_viewer", "viewerpass123")

TEST_DB_URL = "postgresql+psycopg://fortify_user:fortify_pass@localhost:5432/fortify_test"
_engine = create_engine(TEST_DB_URL, pool_pre_ping=True)
_Session = sessionmaker(bind=_engine)


def _token(client, creds):
    r = client.post(
        "/auth/token",
        data={"username": creds[0], "password": creds[1]},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    return r.json()["access_token"]


def _auth(tok):
    return {"Authorization": f"Bearer {tok}"}


def _create_user(client, admin_tok, username, password, role):
    r = client.post(
        "/auth/users",
        headers=_auth(admin_tok),
        json={"username": username, "password": password, "role": role},
    )
    assert r.status_code in (201, 409)
    if r.status_code == 201:
        return r.json()["id"]
    # already exists from a prior run — look it up
    db = _Session()
    try:
        return db.query(User).filter(User.username == username).first().id
    finally:
        db.close()


class TestUserListing:
    def test_list_requires_admin(self, client):
        assert client.get("/auth/users", headers=_auth(_token(client, _VIEWER))).status_code == 403
        assert client.get("/auth/users", headers=_auth(_token(client, _OPERATOR))).status_code == 403
        r = client.get("/auth/users", headers=_auth(_token(client, _ADMIN)))
        assert r.status_code == 200
        assert any(u["username"] == "suite_admin" for u in r.json())


class TestRoleAndStatus:
    def test_promote_role(self, client):
        admin = _token(client, _ADMIN)
        uid = _create_user(client, admin, "promo_user", "password123", "viewer")
        r = client.patch(f"/auth/users/{uid}", headers=_auth(admin), json={"role": "operator"})
        assert r.status_code == 200
        assert r.json()["role"] == "operator"

    def test_invalid_role_rejected(self, client):
        admin = _token(client, _ADMIN)
        uid = _create_user(client, admin, "badrole_user", "password123", "viewer")
        r = client.patch(f"/auth/users/{uid}", headers=_auth(admin), json={"role": "superuser"})
        assert r.status_code == 400

    def test_deactivate_blocks_login(self, client):
        admin = _token(client, _ADMIN)
        uid = _create_user(client, admin, "deact_user", "password123", "viewer")
        # works before deactivation
        assert client.post("/auth/token", data={"username": "deact_user", "password": "password123"},
                           headers={"Content-Type": "application/x-www-form-urlencoded"}).status_code == 200
        # deactivate
        assert client.patch(f"/auth/users/{uid}", headers=_auth(admin),
                            json={"is_active": False}).status_code == 200
        # login now refused
        assert client.post("/auth/token", data={"username": "deact_user", "password": "password123"},
                           headers={"Content-Type": "application/x-www-form-urlencoded"}).status_code == 401


class TestPasswords:
    def test_admin_reset_password(self, client):
        admin = _token(client, _ADMIN)
        uid = _create_user(client, admin, "pwreset_user", "oldpassword1", "viewer")
        r = client.post(f"/auth/users/{uid}/password", headers=_auth(admin),
                        json={"new_password": "newpassword2"})
        assert r.status_code == 204
        # old fails, new works
        assert client.post("/auth/token", data={"username": "pwreset_user", "password": "oldpassword1"},
                           headers={"Content-Type": "application/x-www-form-urlencoded"}).status_code == 401
        assert client.post("/auth/token", data={"username": "pwreset_user", "password": "newpassword2"},
                           headers={"Content-Type": "application/x-www-form-urlencoded"}).status_code == 200

    def test_self_password_change(self, client):
        admin = _token(client, _ADMIN)
        _create_user(client, admin, "selfpw_user", "firstpass1", "viewer")
        tok = _token(client, ("selfpw_user", "firstpass1"))
        # wrong current password rejected
        assert client.post("/auth/me/password", headers=_auth(tok),
                           json={"current_password": "WRONG", "new_password": "secondpass2"}).status_code == 400
        # correct change
        assert client.post("/auth/me/password", headers=_auth(tok),
                           json={"current_password": "firstpass1", "new_password": "secondpass2"}).status_code == 204
        # new password works, old does not
        assert client.post("/auth/token", data={"username": "selfpw_user", "password": "secondpass2"},
                           headers={"Content-Type": "application/x-www-form-urlencoded"}).status_code == 200
        assert client.post("/auth/token", data={"username": "selfpw_user", "password": "firstpass1"},
                           headers={"Content-Type": "application/x-www-form-urlencoded"}).status_code == 401


class TestLastAdminProtection:
    def test_cannot_demote_last_admin(self, client):
        """With all other admins inactive, demoting the sole admin is blocked."""
        admin = _token(client, _ADMIN)
        uid = _create_user(client, admin, "sole_admin", "password123", "admin")

        db = _Session()
        # Snapshot and deactivate every other admin so sole_admin is the only one.
        others = db.query(User).filter(User.role == "admin", User.username != "sole_admin",
                                       User.is_active.is_(True)).all()
        snapshot = [u.id for u in others]
        for u in others:
            u.is_active = False
        db.commit()
        try:
            sole = _token(client, ("sole_admin", "password123"))
            # demote the only active admin -> blocked
            assert client.patch(f"/auth/users/{uid}", headers=_auth(sole),
                                json={"role": "viewer"}).status_code == 409
            # deactivating the only active admin -> also blocked
            assert client.patch(f"/auth/users/{uid}", headers=_auth(sole),
                                json={"is_active": False}).status_code == 409
        finally:
            for admin_id in snapshot:
                db.query(User).filter(User.id == admin_id).update({"is_active": True})
            db.commit()
            db.close()
