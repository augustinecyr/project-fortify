# Sprint 10: v1.0 Hardening & Handover Readiness

**Duration:** 2 weeks  
**Goal:** Elevate Project Fortify to a production-ready v1.0 that can be confidently handed over to internal stakeholders. This sprint closes the four remaining gaps: persistent session management so login survives a browser refresh, security hardening across the API surface, structured observability so an ops team can monitor and debug the running stack, and UI/UX polish that removes friction for non-technical users. The sprint ends with a complete operations runbook and an architecture handover guide.

---

## Deferred from Sprint 9

`frontend/dashboard/pages/login.py` stores the JWT token exclusively in `st.session_state`, which is an in-memory Python dictionary scoped to a single browser tab and server connection. Any page refresh, tab duplicate, or Streamlit server restart silently destroys the token, and the user is bounced back to the login screen with no explanatory message. This is the most visible usability regression in the current build and is the first item addressed in Sprint 10.

---

## Sprint Deliverables

1. **Persistent session management** — JWT token survives browser refresh via a browser cookie. Login page reads the cookie on load and silently restores the session if the token is still valid; an expired token clears the cookie and redirects cleanly to login.
2. **Secure HTTP headers** — API responses include `X-Content-Type-Options`, `X-Frame-Options`, `Strict-Transport-Security`, and `X-XSS-Protection` headers via a FastAPI middleware.
3. **Audit logging** — Structured JSON log entry emitted on every auth event (login success, login failure, token rejection) and on every protected endpoint call, including the authenticated username.
4. **Structured API logging** — All `uvicorn` and application log output is structured JSON with `timestamp`, `level`, `logger`, `message`, and `request_id` fields so log aggregators can parse it without regex.
5. **Docker Compose log configuration** — `docker-compose.yml` sets `logging.driver` and `logging.options` for all services; `docs/commands.md` documents the key `docker compose logs` commands an operator needs.
6. **UI/UX fixes** — Broken flows resolved: post-refresh redirect, 401/429/500 error messages surfaced to the user rather than shown as raw exceptions, empty-state placeholders on all data pages, and consistent page titles and footers.
7. **Observability guide** — New `docs/observability.md` covering what to watch, where to look, and what each key log pattern means.
8. **Operations runbook** — New `docs/runbook.md` covering start/stop/upgrade/rollback procedures, environment variable reference, and common troubleshooting steps.
9. **Handover guide** — New `docs/handover.md` covering architecture summary, service ownership, credential rotation, and stakeholder contacts.
10. **Version bump to v1.0.0** — `api/app/main.py`, `frontend/dashboard/app.py`, and all page footers updated.

---

## Day 1–2: Persistent Session Management

### Problem

`st.session_state` is wiped on every page refresh because Streamlit reconnects via WebSocket and allocates a new session. The token stored in `st.session_state["token"]` is gone, and the user must log in again.

### Solution

Use the `extra-streamlit-components` library which exposes a `CookieManager` component. On login, the JWT is written to a browser cookie with an `HttpOnly`-equivalent TTL. On every page load, the app reads the cookie first; if a valid token exists the user skips the login screen.

1. Install the dependency:

   ```powershell
   pip install extra-streamlit-components
   ```

   Add to `frontend/dashboard/requirements.txt`:

   ```
   extra-streamlit-components
   ```

2. Create `frontend/dashboard/utils/session.py`:

   ```python
   import extra_streamlit_components as stx
   import streamlit as st

   COOKIE_NAME = "fortify_token"
   COOKIE_TTL_DAYS = 1

   def get_cookie_manager():
       return stx.CookieManager(key="fortify_cookie_mgr")

   def save_token(token: str):
       cm = get_cookie_manager()
       cm.set(COOKIE_NAME, token, max_age=COOKIE_TTL_DAYS * 86400)
       st.session_state["token"] = token

   def load_token() -> str | None:
       if "token" in st.session_state and st.session_state["token"]:
           return st.session_state["token"]
       cm = get_cookie_manager()
       token = cm.get(COOKIE_NAME)
       if token:
           st.session_state["token"] = token
       return token

   def clear_token():
       cm = get_cookie_manager()
       cm.delete(COOKIE_NAME)
       st.session_state.pop("token", None)
   ```

