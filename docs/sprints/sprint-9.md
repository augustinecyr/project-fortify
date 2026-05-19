# Sprint 9: Docker Containerization

**Duration:** 1 week
**Goal:** `docker compose up` brings up the complete Project Fortify stack (API + Streamlit frontend + PostgreSQL + Redis) with zero manual steps beyond copying `.env`. The result is a single-command demo-ready artefact suitable for capstone submission.

---

## Deferred from Sprint 8

`infrastructure/docker-compose.yml` covers only the API, PostgreSQL, and Redis services. The Streamlit frontend has no Dockerfile and is not part of the compose stack. The API service passes `DATABASE_URL` without the `+psycopg` driver qualifier (`postgresql://` instead of `postgresql+psycopg://`), which will cause SQLAlchemy to fall back to the deprecated `psycopg2` adapter at container start. The `SECRET_KEY`, `GROQ_API_KEY`, and `ACCESS_TOKEN_EXPIRE_MINUTES` variables are absent from the compose environment block. Both issues are corrected in Sprint 9 as part of Day 3.

---

## Sprint Deliverables

1. **API Dockerfile (hardened)** — `api/Dockerfile` rebuilt on `python:3.12-slim`, non-root user, no `venv` volume mount in production mode.
2. **Frontend Dockerfile** — `frontend/Dockerfile` using `python:3.12-slim`, installs `frontend/dashboard/requirements.txt`, runs `streamlit run app.py`.
3. **Root `docker-compose.yml`** — replaces `infrastructure/docker-compose.yml` as the canonical compose file; defines `api`, `frontend`, `postgres`, and `redis` services with proper health-check ordering, named internal network, and named volumes.
4. **Environment variable passthrough** — all secrets (`SECRET_KEY`, `GROQ_API_KEY`, `POSTGRES_PASSWORD`, `REDIS_URL`, `DATABASE_URL`) flow from a single `.env` file at the project root into every container that needs them; frontend reads `API_BASE_URL` to resolve the API container by service name instead of `localhost`.
5. **Security hardening** — rate limiting on `POST /auth/token`, CORS origin locked to the frontend container's address, `.env.example` audited and committed, `.env` confirmed in `.gitignore`.
6. **Automated migration + seed on start** — the API container entrypoint runs `alembic upgrade head` and `python data/seeds/seed_users.py` before starting uvicorn, so a fresh volume always gets a usable schema and admin user without manual steps.
7. **Integration smoke test** — one `docker compose up --build -d` and a five-command PowerShell verification script that proves the full stack is reachable.
8. **Version bump to v0.8.0** — `api/app/main.py`, `frontend/dashboard/app.py`, and all page footers updated.
9. **README and `commands.md` updated** — Docker-first Quick Start replaces the four-terminal manual flow.

---

## Day 1–2: Dockerfiles (API and Frontend)

### API Dockerfile (`api/Dockerfile`)

The existing `api/Dockerfile` uses `python:3.10-slim` and copies the full working directory into `/app`, which means it also picks up the local `venv/` folder if the `.dockerignore` is missing. The following steps harden it.

1. Create `api/.dockerignore` with the following exclusions:

   ```
   venv/
   __pycache__/
   *.pyc
   .pytest_cache/
   htmlcov/
   .coverage
   .env
   alembic/versions/*.pyc
   ```

2. Rewrite `api/Dockerfile`:

   - Base image: `python:3.12-slim`
   - Install only the two system packages required by `psycopg` binary: `libpq-dev` and `gcc` — then delete the apt cache in the same `RUN` layer.
   - `COPY requirements.txt .` then `pip install --no-cache-dir -r requirements.txt` as a separate layer (cache-friendly).
   - `COPY . .` for application code.
   - Create a non-root user `appuser` (`addgroup` + `adduser`) and `USER appuser` before the `CMD`.
   - `EXPOSE 8000`
   - `CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]` — the entrypoint script overrides this in compose.

3. Create `api/entrypoint.sh`:

   ```bash
   #!/bin/sh
   set -e
   echo "[entrypoint] Running Alembic migrations..."
   alembic upgrade head
   echo "[entrypoint] Seeding admin user..."
   python /app/data/seeds/seed_users.py || true
   echo "[entrypoint] Starting API..."
   exec uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```

   The `|| true` on the seed step prevents a crash when the admin user already exists (duplicate key). The `exec` hands PID 1 to uvicorn so Docker stop signals propagate correctly.

   Because Docker build context cannot reference paths outside the `context:` directory, the compose file sets `context: .` (project root) rather than `context: ./api`. The `data/seeds/` folder is then available inside the build context. The `api/Dockerfile` copies it explicitly:

   ```dockerfile
   COPY --chown=appuser:appuser data/seeds/ /app/data/seeds/
   ```

