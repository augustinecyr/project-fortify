# Sprint 7: Integration Tests, Error Handling & UI Consistency

**Duration:** 1 week  
**Goal:** Ship v0.6.0 with a passing integration test suite, consistent error handling across all six pages, and a UI consistency pass. Scoped for capstone submission.

---

## Sprint Deliverables

1. **Integration Test Suite** — pytest integration tests covering all API endpoints. Runnable with a single `pytest` command from `api/`.
2. **Error Handling Sweep** — Every API call on every frontend page wrapped in a graceful fallback. No Python tracebacks visible to end users.
3. **UI Consistency Pass** — Headers, footers, captions, and version number uniform across all six pages.
4. **Version Bump** — API and all page footers updated to `v0.6.0`.
5. **Documentation** — `commands.md` updated with integration test commands.

---

## Day 1–2: Integration Test Suite

### Setup

1. Create `api/tests/integration/` directory with `__init__.py` and `conftest.py`.
2. Install test dependencies: `pip install fakeredis httpx`
3. In `conftest.py`:
   - `test_client` fixture: wraps FastAPI `TestClient` with a separate `fortify_test` PostgreSQL database.
   - `override_db` fixture: overrides `get_db` dependency via `app.dependency_overrides`.
   - Redis patched via `unittest.mock.patch` since `cache_get`/`cache_set` are called directly (not injected via `Depends`).
   - Seed fixture: inserts 3 minimal `VirtualMachine` rows and a handful of `CPUMetric` rows so every endpoint has data to work with.

### Test Files

**`test_health.py`**
- `GET /health` returns `200` and `status: healthy`.
- `GET /api/v1/status` returns `200` and `database: connected`.
- `GET /api/v1/health/{vm_id}` returns `health_score` between 0 and 100, includes `components` and `anomaly_details`.
- `GET /api/v1/health/{vm_id}` returns `404` for unknown VM.

**`test_metrics.py`**
- `POST /api/v1/metrics/cpu` valid payload returns `201`.
- `POST /api/v1/metrics/cpu` with `cpu_percent` outside 0–100 returns `422`.
- `POST /api/v1/metrics/cpu` with unknown `vm_id` returns `404`.
- `GET /api/v1/metrics/cpu/{vm_id}` returns time-series data.
- `GET /api/v1/metrics/cpu/{vm_id}` respects `limit` param.
- `GET /api/v1/metrics/cpu/{vm_id}` returns `404` for unknown VM.

**`test_vms.py`**
- `GET /api/v1/vms` returns list with correct `total`.
- `GET /api/v1/vms/summary` returns fleet aggregates — `total_vms`, `fleet_health_score`, `fleet_security_score`.
- `GET /api/v1/vms/{vm_id}` returns all expected fields.
- `GET /api/v1/vms/{vm_id}` returns `404` for unknown VM.
- `PATCH /api/v1/vms/{vm_id}` partial update accepted, `updated_at` changes.

**`test_security.py`**
- `GET /api/v1/security/summary` returns `avg_security_score`, `total_open_vulnerabilities`, `patch_lag_distribution`.
- All four `patch_lag_distribution` keys present.
- `vms` list in response has correct length.

**`test_optimization.py`**
- `GET /api/v1/optimization/recommendations` returns `recommendations` list and `fleet_summary`.
- Each recommendation has `vm_id`, `severity`, `recommendation_type`, `reason`.
- Severity values restricted to `info`, `warning`, `critical`.

**`test_ai.py`**
- `GET /api/v1/ai/insights` with mocked `query_llm` returns `fleet_summary`, `anomalies`, `recommendations`, `predictions`, `analysis_timestamp`, `model_used`.
- `GET /api/v1/ai/vm-analysis/{vm_id}` with mocked `query_llm` returns per-VM fields.
- `GET /api/v1/ai/vm-analysis/{vm_id}` returns `404` for unknown VM.
- `DELETE /api/v1/ai/cache` returns `200`.

**Checkpoint:** `pytest api/tests/integration/ -v` passes with zero failures.

---

## Day 3: Error Handling Sweep

Apply a consistent pattern across all six pages: `home.py`, `vm_health_monitor.py`, `security_posture.py`, `optimization.py`, `export_report.py`, `ai_insights.py`.

