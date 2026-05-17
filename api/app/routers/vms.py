"""
Virtual Machines endpoints - ENHANCED VERSION
Now returns all VM fields including host, security, resources, etc.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta, timezone
from typing import List
from fastapi import Request
from app.db.database import get_db
from app.db.models import VirtualMachine, CPUMetric, HealthScore
from app.auth.dependencies import get_current_user
from app.models.user import User
from app.models.schemas import VMUpdate
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "analytics"))
from scoring import calculate_health_score

router = APIRouter(prefix="/api/v1", tags=["vms"])


@router.get("/vms")
async def get_all_vms(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
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
async def get_vms_summary(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    """
    Get all VMs with their complete information including health, security, and resources.
    This is optimized for dashboard overview - returns everything in one query.
    
    ENHANCED: Now returns all 30+ VM fields from the enhanced model.
    """
    vms = db.query(VirtualMachine).all()
    
    summary = []
    end_time = datetime.now(timezone.utc)
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
        
                # Fetch last 24h CPU metrics
        metrics = (
            db.query(CPUMetric)
            .filter(CPUMetric.vm_id == vm.vm_id)
            .filter(CPUMetric.timestamp >= start_time)
            .filter(CPUMetric.timestamp <= end_time)
            .order_by(CPUMetric.timestamp.asc())
            .all()
        )

        cpu_values = [m.cpu_percent for m in metrics]

        # Compute health dynamically
        health_result = calculate_health_score(cpu_values)
        computed_health = health_result["health_score"]
        
        # Get latest CPU reading
        latest_metric = (
            db.query(CPUMetric)
            .filter(CPUMetric.vm_id == vm.vm_id)
            .order_by(CPUMetric.timestamp.desc())
            .first()
        )
        
        # Determine status from VM.status field or fall back to metric availability
        status = vm.status if vm.status else ("online" if metric_count > 0 else "offline")
        last_seen = latest_metric.timestamp.isoformat() if latest_metric else None
        current_cpu = latest_metric.cpu_percent if latest_metric else vm.current_cpu
        
        # Build complete VM summary with ALL enhanced fields
        summary.append({
            # Core identification
            "vm_id": vm.vm_id,
            "name": vm.name,
            "created_at": vm.created_at.isoformat(),
            
            # Infrastructure & Host
            "host": vm.host,
            "os_version": vm.os_version,
            "status": status,
            
            # Uptime & Boot
            "uptime_hours": vm.uptime_hours,
            "last_boot_time": vm.last_boot_time.isoformat() if vm.last_boot_time else None,
            
            # Health & Security Scores
            "health_score": computed_health,
            "security_score": vm.security_score,
            
            # Current Resource Utilization
            "current_cpu": round(current_cpu, 2) if current_cpu else None,
            "current_memory": vm.current_memory,
            "current_disk": vm.current_disk,
            
            # Memory Metrics
            "memory_total_mb": vm.memory_total_mb,
            "memory_used_mb": vm.memory_used_mb,
            
            # Disk Metrics
            "disk_total_gb": vm.disk_total_gb,
            "disk_used_gb": vm.disk_used_gb,
            
            # Network Metrics
            "network_in_mbps": vm.network_in_mbps,
            "network_out_mbps": vm.network_out_mbps,
            
            # Security & Compliance
            "last_patch_date": vm.last_patch_date.isoformat() if vm.last_patch_date else None,
            "open_vulnerabilities": vm.open_vulnerabilities,
            "critical_vulnerabilities": vm.critical_vulnerabilities,
            "compliance_score": vm.compliance_score,
            "firewall_enabled": vm.firewall_enabled,
            "ssh_key_auth": vm.ssh_key_auth,
            "disk_encryption": vm.disk_encryption,
            
            # Alerts & Monitoring
            "alert_count": vm.alert_count,
            "anomaly_detected": vm.anomaly_detected,
            "last_anomaly_time": vm.last_anomaly_time.isoformat() if vm.last_anomaly_time else None,
            
            # 24-hour Aggregates
            "avg_cpu_24h": round(avg_cpu, 2) if avg_cpu else vm.avg_cpu_24h,
            "avg_memory_24h": vm.avg_memory_24h,
            "avg_disk_24h": vm.avg_disk_24h,
            "peak_cpu_24h": vm.peak_cpu_24h,
            "metric_count_24h": metric_count or vm.metric_count_24h or 0,
            
            # Metadata
            "last_seen": last_seen,
            "updated_at": vm.updated_at.isoformat() if vm.updated_at else None
        })
    
    # Calculate fleet statistics
    online_vms = [vm for vm in summary if vm["status"] == "online"]
    
    # Health distribution
    healthy = sum(1 for vm in online_vms if vm.get("health_score") and vm["health_score"] >= 80)
    warning = sum(1 for vm in online_vms if vm.get("health_score") and 60 <= vm["health_score"] < 80)
    critical = sum(1 for vm in online_vms if vm.get("health_score") and vm["health_score"] < 60)
    
    # Fleet averages
    fleet_health = sum(vm.get("health_score", 0) or 0 for vm in online_vms)
    fleet_security = sum(vm.get("security_score", 0) or 0 for vm in online_vms)
    
    return {
        "total": len(summary),
        "total_vms": len(summary),
        "online": len(online_vms),
        "online_vms": len(online_vms),
        "offline": len(summary) - len(online_vms),
        "offline_vms": len(summary) - len(online_vms),
        
        # Fleet health distribution
        "healthy_vms": healthy,
        "warning_vms": warning,
        "critical_vms": critical,
        
        # Fleet scores
        "fleet_health_score": fleet_health // len(online_vms) if online_vms else 0,
        "fleet_security_score": fleet_security // len(online_vms) if online_vms else 0,
        
        # Fleet security stats
        "total_alerts": sum(vm.get("alert_count", 0) or 0 for vm in summary),
        "total_vulnerabilities": sum(vm.get("open_vulnerabilities", 0) or 0 for vm in summary),
        "critical_vulnerabilities": sum(vm.get("critical_vulnerabilities", 0) or 0 for vm in summary),
        
        # Complete VM list
        "vms": summary
    }


@router.get("/vms/{vm_id}")
async def get_vm_details(vm_id: str, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    """
    Get detailed information for a single VM.
    Returns all fields from the VirtualMachine model.
    """
    vm = db.query(VirtualMachine).filter(VirtualMachine.vm_id == vm_id).first()
    
    if not vm:
        return {"error": f"VM '{vm_id}' not found"}, 404
    
    # Calculate 24h metrics
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(hours=24)
    
    avg_cpu = (
        db.query(func.avg(CPUMetric.cpu_percent))
        .filter(CPUMetric.vm_id == vm_id)
        .filter(CPUMetric.timestamp >= start_time)
        .filter(CPUMetric.timestamp <= end_time)
        .scalar()
    )
    
    metric_count = (
        db.query(func.count(CPUMetric.id))
        .filter(CPUMetric.vm_id == vm_id)
        .filter(CPUMetric.timestamp >= start_time)
        .filter(CPUMetric.timestamp <= end_time)
        .scalar()
    )
    
    return {
        # Core identification
        "vm_id": vm.vm_id,
        "name": vm.name,
        "created_at": vm.created_at.isoformat(),
        
        # Infrastructure
        "host": vm.host,
        "os_version": vm.os_version,
        "status": vm.status,
        
        # Uptime
        "uptime_hours": vm.uptime_hours,
        "last_boot_time": vm.last_boot_time.isoformat() if vm.last_boot_time else None,
        
        # Scores
        "health_score": vm.health_score,
        "security_score": vm.security_score,
        
        # Resources
        "current_cpu": vm.current_cpu,
        "current_memory": vm.current_memory,
        "current_disk": vm.current_disk,
        "memory_total_mb": vm.memory_total_mb,
        "memory_used_mb": vm.memory_used_mb,
        "disk_total_gb": vm.disk_total_gb,
        "disk_used_gb": vm.disk_used_gb,
        "network_in_mbps": vm.network_in_mbps,
        "network_out_mbps": vm.network_out_mbps,
        
        # Security
        "last_patch_date": vm.last_patch_date.isoformat() if vm.last_patch_date else None,
        "open_vulnerabilities": vm.open_vulnerabilities,
        "critical_vulnerabilities": vm.critical_vulnerabilities,
        "compliance_score": vm.compliance_score,
        "firewall_enabled": vm.firewall_enabled,
        "ssh_key_auth": vm.ssh_key_auth,
        "disk_encryption": vm.disk_encryption,
        
        # Alerts
        "alert_count": vm.alert_count,
        "anomaly_detected": vm.anomaly_detected,
        "last_anomaly_time": vm.last_anomaly_time.isoformat() if vm.last_anomaly_time else None,
        
        # Aggregates
        "avg_cpu_24h": round(avg_cpu, 2) if avg_cpu else vm.avg_cpu_24h,
        "avg_memory_24h": vm.avg_memory_24h,
        "avg_disk_24h": vm.avg_disk_24h,
        "peak_cpu_24h": vm.peak_cpu_24h,
        "metric_count_24h": metric_count or vm.metric_count_24h or 0,
        
        # Metadata
        "updated_at": vm.updated_at.isoformat() if vm.updated_at else None
    }


@router.post("/metrics")
async def create_cpu_metric(
    request: Request,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """
    Ingest a single CPU metric.
    Expects JSON: {
        "vm_id": "vm-001",
        "timestamp": "2026-02-11T14:32:01.123Z",
        "cpu_percent": 45.2,
        "source": "simulator"  # optional
    }
    """
    # Parse JSON body
    data = await request.json()
    
    # --- Manual validation ---
    required_fields = ["vm_id", "timestamp", "cpu_percent"]
    for field in required_fields:
        if field not in data:
            return {"error": f"Missing required field: '{field}'"}, 400
    
    vm_id = data["vm_id"]
    
    # Parse timestamp (handle both 'Z' and '+00:00' formats)
    timestamp_str = data["timestamp"]
    if timestamp_str.endswith('Z'):
        timestamp_str = timestamp_str.replace('Z', '+00:00')
    try:
        timestamp = datetime.fromisoformat(timestamp_str)
    except ValueError:
        return {"error": "Invalid timestamp format. Use ISO 8601."}, 400
    
    try:
        cpu_percent = float(data["cpu_percent"])
    except (ValueError, TypeError):
        return {"error": "cpu_percent must be a number"}, 400
    
    source = data.get("source", "api")
    
    # Optional: validate range (0-100)
    if cpu_percent < 0 or cpu_percent > 100:
        return {"error": "cpu_percent must be between 0 and 100"}, 400
    
    # --- Database operations ---
    # Verify VM exists
    vm = db.query(VirtualMachine).filter(VirtualMachine.vm_id == vm_id).first()
    if not vm:
        return {"error": f"VM '{vm_id}' not found"}, 404
    
    # Create metric record
    db_metric = CPUMetric(
        vm_id=vm_id,
        timestamp=timestamp,
        cpu_percent=cpu_percent,
        source=source
    )
    db.add(db_metric)
    db.commit()
    db.refresh(db_metric)
    
    # Update VM's current CPU
    vm.current_cpu = cpu_percent
    
    # Update 24-hour average CPU
    day_ago = datetime.now(timezone.utc) - timedelta(days=1)
    avg = db.query(func.avg(CPUMetric.cpu_percent)).filter(
        CPUMetric.vm_id == vm_id,
        CPUMetric.timestamp >= day_ago
    ).scalar()
    vm.avg_cpu_24h = round(avg, 2) if avg else None
    
    db.commit()
    
    return {"status": "success", "id": db_metric.id}

@router.patch("/vms/{vm_id}")
async def update_vm(vm_id: str, update_data: VMUpdate, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    """
    Update VM fields (partial update). Used by the metrics simulator to keep VM state current.
    """
    vm = db.query(VirtualMachine).filter(VirtualMachine.vm_id == vm_id).first()
    if not vm:
        raise HTTPException(status_code=404, detail=f"VM '{vm_id}' not found")
    
    # Update only the fields that are provided
    update_dict = update_data.model_dump(exclude_unset=True)
    for key, value in update_dict.items():
        setattr(vm, key, value)
    
    # Update the 'updated_at' timestamp if your model has it
    if hasattr(vm, 'updated_at'):
        vm.updated_at = datetime.now(timezone.utc)
    
    db.commit()
    
    return {"status": "updated", "vm_id": vm_id}