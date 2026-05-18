# Sprint 8: OAuth2/JWT Authentication

**Duration:** 2 weeks
**Goal:** Implement OAuth2/JWT bearer authentication across all FastAPI endpoints, protecting the API and satisfying the Cybersecurity module requirement for capstone submission.

---

## Deferred from Sprint 7

`api/app/main.py` still reads `version="0.5.0"`. The Sprint 7 version bump commit targeted frontend footers but did not update `main.py`. This is corrected in Sprint 8 as part of the v0.7.0 bump on Day 5.

---

## Sprint Deliverables

1. **JWT Token Endpoint** — `POST /auth/token` accepts credentials and returns a signed JWT. Token expires after a configurable TTL.
2. **Protected API Routes** — All `/api/v1/` endpoints require a valid Bearer token. `GET /health` and `GET /api/v1/status` remain public.
3. **User Model and Seed** — `User` table with hashed passwords. Seed creates one `admin` user for development and testing.
4. **Authenticated Frontend Client** — Login page added to Streamlit; session token stored in `st.session_state`; API client passes `Authorization: Bearer <token>` on every request.
5. **Auth Integration Tests** — Tests covering token issuance, rejection of invalid credentials, and access control on protected endpoints.
6. **Version Bump** — API and all frontend pages bumped to `v0.7.0`; `main.py` corrected from `v0.5.0`.
7. **Documentation** — `commands.md` updated with auth endpoint commands and token testing steps.

---

## Day 1–2: JWT Infrastructure

1. Install dependencies in `api/`:
   ```
   pip install "python-jose[cryptography]" "passlib[bcrypt]"
   ```
2. Create `api/app/auth/` directory with `__init__.py`, `security.py`, `dependencies.py`.
3. In `api/app/auth/security.py`:
   - Read `SECRET_KEY`, `ALGORITHM = "HS256"`, `ACCESS_TOKEN_EXPIRE_MINUTES` from `settings`.
   - `create_access_token(data: dict) -> str`: signs a JWT payload using `python-jose`.
   - `verify_password(plain, hashed) -> bool`: uses `passlib.context.CryptContext` with bcrypt scheme.
   - `get_password_hash(password: str) -> str`: hashes plaintext for storage.
4. Add `SECRET_KEY` and `ACCESS_TOKEN_EXPIRE_MINUTES` to `api/app/config.py` and `.env.example`.
5. Create `api/app/models/user.py` — `User` SQLAlchemy model: `id`, `username`, `hashed_password`, `is_active`, `created_at`.
6. Generate Alembic migration:
   ```
   alembic revision --autogenerate -m "add users table"
   alembic upgrade head
   ```
7. Create `data/seeds/seed_users.py`: inserts one `admin` user with a bcrypt-hashed password (`admin123`).

**Checkpoint:** The following prints a JWT string without error:
```
python -c "from app.auth.security import create_access_token; print(create_access_token({'sub': 'admin'}))"
```

---

## Day 3: Token Endpoint and Route Protection

1. Create `api/app/routers/auth.py`:
   - `POST /auth/token` — accepts `OAuth2PasswordRequestForm`, queries the `User` table, verifies the password, and returns `{"access_token": <jwt>, "token_type": "bearer"}`.
   - Returns `HTTPException(401)` for invalid credentials.
2. In `api/app/auth/dependencies.py`:
   - `get_current_user` FastAPI dependency: extracts Bearer token from `Authorization` header, decodes it with `python-jose`, returns the `User` object or raises `HTTPException(401)`.
3. Add `Depends(get_current_user)` to all route functions in: `metrics.py`, `vms.py`, `security.py`, `optimization.py`, `ai.py`, and the VM-level route in `health.py`.
   - Keep `GET /health` and `GET /api/v1/status` public — no dependency.
4. Register `auth.router` in `api/app/main.py` with prefix `/auth` and tag `"auth"`.

**Checkpoint:** Three-command verification:
```
# Step 1 — unauthenticated request should return 401
Invoke-RestMethod http://localhost:8000/api/v1/vms

# Step 2 — obtain token
$r = Invoke-RestMethod -Method POST http://localhost:8000/auth/token -Body "username=admin&password=admin123" -ContentType "application/x-www-form-urlencoded"

# Step 3 — authenticated request should return data
Invoke-RestMethod http://localhost:8000/api/v1/vms -Headers @{Authorization="Bearer $($r.access_token)"}
```

---

## Day 4: Frontend Authentication

1. Create `frontend/dashboard/pages/login.py`:
   - `st.set_page_config(page_title="Fortify — Login")`.
   - Username and password `st.text_input` fields and a "Sign in" button.
   - On submit: `POST /auth/token` with form credentials via `api_client`.
   - On success: store token in `st.session_state["token"]` and call `st.rerun()`.
   - On failure: display styled error card (reuse `.error-card` CSS class from `custom.css`).
2. Update `frontend/dashboard/utils/api_client.py`:
   - All request methods accept `token: str | None = None`.
   - When `token` is provided, add `Authorization: Bearer {token}` to request headers.
3. On all six existing pages (`home.py`, `vm_health_monitor.py`, `security_posture.py`, `optimization.py`, `export_report.py`, `ai_insights.py`):
   - At the top of the page body, read `token = st.session_state.get("token")`.
   - If `token` is `None`, display an "Authentication required — please log in." message and call `st.stop()`.
   - Pass `token` to all `api_client` calls.

