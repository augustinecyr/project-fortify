"""
Virtual Machines endpoints.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from typing import List

from app.db.database import get_db
from app.db.models import VirtualMachine, CPUMetric, HealthScore

router = APIRouter(prefix="/api/v1", tags=["vms"])


@router.get("/vms")
async def get_all_vms(db: Session = Depends(get_db)):
    """
    Get all virtual machines with basic information.
    """
    vms = db.query(VirtualMachine).all()
    
    return {
        "total": len(vms),
        "vms": [
            {
                "vm_id": vm.vm_id,
                "name": vm.name,
                "created_at": vm.created_at.isoformat()
            }
            for vm in vms
        ]
    }


@router.get("/vms/summary")
async def get_vms_summary(db: Session = Depends(get_db)):
    """
    Get all VMs with their latest health metrics and status.
    This is optimized for dashboard overview - returns everything in one query.
    """
    vms = db.query(VirtualMachine).all()
    
    summary = []
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(hours=24)
    
    for vm in vms:
        # Get latest metric count (last 24h)
        metric_count = (
            db.query(func.count(CPUMetric.id))
            .filter(CPUMetric.vm_id == vm.vm_id)
            .filter(CPUMetric.timestamp >= start_time)
            .filter(CPUMetric.timestamp <= end_time)
            .scalar()
        )
        
        # Get average CPU (last 24h)
        avg_cpu = (
            db.query(func.avg(CPUMetric.cpu_percent))
            .filter(CPUMetric.vm_id == vm.vm_id)
            .filter(CPUMetric.timestamp >= start_time)
            .filter(CPUMetric.timestamp <= end_time)
            .scalar()
        )
        
        # Get latest CPU reading
        latest_metric = (
            db.query(CPUMetric)
            .filter(CPUMetric.vm_id == vm.vm_id)
            .order_by(CPUMetric.timestamp.desc())
            .first()
        )
        
        # Determine status based on data availability
        if metric_count > 0:
            status = "online"
            last_seen = latest_metric.timestamp.isoformat() if latest_metric else None
            current_cpu = latest_metric.cpu_percent if latest_metric else None
        else:
            status = "offline"
            last_seen = None
            current_cpu = None
        
        summary.append({
            "vm_id": vm.vm_id,
            "name": vm.name,
            "status": status,
            "metric_count_24h": metric_count or 0,
            "avg_cpu_24h": round(avg_cpu, 2) if avg_cpu else None,
            "current_cpu": round(current_cpu, 2) if current_cpu else None,
            "last_seen": last_seen,
            "created_at": vm.created_at.isoformat()
        })
    
    return {
        "total": len(summary),
        "online": sum(1 for vm in summary if vm["status"] == "online"),
        "offline": sum(1 for vm in summary if vm["status"] == "offline"),
        "vms": summary
    }