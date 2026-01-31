"""
Pydantic schemas for request and response validation.
"""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List


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


# --- VM Schemas ---

class VMResponse(BaseModel):
    """Schema for VM response."""
    vm_id: str
    name: str
    created_at: datetime

    class Config:
        from_attributes = True