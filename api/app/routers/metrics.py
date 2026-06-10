"""
CPU Metrics endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta, timezone
from typing import Optional

from app.db.database import get_db
from app.db.models import VirtualMachine, CPUMetric
from app.auth.dependencies import require_viewer, require_operator
from app.limiter import limiter
from app.models.user import User
from app.models.schemas import (
    CPUMetricCreate,
    CPUMetricIngestionResponse,
    CPUMetricsListResponse,
    CPUMetricResponse,
)

router = APIRouter(prefix="/api/v1", tags=["metrics"])


@router.post("/metrics/cpu", response_model=CPUMetricIngestionResponse, status_code=201)
@limiter.limit("240/minute")
async def ingest_cpu_metric(
    request: Request,
    metric: CPUMetricCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_operator),
):
    """
    Ingest a single CPU metric entry.

    Validates that the VM exists before inserting the metric, and keeps the
    VM's live reading (current_cpu) and 24h rolling average up to date so the
    fleet summary reflects ingested data without a separate update call.
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
    # The session runs with autoflush=False, so flush explicitly — the 24h
    # average below must include the metric being ingested.
    db.flush()

    # Update VM live state and 24h aggregate.
    vm.current_cpu = metric.cpu_percent
    day_ago = datetime.now(timezone.utc) - timedelta(days=1)
    avg = (
        db.query(func.avg(CPUMetric.cpu_percent))
        .filter(CPUMetric.vm_id == metric.vm_id, CPUMetric.timestamp >= day_ago)
        .scalar()
    )
    vm.avg_cpu_24h = round(float(avg), 2) if avg is not None else None

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
    limit: int = Query(1000, ge=1, le=10000),
    db: Session = Depends(get_db),
    _: User = Depends(require_viewer),
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