**Checkpoint:** Visiting the dashboard without a session shows the authentication prompt and stops rendering. Submitting valid credentials on the login page loads the home page with live data.

---

## Day 5: Integration Tests, Version Bump, and Documentation

1. Create `api/tests/integration/test_auth.py`:
   - `POST /auth/token` with valid credentials returns `200` and a non-empty `access_token`.
   - `POST /auth/token` with an invalid password returns `401`.
   - `GET /api/v1/vms` without a token returns `401`.
   - `GET /api/v1/vms` with a valid Bearer token returns `200`.
2. Bump version to `v0.7.0`:
   - `api/app/main.py` — set `version="0.7.0"` in both the `FastAPI(...)` constructor and the root endpoint response.
   - All six frontend page footers — update caption from `v0.6.0` to `v0.7.0`.
3. Update `commands.md` with auth commands (see Commands Reference below).
4. Run full integration test suite:
   ```
   cd api
   pytest tests/integration/ -v
   ```
5. Commit all changes with conventional commit messages. Open PR from `sprint-8-plan` to `develop`.

**Checkpoint:** `pytest api/tests/integration/ -v` passes with zero failures, including `test_auth.py`.

---

## New Files

```
api/app/auth/__init__.py
api/app/auth/security.py
api/app/auth/dependencies.py
api/app/models/user.py
api/app/routers/auth.py
api/app/alembic/versions/<hash>_add_users_table.py
data/seeds/seed_users.py
frontend/dashboard/pages/login.py
api/tests/integration/test_auth.py
```

---

## Modified Files

```
api/app/main.py                                    — add auth router, bump to v0.7.0
api/app/config.py                                  — add SECRET_KEY, ACCESS_TOKEN_EXPIRE_MINUTES
api/app/routers/health.py                          — protect vm-level health route with Depends(get_current_user)
api/app/routers/metrics.py                         — add Depends(get_current_user) to all routes
api/app/routers/vms.py                             — add Depends(get_current_user) to all routes
api/app/routers/security.py                        — add Depends(get_current_user) to all routes
api/app/routers/optimization.py                    — add Depends(get_current_user) to all routes
api/app/routers/ai.py                              — add Depends(get_current_user) to all routes
frontend/dashboard/utils/api_client.py             — add token header support to all request methods
frontend/dashboard/pages/home.py                   — session token check, v0.7.0 footer
frontend/dashboard/pages/vm_health_monitor.py      — session token check, v0.7.0 footer
frontend/dashboard/pages/security_posture.py       — session token check, v0.7.0 footer
frontend/dashboard/pages/optimization.py           — session token check, v0.7.0 footer
frontend/dashboard/pages/export_report.py          — session token check, v0.7.0 footer
frontend/dashboard/pages/ai_insights.py            — session token check, v0.7.0 footer
.env.example                                       — add SECRET_KEY and ACCESS_TOKEN_EXPIRE_MINUTES
docs/commands.md                                   — auth endpoint commands and token testing
```

---

## Success Criteria

1. `POST /auth/token` with valid credentials returns a signed JWT in under 200ms.
2. All `/api/v1/` endpoints (except `GET /health` and `GET /api/v1/status`) return `401` without a token.
3. All `/api/v1/` endpoints return data when called with a valid Bearer token.
4. Streamlit login page accepts credentials and stores the token in `st.session_state`.
5. All six dashboard pages display an authentication prompt and stop when no token is present.
6. `pytest api/tests/integration/ -v` passes with zero failures, including `test_auth.py`.
7. `main.py` version string reads `0.7.0` and all frontend page footers read `v0.7.0`.
8. `commands.md` updated with auth commands.

---

## Commands Reference

```powershell
# Obtain an access token
$r = Invoke-RestMethod -Method POST http://localhost:8000/auth/token `
     -Body "username=admin&password=admin123" `
     -ContentType "application/x-www-form-urlencoded"
$token = $r.access_token

# Call a protected endpoint
Invoke-RestMethod http://localhost:8000/api/v1/vms `
    -Headers @{Authorization="Bearer $token"}

# Verify unauthenticated request is rejected
try {
    Invoke-RestMethod http://localhost:8000/api/v1/vms
} catch {
    $_.Exception.Response.StatusCode  # Should be 401
}

# Run auth integration tests only
cd api
.\venv\Scripts\Activate.ps1
pytest tests/integration/test_auth.py -v

# Run full integration suite
pytest tests/integration/ -v
```

---

## Definition of Done

- `User` model and Alembic migration created and applied to the development database.
- `data/seeds/seed_users.py` creates the `admin` user and runs without error.
- `POST /auth/token` endpoint returns a signed JWT for valid credentials.
- `GET /api/v1/vms` (and all other protected routes) returns `401` without a token.
- Streamlit login page functional: successful login stores the token, failed login shows the error card.
- All six frontend pages check for a session token and stop rendering if none is present.
- `pytest api/tests/integration/ -v` passes with zero failures, including `test_auth.py`.
- `main.py` version set to `0.7.0`; all six frontend page footers updated to `v0.7.0`.
- `commands.md` updated with auth endpoint commands.
- Sprint file committed to `sprint-8-plan` branch and draft PR opened targeting `develop`.
