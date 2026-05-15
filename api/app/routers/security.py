"""
Security endpoints.
Provides fleet-wide security aggregates for the Security Posture dashboard page.
"""
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db.database import get_db
from app.db.models import VirtualMachine
from app.utils.redis_client import cache_get, cache_set

router = APIRouter(prefix="/api/v1", tags=["security"])

CACHE_KEY = "security:summary"
CACHE_TTL = 60  # seconds


@router.get("/security/summary")
async def get_security_summary(db: Session = Depends(get_db)):
    """
    Fleet-wide security aggregates for the Security Posture page.

    Returns:
    - Average security score across all VMs
    - Total open and critical vulnerabilities
    - Count of VMs with firewall disabled
    - Patch lag distribution bucketed into four time bands
    - Per-VM security detail list for the sortable table

    Cached in Redis for 60 seconds.
    """
    cached = cache_get(CACHE_KEY)
    if cached:
        return cached

    vms = db.query(VirtualMachine).all()

    if not vms:
        return {
            "avg_security_score": 0,
            "total_open_vulnerabilities": 0,
            "total_critical_vulnerabilities": 0,
            "firewall_disabled_count": 0,
            "patch_lag_distribution": {
                "0_7_days": 0,
                "8_30_days": 0,
                "31_90_days": 0,
                "90_plus_days": 0,
            },
            "vms": [],
        }

    now = datetime.now(timezone.utc)

    # ---- Aggregates ----
    security_scores = [vm.security_score for vm in vms if vm.security_score is not None]
    avg_security_score = round(sum(security_scores) / len(security_scores), 1) if security_scores else 0

    total_open_vulns = sum(vm.open_vulnerabilities or 0 for vm in vms)
    total_critical_vulns = sum(vm.critical_vulnerabilities or 0 for vm in vms)
    firewall_disabled_count = sum(1 for vm in vms if vm.firewall_enabled is False)

    # ---- Patch lag distribution ----
    patch_lag = {"0_7_days": 0, "8_30_days": 0, "31_90_days": 0, "90_plus_days": 0}

    for vm in vms:
        if vm.last_patch_date is None:
            patch_lag["90_plus_days"] += 1
            continue
        # Postgres DateTime columns are naive — attach UTC before comparing
        patch_date = vm.last_patch_date.replace(tzinfo=timezone.utc)
        days_since_patch = (now - patch_date).days
        if days_since_patch <= 7:
            patch_lag["0_7_days"] += 1
        elif days_since_patch <= 30:
            patch_lag["8_30_days"] += 1
        elif days_since_patch <= 90:
            patch_lag["31_90_days"] += 1
        else:
            patch_lag["90_plus_days"] += 1

    # ---- Per-VM security detail (for frontend table) ----
    vm_list = []
    for vm in sorted(vms, key=lambda v: (v.security_score or 0)):  # worst first
        days_since_patch = None
        if vm.last_patch_date:
            patch_date = vm.last_patch_date.replace(tzinfo=timezone.utc)
            days_since_patch = (now - patch_date).days

        # Derive score tier for the distribution chart
        score = vm.security_score or 0
        if score >= 80:
            score_tier = "high"
        elif score >= 60:
            score_tier = "medium"
        else:
            score_tier = "low"

        vm_list.append({
            "vm_id": vm.vm_id,
            "name": vm.name,
            "status": vm.status,
            "security_score": vm.security_score,
            "score_tier": score_tier,
            "open_vulnerabilities": vm.open_vulnerabilities or 0,
            "critical_vulnerabilities": vm.critical_vulnerabilities or 0,
            "firewall_enabled": vm.firewall_enabled,
            "ssh_key_auth": vm.ssh_key_auth,
            "disk_encryption": vm.disk_encryption,
            "compliance_score": vm.compliance_score,
            "last_patch_date": vm.last_patch_date.isoformat() if vm.last_patch_date else None,
            "days_since_patch": days_since_patch,
        })

    result = {
        "avg_security_score": avg_security_score,
        "total_open_vulnerabilities": total_open_vulns,
        "total_critical_vulnerabilities": total_critical_vulns,
        "firewall_disabled_count": firewall_disabled_count,
        "patch_lag_distribution": patch_lag,
        "vms": vm_list,
    }

    cache_set(CACHE_KEY, result, CACHE_TTL)
    return result