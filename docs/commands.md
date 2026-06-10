# Project Fortify - Commands Reference

Quick reference for all development commands used in Project Fortify.

---

## Observability (v1.0.0)

```powershell
# Stream all service logs
docker compose logs -f

# API logs only (structured JSON)
docker compose logs -f api

# Filter for errors
docker compose logs api | Select-String '"level":"ERROR"'

# Filter for auth failures
docker compose logs api | Select-String "auth_failure"

# Filter for auth successes
docker compose logs api | Select-String "auth_success"

# Filter for a specific VM's requests
docker compose logs api | Select-String "vm-prod-01"

# Verify every API log line is valid JSON (structured logging check)
docker compose logs api | ForEach-Object {
    try { $_ | ConvertFrom-Json | Out-Null } catch { Write-Host "Non-JSON line: $_" }
}

# Check container health status
docker compose ps

# Live resource usage
docker stats --no-stream
```

---

## Docker Quick Start (v0.8.0)

Runs the full stack (API + Streamlit frontend + PostgreSQL + Redis) with a single command. No local Python environment required.

```powershell
# 1. Copy environment template and fill in secrets
Copy-Item .env.example .env
# Edit .env: set POSTGRES_PASSWORD, SECRET_KEY, GROQ_API_KEY

# 2. Build and start all four services
docker compose up --build -d

# 3. Confirm all containers are healthy
docker compose ps

# 4. Run the smoke test
.\scripts\smoke_test.ps1

# Access points:
# Dashboard: http://localhost:8501  (login: admin / admin123)
# API docs:  http://localhost:8000/docs
```

### Docker Container Commands

```powershell
# Tail live logs from all containers
docker compose logs -f

# Tail logs from a specific service
docker compose logs -f api
docker compose logs -f frontend

# Rebuild a single service after code changes
docker compose up --build -d api

# Open a shell in the API container
docker exec -it fortify-api sh

# Re-run seed scripts manually (if needed)
docker exec fortify-api python /app/data/seeds/seed_database.py
docker exec fortify-api python /app/data/seeds/seed_users.py

# Stop everything (keeps volumes/data)
docker compose down

# Stop and wipe all data (fresh start)
docker compose down -v
```

---

## Initial Setup Commands

### Environment Setup

```powershell
# Copy environment template
Copy-Item .env.example .env

# Create Python virtual environment
cd api
python -m venv venv

# Activate virtual environment (PowerShell)
.\venv\Scripts\Activate.ps1

# Activate virtual environment (Git Bash)
source venv/Scripts/activate

# Upgrade pip
python -m pip install --upgrade pip

# Install dependencies
pip install --only-binary :all: -r requirements.txt

# Deactivate virtual environment
deactivate
```

### Docker Commands

```powershell
# Start all Docker services
docker-compose up -d

# Start specific services only
docker-compose up -d postgres redis

# Stop all services
docker-compose down

# View running containers
docker ps

# View logs
docker-compose logs -f

# Stop specific container
docker stop fortify-api

# Rebuild and restart containers
docker-compose up -d --build

# Remove volumes (WARNING: deletes data)
docker-compose down -v
```

### Re-seed Database with Fresh Data

```powershell
# Activate API venv
cd api
.\venv\Scripts\Activate.ps1
cd ..

# Run seed script (generates 20 VMs with 30+ fields + 7 days of CPU metrics)
python data/seeds/seed_database.py

# This will:
# - Clear existing data
# - Create 20 VMs with health, security, resource, and alert fields
# - Generate ~201,600 CPU metrics (7 days history)
# Takes ~30-60 seconds

# Run metrics simulator in a SEPARATE terminal (keeps VM fields updated in real time)
# Terminal 2:
cd api
.\venv\Scripts\Activate.ps1
cd ..
python data/generators/metrics_simulator.py

# Simulator will:
# - Update CPU, memory, disk, network every few seconds
# - Recalculate health scores, anomaly flags, and alerts continuously
# - Apply VM-specific profiles (web servers, databases, workers)
# - Log AI insights status at startup and every 5 minutes
# - Run indefinitely until stopped (Ctrl+C)
```

### Database Commands