**Pattern to enforce on every API call:**

```python
data = api_client.get_something()
if data is None:
    st.markdown("""
        <div class="error-card">
            <strong>Unable to load data</strong><br>
            The API is unavailable or returned an error.
            Verify the backend is running and refresh the page.
        </div>
    """, unsafe_allow_html=True)
    st.stop()
```

Add the `error-card` CSS class to `assets/custom.css`:

```css
.error-card {
    background: #fef2f2;
    border: 1px solid #fecaca;
    border-left: 4px solid #dc2626;
    border-radius: 6px;
    padding: 16px 20px;
    color: #7f1d1d;
    font-size: 13px;
    line-height: 1.6;
    margin: 16px 0;
}
```

**Checklist per page:**
- No raw `st.exception()` or Python traceback visible when API is down.
- All `api_client` calls have a `None` guard with the styled error card.
- Empty-state scenario (API returns empty list) shows an informative message.
- Loading spinners use plain text — no emojis.

**Checkpoint:** With the API container stopped, all six pages display the styled error card and no tracebacks.

---

## Day 4: UI Consistency Pass

Audit all six pages against the CSS classes established in Sprint 6 and enforce uniformity.

**Checklist per page:**
- Header uses `.page-header-title`, `.page-header-sub`, `.header-divider` classes.
- Refresh button follows `[9, 0.4]` column layout pattern.
- `st.set_page_config` title follows pattern `"Fortify — <Page Name>"`.
- `st.caption()` subtitle uses sentence case, no emojis.
- Version footer reads `v0.6.0`.
- No residual stub labels or `st.info("Coming soon...")` content.

**Also bump version:**
- `api/app/main.py` — update `version="0.6.0"`.
- All six page footers — update to `v0.6.0`.

**Checkpoint:** Visual walkthrough across all six pages shows consistent headers, footers, and no emojis in production UI.

---

## Day 5: Documentation & Final Verification

1. Update `commands.md` with integration test commands.
2. Run full integration test suite — all tests pass.
3. Run end-to-end walkthrough across all six pages with the simulator running.
4. Commit all changes with conventional commit messages.
5. Open PR from `develop` to `main`.

---

## New Files

```
api/tests/integration/__init__.py
api/tests/integration/conftest.py
api/tests/integration/test_health.py
api/tests/integration/test_metrics.py
api/tests/integration/test_vms.py
api/tests/integration/test_security.py
api/tests/integration/test_optimization.py
api/tests/integration/test_ai.py
```

## Modified Files

```
api/app/main.py                                   — version bump to 0.6.0
frontend/dashboard/pages/home.py                  — error handling, version footer
frontend/dashboard/pages/vm_health_monitor.py     — error handling, version footer
frontend/dashboard/pages/security_posture.py      — error handling, version footer
frontend/dashboard/pages/optimization.py          — error handling, version footer
frontend/dashboard/pages/export_report.py         — error handling, version footer
frontend/dashboard/pages/ai_insights.py           — error handling, version footer
frontend/dashboard/assets/custom.css              — error-card CSS class
commands.md                                       — integration test commands
```

---

## Success Criteria

1. `pytest api/tests/integration/ -v` passes with zero failures.
2. All six frontend pages display the styled error card when the API is unavailable — no tracebacks.
3. All six pages use the consistent header CSS pattern.
4. Version footer reads `v0.6.0` on every page and in `main.py`.
5. No emojis in any page title, caption, button, or navigation label.
6. `commands.md` updated.
7. Code committed and PR merged to `main`.

---

## Commands Reference

```bash
# Install test dependencies
pip install fakeredis httpx

# Run integration tests
cd api
pytest tests/integration/ -v

# Run with coverage
pytest tests/integration/ -v --cov=app --cov-report=term-missing
```

---

## Definition of Done

- Integration test suite created and all tests passing.
- All six frontend pages have consistent error handling with no visible tracebacks.
- UI consistency pass complete — headers, footers, captions uniform across all pages.
- API version bumped to `v0.6.0`.
- `commands.md` updated.
- Code reviewed and merged to `main` via PR.