4. Verify the API image builds standalone:

   ```powershell
   # Run from project root so the build context includes data/seeds/
   docker build -f api/Dockerfile -t fortify-api:test .
   ```

**Checkpoint (Day 1–2 API):** The following exits 0 and prints `Project Fortify API`:

```powershell
docker run --rm -e DATABASE_URL=sqlite:///./test.db -e SECRET_KEY=test -e GROQ_API_KEY="" `
    fortify-api:test python -c "from app.main import app; print(app.title)"
```

### Frontend Dockerfile (`frontend/Dockerfile`)

The frontend has no Dockerfile yet. `frontend/dashboard/utils/api_client.py` has a hardcoded default of `http://localhost:8000`. Inside a Docker network this resolves to the container itself, not the API service. The fix is to read `API_BASE_URL` from the environment.

1. Create `frontend/.dockerignore`:

   ```
   dashboard/venv/
   __pycache__/
   *.pyc
   .env
   ```

2. Create `frontend/Dockerfile`:

   ```dockerfile
   FROM python:3.12-slim

   WORKDIR /app

   COPY dashboard/requirements.txt .
   RUN pip install --no-cache-dir --upgrade pip && \
       pip install --no-cache-dir -r requirements.txt

   COPY dashboard/ .

   RUN addgroup --system appgroup && adduser --system --ingroup appgroup appuser
   USER appuser

   EXPOSE 8501

   HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
     CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8501/_stcore/health')" || exit 1

   CMD ["streamlit", "run", "app.py", \
        "--server.port=8501", \
        "--server.address=0.0.0.0", \
        "--server.headless=true", \
        "--browser.gatherUsageStats=false"]
   ```

3. Modify `frontend/dashboard/utils/api_client.py` — change the `__init__` default:

   ```python
   import os

   class FortifyAPIClient:
       def __init__(self, base_url: str = os.getenv("API_BASE_URL", "http://localhost:8000")):
           self.base_url = base_url
   ```

   Fully backward-compatible: running locally without the env var set continues to use `localhost:8000`. Inside Docker, compose sets `API_BASE_URL=http://api:8000` and the container resolves it over the internal network.

4. Verify the frontend image builds standalone:

   ```powershell
   docker build -f frontend/Dockerfile -t fortify-frontend:test frontend/
   ```

**Checkpoint (Day 1–2 Frontend):** The following exits 0:

```powershell
docker run --rm fortify-frontend:test python -c "import streamlit; print(streamlit.__version__)"
```

---

## Day 3: `docker-compose.yml`, Networking, and Environment Variable Passthrough

The canonical compose file is promoted from `infrastructure/docker-compose.yml` to the project root. This aligns with the Docker convention of `docker compose up` from the project root and allows the `context: .` build path to include both `api/` and `data/seeds/` in a single build context.

1. Create `docker-compose.yml` at the project root with the following service definitions:

   **`postgres`** — `postgres:15-alpine`, named volume `postgres_data`, healthcheck `pg_isready -U fortify_user -d fortify`, network `fortify-network`.

   **`redis`** — `redis:7-alpine`, named volume `redis_data`, healthcheck `redis-cli ping`.

   **`api`**:
   - `build.context: .` (project root), `build.dockerfile: api/Dockerfile`
   - `entrypoint: ["/bin/sh", "/app/api/entrypoint.sh"]`
   - Environment block (all sourced from `.env`):
     ```yaml
     DATABASE_URL: postgresql+psycopg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}
     REDIS_URL: redis://redis:6379/0
     SECRET_KEY: ${SECRET_KEY}
     GROQ_API_KEY: ${GROQ_API_KEY}
     ACCESS_TOKEN_EXPIRE_MINUTES: ${ACCESS_TOKEN_EXPIRE_MINUTES:-30}
     API_KEY: ${API_KEY:-dev-api-key-12345}
     LOG_LEVEL: ${LOG_LEVEL:-INFO}
     CORS_ALLOWED_ORIGINS: http://localhost:8501,http://frontend:8501
     ```
   - `depends_on: postgres: condition: service_healthy`, `redis: condition: service_healthy`
   - `ports: ["8000:8000"]`
   - `networks: [fortify-network]`
   - Healthcheck:
     ```yaml
     healthcheck:
       test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"]
       interval: 15s
       timeout: 5s
       retries: 5
       start_period: 20s
     ```

   **`frontend`**:
   - `build.context: frontend`, `build.dockerfile: Dockerfile`
   - Environment block:
     ```yaml
     API_BASE_URL: http://api:8000
     ```
   - `depends_on: api: condition: service_healthy`
   - `ports: ["8501:8501"]`
   - `networks: [fortify-network]`

