# Sprint 1: Project Foundation & Core Backend

**Duration:** 2 weeks  
**Goal:** Set up development environment and build core API with metric ingestion and health scoring  

---

## What I'm Building This Sprint

By the end of Sprint 1, I'll have:
- ✅ Local development environment running via Docker Compose
- ✅ FastAPI application with core endpoints working
- ✅ PostgreSQL database with schema
- ✅ Mock data for testing (20 VMs with 7 days of metrics)
- ✅ CPU metrics ingestion endpoint
- ✅ Basic health scoring working
- ✅ Unit tests covering critical paths

---

## Week 1: Foundation & Setup

### Day 1-2: Environment Setup
**Goal:** Get Docker environment running

**Tasks:**
- [ ] Create `docker-compose.yml` (PostgreSQL + Redis + API)
- [ ] Create `.env.example` with configuration variables
- [ ] Create `Makefile` for common commands
- [ ] Setup `.gitignore` for Python
- [ ] Initialize Python virtual environment
- [ ] Install base dependencies (FastAPI, SQLAlchemy, pytest)

**Checkpoint:** Run `docker-compose up` successfully, connect to PostgreSQL

---

### Day 3-4: Database & Mock Data
**Goal:** Database schema ready with test data

**Tasks:**
- [ ] Install SQLAlchemy and Alembic
- [ ] Create database models:
  - `VirtualMachine` (id, vm_id, name, created_at)
  - `CPUMetric` (id, vm_id, timestamp, cpu_percent, source)
  - `HealthScore` (id, vm_id, score, computed_at, components)
- [ ] Setup Alembic migrations
- [ ] Create initial migration
- [ ] Write 20 VM fixtures in `data/fixtures/vms.json`
- [ ] Generate CPU metrics for each VM (7 days, 1-min intervals)
- [ ] Create seed script to populate database

**Checkpoint:** Database seeded with 20 VMs and ~200k metric records

---

### Day 5: API Skeleton
**Goal:** Basic FastAPI app running

**Tasks:**
- [ ] Create FastAPI project structure:
  ```
  /api
    /app
      main.py
      /routers
      /models      # Pydantic schemas
      /db          # Database connection
      /services    # Business logic
    /tests
    requirements.txt
    Dockerfile
  ```
- [ ] Setup FastAPI app in `main.py`
- [ ] Create `/health` endpoint (returns 200 OK)
- [ ] Create `/api/v1/status` endpoint (DB connectivity check)
- [ ] Add logging middleware
- [ ] Add error handling middleware
- [ ] Test Swagger docs at `/docs`

**Checkpoint:** API running on localhost:8000, Swagger UI accessible

---

## Week 2: Core Features

### Day 6-7: Metrics Ingestion
**Goal:** Accept and store CPU metrics

**Tasks:**
- [ ] Create Pydantic schemas for CPU metrics (request/response)
- [ ] Implement POST `/api/v1/metrics/cpu`:
  - Accept JSON: `{vm_id, timestamp, cpu_percent, source}`
  - Validate input (cpu_percent 0-100, valid timestamp)
  - Store in database
  - Return 201 Created with ingestion ID
  - Handle errors (400 for invalid data, 500 for DB errors)
- [ ] Implement GET `/api/v1/metrics/cpu/{vm_id}`:
  - Query params: `start_time`, `end_time`, `limit` (default 1000)
  - Return time-series data
  - Handle 404 if VM not found
- [ ] Test endpoints with Postman/curl

**Checkpoint:** Can POST metrics and GET them back successfully

---

### Day 8-9: Health Scoring Algorithm
**Goal:** Calculate VM health scores

**Tasks:**
- [ ] Create `analytics/anomaly_detection.py`:
  - Implement z-score anomaly detection
  - Input: list of CPU values
  - Output: anomaly score (0-1)
- [ ] Create `analytics/scoring.py`:
  - Calculate health score (0-100) from:
    - Anomaly presence (40%)
    - Metric stability/variance (30%)
    - Historical average (30%)
  - Return score breakdown