```powershell
# Connect to PostgreSQL in Docker
docker exec -it fortify-postgres psql -U fortify_user -d fortify

# PostgreSQL commands (once connected)
\l                  # List databases
\dt                 # List tables
\d table_name       # Describe table
\q                  # Quit
```

---

## Development Commands

### Script method to boot services

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\infrastructure\start-fortify.ps1
```

### Running the Dashboard

```powershell
# Setup dashboard environment (one-time)
cd frontend/dashboard
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Run dashboard
streamlit run app.py

# Run on specific port
streamlit run app.py --server.port=8502

# Run with auto-reload on file save
streamlit run app.py --server.runOnSave=true

# Clear cache and restart
streamlit cache clear
streamlit run app.py
```

### Running the API

```powershell
# Run API locally (with hot-reload)
cd api
.\venv\Scripts\Activate.ps1
uvicorn app.main:app --reload

# Run API on specific host/port
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Run API in Docker (after building)
docker-compose up -d api
```

### Testing Endpoints

```powershell
# Using PowerShell (Invoke-RestMethod recommended over curl)
Invoke-RestMethod http://localhost:8000/api/v1/status

# Interactive API docs (browser)
# Open: http://localhost:8000/docs
```

---

## Authentication (Sprint 8)

All API routes except `GET /health` and `GET /api/v1/status` require a Bearer token.

### Seed the Admin User (one-time)

```powershell
cd api
.\venv\Scripts\Activate.ps1
cd ..
python data/seeds/seed_users.py
# Creates: username=admin / password=admin123
```

### Obtain a Token

```powershell
# PowerShell
$response = Invoke-RestMethod -Method POST http://localhost:8000/auth/token `
    -ContentType "application/x-www-form-urlencoded" `
    -Body "username=admin&password=admin123"
$token = $response.access_token
Write-Host "Token: $token"
```

### Call a Protected Endpoint

```powershell
# Use the token from above
Invoke-RestMethod http://localhost:8000/api/v1/vms/summary `
    -Headers @{ Authorization = "Bearer $token" }

