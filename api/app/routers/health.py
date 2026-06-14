"""
Health check and VM health scoring endpoints.
"""
import logging
import sys
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

from app.db.database import get_db
from app.db.models import VirtualMachine, CPUMetric
from app.auth.dependencies import require_viewer
from app.models.user import User

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
async def system_status(response: Response, db: Session = Depends(get_db)):
    """
    System status endpoint with database connectivity check.

    Returns 503 when the database is unreachable so orchestrators and load
    balancers can detect an unhealthy instance. The raw exception is logged
    server-side only — never echoed to the client.
    """
    try:
        db.execute(text("SELECT 1"))
        return {
            "status": "operational",
            "database": "connected",
            "version": "1.1.1",
        }
    except Exception as e:
        logger.error("Database connectivity check failed: %s", e)
        response.status_code = 503
        return {
            "status": "degraded",
            "database": "disconnected",
            "version": "1.1.1",
        }


@router.get("/api/v1/health/{vm_id}")
async def get_vm_health(vm_id: str, db: Session = Depends(get_db), _: User = Depends(require_viewer)):
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
    end_time = datetime.now(timezone.utc)
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