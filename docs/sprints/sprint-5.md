# Sprint 5: Security Posture, Cost Optimization & Platform Hardening

**Duration:** 2 weeks  
**Goal:** Implement the two remaining stub pages (Security Posture & Cost Optimization), add supporting API endpoints, and harden the platform for a production-ready v0.4.0 demo.

---

## Sprint Deliverables

1. **Security Posture Page** – Full implementation of `security_posture.py` with fleet-level KPIs, per-VM security table, and vulnerability/patch-lag charts.
2. **Cost Optimization Page** – Full implementation of `optimization.py` with resource utilization analysis and a rule-based recommendations engine.
3. **New API Endpoints** – `/security/summary` and `/optimization/recommendations` with Redis caching.
4. **Dashboard Polish** – Complete the Fleet Overview second row, add a health distribution donut chart, and implement auto-refresh.
5. **Error Handling** – Consistent graceful fallback UI across all pages when the API is unavailable.
6. **Testing & Deployment** – Integration tests for all summary endpoints, production `docker-compose.prod.yml`, and navigation cleanup.

---

## Week 1: Feature Buildout

### Days 1–2: Backend — New API Endpoints

- [ ] Add `GET /api/v1/security/summary` endpoint:
  - Returns fleet-level aggregates: avg security score, total open vulns, total critical vulns, count of VMs with firewall disabled, patch lag distribution.
  - Cache response in Redis with 60-second TTL.
- [ ] Add `GET /api/v1/optimization/recommendations` endpoint:
  - Returns list of recommendation objects: `{vm_id, vm_name, recommendation_type, reason, severity}`.
  - Severity levels: `info`, `warning`, `critical`.
  - Rule logic: CPU <20% avg → downsize suggestion; CPU >85% avg → scale-up; Disk >90% → cleanup; VM offline >48h → review.
  - Cache response in Redis with 120-second TTL.
- [ ] Verify both endpoints return correct data against seeded VM fleet.

**Checkpoint:** Both new endpoints live, Redis-cached, and returning valid responses.

### Days 3–4: Security Posture Frontend

- [ ] Replace stub in `security_posture.py` with full implementation:
  - **Fleet KPI row:** Average Security Score, Total Open Vulnerabilities, Total Critical Vulnerabilities, VMs with Firewall Disabled — using existing `metric-card` CSS.
  - **Security distribution chart:** Plotly donut or bar chart grouping VMs by score tier (High ≥80 / Medium 60–79 / Low <60).
  - **Patch lag chart:** Plotly bar chart grouping VMs by days since last patch (0–7, 8–30, 31–90, 90+).
  - **Per-VM security table:** Columns — VM ID (deep link to `/vm_health_monitor?vm=<id>`), Name, Security Score (color-coded), Open Vulns, Critical Vulns, Firewall (✅/❌), SSH Key Auth (✅/❌), Disk Encryption (✅/❌), Compliance Score, Last Patch Date. Default sort: Security Score ascending (worst first).
- [ ] Add `get_security_summary()` method to `api_client.py`.

**Checkpoint:** Security Posture page fully functional, stub removed.

### Day 5: Cost Optimization Frontend

- [ ] Replace stub in `optimization.py` with full implementation:
  - **Fleet KPI row:** Average CPU Utilization, Average Memory Utilization, Over-provisioned VM count (CPU <20%), Under-provisioned VM count (CPU >85%).
  - **Utilization chart:** Plotly scatter or bar chart — CPU vs Memory per VM, color-coded by zone (Optimal / Wasteful / Overloaded).
  - **Recommendations section:** Fetch from `/optimization/recommendations` and render each item using existing `alert-box` CSS (🔴 critical / 🟡 warning / 🟢 info). Each recommendation links to the relevant VM's health page.
  - **VM utilization table:** Columns — VM ID (deep link), Name, CPU %, Memory %, Disk %, Recommendation Type.
- [ ] Add `get_optimization_recommendations()` method to `api_client.py`.

**Checkpoint:** Cost Optimization page fully functional, stub removed.

---

## Week 2: Polish, Testing & Deployment

### Days 6–7: Dashboard Polish & UX Improvements

- [ ] Complete `home.py` Fleet Overview second row:
  - `col2`: Fleet-wide average CPU utilization card.
  - `col3`: Total active alerts card.
  - Donut chart for health distribution (Healthy / Warning / Critical) using Plotly inside `health-score-card` div.
- [ ] Add auto-refresh capability across all pages:
  - Sidebar toggle: "Auto-refresh" on/off with interval options (30s / 60s / 5min).
  - Implemented via `st.rerun()` with `time.sleep()` or `st_autorefresh` component.
  - Refresh state persisted in `st.session_state`.
  - "Last refreshed" timestamp shown on every page.
- [ ] Update version footer to `v0.4.0` across all pages.

**Checkpoint:** Dashboard second row complete, auto-refresh working on all pages.

### Days 8–9: Error Handling & Testing

- [ ] Standardise error handling across all pages:
  - All `api_client` calls wrapped with graceful fallback — display styled error card (not raw Streamlit error or Python traceback) when API returns `None`.
  - Empty state with a "Retry" button if `get_vms_summary()` returns no VMs.
  - Loading spinners consistent across all pages.
- [ ] Write integration tests for:
  - `GET /api/v1/vms/summary`
  - `GET /api/v1/vms/{vm_id}/health`
  - `GET /api/v1/vms/{vm_id}/cpu-metrics`
  - `GET /api/v1/security/summary`
  - `GET /api/v1/optimization/recommendations`
  - Tests use pytest fixtures or a test PostgreSQL instance.
  - All tests runnable via `pytest` from the `api/` directory.