2. Create `.env.example` at the project root:

   ```bash
   # Database
   POSTGRES_DB=fortify
   POSTGRES_USER=fortify_user
   POSTGRES_PASSWORD=change-me-in-production

   # Redis
   REDIS_URL=redis://redis:6379/0

   # API
   API_KEY=dev-api-key-12345
   LOG_LEVEL=INFO

   # JWT Auth — MUST be changed before any deployment
   SECRET_KEY=change-me-in-production
   ACCESS_TOKEN_EXPIRE_MINUTES=30

   # CORS — comma-separated list of allowed browser origins
   CORS_ALLOWED_ORIGINS=http://localhost:8501,http://frontend:8501

   # AI / LLM — get from https://console.groq.com/keys
   GROQ_API_KEY=gsk_your_key_here

   # Analytics
   ANOMALY_THRESHOLD=0.7
   SCORE_UPDATE_INTERVAL=300
   ```

3. Add a deprecation notice to `infrastructure/docker-compose.yml`:

   ```yaml
   # DEPRECATED as of v0.8.0 — use docker-compose.yml at the project root instead.
   # This file is kept for reference only.
   ```

**Checkpoint (Day 3):** The following brings up all four containers with no errors:

```powershell
# From project root — copy your real .env first
docker compose up --build -d
docker compose ps
# All four services should show status "running" or "healthy"
```

---

## Day 4: Security Hardening

### Rate Limiting on `POST /auth/token`

1. Add `slowapi>=0.1.9` to `api/requirements.txt`.

2. Create `api/app/limiter.py` to avoid circular imports:

   ```python
   from slowapi import Limiter
   from slowapi.util import get_remote_address

   limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"])
   ```

3. In `api/app/main.py` — import and wire the limiter:

   ```python
   from slowapi import _rate_limit_exceeded_handler
   from slowapi.errors import RateLimitExceeded
   from app.limiter import limiter

   app.state.limiter = limiter
   app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
   ```

4. In `api/app/routers/auth.py` — decorate the token endpoint:

   ```python
   from fastapi import Request
   from app.limiter import limiter

   @router.post("/token")
   @limiter.limit("10/minute")
   async def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
       ...
   ```

   Note: `slowapi` requires `request: Request` as the first positional argument. It is not used in the function body but must be present for `slowapi` to extract the client IP.

### CORS Lockdown

5. In `api/app/main.py`, replace the wildcard CORS config:

   ```python
   import os

   ALLOWED_ORIGINS = os.getenv(
       "CORS_ALLOWED_ORIGINS",
       "http://localhost:8501,http://frontend:8501"
   ).split(",")

   app.add_middleware(
       CORSMiddleware,
       allow_origins=ALLOWED_ORIGINS,
       allow_credentials=True,
       allow_methods=["GET", "POST", "DELETE"],
       allow_headers=["Authorization", "Content-Type"],
   )
   ```

### `.env` Secrets Audit

6. Verify `.env` is not tracked by git:

   ```powershell
   git status
   # .env must not appear under "Changes to be committed"
   git ls-files --error-unmatch .env
   # Expected: fatal — confirms it is not tracked
   ```

**Checkpoint (Day 4):** Exceeding the auth rate limit returns HTTP 429:

