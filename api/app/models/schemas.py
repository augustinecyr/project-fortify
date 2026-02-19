"""
Pydantic schemas for request and response validation.
Enhanced with comprehensive VM monitoring fields.
"""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List


# --- CPU Metrics Schemas (unchanged) ---

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

    class Config:
        from_attributes = True


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
    # Core identification
    vm_id: str
    name: str
    created_at: datetime
    
    # Infrastructure & host
    host: Optional[str] = None
    os_version: Optional[str] = None
    status: Optional[str] = "online"
    
    # Uptime & boot
    uptime_hours: Optional[float] = None
    last_boot_time: Optional[datetime] = None
    
    # Health & security scores
    health_score: Optional[int] = None
    security_score: Optional[int] = None
    
    # Current resource snapshot
    current_cpu: Optional[float] = None
    current_memory: Optional[float] = None
    current_disk: Optional[float] = None
    
    # Memory metrics
    memory_total_mb: Optional[int] = None
    memory_used_mb: Optional[int] = None
    
    # Disk metrics
    disk_total_gb: Optional[int] = None
    disk_used_gb: Optional[int] = None
    
    # Network metrics
    network_in_mbps: Optional[float] = None
    network_out_mbps: Optional[float] = None
    
    # Security & compliance
    last_patch_date: Optional[datetime] = None
    open_vulnerabilities: Optional[int] = 0
    critical_vulnerabilities: Optional[int] = 0
    compliance_score: Optional[str] = None
    firewall_enabled: Optional[bool] = True
    ssh_key_auth: Optional[bool] = True
    disk_encryption: Optional[bool] = False
    
    # Alerts & monitoring
    alert_count: Optional[int] = 0
    anomaly_detected: Optional[bool] = False
    last_anomaly_time: Optional[datetime] = None
    
    # 24-hour aggregates
    avg_cpu_24h: Optional[float] = None
    avg_memory_24h: Optional[float] = None
    avg_disk_24h: Optional[float] = None
    peak_cpu_24h: Optional[float] = None
    metric_count_24h: Optional[int] = 0
    
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


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

    class Config:
        from_attributes = True


class FleetSummaryResponse(BaseModel):
    """Schema for fleet-wide summary statistics."""
    total_vms: int
    online_vms: int
    offline_vms: int
    healthy_vms: int  # health_score >= 80
    warning_vms: int  # health_score 60-79
    critical_vms: int  # health_score < 60
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
    
    class Config:
        from_attributes = True