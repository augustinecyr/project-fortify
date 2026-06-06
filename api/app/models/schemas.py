"""
Pydantic schemas for request and response validation.
Enhanced with comprehensive VM monitoring fields.
"""
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from typing import Optional, List


# --- User / Auth Schemas ---

class UserCreate(BaseModel):
    """Schema for admin-driven user provisioning."""
    username: str = Field(..., min_length=3, max_length=50, description="Unique username")
    password: str = Field(..., min_length=8, description="Plaintext password (hashed server-side)")
    role: str = Field("viewer", description="viewer | operator | admin")


class UserResponse(BaseModel):
    """Schema for returning a user (never includes the password hash)."""
    id: int
    username: str
    role: str
    is_active: bool
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class UserUpdate(BaseModel):
    """Schema for admin updates to a user's role and/or active status."""
    role: Optional[str] = Field(None, description="viewer | operator | admin")
    is_active: Optional[bool] = Field(None, description="Deactivate/reactivate the account")


class PasswordReset(BaseModel):
    """Schema for an admin resetting another user's password."""
    new_password: str = Field(..., min_length=8)


class PasswordChange(BaseModel):
    """Schema for a user changing their own password."""
    current_password: str = Field(...)
    new_password: str = Field(..., min_length=8)


class AuditLogResponse(BaseModel):
    """Schema for a single audit-trail entry."""
    id: int
    timestamp: datetime
    event: str
    actor: Optional[str] = None
    role: Optional[str] = None
    target: Optional[str] = None
    detail: Optional[str] = None
    ip: Optional[str] = None
    success: Optional[bool] = None

    model_config = ConfigDict(from_attributes=True)


class AuditLogListResponse(BaseModel):
    """Schema for a paginated list of audit entries."""
    total: int
    limit: int
    offset: int
    entries: List[AuditLogResponse]


# --- CPU Metrics Schemas ---

class CPUMetricCreate(BaseModel):
    """Schema for creating a CPU metric entry."""
    vm_id: str = Field(..., description="Virtual Machine ID")
    timestamp: datetime = Field(..., description="Metric timestamp in ISO 8601 format")
    cpu_percent: float = Field(..., ge=0.0, le=100.0, description="CPU utilization percentage (0-100)")
    source: str = Field(..., description="Monitoring source identifier")


class CPUMetricResponse(BaseModel):
    """Schema for CPU metric response."""
    id: int
    vm_id: str
    timestamp: datetime
    cpu_percent: float
    source: str

    model_config = ConfigDict(from_attributes=True)


class CPUMetricIngestionResponse(BaseModel):
    """Schema for metric ingestion acknowledgment."""
    message: str
    ingestion_id: int
    vm_id: str
    timestamp: datetime


class CPUMetricsListResponse(BaseModel):
    """Schema for listing CPU metrics."""
    vm_id: str
    total_records: int
    start_time: datetime
    end_time: datetime
    metrics: List[CPUMetricResponse]


# --- Enhanced VM Schemas ---

class VMResponse(BaseModel):
    """Enhanced schema for VM response with all monitoring parameters."""
    vm_id: str
    name: str
    created_at: datetime
    host: Optional[str] = None
    os_version: Optional[str] = None
    status: Optional[str] = "online"
    uptime_hours: Optional[float] = None
    last_boot_time: Optional[datetime] = None
    health_score: Optional[int] = None
    security_score: Optional[int] = None
    current_cpu: Optional[float] = None
    current_memory: Optional[float] = None
    current_disk: Optional[float] = None
    memory_total_mb: Optional[int] = None
    memory_used_mb: Optional[int] = None
    disk_total_gb: Optional[int] = None
    disk_used_gb: Optional[int] = None
    network_in_mbps: Optional[float] = None
    network_out_mbps: Optional[float] = None
    last_patch_date: Optional[datetime] = None
    open_vulnerabilities: Optional[int] = 0
    critical_vulnerabilities: Optional[int] = 0
    compliance_score: Optional[str] = None
    firewall_enabled: Optional[bool] = True
    ssh_key_auth: Optional[bool] = True
    disk_encryption: Optional[bool] = False
    alert_count: Optional[int] = 0
    anomaly_detected: Optional[bool] = False
    last_anomaly_time: Optional[datetime] = None
    avg_cpu_24h: Optional[float] = None
    avg_memory_24h: Optional[float] = None
    avg_disk_24h: Optional[float] = None
    peak_cpu_24h: Optional[float] = None
    metric_count_24h: Optional[int] = 0
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class VMSummaryResponse(BaseModel):
    """Schema for VM summary (used in dashboard overview)."""
    vm_id: str
    name: str
    host: Optional[str] = None
    status: str
    health_score: Optional[int] = None
    security_score: Optional[int] = None
    current_cpu: Optional[float] = None
    avg_cpu_24h: Optional[float] = None
    alert_count: Optional[int] = 0
    anomaly_detected: Optional[bool] = False

    model_config = ConfigDict(from_attributes=True)


class FleetSummaryResponse(BaseModel):
    """Schema for fleet-wide summary statistics."""
    total_vms: int
    online_vms: int
    offline_vms: int
    healthy_vms: int
    warning_vms: int
    critical_vms: int
    fleet_health_score: int
    fleet_security_score: int
    total_alerts: int
    total_vulnerabilities: int
    critical_vulnerabilities: int
    vms: List[VMSummaryResponse]


class VMUpdate(BaseModel):
    """Schema for updating VM fields."""
    status: Optional[str] = None
    host: Optional[str] = None
    current_cpu: Optional[float] = None
    current_memory: Optional[float] = None
    current_disk: Optional[float] = None
    health_score: Optional[int] = None
    security_score: Optional[int] = None
    alert_count: Optional[int] = None
    anomaly_detected: Optional[bool] = None
    avg_memory_24h: Optional[float] = None
    avg_disk_24h: Optional[float] = None
    last_anomaly_time: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)