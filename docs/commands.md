# Project Fortify - Commands Reference

Quick reference for all development commands used in Project Fortify.

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
docker-compose -f infrastructure/docker-compose.yml up -d

# Start specific services only
docker-compose -f infrastructure/docker-compose.yml up -d postgres redis

# Stop all services
docker-compose -f infrastructure/docker-compose.yml down

# View running containers
docker ps

# View logs
docker-compose -f infrastructure/docker-compose.yml logs -f

# Stop specific container
docker stop fortify-api

# Rebuild and restart containers
docker-compose -f infrastructure/docker-compose.yml up -d --build

# Remove volumes (WARNING: deletes data)
docker-compose -f infrastructure/docker-compose.yml down -v
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

### Running the API

```powershell
# Run API locally (with hot-reload)
cd api
.\venv\Scripts\Activate.ps1
uvicorn app.main:app --reload

# Run API on specific host/port
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Run API in Docker (after building)
docker-compose -f infrastructure/docker-compose.yml up -d api
```

### Testing Endpoints

```powershell
# Using PowerShell
Invoke-WebRequest -Uri http://localhost:8000/health -UseBasicParsing | Select-Object -ExpandProperty Content
Invoke-WebRequest -Uri http://localhost:8000/api/v1/status -UseBasicParsing | Select-Object -ExpandProperty Content

# Using curl (if available)
curl http://localhost:8000/health
curl http://localhost:8000/api/v1/status

# Interactive API docs (browser)
# Open: http://localhost:8000/docs
```

### Code Quality

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

# Restart Docker Desktop (if needed)
# Close and reopen Docker Desktop application

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
# Check what's using a port (PowerShell)
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

### Starting a New Development Session

```powershell
# 1. Start Docker services
docker-compose -f infrastructure/docker-compose.yml up -d postgres redis

# 2. Activate virtual environment
cd api
.\venv\Scripts\Activate.ps1

# 3. Run API
uvicorn app.main:app --reload

# 4. Open browser to test
# http://localhost:8000/docs
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

## Useful Aliases (Optional)

Add these to your PowerShell profile for shortcuts:

```powershell
# Edit profile
notepad $PROFILE

# Add these functions:
function Start-Fortify {
    docker-compose -f infrastructure/docker-compose.yml up -d postgres redis
    cd api
    .\venv\Scripts\Activate.ps1
    uvicorn app.main:app --reload
}

function Stop-Fortify {
    docker-compose -f infrastructure/docker-compose.yml down
}

function Test-Api {
    Invoke-WebRequest -Uri http://localhost:8000/api/v1/status -UseBasicParsing | Select-Object -ExpandProperty Content
}
```

---

## Environment Variables Reference

Key variables in `.env` file:

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

# Analytics
ANOMALY_THRESHOLD=0.7
SCORE_UPDATE_INTERVAL=300
```
