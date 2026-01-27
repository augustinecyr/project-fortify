"""
SQLAlchemy database models.
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.database import Base


class VirtualMachine(Base):
    """Virtual Machine model."""
    __tablename__ = "virtual_machines"
    
    id = Column(Integer, primary_key=True, index=True)
    vm_id = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    cpu_metrics = relationship("CPUMetric", back_populates="virtual_machine", cascade="all, delete-orphan")
    health_scores = relationship("HealthScore", back_populates="virtual_machine", cascade="all, delete-orphan")


class CPUMetric(Base):
    """CPU Metric model."""
    __tablename__ = "cpu_metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    vm_id = Column(String, ForeignKey("virtual_machines.vm_id"), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    cpu_percent = Column(Float, nullable=False)
    source = Column(String, nullable=False)
    
    # Relationships
    virtual_machine = relationship("VirtualMachine", back_populates="cpu_metrics")


class HealthScore(Base):
    """Health Score model."""
    __tablename__ = "health_scores"
    
    id = Column(Integer, primary_key=True, index=True)
    vm_id = Column(String, ForeignKey("virtual_machines.vm_id"), nullable=False, index=True)
    score = Column(Integer, nullable=False)
    computed_at = Column(DateTime, default=datetime.utcnow, index=True)
    components = Column(JSON, nullable=True)  # Store score breakdown
    
    # Relationships
    virtual_machine = relationship("VirtualMachine", back_populates="health_scores")