```powershell
1..11 | ForEach-Object {
    try {
        Invoke-RestMethod -Method POST http://localhost:8000/auth/token `
            -ContentType "application/x-www-form-urlencoded" `
            -Body "username=wrong&password=wrong"
    } catch {
        Write-Host "Attempt $_`: $($_.Exception.Response.StatusCode)"
    }
}
# Attempt 11 should print: 429
```

---

## Day 5: Integration Smoke Test, README Update, Version Bump, Commit and PR

### Smoke Test Script

1. Create `scripts/smoke_test.ps1`:

   ```powershell
   # Project Fortify — Docker stack smoke test
   # Run from project root after: docker compose up --build -d

   $ErrorActionPreference = "Stop"
   $api = "http://localhost:8000"
   $dash = "http://localhost:8501"
   $pass = 0; $fail = 0

   function Test-Step($label, $block) {
       try { & $block; Write-Host "[PASS] $label" -ForegroundColor Green; $script:pass++ }
       catch { Write-Host "[FAIL] $label — $_" -ForegroundColor Red; $script:fail++ }
   }

   Test-Step "API health endpoint returns 200" {
       $r = Invoke-RestMethod "$api/health"
       if ($r.status -ne "healthy") { throw "status not healthy" }
   }

   Test-Step "Unauthenticated /api/v1/vms returns 401" {
       try { Invoke-RestMethod "$api/api/v1/vms" }
       catch { if ($_.Exception.Response.StatusCode.value__ -ne 401) { throw "expected 401" } }
   }

   Test-Step "POST /auth/token returns a JWT" {
       $script:token = (Invoke-RestMethod -Method POST "$api/auth/token" `
           -ContentType "application/x-www-form-urlencoded" `
           -Body "username=admin&password=admin123").access_token
       if (-not $script:token) { throw "empty token" }
   }

   Test-Step "Authenticated /api/v1/vms/summary returns data" {
       $r = Invoke-RestMethod "$api/api/v1/vms/summary" `
           -Headers @{ Authorization = "Bearer $($script:token)" }
       if (-not $r) { throw "empty response" }
   }

   Test-Step "Streamlit frontend responds on port 8501" {
       $r = Invoke-WebRequest "$dash/_stcore/health" -UseBasicParsing
       if ($r.StatusCode -ne 200) { throw "status $($r.StatusCode)" }
   }

   Write-Host ""
   Write-Host "Results: $pass passed, $fail failed" -ForegroundColor $(if ($fail -eq 0) { "Green" } else { "Red" })
   if ($fail -gt 0) { exit 1 }
   ```

### README Update

2. Rewrite the **Quick Start** section of `README.md` with a Docker-first flow replacing the four-terminal manual setup:

   ```markdown
   ## Quick Start (Docker — Recommended)

   Prerequisites: Docker Desktop running on Windows 11.

   # 1. Clone and enter the repository
   git clone <repo-url>
   cd project-fortify

   # 2. Configure environment
   Copy-Item .env.example .env
   # Edit .env: set GROQ_API_KEY to your key from https://console.groq.com/keys

   # 3. Start the full stack
   docker compose up --build -d

   # 4. Wait ~30 s for migrations and seed to complete, then open:
   #    Dashboard:  http://localhost:8501
   #    API docs:   http://localhost:8000/docs
   #    Login:      username=admin / password=admin123

   # To stop all services (data volumes preserved):
   docker compose down

   # To also delete the PostgreSQL data volume:
   docker compose down -v
   ```

### Version Bump

3. In `api/app/main.py`:
   - Change `version="0.7.0"` to `version="0.8.0"` in the `FastAPI(...)` constructor.
   - Change `"version": "0.7.0"` to `"version": "0.8.0"` in the root endpoint return dict.

4. In `frontend/dashboard/app.py`:
   - Change `v0.7.0` to `v0.8.0` in the `menu_items` About string.

5. Update the footer caption in all six page files from `v0.7.0` to `v0.8.0`:
   - `frontend/dashboard/pages/home.py`
   - `frontend/dashboard/pages/vm_health_monitor.py`
   - `frontend/dashboard/pages/security_posture.py`
   - `frontend/dashboard/pages/optimization.py`
   - `frontend/dashboard/pages/export_report.py`
   - `frontend/dashboard/pages/ai_insights.py`

### `commands.md` Update

6. Prepend a new **Docker Commands (v0.8.0)** section to `docs/commands.md` immediately after the title.

### Final Run and Commit

7. Run the full smoke test against the running stack:

   ```powershell
   docker compose up --build -d
   Start-Sleep -Seconds 30
   .\scripts\smoke_test.ps1
   ```

8. Commit all changes with conventional commit messages. Open PR from `sprint-9-docker` to `develop`.

**Checkpoint (Day 5):** `.\scripts\smoke_test.ps1` prints `Results: 5 passed, 0 failed` with a green exit.

---

## New Files

```
api/.dockerignore
api/entrypoint.sh
api/app/limiter.py
frontend/Dockerfile
frontend/.dockerignore
docker-compose.yml                                   — root-level, canonical compose file
.env.example                                         — committed template; .env remains git-ignored
scripts/smoke_test.ps1
docs/sprints/sprint-9.md
```

---

## Modified Files

```
api/Dockerfile                                       — python:3.12-slim, non-root user, data/seeds copy
api/requirements.txt                                 — add slowapi>=0.1.9
api/app/main.py                                      — import limiter, CORS lockdown, bump to v0.8.0
api/app/routers/auth.py                              — @limiter.limit("10/minute") on POST /token
frontend/dashboard/utils/api_client.py               — read API_BASE_URL from env with localhost fallback
frontend/dashboard/app.py                            — v0.8.0 in About string
frontend/dashboard/pages/home.py                     — v0.8.0 footer
frontend/dashboard/pages/vm_health_monitor.py        — v0.8.0 footer
frontend/dashboard/pages/security_posture.py         — v0.8.0 footer
frontend/dashboard/pages/optimization.py             — v0.8.0 footer
frontend/dashboard/pages/export_report.py            — v0.8.0 footer
frontend/dashboard/pages/ai_insights.py              — v0.8.0 footer
infrastructure/docker-compose.yml                    — deprecation notice comment added
docs/commands.md                                     — prepend Docker v0.8.0 section
README.md                                            — Docker-first Quick Start
```

---

## Success Criteria

1. `docker compose up --build -d` from the project root starts all four containers with no manual steps beyond copying `.env`.
2. `docker compose ps` shows all four services healthy within 60 seconds of startup.
3. `GET http://localhost:8000/health` returns `{"status": "healthy"}`.
4. `POST http://localhost:8000/auth/token` with `username=admin&password=admin123` returns a JWT on a fresh volume (seed ran automatically via entrypoint).
5. `GET http://localhost:8000/api/v1/vms/summary` with a valid Bearer token returns VM data.
6. `GET http://localhost:8501/_stcore/health` returns HTTP 200.
7. Logging in via the Streamlit dashboard loads the home page with live data from the API container.
8. Firing 11 consecutive `POST /auth/token` requests within one minute results in HTTP 429 on the 11th.
9. `api/app/main.py` version and all frontend footers read `v0.8.0`.
10. `.env` does not appear in `git status` as a tracked or staged file.
11. `.\scripts\smoke_test.ps1` exits with code 0 and prints `Results: 5 passed, 0 failed`.

---

## Commands Reference

```powershell
# ── Full stack management ──────────────────────────────────────────────────
docker compose up --build -d
docker compose ps
docker compose logs -f
docker compose logs -f api
docker compose logs -f frontend
docker compose down
docker compose down -v

# ── Build operations ───────────────────────────────────────────────────────
# Rebuild a single service without touching others
docker compose build api
docker compose up -d --no-deps api

# Build images standalone
docker build -f api/Dockerfile -t fortify-api:local .
docker build -f frontend/Dockerfile -t fortify-frontend:local frontend/

# ── Smoke test ────────────────────────────────────────────────────────────
.\scripts\smoke_test.ps1

# ── Auth verification ─────────────────────────────────────────────────────
$token = (Invoke-RestMethod -Method POST http://localhost:8000/auth/token `
    -ContentType "application/x-www-form-urlencoded" `
    -Body "username=admin&password=admin123").access_token

Invoke-RestMethod http://localhost:8000/api/v1/vms/summary `
    -Headers @{ Authorization = "Bearer $token" }

# ── Rate limit verification ───────────────────────────────────────────────
1..11 | ForEach-Object {
    try {
        Invoke-RestMethod -Method POST http://localhost:8000/auth/token `
            -ContentType "application/x-www-form-urlencoded" `
            -Body "username=wrong&password=wrong"
    } catch {
        Write-Host "Attempt $_`: $($_.Exception.Response.StatusCode)"
    }
}

# ── Database access ───────────────────────────────────────────────────────
docker exec -it fortify-postgres psql -U fortify_user -d fortify

# ── Port conflict check ───────────────────────────────────────────────────
Get-NetTCPConnection -LocalPort 8000, 8501, 5432, 6379 -ErrorAction SilentlyContinue |
    Select-Object LocalPort, State, OwningProcess
```

---

## Definition of Done

- `docker compose up --build -d` from the project root exits 0 and brings up all four services.
- The API entrypoint runs `alembic upgrade head` and `seed_users.py` automatically; no manual migration or seed step is required.
- `frontend/dashboard/utils/api_client.py` reads `API_BASE_URL` from the environment; the Streamlit container connects to the API by service name (`http://api:8000`), not `localhost`.
- `POST /auth/token` is rate-limited to 10 requests per minute per IP; the 11th request within a minute returns HTTP 429.
- CORS `allow_origins` is locked to `["http://localhost:8501", "http://frontend:8501"]`; the wildcard `*` is removed.
- `.env.example` is committed to the repository; `.env` is not.
- `api/Dockerfile` runs as a non-root user (`appuser`).
- `.\scripts\smoke_test.ps1` passes all five checks against the running Docker stack.
- `api/app/main.py` version is `0.8.0`; all six frontend page footers and `app.py` read `v0.8.0`.
- `README.md` Docker Quick Start section is present and accurate.
- `docs/commands.md` has a Docker v0.8.0 section prepended.
- Sprint file committed to `sprint-9-docker` branch and draft PR opened targeting `develop`.
