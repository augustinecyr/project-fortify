"""
Seed script: creates the default development/demo users — one per RBAC role.
For local development and demos only; these are well-known credentials and
must never be used in a real deployment.
Run from the api/ directory with the venv activated:
    python ../data/seeds/seed_users.py
"""
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2] / "api"))

from app.db.database import SessionLocal
from app.models.user import User
from app.auth.security import get_password_hash

# (username, password, role) — one account per role for demo / RBAC sanity checks.
DEMO_USERS = [
    ("admin", "admin123", "admin"),
    ("operator", "operator123", "operator"),
    ("viewer", "viewer123", "viewer"),
]


def seed():
    db = SessionLocal()
    try:
        created = 0
        for username, password, role in DEMO_USERS:
            if db.query(User).filter(User.username == username).first():
                print(f"User '{username}' already exists — skipping.")
                continue
            db.add(User(
                username=username,
                hashed_password=get_password_hash(password),
                role=role,
                is_active=True,
            ))
            created += 1
            print(f"User '{username}' ({role}) created.")
        db.commit()
        print(f"Done — {created} user(s) created.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
