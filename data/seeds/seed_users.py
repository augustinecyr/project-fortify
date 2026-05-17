"""
Seed script: creates the default admin user for development and testing.
Run from the api/ directory with the venv activated:
    python ../data/seeds/seed_users.py
"""
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2] / "api"))

from app.db.database import SessionLocal
from app.models.user import User
from app.auth.security import get_password_hash


def seed():
    db = SessionLocal()
    try:
        if db.query(User).filter(User.username == "admin").first():
            print("Admin user already exists — skipping.")
            return
        admin = User(
            username="admin",
            hashed_password=get_password_hash("admin123"),
            is_active=True,
        )
        db.add(admin)
        db.commit()
        print("Admin user created successfully.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