- [ ] Set up GitHub Actions workflow: run pytest on every push to `main`.

**Checkpoint:** Error handling consistent, all five endpoints have passing tests, CI green.

### Day 10: Deployment Prep & Final Polish

- [ ] Create `docker-compose.prod.yml`:
  - API runs without `--reload` flag.
  - Streamlit container added to compose stack.
  - `restart: unless-stopped` on all services.
  - Environment variables sourced from `.env.prod` (never hardcoded defaults).
  - `.env.prod` added to `.gitignore`.
- [ ] Clean up navigation:
  - Remove all `st.info("🚧 Coming soon...")` stubs now that pages are complete.
  - Consistent sidebar labels: "🏠 Dashboard", "🖥️ VM Health", "🔒 Security Posture", "📉 Cost Optimization", "📥 Export Report".
  - Each page has a matching title + `st.caption()` subtitle.
- [ ] Update `README.md` with setup and run instructions for both dev and prod.
- [ ] Run end-to-end walkthrough across all 5 pages, verify no tracebacks visible to end users.

**Checkpoint:** Sprint ready for capstone demo.

---

## Technical Implementation Details

### New API Endpoints

```python
# GET /api/v1/security/summary — response shape
{
  "avg_security_score": float,
  "total_open_vulnerabilities": int,
  "total_critical_vulnerabilities": int,
  "firewall_disabled_count": int,
  "patch_lag_distribution": {
    "0_7_days": int,
    "8_30_days": int,
    "31_90_days": int,
    "90_plus_days": int
  }
}

# GET /api/v1/optimization/recommendations — recommendation object
{
  "vm_id": str,
  "vm_name": str,
  "recommendation_type": str,   # "downsize" | "scale_up" | "disk_cleanup" | "review_offline"
  "reason": str,
  "severity": str               # "info" | "warning" | "critical"
}
```

### Optimization Recommendation Rules

```python
# Applied per VM against data from vms_summary
if vm["current_cpu"] < 20:
    → severity: "info",     type: "downsize"
if vm["current_cpu"] > 85:
    → severity: "warning",  type: "scale_up"
if vm["current_disk"] > 90:
    → severity: "critical", type: "disk_cleanup"
if vm["status"] == "offline" and vm["uptime_hours"] == 0:
    → severity: "info",     type: "review_offline"
```

### New `api_client.py` Methods

```python
def get_security_summary(self) -> dict | None:
    """Fetch fleet-wide security aggregates from /security/summary."""

def get_optimization_recommendations(self) -> list | None:
    """Fetch rule-based VM optimization recommendations."""
```

### Production Docker Compose (additions to existing `docker-compose.yml`)

```yaml
api:
  command: uvicorn app.main:app --host 0.0.0.0 --port 8000   # remove --reload
  restart: unless-stopped
  env_file: .env.prod

streamlit:
  build:
    context: ./frontend
    dockerfile: Dockerfile
  container_name: fortify-streamlit
  ports:
    - "8501:8501"
  depends_on:
    - api
  restart: unless-stopped
  env_file: .env.prod
  networks:
    - fortify-network
```

---

## Success Criteria

- [ ] Security Posture page live with KPIs, charts, and per-VM table — no stub placeholder.
- [ ] Cost Optimization page live with utilization analysis and recommendations — no stub placeholder.
- [ ] `/security/summary` and `/optimization/recommendations` endpoints return correct data and are Redis-cached.
- [ ] Home dashboard Fleet Overview second row complete with CPU, alerts, and donut chart.
- [ ] Auto-refresh works on all pages with configurable interval.
- [ ] No Python tracebacks visible to end users on any page when API is unavailable.
- [ ] All five summary/health endpoints covered by passing pytest integration tests.
- [ ] GitHub Actions CI runs and passes on push to `main`.
- [ ] `docker-compose.prod.yml` brings up the full stack (API + Streamlit + Postgres + Redis) with a single command.
- [ ] Sidebar navigation consistent across all 5 pages, no stub labels.

---

## Risks & Mitigation

| Risk | Mitigation |
|---|---|
| Security/optimization pages drawing from same VM data may feel thin | Add server-side aggregation logic in new endpoints to surface genuinely different insights |
| Redis TTL too short causes excessive API calls | Start at 60s/120s; tune upward based on simulator update frequency |
| Auto-refresh resets Streamlit widget state | Use `st.session_state` guards to preserve selections across reruns |
| Production compose blocked by missing Streamlit Dockerfile | Create minimal `frontend/Dockerfile` early in Week 2 to avoid Day 10 blockers |

---

## Commands Reference

```bash
# Run full dev stack
docker-compose up --build

# Run new integration tests
cd api
pytest tests/integration/ -v

# Seed database (if resetting)
python data/seeds/seed_database.py

# Start metrics simulator
python data/generators/metrics_simulator.py

# Run production stack
docker-compose -f docker-compose.prod.yml --env-file .env.prod up -d

# Run Streamlit locally
cd frontend/dashboard
streamlit run app.py
```

---

## Definition of Done

- [ ] Security Posture and Cost Optimization pages fully implemented, stubs removed.
- [ ] Two new backend endpoints live and Redis-cached.
- [ ] Dashboard second row and donut chart complete.
- [ ] Auto-refresh and consistent error handling on all pages.
- [ ] Integration tests passing in CI.
- [ ] Production Docker Compose ships the full stack.
- [ ] Navigation cleaned up and version bumped to v0.4.0.
- [ ] README updated with dev and prod setup instructions.
- [ ] Code reviewed and merged.

---
