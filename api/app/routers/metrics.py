"""
CPU Metrics endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime, timedelta, timezone
from typing import Optional

from app.db.database import get_db
from app.db.models import VirtualMachine, CPUMetric
from app.auth.dependencies import get_current_user
from app.models.user import User
from app.models.schemas import (
    CPUMetricCreate,
    CPUMetricIngestionResponse,
    CPUMetricsListResponse,
    CPUMetricResponse,
)

router = APIRouter(prefix="/api/v1", tags=["metrics"])


@router.post("/metrics/cpu", response_model=CPUMetricIngestionResponse, status_code=201)
async def ingest_cpu_metric(metric: CPUMetricCreate, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    """
    Ingest a single CPU metric entry.
    
    Validates that the VM exists before inserting the metric.
    """
    # Check if VM exists
    vm = db.query(VirtualMachine).filter(VirtualMachine.vm_id == metric.vm_id).first()
    if not vm:
        raise HTTPException(
            status_code=404,
            detail=f"VM '{metric.vm_id}' not found"
        )

    # Create metric
    db_metric = CPUMetric(
        vm_id=metric.vm_id,
        timestamp=metric.timestamp,
        cpu_percent=metric.cpu_percent,
        source=metric.source,
    )
    db.add(db_metric)
    db.commit()
    db.refresh(db_metric)

    return CPUMetricIngestionResponse(
        message="Metric ingested successfully",
        ingestion_id=db_metric.id,
        vm_id=db_metric.vm_id,
        timestamp=db_metric.timestamp,
    )


@router.get("/metrics/cpu/{vm_id}", response_model=CPUMetricsListResponse)
async def get_cpu_metrics(
    vm_id: str,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    limit: int = 1000,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """
    Retrieve CPU metrics for a specific VM.
    
    Supports filtering by time range and limiting results.
    Default time window is last 24 hours if no range specified.
    """
    # Check if VM exists
    vm = db.query(VirtualMachine).filter(VirtualMachine.vm_id == vm_id).first()
    if not vm:
        raise HTTPException(
            status_code=404,
            detail=f"VM '{vm_id}' not found"
        )

    # Default time range: last 24 hours
    if end_time is None:
        end_time = datetime.now(timezone.utc)
    if start_time is None:
        start_time = end_time - timedelta(hours=24)

    # Query metrics
    query = (
        db.query(CPUMetric)
        .filter(CPUMetric.vm_id == vm_id)
        .filter(CPUMetric.timestamp >= start_time)
        .filter(CPUMetric.timestamp <= end_time)
        .order_by(CPUMetric.timestamp.asc())
        .limit(limit)
    )

    metrics = query.all()

    return CPUMetricsListResponse(
        vm_id=vm_id,
        total_records=len(metrics),
        start_time=start_time,
        end_time=end_time,
        metrics=[CPUMetricResponse.model_validate(m) for m in metrics],
    )