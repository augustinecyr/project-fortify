"""
Health check and VM health scoring endpoints.
"""
import sys
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime, timedelta

from app.db.database import get_db
from app.db.models import VirtualMachine, CPUMetric

# Add analytics to path
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "analytics"))
from scoring import calculate_health_score

router = APIRouter()


@router.get("/health")
async def health_check():
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "service": "Project Fortify API"
    }


@router.get("/api/v1/status")
async def system_status(db: Session = Depends(get_db)):
    """
    System status endpoint with database connectivity check.
    """
    try:
        db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"

    return {
        "status": "operational",
        "database": db_status,
        "version": "0.1.0"
    }


@router.get("/api/v1/health/{vm_id}")
async def get_vm_health(vm_id: str, db: Session = Depends(get_db)):
    """
    Get health score for a specific VM.
    Fetches last 24 hours of CPU metrics and calculates health score.
    """
    # Check if VM exists
    vm = db.query(VirtualMachine).filter(VirtualMachine.vm_id == vm_id).first()
    if not vm:
        raise HTTPException(
            status_code=404,
            detail=f"VM '{vm_id}' not found"
        )

    # Fetch last 24 hours of CPU metrics
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(hours=24)

    metrics = (
        db.query(CPUMetric)
        .filter(CPUMetric.vm_id == vm_id)
        .filter(CPUMetric.timestamp >= start_time)
        .filter(CPUMetric.timestamp <= end_time)
        .order_by(CPUMetric.timestamp.asc())
        .all()
    )

    # Extract CPU values
    cpu_values = [m.cpu_percent for m in metrics]

    # Calculate health score
    result = calculate_health_score(cpu_values)

    return {
        "vm_id": vm_id,
        "vm_name": vm.name,
        "health_score": result["health_score"],
        "computed_at": end_time.isoformat(),
        "components": result["components"],
        "anomaly_details": result["anomaly_details"],
        "metrics_analyzed": len(cpu_values),
    }