"""
Optimization endpoints.
Provides rule-based VM resource recommendations for the Cost Optimization dashboard page.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import VirtualMachine
from app.utils.redis_client import cache_get, cache_set

router = APIRouter(prefix="/api/v1", tags=["optimization"])

CACHE_KEY = "optimization:recommendations"
CACHE_TTL = 120  # seconds

# ---- Thresholds ----
CPU_UNDERUSE_THRESHOLD = 20.0   # % — candidate for downsizing
CPU_OVERUSE_THRESHOLD = 85.0    # % — candidate for scaling up
DISK_CRITICAL_THRESHOLD = 90.0  # % — disk cleanup needed


def _build_recommendations(vms: list[VirtualMachine]) -> list[dict]:
    """
    Apply rule logic to each VM and return a list of recommendation objects.
    A single VM can produce multiple recommendations (e.g. both overloaded CPU and full disk).
    Rules are applied against current snapshot values stored on the VirtualMachine model.
    """
    recommendations = []

    for vm in vms:
        cpu = vm.current_cpu
        disk = vm.current_disk
        status = vm.status or "online"

        # Rule 1 — Under-provisioned CPU (wasteful spend)
        if cpu is not None and cpu < CPU_UNDERUSE_THRESHOLD:
            recommendations.append({
                "vm_id": vm.vm_id,
                "vm_name": vm.name,
                "recommendation_type": "downsize",
                "reason": (
                    f"CPU utilization is only {cpu:.1f}% — well below the {CPU_UNDERUSE_THRESHOLD}% "
                    "threshold. Consider downsizing to a smaller instance type or consolidating workloads."
                ),
                "severity": "info",
                "current_cpu": cpu,
                "current_disk": disk,
            })

        # Rule 2 — Over-provisioned CPU (performance risk)
        if cpu is not None and cpu > CPU_OVERUSE_THRESHOLD:
            recommendations.append({
                "vm_id": vm.vm_id,
                "vm_name": vm.name,
                "recommendation_type": "scale_up",
                "reason": (
                    f"CPU utilization is {cpu:.1f}%, exceeding the {CPU_OVERUSE_THRESHOLD}% warning threshold. "
                    "Consider scaling up to a larger instance or distributing the workload."
                ),
                "severity": "warning",
                "current_cpu": cpu,
                "current_disk": disk,
            })

        # Rule 3 — Disk nearly full (operational risk)
        if disk is not None and disk > DISK_CRITICAL_THRESHOLD:
            recommendations.append({
                "vm_id": vm.vm_id,
                "vm_name": vm.name,
                "recommendation_type": "disk_cleanup",
                "reason": (
                    f"Disk usage is at {disk:.1f}%, above the {DISK_CRITICAL_THRESHOLD}% critical threshold. "
                    "Perform disk cleanup, archive old data, or expand storage."
                ),
                "severity": "critical",
                "current_cpu": cpu,
                "current_disk": disk,
            })

        # Rule 4 — VM offline with zero uptime (idle resource)
        if status == "offline" and (vm.uptime_hours is None or vm.uptime_hours == 0):
            recommendations.append({
                "vm_id": vm.vm_id,
                "vm_name": vm.name,
                "recommendation_type": "review_offline",
                "reason": (
                    f"{vm.name} is currently offline with no recorded uptime. "
                    "Verify whether this VM is still needed or can be decommissioned."
                ),
                "severity": "info",
                "current_cpu": cpu,
                "current_disk": disk,
            })

    # Sort: critical first, then warning, then info
    severity_order = {"critical": 0, "warning": 1, "info": 2}
    recommendations.sort(key=lambda r: severity_order.get(r["severity"], 3))

    return recommendations


@router.get("/optimization/recommendations")
async def get_optimization_recommendations(db: Session = Depends(get_db)):
    """
    Rule-based VM optimization recommendations for the Cost Optimization page.

    Rules applied per VM:
    - CPU < 20%  → downsize suggestion (info)
    - CPU > 85%  → scale-up suggestion (warning)
    - Disk > 90% → disk cleanup required (critical)
    - Offline + zero uptime → review if VM is still needed (info)

    Also returns fleet-level utilization summary for the KPI cards.

    Cached in Redis for 120 seconds.
    """
    cached = cache_get(CACHE_KEY)
    if cached:
        return cached

    vms = db.query(VirtualMachine).all()

    if not vms:
        return {
            "recommendations": [],
            "total_recommendations": 0,
            "fleet_summary": {},
        }

    recommendations = _build_recommendations(vms)

    # ---- Fleet utilization summary (for KPI cards) ----
    online_vms = [vm for vm in vms if vm.status == "online"]

    cpu_values = [vm.current_cpu for vm in online_vms if vm.current_cpu is not None]
    mem_values = [vm.current_memory for vm in online_vms if vm.current_memory is not None]
    disk_values = [vm.current_disk for vm in online_vms if vm.current_disk is not None]

    fleet_summary = {
        "avg_cpu": round(sum(cpu_values) / len(cpu_values), 1) if cpu_values else 0,
        "avg_memory": round(sum(mem_values) / len(mem_values), 1) if mem_values else 0,
        "avg_disk": round(sum(disk_values) / len(disk_values), 1) if disk_values else 0,
        "overprovisioned_count": sum(1 for v in online_vms if v.current_cpu is not None and v.current_cpu < CPU_UNDERUSE_THRESHOLD),
        "underprovisioned_count": sum(1 for v in online_vms if v.current_cpu is not None and v.current_cpu > CPU_OVERUSE_THRESHOLD),
        "vms": [
            {
                "vm_id": vm.vm_id,
                "name": vm.name,
                "status": vm.status,
                "current_cpu": vm.current_cpu,
                "current_memory": vm.current_memory,
                "current_disk": vm.current_disk,
                "avg_cpu_24h": vm.avg_cpu_24h,
            }
            for vm in vms
        ],
    }

    result = {
        "recommendations": recommendations,
        "total_recommendations": len(recommendations),
        "fleet_summary": fleet_summary,
    }

    cache_set(CACHE_KEY, result, CACHE_TTL)
    return result