#!/bin/sh
set -e
echo "[entrypoint] Running Alembic migrations..."
alembic upgrade head
echo "[entrypoint] Seeding admin user..."
python /app/data/seeds/seed_users.py || true
echo "[entrypoint] Seeding VM data..."
python /app/data/seeds/seed_database.py || true
echo "[entrypoint] Starting API..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
