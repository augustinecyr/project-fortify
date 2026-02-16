"""
SQLAlchemy database models.
Enhanced with comprehensive VM monitoring parameters.
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, JSON, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.database import Base


class VirtualMachine(Base):
    """Virtual Machine model with enhanced monitoring parameters."""
    __tablename__ = "virtual_machines"
    
    # Primary identification
    id = Column(Integer, primary_key=True, index=True)
    vm_id = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # NEW: Infrastructure & Host Information
    host = Column(String, nullable=True, index=True)  # Physical host (e.g., "host-01")
    os_version = Column(String, nullable=True)  # e.g., "Ubuntu 22.04 LTS"
    status = Column(String, default="online", index=True)  # online/offline/maintenance
    
    # NEW: Uptime & Boot Information
    uptime_hours = Column(Float, nullable=True)  # Current uptime in hours
    last_boot_time = Column(DateTime, nullable=True)
    
    # NEW: Health & Security Scores (0-100)
    health_score = Column(Integer, nullable=True, index=True)
    security_score = Column(Integer, nullable=True, index=True)
    
    # NEW: Current Resource Utilization Snapshot
    current_cpu = Column(Float, nullable=True)  # Current CPU %
    current_memory = Column(Float, nullable=True)  # Current Memory %
    current_disk = Column(Float, nullable=True)  # Current Disk %
    
    # NEW: Memory Metrics
    memory_total_mb = Column(Integer, nullable=True)
    memory_used_mb = Column(Integer, nullable=True)
    
    # NEW: Disk Metrics
    disk_total_gb = Column(Integer, nullable=True)
    disk_used_gb = Column(Integer, nullable=True)
    
    # NEW: Network Metrics
    network_in_mbps = Column(Float, nullable=True)
    network_out_mbps = Column(Float, nullable=True)
    
    # NEW: Security & Compliance
    last_patch_date = Column(DateTime, nullable=True)
    open_vulnerabilities = Column(Integer, default=0)
    critical_vulnerabilities = Column(Integer, default=0)
    compliance_score = Column(String, nullable=True)  # e.g., "4/6"
    firewall_enabled = Column(Boolean, default=True)
    ssh_key_auth = Column(Boolean, default=True)
    disk_encryption = Column(Boolean, default=False)
    
    # NEW: Alerts & Monitoring
    alert_count = Column(Integer, default=0)
    anomaly_detected = Column(Boolean, default=False)
    last_anomaly_time = Column(DateTime, nullable=True)
    
    # NEW: 24-hour Aggregated Metrics (for dashboard performance)
    avg_cpu_24h = Column(Float, nullable=True)
    avg_memory_24h = Column(Float, nullable=True)
    avg_disk_24h = Column(Float, nullable=True)
    peak_cpu_24h = Column(Float, nullable=True)
    metric_count_24h = Column(Integer, default=0)
    
    # Metadata
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    cpu_metrics = relationship("CPUMetric", back_populates="virtual_machine", cascade="all, delete-orphan")
    health_scores = relationship("HealthScore", back_populates="virtual_machine", cascade="all, delete-orphan")


class CPUMetric(Base):
    """CPU Metric model - unchanged for backward compatibility."""
    __tablename__ = "cpu_metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    vm_id = Column(String, ForeignKey("virtual_machines.vm_id"), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    cpu_percent = Column(Float, nullable=False)
    source = Column(String, nullable=False)
    
    # Relationships
    virtual_machine = relationship("VirtualMachine", back_populates="cpu_metrics")


class HealthScore(Base):
    """Health Score model - unchanged for backward compatibility."""
    __tablename__ = "health_scores"
    
    id = Column(Integer, primary_key=True, index=True)
    vm_id = Column(String, ForeignKey("virtual_machines.vm_id"), nullable=False, index=True)
    score = Column(Integer, nullable=False)
    computed_at = Column(DateTime, default=datetime.utcnow, index=True)
    components = Column(JSON, nullable=True)  # Store score breakdown
    
    # Relationships
    virtual_machine = relationship("VirtualMachine", back_populates="health_scores")