3. Update `frontend/dashboard/pages/login.py`:
   - On successful login, call `save_token(token)` instead of writing directly to `st.session_state`.
   - Add a logout button that calls `clear_token()` and reruns.

4. Update `frontend/dashboard/app.py` (and each protected page) to call `load_token()` at the top of the page before any auth check:

   ```python
   from utils.session import load_token, clear_token

   token = load_token()
   if not token:
       st.switch_page("pages/login.py")
   ```

5. Add cookie expiry handling: wrap every API call in a try/except for `401`; on 401, call `clear_token()` and redirect to login with an `st.warning("Session expired. Please log in again.")`.

**Checkpoint (Day 1–2):**
1. Log in. Copy the URL. Open a new tab and paste the URL — you should land on the dashboard, not the login page.
2. Refresh the browser — session should persist.
3. Wait for token TTL to expire (or manually delete the cookie) and refresh — you should be redirected to login with an expiry message.

---

## Day 3: Security Hardening

### Secure HTTP Headers

1. Add a middleware to `api/app/main.py`:

   ```python
   from starlette.middleware.base import BaseHTTPMiddleware
   from starlette.requests import Request

   class SecurityHeadersMiddleware(BaseHTTPMiddleware):
       async def dispatch(self, request: Request, call_next):
           response = await call_next(request)
           response.headers["X-Content-Type-Options"] = "nosniff"
           response.headers["X-Frame-Options"] = "DENY"
           response.headers["X-XSS-Protection"] = "1; mode=block"
           response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
           return response

   app.add_middleware(SecurityHeadersMiddleware)
   ```

2. Install and configure `slowapi` to also rate-limit `POST /api/v1/vms` and `POST /api/v1/security` in addition to the existing `/auth/token` limit.

### Audit Logging

1. Create `api/app/audit.py`:

   ```python
   import logging, json
   from datetime import datetime, timezone

   audit_logger = logging.getLogger("fortify.audit")

   def log_auth_event(event: str, username: str, success: bool, ip: str = ""):
       audit_logger.info(json.dumps({
           "timestamp": datetime.now(timezone.utc).isoformat(),
           "event": event,
           "username": username,
           "success": success,
           "ip": ip,
       }))
   ```

2. Call `log_auth_event` in:
   - `api/app/routers/auth.py` — on token issuance (success) and credential rejection (failure).
   - `api/app/auth/dependencies.py` — on token decode failure (invalid/expired).

3. Add a request-level log in a middleware that records `method`, `path`, `status_code`, `duration_ms`, and `username` (from the token if present) for every request.

**Checkpoint (Day 3):**

```powershell
# Confirm secure headers are present
$r = Invoke-WebRequest http://localhost:8000/health
$r.Headers | Select-String "X-Content-Type"

# Attempt login with wrong password and check audit log
docker compose logs api | Select-String "auth_failure"
```

---

## Day 4: Structured Logging & Docker Observability

### Structured JSON Logging

1. Add `python-json-logger` to `api/requirements.txt`.

2. Configure logging in `api/app/main.py` startup:

   ```python
   import logging
   from pythonjsonlogger import jsonlogger

   handler = logging.StreamHandler()
   handler.setFormatter(jsonlogger.JsonFormatter(
       "%(timestamp)s %(level)s %(name)s %(message)s"
   ))
   logging.root.setLevel(logging.INFO)
   logging.root.handlers = [handler]
   ```

3. Replace all `print()` statements in the API with `logging.getLogger(__name__).info(...)`.

### Docker Compose Logging Configuration

Update `docker-compose.yml` to add log rotation for all services:

```yaml
x-logging: &default-logging
  driver: "json-file"
  options:
    max-size: "10m"
    max-file: "3"

services:
  api:
    logging: *default-logging
  frontend:
    logging: *default-logging
  postgres:
    logging: *default-logging
  redis:
    logging: *default-logging
```

### Update `docs/commands.md`

Add an **Observability v1.0** section:

```powershell
# Stream all service logs
docker compose logs -f

# API logs only (structured JSON)
docker compose logs -f api

# Filter for errors
docker compose logs api | Select-String '"level":"ERROR"'

# Filter for auth failures
docker compose logs api | Select-String "auth_failure"

# Filter for a specific VM's requests
docker compose logs api | Select-String "vm-prod-01"

# Check container health
docker compose ps

# Resource usage
docker stats --no-stream
```

**Checkpoint (Day 4):**

