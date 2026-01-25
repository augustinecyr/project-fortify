.PHONY: help setup install docker-up docker-down docker-logs run test test-cov lint format migrate migrate-create seed-data db-reset clean

help:
	@echo "Project Fortify - Development Commands"
	@echo ""
	@echo "Setup Commands:"
	@echo "  make setup          - Initial project setup (venv + dependencies)"
	@echo "  make install        - Install Python dependencies"
	@echo ""
	@echo "Docker Commands:"
	@echo "  make docker-up      - Start all Docker services"
	@echo "  make docker-down    - Stop all Docker services"
	@echo "  make docker-logs    - View Docker logs"
	@echo "  make docker-rebuild - Rebuild and restart containers"
	@echo ""
	@echo "Development Commands:"
	@echo "  make run            - Run API locally (outside Docker)"
	@echo "  make test           - Run test suite"
	@echo "  make test-cov       - Run tests with coverage report"
	@echo "  make lint           - Run linters"
	@echo "  make format         - Auto-format code"
	@echo ""
	@echo "Database Commands:"
	@echo "  make migrate        - Run database migrations"
	@echo "  make migrate-create - Create new migration (name=description)"
	@echo "  make seed-data      - Load mock data into database"
	@echo "  make db-reset       - Reset database (drop + recreate + migrate)"
	@echo ""
	@echo "Cleanup Commands:"
	@echo "  make clean          - Remove temporary files and caches"

setup:
	@echo "Setting up project..."
	cp -n .env.example .env || true
	cd api && python -m venv venv
	cd api && . venv/bin/activate && pip install --upgrade pip
	@echo "Run 'make install' to install dependencies"

install:
	@echo "Installing API dependencies..."
	cd api && . venv/bin/activate && pip install -r requirements.txt
	@echo "Installing Analytics dependencies..."
	cd analytics && python -m venv venv || true
	cd analytics && . venv/bin/activate && pip install -r requirements.txt

docker-up:
	@echo "Starting Docker services..."
	docker-compose up -d
	@echo "Waiting for services to be healthy..."
	sleep 5
	docker-compose ps

docker-down:
	@echo "Stopping Docker services..."
	docker-compose down

docker-logs:
	docker-compose logs -f

docker-rebuild:
	@echo "Rebuilding containers..."
	docker-compose down
	docker-compose build --no-cache
	docker-compose up -d

run:
	@echo "Starting API locally..."
	cd api && . venv/bin/activate && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

test:
	@echo "Running tests..."
	cd api && . venv/bin/activate && pytest

test-cov:
	@echo "Running tests with coverage..."
	cd api && . venv/bin/activate && pytest --cov=app --cov-report=html --cov-report=term

lint:
	@echo "Running linters..."
	cd api && . venv/bin/activate && flake8 app/
	cd api && . venv/bin/activate && mypy app/

format:
	@echo "Formatting code..."
	cd api && . venv/bin/activate && black app/
	cd api && . venv/bin/activate && isort app/

migrate:
	@echo "Running migrations..."
	cd api && . venv/bin/activate && alembic upgrade head

migrate-create:
	@echo "Creating migration: $(name)"
	cd api && . venv/bin/activate && alembic revision --autogenerate -m "$(name)"

seed-data:
	@echo "Seeding database with mock data..."
	cd data && python seed_database.py

db-reset:
	@echo "Resetting database..."
	docker-compose down postgres
	docker volume rm project-fortify_postgres_data || true
	docker-compose up -d postgres
	sleep 5
	make migrate
	make seed-data

clean:
	@echo "Cleaning up..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name ".coverage" -delete
	@echo "Cleanup complete"