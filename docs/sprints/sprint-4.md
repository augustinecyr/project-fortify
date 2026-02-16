# Sprint 4: Enhanced VM Parameters & Fleet Analytics

**Duration:** 2 weeks  
**Goal:** Extend VM data model with 30+ new parameters, upgrade metrics simulation, and build a comprehensive fleet overview dashboard.

---

## Sprint Deliverables

1. **Enhanced Database Models** – `VirtualMachine` model with fields for health scores, security, resources, alerts, and aggregates.
2. **Updated API Schemas** – Pydantic models for new VM responses and fleet summary.
3. **Seeding & Simulation** – Improved `seed_database.py` and `metrics_simulator.py` to populate and continuously update new fields.
4. **Modern Home Dashboard** – Fleet health score, status distribution, AI recommendations, and detailed VM table with new metrics.
5. **Backward Compatibility** – All changes non‑breaking; existing CPU metrics endpoints remain intact.
6. **Documentation & Testing** – Migration guide, verification checklist, and test scenarios.

---

## Week 1: Backend Foundation

### Days 1–2: Database & Models

- [ ] Replace `models.py` with enhanced version (add 30+ fields: health, security, resources, alerts, aggregates).
- [ ] Run migration (fresh database or Alembic script) to apply new schema.
- [ ] Update `schemas.py` with `VMResponse`, `VMSummaryResponse`, `FleetSummaryResponse`.
- [ ] Ensure all new fields are nullable for backward compatibility.

**Checkpoint:** Database upgraded, schemas defined, no breaking changes.

### Days 3–4: Seeding & Data Generation

- [ ] Replace `vms.json` with enhanced fixture (20 VMs with realistic values for new fields).
- [ ] Upgrade `seed_database.py` to load all new fields and calculate 24‑hour aggregates.
- [ ] Test seeding: run script and verify all VMs have proper data (health scores, security, resource metrics, etc.).
- [ ] Generate 7 days of CPU metrics (unchanged) plus new simulator output.

**Checkpoint:** Seeder populates all new fields correctly.

### Day 5: Advanced Metrics Simulator

- [ ] Replace `metrics_simulator.py` with enhanced version:
  - Simulate **CPU, memory, disk, network** in real time.
  - VM‑profile behavior (web servers, databases, workers).
  - Time‑of‑day variation.
  - Auto‑update health scores, anomaly flags, alerts.
- [ ] Run simulator alongside API and verify updates reflect in database.

**Checkpoint:** Simulator runs continuously and updates VM fields dynamically.

---

## Week 2: Frontend & Integration

### Days 6–7: Fleet Overview Dashboard

- [ ] Update `home.py` to consume new fleet summary endpoint:
  - Display fleet health score, healthy/warning/critical counts.
  - Show fleet security score and total vulnerabilities.
  - Present AI recommendations based on new data.
- [ ] Enhance VM table with new columns (status, health score, CPU, memory, alerts).
- [ ] Ensure design matches modern card‑based layout.

**Checkpoint:** Home page displays all enhanced fleet metrics.

### Days 8–9: VM Health Page Enhancements

- [ ] Modify `vm_health_monitor.py` to show new fields:
  - Security score, compliance, vulnerabilities.
  - Memory and disk usage (progress bars).
  - Network I/O.
  - Alert and anomaly indicators.
- [ ] Keep existing CPU chart and anomaly details.
- [ ] Update export to include new fields in CSV/JSON reports.

**Checkpoint:** VM Health page reflects all new parameters.

### Day 10: Testing & Polishing

- [ ] Run end‑to‑end tests with all 20 VMs.
- [ ] Verify simulator updates all fields correctly over time.
- [ ] Check responsiveness and styling on different screen sizes.
- [ ] Update documentation: `IMPLEMENTATION_GUIDE.md` with final steps.

**Checkpoint:** Sprint ready for demo.

---

## Technical Implementation Details

### New Database Fields (in `models.py`)

```python
host: str
os_version: str
status: str  # online/offline/maintenance
uptime_hours: float
last_boot_time: datetime

health_score: float          # 0-100
security_score: float         # 0-100
compliance_score: float       # 0-100

current_cpu: float
current_memory: float
current_disk: float

memory_total_mb: int
memory_used_mb: int
disk_total_gb: int
disk_used_gb: int

network_in_mbps: float
network_out_mbps: float

last_patch_date: datetime
vulnerabilities: int          # total vulnerabilities
critical_vulnerabilities: int
alerts: int
anomaly_detected: bool
last_anomaly_time: datetime

firewall_enabled: bool
ssh_key_auth: bool
disk_encryption: bool

avg_cpu_24h: float
peak_cpu_24h: float
metric_count_24h: int
```

### API Endpoints (add or extend)

- `GET /api/v1/vms` – returns list with all new fields.
- `GET /api/v1/vms/summary` – fleet overview (counts, averages, totals).
- `GET /api/v1/vms/{vm_id}` – detailed VM data.

### Simulator Enhancements

- Uses threading to send updates every few seconds.
- VM‑specific profiles (e.g., web servers have higher CPU during day, databases have steady load).
- Health score calculation: weighted combination of CPU, memory, anomalies, security.
- Alert generation when thresholds crossed (CPU > 90%, disk > 95%, etc.).

### Frontend Components

- Reuse `components/health_widget.py` for health score card.
- Add `components/progress_card.py` for resource meters.
- Use `st.metric` with delta for changes.

---

## Success Criteria

- [ ] Database contains all new fields for every VM.
- [ ] Simulator updates at least one field every 10 seconds (visible in dashboard).
- [ ] Home dashboard shows:
  - Fleet health score (average of all VMs)
  - Health distribution (healthy/warning/critical)
  - Security score and total vulnerabilities
  - AI recommendations based on current fleet state
- [ ] VM Health page displays:
  - Health score, security score, compliance score
  - CPU, memory, disk usage with progress bars
  - Network I/O metrics
  - Alert and anomaly status
- [ ] Export includes all new fields.
- [ ] No breaking changes to existing API clients.

---

## Risks & Mitigation

| Risk                                      | Mitigation                                           |
| ----------------------------------------- | ---------------------------------------------------- |
| Adding many fields could break existing queries | All new fields are nullable; old queries unaffected. |
| Simulator overloads database               | Batch updates, use threading, limit frequency.      |
| Frontend becomes cluttered                 | Use tabs or expanders for secondary metrics.        |
| Migration complexity                       | Provide Alembic script or fresh seed option.        |

---

## Commands Reference

```bash
# Backend setup
cd api
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

# Run migration (if using Alembic)
alembic upgrade head

# Seed database with new fields
python data/seeds/seed_database.py

# Start metrics simulator (separate terminal)
python data/generators/metrics_simulator.py

# Run API
uvicorn main:app --reload

# Run dashboard
cd ../frontend/dashboard
streamlit run app.py
```

---

## Definition of Done

- [ ] All new database fields implemented and seeded.
- [ ] Simulator updates all VMs continuously.
- [ ] Home dashboard and VM Health page show enhanced metrics.
- [ ] Export files contain new data.
- [ ] Code reviewed and merged.
- [ ] Documentation updated.

---