```powershell
# Every API log line should be valid JSON
docker compose logs api | ForEach-Object { $_ | ConvertFrom-Json } | Select-Object -First 5
```

---

## Day 5: UI/UX Fixes

### Error Handling

1. Wrap all API calls in `frontend/dashboard/utils/api_client.py` in a unified error handler that maps HTTP status codes to user-friendly messages:
   - `401` → "Session expired. Please log in again." + redirect to login
   - `429` → "Too many requests. Please wait a moment and try again."
   - `500` → "The server encountered an error. Please contact support."
   - Network error → "Cannot reach the API. Check that the stack is running."

2. Surface errors using `st.error(message)` rather than letting raw exceptions bubble up to the Streamlit UI.

### Empty States

Add an empty-state message to every data page for the case where the API returns an empty list:

```python
if not vms:
    st.info("No virtual machines found. Add VMs via the API or seed script.")
```

Pages to update: `home.py`, `security_posture.py`, `optimization.py`, `ai_insights.py`.

### Navigation & Polish

1. Ensure every page has a consistent `st.set_page_config(page_title="Project Fortify — <Page Name>", page_icon="🔒")` call.
2. Verify all page footers read `v1.0.0`.
3. Add a sidebar logout button on all authenticated pages that calls `clear_token()` and redirects to login.
4. On the login page, display a clear error message for invalid credentials rather than silently reloading the form.

**Checkpoint (Day 5):**
- Log in. Navigate to each page. Confirm no raw Python tracebacks are visible.
- Simulate an API outage (`docker compose stop api`) and refresh the frontend — a user-friendly error message should appear.
- Log out via the sidebar button — should clear cookie and redirect to login.

---

## Day 6: Documentation & v1.0.0 Bump

### `docs/observability.md`

Create a new file covering:
- What services emit logs and where to find them
- Key log fields (`timestamp`, `level`, `event`, `username`, `status_code`)
- Critical log patterns to monitor (auth failures, 500s, rate limit hits)
- Docker health check interpretation
- Redis and PostgreSQL monitoring commands

### `docs/runbook.md`

Create a new file covering:
- Prerequisites (Docker Desktop, `.env` file populated)
- Start stack: `docker compose up --build -d`
- Stop stack: `docker compose down`
- Upgrade procedure (pull latest, rebuild image, restart)
- Rollback procedure (revert to previous image tag)
- Database backup: `docker exec fortify-postgres pg_dump ...`
- Full environment variable reference table
- Common issues and resolutions (port conflicts, migration failures, seed duplicates)

### `docs/handover.md`

Create a new file covering:
- Architecture diagram (ASCII) showing the four services and their communication paths
- Service ownership and responsibility matrix
- Credential rotation steps (SECRET_KEY, GROQ_API_KEY, DB password)
- Stakeholder contacts and escalation path
- Known limitations and deferred Phase 2 items (from `docs/scope-definition.md`)

### Version Bump

Update version string to `1.0.0` in:
- `api/app/main.py` — `version="1.0.0"`
- `frontend/dashboard/app.py` — footer constant
- All page footer strings in `pages/`

Update `docs/commands.md` — prepend a **v1.0.0** section.

---

## Definition of Done

- Logging in and then refreshing the browser preserves the authenticated session; the login page is not shown again until the cookie expires or the user explicitly logs out.
- Logout via the sidebar button clears the cookie and redirects to the login page.
- A 401 response from the API redirects the user to login with a "Session expired" message; no raw exception is shown.
- Every API response includes `X-Content-Type-Options: nosniff` and `X-Frame-Options: DENY` headers.
- Auth failure events are visible in `docker compose logs api` as structured JSON with `"event": "auth_failure"`.
- All API log lines are valid JSON parseable by `ConvertFrom-Json`.
- `docker-compose.yml` configures log rotation (`max-size: 10m`, `max-file: 3`) for all four services.
- No raw Python tracebacks are visible in the Streamlit frontend under any error condition (401, 429, 500, network timeout).
- All data pages display a user-friendly empty-state message when the API returns an empty list.
- `docs/observability.md`, `docs/runbook.md`, and `docs/handover.md` are committed.
- `api/app/main.py` version is `1.0.0`; all frontend page footers and `app.py` read `v1.0.0`.
- Sprint file committed to `sprint-10-v1` branch and draft PR opened targeting `develop`.