# One-liner (obtain + call in sequence)
$token = (Invoke-RestMethod -Method POST http://localhost:8000/auth/token `
    -ContentType "application/x-www-form-urlencoded" `
    -Body "username=admin&password=admin123").access_token
Invoke-RestMethod http://localhost:8000/api/v1/vms/summary `
    -Headers @{ Authorization = "Bearer $token" }
```

### Verify a Bad Token is Rejected

```powershell
Invoke-RestMethod http://localhost:8000/api/v1/vms/summary `
    -Headers @{ Authorization = "Bearer invalid.token.here" }
# Expected: 401 Unauthorized
```

### Run Auth Integration Tests

```powershell
cd api
.\venv\Scripts\Activate.ps1
pytest tests/integration/test_auth.py -v
```

---

## AI / Groq Setup (Sprint 6)

### Getting a Groq API Key

1. Go to [https://console.groq.com/keys](https://console.groq.com/keys)
2. Sign in or create a free account
3. Click **Create API Key**, give it a name (e.g. `fortify-dev`)
4. Copy the key — it starts with `gsk_`

### Adding the Key to Your Environment

Add the following line to your `.env` file at the project root:

```bash
GROQ_API_KEY=gsk_your_key_here
```

> **Note:** The `.env` file lives at the project root (same level as `docker-compose.yml`).
> The API reads it via `env_file=("../.env", ".env")` in `config.py`.

### Verifying the Key is Loaded

```powershell
# From api/ folder with venv active
cd api
.\venv\Scripts\Activate.ps1
python -c "from app.config import settings; print('KEY:', repr(settings.GROQ_API_KEY))"
```

Expected output: `KEY: 'gsk_...'` (your actual key, not an empty string)

### Testing AI Endpoints

```powershell
# Fleet-wide AI analysis (first call hits Groq, subsequent calls return Redis cache)
Invoke-RestMethod http://localhost:8000/api/v1/ai/insights

# Single VM deep-dive analysis
Invoke-RestMethod http://localhost:8000/api/v1/ai/vm-analysis/vm-001

# Bust the AI cache (forces fresh Groq call on next request)
Invoke-RestMethod -Method DELETE http://localhost:8000/api/v1/ai/cache
```

### AI Models Used

| Endpoint | Model | Purpose |
|---|---|---|
| `/api/v1/ai/insights` | `llama-3.1-8b-instant` | Fleet-wide summary, anomalies, recommendations |
| `/api/v1/ai/vm-analysis/{vm_id}` | `llama-3.1-8b-instant` | Per-VM deep-dive analysis |

### Redis Cache TTLs

| Cache Key | TTL | Notes |
|---|---|---|
| `ai:fleet_insights` | 1800s (30 min) | Busted by ↻ button in UI |
| `ai:vm_analysis:{vm_id}` | 600s (10 min) | Per VM, busted by ↻ in VM Health Monitor |
| `security:summary` | 60s (1 min) | Auto-expires, refreshes on next request |
| `optimization:recommendations` | 120s (2 min) | Auto-expires, refreshes on next request |

### Groq Rate Limits (Free Tier)

- Requests per minute: 30
- Tokens per minute: 15,000
- Redis caching prevents redundant Groq calls — fleet insights cached for 30 min, per-VM for 10 min
- If rate-limited, the endpoint returns a graceful fallback response with `"is_fallback": true`

### Debugging Groq Issues

```powershell
# Run the test script directly to see raw Groq output
cd api
.\venv\Scripts\Activate.ps1
python test_groq.py

# Check simulator AI status log (appears at startup and every 5 minutes)
# Look for lines starting with: 🤖 [AI]
```

---

## Integration Tests (Sprint 7)

Integration tests hit a real `fortify_test` PostgreSQL database. Redis is patched to no-ops and Groq is mocked at the router boundary — no external API calls are made during the test run.

### Prerequisites

Docker must be running with PostgreSQL available (see Docker Commands above).

```powershell
# Create the test database — one-time setup
docker exec -it fortify-postgres psql -U fortify_user -d postgres -c "CREATE DATABASE fortify_test;"
```

### Running Integration Tests

```powershell
cd api
.\venv\Scripts\Activate.ps1

# Run all integration tests
pytest tests/integration/ -v

# Run a specific integration test file
pytest tests/integration/test_auth.py -v
pytest tests/integration/test_health.py -v
pytest tests/integration/test_vms.py -v
pytest tests/integration/test_security.py -v
pytest tests/integration/test_metrics.py -v
pytest tests/integration/test_optimization.py -v
pytest tests/integration/test_ai.py -v

# Run with coverage
pytest tests/integration/ --cov=app --cov-report=html -v
```

### Running Unit Tests Only

Unit tests do not require a database or Docker.

```powershell
cd api
.\venv\Scripts\Activate.ps1
pytest tests/test_anomaly_detection.py tests/test_scoring.py -v
```

### Running All Tests

```powershell
cd api
.\venv\Scripts\Activate.ps1
pytest tests/ -v
```

### Test Mocking Strategy

| Component | Strategy |
|---|---|
| PostgreSQL | Separate `fortify_test` DB — real queries, isolated data |
| Redis | `cache_get` / `cache_set` patched to no-ops (prevents stale cache hits) |
| Groq LLM | `query_llm` mocked at router boundary (no real API calls or spend) |

> Seed data (3 VMs + 20 CPU metrics) is inserted once per session and dropped on teardown.
> Test VMs: `test-vm-001` (healthy), `test-vm-002` (critical), `test-vm-003` (offline).

---

## Code Quality

```powershell
# Format code with black
cd api
.\venv\Scripts\Activate.ps1
black app/

# Sort imports
isort app/

# Lint code
flake8 app/

# Type checking
mypy app/

# Run all formatting
black app/ && isort app/ && flake8 app/
```

### Testing

```powershell
# Run all tests
cd api
.\venv\Scripts\Activate.ps1
pytest

# Run tests with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_health.py

# Run tests in verbose mode
pytest -v
```

---

## Database Migration Commands (Alembic)

### Initial Setup

```powershell
cd api
.\venv\Scripts\Activate.ps1

# Initialize Alembic (one-time setup)
alembic init alembic
```

### Creating Migrations

```powershell
# Create new migration (auto-generate from models)
alembic revision --autogenerate -m "description of changes"

# Create empty migration
alembic revision -m "description of changes"
```

### Running Migrations

```powershell
# Apply all pending migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# Rollback to specific revision
alembic downgrade <revision_id>

# Show current revision
alembic current

# Show migration history
alembic history
```

---

## Git Commands

### Branch Management

```powershell
# View all branches
git branch -a

# Create and switch to new branch
git checkout -b branch-name

# Switch to existing branch
git checkout branch-name

# Delete local branch
git branch -d branch-name

# Delete remote branch
git push origin --delete branch-name
```

### Committing Changes

```powershell
# Check status
git status

# Add all files
git add .

# Add specific file
git add path/to/file

# Commit with message
git commit -m "type: description"

# Commit types:
# feat: New feature
# fix: Bug fix
# docs: Documentation only
# chore: Setup, tooling, config
# refactor: Code restructuring
# test: Adding tests
```

### Syncing with Remote

```powershell
# Push to remote
git push

# Push new branch to remote
git push -u origin branch-name

# Pull latest changes
git pull

# Fetch without merging
git fetch
```

---

## Project Structure Commands

### Creating Directories

```powershell
# Create directory with subdirectories
New-Item -ItemType Directory -Path "path/to/directory" -Force

# Create multiple directories
New-Item -ItemType Directory -Path "app/routers", "app/models", "app/db" -Force
```

### Creating Files

```powershell
# Create empty file
New-Item -ItemType File -Path "path/to/file.py"

# Create multiple files
New-Item -ItemType File -Path "app/__init__.py", "app/main.py"
```

### Viewing Files

```powershell
# View file content
cat filename

# View with grep/filter
cat filename | Select-String "pattern"

# List files in directory
ls
ls -Recurse  # Recursive
```

---

## Troubleshooting Commands

### Python Environment Issues

```powershell
# Check Python version
python --version

# Check pip version
pip --version

# List installed packages
pip list

# Check if package is installed
pip show package-name

# Reinstall package
pip uninstall package-name
pip install package-name
```

### Docker Issues

```powershell
# Check Docker is running
docker --version

# View container logs
docker logs fortify-postgres
docker logs fortify-redis
docker logs fortify-api

# Inspect container
docker inspect fortify-postgres

# Remove all stopped containers
docker container prune

# Remove unused images
docker image prune
```

### Port Conflicts

```powershell
# Check what's using a port
Get-NetTCPConnection -LocalPort 8000

# Kill process using port
Stop-Process -Id <PID> -Force
```

### Database Connection Issues

```powershell
# Test PostgreSQL connection
docker exec -it fortify-postgres psql -U fortify_user -d fortify

# Check PostgreSQL is healthy
docker ps | Select-String "fortify-postgres"

# Restart PostgreSQL
docker restart fortify-postgres
```

---

## Quick Start Checklist

### Starting a Full Development Session

```powershell
# Option A — script (recommended)
cd infrastructure
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\start-fortify.ps1

# Option B — manual (4 terminals)
# Terminal 1 — Docker
docker-compose up -d postgres redis

# Terminal 2 — API
cd api
.\venv\Scripts\Activate.ps1
uvicorn app.main:app --reload

# Terminal 3 — Simulator
cd api
.\venv\Scripts\Activate.ps1
cd ..
python data/generators/metrics_simulator.py

# Terminal 4 — Dashboard
cd frontend/dashboard
.\venv\Scripts\Activate.ps1
streamlit run app.py

# Access points
# API docs:  http://localhost:8000/docs
# Dashboard: http://localhost:8501
```

### Before Committing Code

```powershell
# 1. Format code
black app/
isort app/

# 2. Run tests
pytest

# 3. Check what changed
git status

# 4. Add and commit
git add .
git commit -m "type: description"

# 5. Push to remote
git push
```

---

## Environment Variables Reference

Key variables in `.env` file at project root:

```bash
# Database
DATABASE_URL=postgresql+psycopg://fortify_user:fortify_pass@localhost:5432/fortify
POSTGRES_DB=fortify
POSTGRES_USER=fortify_user
POSTGRES_PASSWORD=fortify_pass

# Redis
REDIS_URL=redis://localhost:6379/0

# API
API_KEY=dev-api-key-12345
LOG_LEVEL=INFO

# AI / LLM (Sprint 6)
GROQ_API_KEY=gsk_your_key_here  # Get from https://console.groq.com/keys
```