- [ ] Implement GET `/api/v1/health/{vm_id}`:
  - Fetch last 24 hours of metrics
  - Run anomaly detection
  - Calculate health score
  - Return score with breakdown
- [ ] Write unit tests for scoring logic with known datasets

**Checkpoint:** Health scores calculated correctly for test VMs

---

### Day 10: Testing & Documentation
**Goal:** Ensure quality and document work

**Tasks:**
- [ ] Setup pytest configuration
- [ ] Write unit tests:
  - Database models (create, read, relationships)
  - Pydantic schema validation
  - Ingestion endpoint (valid/invalid inputs)
  - Health scoring algorithm (known inputs → expected outputs)
- [ ] Run coverage report (target: >80%)
- [ ] Update README.md:
  - Project overview
  - Setup instructions
  - Quick start guide
  - API endpoint documentation
- [ ] Create database schema diagram
- [ ] Add code comments for complex logic

**Checkpoint:** Tests passing, documentation complete

---

## Key Deliverables

### 1. Docker Compose Environment
```yaml
# docker-compose.yml
services:
  - postgres (port 5432)
  - redis (port 6379)
  - api (port 8000)
```

### 2. API Endpoints (Functional)
- `GET /health` - Health check
- `GET /api/v1/status` - System status
- `POST /api/v1/metrics/cpu` - Ingest metrics
- `GET /api/v1/metrics/cpu/{vm_id}` - Retrieve metrics
- `GET /api/v1/health/{vm_id}` - Get health score

### 3. Database Schema
- 3 tables: virtual_machines, cpu_metrics, health_scores
- Proper indexes and foreign keys
- Seeded with 20 test VMs

### 4. Mock Data
- 20 VM fixtures
- 7 days of CPU metrics per VM
- Realistic patterns (normal, spiky, degraded)

### 5. Test Suite
- Unit tests with >80% coverage
- Tests run with `make test`

---

## Success Criteria

**Must Have (P0):**
- ✅ Docker environment starts with one command
- ✅ Can POST CPU metrics via API
- ✅ Can GET metrics back with time filtering
- ✅ Health scores calculated and returned correctly
- ✅ All tests passing

**Nice to Have (P1):**
- ⭐ API response times < 500ms
- ⭐ Comprehensive error messages
- ⭐ Database migrations working
- ⭐ Code formatted with black/flake8

---

## Risks & Mitigation

| Risk | Mitigation |
|------|------------|
| Docker issues on my machine | Test early, document workarounds |
| Z-score too simplistic | Fine for MVP, plan Isolation Forest for Sprint 3 |
| Database performance with mock data | Use indexes, test with 500 VMs if time permits |
| Scope creep | Stick to must-haves, defer nice-to-haves |

---

## Daily Progress Tracking

| Day | Planned | Actual | Blockers | Notes |
|-----|---------|--------|----------|-------|
| 1 | Docker setup | | | |
| 2 | Docker setup | | | |
| 3 | Database models | | | |
| 4 | Mock data | | | |
| 5 | API skeleton | | | |
| 6 | Ingestion endpoint | | | |
| 7 | Metrics retrieval | | | |
| 8 | Health scoring | | | |
| 9 | Testing health scores | | | |
| 10 | Tests & docs | | | |

---

## Quick Reference Commands

```bash
# Setup
make setup          # Create venv, install deps
make docker-up      # Start all services
make seed-data      # Load mock data

# Development
make run            # Start API locally
make test           # Run tests
make lint           # Check code style

# Database
make migrate        # Run migrations
make db-reset       # Fresh database

# Cleanup
make docker-down    # Stop services
make clean          # Remove temp files
```

---

## Sprint 2 Preview

Once Sprint 1 is complete, I'll tackle:
- Security metadata ingestion
- Security posture scoring  
- Background scheduler for automated scoring
- Streamlit dashboard foundation

---

## Reflection Questions (End of Sprint)

**What went well?**
- 

**What was challenging?**
- 

**What would I do differently?**
- 

**What did I learn?**
- 

**Ready for Sprint 2?**
- [ ] Yes / [ ] No - if no, what needs completion?

---

**Version:** 1.0  
**Last Updated:** [Date]