# Observability Guide — Project Fortify v1.0

## Services and their log streams

| Service | Container | What it emits |
|---|---|---|
| `api` | `fortify-api` | Structured JSON — auth events, every HTTP request, app errors |
| `frontend` | `fortify-frontend` | Streamlit server start/stop, Python exceptions |
| `postgres` | `fortify-postgres` | Connection events, slow queries, startup messages |
| `redis` | `fortify-redis` | Connection events, eviction notices |

All four services write to Docker's `json-file` log driver with rotation (`max-size: 10m`, `max-file: 3`).

> **Audit trail vs. access logs.** The stdout stream below (including per-request
> access logs) is for *observability* and is rotated/capped. Security-relevant
> events — logins, authorization denials, and state changes — are *additionally*
> persisted to the durable, queryable `audit_logs` table and surfaced via the
> operator-gated `GET /api/v1/audit` endpoint (see `docs/runbook.md` → Audit
> trail). For "who did what", query that endpoint, not the container logs.

---

## Key log fields (API)

Every line emitted by the API is valid JSON. The fields that matter for operations are:

| Field | Type | Description |
|---|---|---|
| `timestamp` | ISO-8601 string | UTC time the event was recorded |
| `level` | string | `INFO`, `WARNING`, `ERROR`, `CRITICAL` |
| `logger` | string | Python logger name — see table below |
| `message` | string | Human-readable summary |
| `event` | string | Machine-readable event type (auth and request logs) |
| `username` | string | Authenticated user who triggered the event |
| `success` | bool | `true` / `false` (auth events only) |
| `ip` | string | Client IP address (auth events only) |
| `method` | string | HTTP verb (request logs only) |
| `path` | string | Request path (request logs only) |
| `status_code` | int | HTTP response code (request logs only) |
| `duration_ms` | float | Time to respond in milliseconds (request logs only) |

### Logger names

| Logger | What it covers |
|---|---|
| `fortify.audit` | Auth events and per-request access log |
| `uvicorn.access` | Low-level HTTP connection lines |
| `uvicorn.error` | Startup, shutdown, and unhandled errors |
| `app.*` | Individual router and service modules |

---

## Critical log patterns to monitor

### Auth failures
```powershell
docker compose logs api | Select-String '"event":"auth_failure"'
```
Repeated failures from the same IP indicate a brute-force attempt. The `/auth/token` endpoint is rate-limited to 10 requests/minute per IP.

### Auth successes
```powershell
docker compose logs api | Select-String '"event":"auth_success"'
```

### HTTP 500 errors
```powershell
docker compose logs api | Select-String '"status_code":500'
```

### Rate limit hits (HTTP 429)
```powershell
docker compose logs api | Select-String '"status_code":429'
```

### Slow requests (> 1 second)
The `duration_ms` field lets you spot slow endpoints. Parse the JSON and filter:
```powershell
docker compose logs api | ForEach-Object {
    try {
        $j = $_ | ConvertFrom-Json
        if ($j.duration_ms -gt 1000) { $j }
    } catch {}
}
```

### Verify all API lines are valid JSON
```powershell
docker compose logs api | ForEach-Object {
    try { $_ | ConvertFrom-Json | Out-Null }
    catch { Write-Host "Non-JSON line: $_" }
}
```

---

## Docker health checks

Each service declares a health check in `docker-compose.yml`. Status is visible via:

```powershell
docker compose ps
```

| Service | Health check | What it tests |
|---|---|---|
| `postgres` | `pg_isready` | PostgreSQL accepting connections |
| `redis` | `redis-cli ping` | Redis responding |
| `api` | HTTP GET `/health` | FastAPI up and DB reachable |
| `frontend` | _(none)_ | Depends on `api` being healthy |

A container stuck in `(health: starting)` for more than 60 seconds usually means its dependency is not ready. Check the dependency's logs first.

---

## Streaming logs

```powershell
# All services
docker compose logs -f

# API only
docker compose logs -f api

# Filter for a specific VM or username
docker compose logs api | Select-String "vm-prod-01"
docker compose logs api | Select-String '"username":"admin"'
```

---

## Resource usage

```powershell
# Snapshot (all containers)
docker stats --no-stream

# Live stream
docker stats
```

---

## PostgreSQL monitoring

```powershell
# Connect to the running database
docker exec -it fortify-postgres psql -U fortify_user -d fortify

# Inside psql — active connections
SELECT pid, usename, state, query FROM pg_stat_activity WHERE datname = 'fortify';

# Inside psql — table sizes
SELECT relname, pg_size_pretty(pg_total_relation_size(relid))
FROM pg_catalog.pg_statio_user_tables
ORDER BY pg_total_relation_size(relid) DESC;
```

---

## Redis monitoring

```powershell
# Connect to Redis CLI
docker exec -it fortify-redis redis-cli

# Inside redis-cli — server info and memory usage
INFO memory

# List all cached keys
KEYS *

# Check TTL on a specific key
TTL ai:fleet_insights
TTL security:summary
```

### Cache TTLs reference

| Key | TTL | Notes |
|---|---|---|
| `ai:fleet_insights` | 1800 s (30 min) | Busted by the ↻ button in AI Insights |
| `ai:vm_analysis:{vm_id}` | 600 s (10 min) | Per-VM; busted by ↻ in VM Health Monitor |
| `security:summary` | 60 s (1 min) | Auto-expires |
| `optimization:recommendations` | 120 s (2 min) | Auto-expires |
