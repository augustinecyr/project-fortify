# Operations Runbook — Project Fortify v1.0

## Prerequisites

| Requirement | Version | Notes |
|---|---|---|
| Docker Desktop | 4.x or later | Must be running before any `docker compose` command |
| `.env` file | — | Copy from `.env.example` and populate secrets (see below) |
| Port 8000 | free | API |
| Port 8501 | free | Streamlit frontend |
| Port 5432 | free | PostgreSQL (exposed for local tooling) |
| Port 6379 | free | Redis (exposed for local tooling) |

---

## Start the stack

```powershell
# 1. Ensure .env is populated (one-time)
Copy-Item .env.example .env
# Edit .env — set POSTGRES_PASSWORD, SECRET_KEY, GROQ_API_KEY

# 2. Build images and start all four services in the background
docker compose up --build -d

# 3. Confirm all containers reach healthy status
docker compose ps
# All four services should show "(healthy)" within ~60 seconds

# 4. Run the smoke test
.\scripts\smoke_test.ps1
```

Access points once healthy:
- Dashboard: `http://localhost:8501` (login: `admin` / `admin123`)
- API docs: `http://localhost:8000/docs`

---

## Stop the stack

```powershell
# Stop all containers — data volumes are preserved
docker compose down

# Stop and wipe all data (fresh start)
docker compose down -v
```

---

## User roles & access control (RBAC)

Fortify enforces three hierarchical roles on top of JWT authentication
(see ADR-7 in `docs/design-decisions.md`). Higher roles inherit all lower
capabilities.

| Role | Can do | Cannot do |
|---|---|---|
| `viewer` | Read all dashboards: fleet/VM lists, health, security, optimization, AI insights | Mutate any state |
| `operator` | Everything viewer can + ingest metrics, update VMs, refresh/clear AI cache | Manage users |
| `admin` | Everything operator can + create users & assign roles | — |

**Defaults & migration.** New users default to `viewer`. The `add_user_role`
migration backfills *existing* accounts to `admin` to avoid lock-out; the
seeded `admin` user (`data/seeds/seed_users.py`) is created as `admin`. After
upgrading, review accounts and down-assign roles as appropriate.

**Provision a user (admin only):**

```powershell
# 1. Obtain an admin token
$tok = (Invoke-RestMethod -Method POST http://localhost:8000/auth/token `
  -Body @{username='admin'; password='admin123'} `
  -ContentType 'application/x-www-form-urlencoded').access_token

# 2. Create a viewer/operator/admin user
Invoke-RestMethod -Method POST http://localhost:8000/auth/users `
  -Headers @{Authorization="Bearer $tok"} -ContentType 'application/json' `
  -Body (@{username='alice'; password='changeme123'; role='operator'} | ConvertTo-Json)

# 3. Check your own identity and role
Invoke-RestMethod http://localhost:8000/auth/me -Headers @{Authorization="Bearer $tok"}
```

A `403` response means the caller's role is insufficient; denials are recorded
in the audit log as `authz_denied` events.

**Manage existing users (admin only):**

```powershell
# List all users with roles and status
Invoke-RestMethod http://localhost:8000/auth/users -Headers @{Authorization="Bearer $tok"}

# Change a user's role and/or deactivate (id from the list above)
Invoke-RestMethod -Method PATCH http://localhost:8000/auth/users/5 `
  -Headers @{Authorization="Bearer $tok"} -ContentType 'application/json' `
  -Body (@{role='operator'; is_active=$true} | ConvertTo-Json)

# Admin reset of another user's password
Invoke-RestMethod -Method POST http://localhost:8000/auth/users/5/password `
  -Headers @{Authorization="Bearer $tok"} -ContentType 'application/json' `
  -Body (@{new_password='newpass1234'} | ConvertTo-Json)
```

The API refuses to demote or deactivate the **last active administrator**
(`409`), preventing accidental lock-out. A user can change their own password
via `POST /auth/me/password` (supplying the current password).

## Audit trail

Security-relevant events (logins, authorization denials, user-management
actions, VM updates, cache clears) are persisted to the `audit_logs` table and
exposed via an **operator-gated** endpoint:

```powershell
# Recent events (newest first); filter by event/actor/time
Invoke-RestMethod "http://localhost:8000/api/v1/audit?limit=50" -Headers @{Authorization="Bearer $tok"}
Invoke-RestMethod "http://localhost:8000/api/v1/audit?event=auth_failure&actor=alice" -Headers @{Authorization="Bearer $tok"}
```

This is the durable, queryable security record. Per-request access logs remain
in the container stdout stream (see `docs/observability.md`) and are *not*
duplicated into this table.

