# Sprint 1: Project Foundation & Core Backend

Duration: 2 weeks  
Goal: Set up development environment and build core API with metric ingestion and health scoring  
Start Date: [Fill in]  
End Date: [Fill in]

---

## Sprint Deliverables

1. Local development environment via Docker Compose
2. FastAPI application with core endpoints
3. PostgreSQL database with schema and migrations
4. Mock data (20 VMs with 7 days of metrics)
5. CPU metrics ingestion and retrieval endpoints
6. Basic health scoring algorithm
7. Unit tests with 80% coverage

---

## Week 1: Foundation & Setup

### Days 1-2: Environment Setup

1. Create docker-compose.yml with PostgreSQL, Redis, API services
2. Create .env.example file
3. Create Makefile with common commands
4. Setup .gitignore
5. Initialize Python virtual environment
6. Install dependencies: FastAPI, SQLAlchemy, pytest, Alembic

Checkpoint: docker-compose up runs successfully, can connect to PostgreSQL

### Days 3-4: Database & Mock Data

1. Install SQLAlchemy and Alembic
2. Create database models:
   - VirtualMachine (id, vm_id, name, created_at)
   - CPUMetric (id, vm_id, timestamp, cpu_percent, source)
   - HealthScore (id, vm_id, score, computed_at, components)
3. Setup Alembic migrations
4. Create initial migration
5. Write 20 VM fixtures in data/fixtures/vms.json
6. Generate CPU metrics for each VM (7 days of data)
7. Create seed script to populate database

Checkpoint: Database seeded with 20 VMs and metric records

### Day 5: API Skeleton

1. Create FastAPI project structure:
   - api/app/main.py
   - api/app/routers/
   - api/app/models/ (Pydantic schemas)
   - api/app/db/ (database connection)
   - api/app/services/ (business logic)
2. Setup FastAPI app in main.py
3. Create GET /health endpoint
4. Create GET /api/v1/status endpoint with DB check
5. Add logging middleware
6. Add error handling middleware
7. Verify Swagger docs at /docs

Checkpoint: API running on localhost:8000, Swagger UI accessible

---

## Week 2: Core Features

### Days 6-7: Metrics Ingestion

1. Create Pydantic schemas for CPU metrics
2. Implement POST /api/v1/metrics/cpu:
   - Accept JSON payload with vm_id, timestamp, cpu_percent, source
   - Validate input (cpu_percent 0-100, valid timestamp)
   - Store in database
   - Return 201 with ingestion ID
   - Handle errors (400, 500)
3. Implement GET /api/v1/metrics/cpu/{vm_id}:
   - Support query params: start_time, end_time, limit
   - Return time-series data
   - Handle 404 if VM not found
4. Test endpoints with curl or Postman

Checkpoint: Can POST metrics and GET them back successfully

### Days 8-9: Health Scoring

1. Create analytics/anomaly_detection.py
2. Implement z-score anomaly detection function
3. Create analytics/scoring.py
4. Implement health score calculation:
   - Anomaly presence (40%)
   - Metric stability (30%)
   - Historical average (30%)
5. Implement GET /api/v1/health/{vm_id}:
   - Fetch last 24 hours of metrics
   - Run anomaly detection
   - Calculate health score
   - Return score with breakdown
6. Write unit tests for scoring logic

Checkpoint: Health scores calculated correctly for test VMs

### Day 10: Testing & Documentation

1. Setup pytest configuration
2. Write unit tests:
   - Database models
   - Pydantic schema validation
   - Ingestion endpoint
   - Health scoring algorithm
3. Run coverage report (target: 80%)
4. Update README.md:
   - Project overview
   - Setup instructions
   - Quick start guide
   - API documentation
5. Create database schema diagram
6. Add code comments

Checkpoint: Tests passing, documentation complete

---

## API Endpoints to Build

1. GET /health - Health check
2. GET /api/v1/status - System status
3. POST /api/v1/metrics/cpu - Ingest CPU metrics
4. GET /api/v1/metrics/cpu/{vm_id} - Retrieve metrics with filtering
5. GET /api/v1/health/{vm_id} - Get VM health score

---

## Success Criteria

Must Have:

1. Docker environment starts with one command
2. Can POST CPU metrics via API
3. Can GET metrics with time filtering
4. Health scores calculated correctly
5. All tests passing
6. Basic documentation complete

Nice to Have:

1. API response times under 500ms
2. Comprehensive error messages
3. Database migrations working smoothly
4. Code formatted with black

---

## Risks & Mitigation

1. Docker issues - Test early, document workarounds
2. Z-score too simple - Fine for MVP, upgrade in Sprint 3
3. Database performance - Use indexes, limit initial dataset
4. Scope creep - Stick to must-haves only

## Command Reference

Setup:

- make setup - Create venv and install dependencies
- make docker-up - Start all services
- make seed-data - Load mock data into database

Development:

- make run - Start API locally
- make test - Run test suite
- make lint - Check code style

Database:

- make migrate - Run database migrations
- make db-reset - Drop and recreate database

Cleanup:

- make docker-down - Stop all services
- make clean - Remove temporary files

Next sprint topics:

1. Security metadata ingestion
2. Security posture scoring
3. Background scheduler for automated scoring
4. Streamlit dashboard foundation

---

## End of Sprint Reflection

What went well:

What was challenging:

What to improve:

What I learned:

Ready for Sprint 2: Yes / No

If no, what needs completion:

---

Version: 1.0  
Last Updated: [Date]
