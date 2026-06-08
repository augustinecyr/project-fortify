from sqlalchemy import Column, Integer, String, Boolean, DateTime
from datetime import datetime
from app.db.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    # Authorization role. Hierarchical: admin > operator > viewer (see
    # app.auth.dependencies.ROLE_HIERARCHY). New users default to the
    # least-privileged role.
    role = Column(String, nullable=False, default="viewer", server_default="viewer")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