> **Note:** metric-ingest agents currently authenticate as `operator` users.
> A dedicated service-account / scoped API-key path is planned future work
> (ADR-7) — do not share human operator credentials with automated agents in a
> real deployment.

---

## Upgrade procedure

```powershell
# 1. Pull latest code
git pull origin main

# 2. Rebuild images and restart services (zero-downtime for postgres/redis)
docker compose up --build -d

# 3. Verify health
docker compose ps

# 4. Run smoke test
.\scripts\smoke_test.ps1
```

If a database migration is included in the release, the API entrypoint (`api/entrypoint.sh`) runs `alembic upgrade head` automatically on startup before uvicorn starts.

---

## Rollback procedure

```powershell
# 1. Revert the code to the previous commit or tag
git checkout <previous-tag-or-commit>

# 2. Rebuild and restart
docker compose up --build -d api frontend

# 3. If the release included a migration, roll it back
docker exec fortify-api alembic downgrade -1

# 4. Verify health
docker compose ps
```

---

## Database backup

```powershell
# Dump the fortify database to a local file
docker exec fortify-postgres pg_dump -U fortify_user fortify > backup-$(Get-Date -Format "yyyyMMdd-HHmm").sql

# Restore from a dump file
Get-Content backup-20260101-0900.sql | docker exec -i fortify-postgres psql -U fortify_user -d fortify
```

---

## Environment variable reference

All variables are read from the `.env` file at the project root and passed to the API container via `docker-compose.yml`.

| Variable | Default | Required | Description |
|---|---|---|---|
| `POSTGRES_DB` | `fortify` | No | Database name |
| `POSTGRES_USER` | `fortify_user` | No | Database user |
| `POSTGRES_PASSWORD` | `fortify_pass` | **Yes** | Change before first deploy |
| `DATABASE_URL` | _(derived)_ | No | Set by compose; override for external DB |
| `REDIS_URL` | `redis://redis:6379/0` | No | Override for external Redis |
| `SECRET_KEY` | `change-me-in-production` | **Yes** | JWT signing key — must be random and secret |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | No | JWT lifetime |
| `GROQ_API_KEY` | _(empty)_ | No | Required for AI Insights; get from `console.groq.com/keys` |
| `CORS_ALLOWED_ORIGINS` | `http://localhost:8501,http://frontend:8501` | No | Comma-separated list of allowed frontend origins |
| `LOG_LEVEL` | `INFO` | No | `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `ANOMALY_THRESHOLD` | `0.7` | No | Z-score threshold for CPU anomaly detection |
| `SCORE_UPDATE_INTERVAL` | `300` | No | Seconds between health score recalculations |
| `API_KEY` | `dev-api-key-12345` | No | Legacy header key; unused in v1.0 JWT flow |

---

## Common issues and resolutions

### Containers don't reach healthy status

```powershell
# Check which container is stuck
docker compose ps

# Read its logs
docker compose logs api
docker compose logs postgres
```

Most common causes:
- `POSTGRES_PASSWORD` in `.env` does not match what the container was originally initialised with → `docker compose down -v` then restart.
- Port already in use → `Get-NetTCPConnection -LocalPort 8000` to find the conflicting process.

---

### Migration fails on startup

The entrypoint runs `alembic upgrade head`. If it fails, the API container exits immediately.

```powershell
docker compose logs api | Select-String -Pattern "alembic|migration|error" -CaseSensitive:$false
```

Fix: resolve the migration error, then `docker compose up --build -d api`.

---

### Seed script creates duplicate data

```powershell
# Wipe and re-seed
docker compose down -v
docker compose up -d postgres redis
# Wait for postgres healthy, then:
docker compose up -d api
# Seed runs automatically via entrypoint
```

---

### Admin user missing after fresh start

The `seed_users.py` script runs via the entrypoint on every startup. If the admin user is missing:

```powershell
docker exec fortify-api python /app/data/seeds/seed_users.py
```

---

### AI Insights returning fallback response

The `is_fallback: true` field in the response means the Groq API was unreachable or rate-limited.

- Verify `GROQ_API_KEY` is set: `docker exec fortify-api env | Select-String GROQ`
- Check Groq rate limits (free tier: 30 req/min, 15k tokens/min).
- Bust the cache and retry (requires an `operator`/`admin` token — see RBAC section):
  `Invoke-RestMethod -Method DELETE http://localhost:8000/api/v1/ai/cache -Headers @{Authorization="Bearer $tok"}`

---

### Port conflict

```powershell
# Find the process using port 8000
Get-NetTCPConnection -LocalPort 8000 | Select-Object OwningProcess
Get-Process -Id <PID>

# Stop it or change the API's host port in docker-compose.yml
```
