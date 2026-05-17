"""
AI Insights router — Groq-powered infrastructure analysis.

Endpoints:
    GET    /api/v1/ai/insights             — Fleet-wide analysis (Redis TTL: 1800s)
    GET    /api/v1/ai/vm-analysis/{vm_id}  — Single-VM deep dive (Redis TTL: 600s)
    DELETE /api/v1/ai/cache                — Bust all AI cache keys

Place at: api/app/routers/ai.py
"""
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.auth.dependencies import get_current_user
from app.models.user import User
from app.db.models import VirtualMachine
from app.utils.redis_client import cache_get, cache_set, get_redis_client
from app.utils.groq_client import (
    FLEET_FALLBACK,
    FLEET_SYSTEM_PROMPT,
    VM_FALLBACK,
    VM_SYSTEM_PROMPT,
    query_llm,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/ai", tags=["ai"])


# ---------------------------------------------------------------------------
# Context builders
# ---------------------------------------------------------------------------
def _days_since(dt: datetime | None) -> int | None:
    """Return the number of days between dt and now, or None."""
    if dt is None:
        return None
    now = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return max(0, (now - dt).days)


def _build_vm_context(vm: VirtualMachine) -> Dict[str, Any]:
    """Convert a VirtualMachine ORM row into the LLM context dict."""
    trend = "stable"
    if vm.current_cpu is not None and vm.avg_cpu_24h is not None:
        delta = vm.current_cpu - vm.avg_cpu_24h
        if delta > 10:
            trend = "increasing"
        elif delta < -10:
            trend = "decreasing"

    return {
        "vm_id":                    vm.vm_id,
        "name":                     vm.name,
        "status":                   vm.status,
        "health_score":             vm.health_score,
        "security_score":           vm.security_score,
        "current_cpu":              round(vm.current_cpu, 1) if vm.current_cpu is not None else None,
        "current_memory":           round(vm.current_memory, 1) if vm.current_memory is not None else None,
        "current_disk":             round(vm.current_disk, 1) if vm.current_disk is not None else None,
        "avg_cpu_24h":              round(vm.avg_cpu_24h, 1) if vm.avg_cpu_24h is not None else None,
        "peak_cpu_24h":             round(vm.peak_cpu_24h, 1) if vm.peak_cpu_24h is not None else None,
        "alert_count":              vm.alert_count,
        "anomaly_detected":         vm.anomaly_detected,
        "open_vulnerabilities":     vm.open_vulnerabilities,
        "critical_vulnerabilities": vm.critical_vulnerabilities,
        "days_since_patch":         _days_since(vm.last_patch_date),
        "firewall_enabled":         vm.firewall_enabled,
        "trend":                    trend,
    }


# ---------------------------------------------------------------------------
# GET /api/v1/ai/insights
# ---------------------------------------------------------------------------
@router.get("/insights")
async def get_fleet_insights(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    """
    Fleet-wide AI analysis. Redis-cached for 300s.
    Returns graceful fallback if Groq is unavailable.
    """
    cache_key = "ai:fleet_insights"
    model = "llama-3.1-8b-instant"

    # Cache hit
    cached = cache_get(cache_key)
    if cached:
        logger.info("Cache hit: %s", cache_key)
        return cached

    # Fetch VMs — cap at 20 to stay within token limits
    vms = db.query(VirtualMachine).limit(20).all()
    if not vms:
        raise HTTPException(status_code=404, detail="No VMs found in database.")

    context_payload = [_build_vm_context(vm) for vm in vms]
    user_prompt = json.dumps(context_payload, indent=2)

    # Call Groq
    insights = query_llm(
        user_prompt=user_prompt,
        system_prompt=FLEET_SYSTEM_PROMPT,
        model=model,
        temperature=0.2,
        retries=1,
    )

    is_fallback = insights is None
    if is_fallback:
        logger.warning("Groq unavailable — returning fleet fallback.")
        insights = FLEET_FALLBACK

    result = {
        **insights,
        "analysis_timestamp": datetime.now(timezone.utc).isoformat(),
        "model_used": model,
        "vm_count": len(context_payload),
        "is_fallback": is_fallback,
    }

    if not is_fallback:
        cache_set(cache_key, result, ttl=1800)
        logger.info("Cached fleet insights for 1800s.")

    return result


# ---------------------------------------------------------------------------
# GET /api/v1/ai/vm-analysis/{vm_id}
# ---------------------------------------------------------------------------
@router.get("/vm-analysis/{vm_id}")
async def get_vm_analysis(vm_id: str, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    """
    Single-VM deep-dive analysis using llama3-70b. Redis-cached per vm_id for 120s.
    Returns graceful fallback if Groq is unavailable.
    """
    cache_key = f"ai:vm_analysis:{vm_id}"
    model = "llama-3.1-8b-instant"

    # Cache hit
    cached = cache_get(cache_key)
    if cached:
        logger.info("Cache hit: %s", cache_key)
        return cached

    # Fetch VM
    vm = db.query(VirtualMachine).filter(VirtualMachine.vm_id == vm_id).first()
    if not vm:
        raise HTTPException(status_code=404, detail=f"VM '{vm_id}' not found.")

    context = _build_vm_context(vm)

    # Include 24h CPU history for richer single-VM analysis
    if vm.cpu_metrics:
        sorted_metrics = sorted(vm.cpu_metrics, key=lambda m: m.timestamp, reverse=True)
        context["cpu_history_24h"] = [
            {
                "timestamp": m.timestamp.isoformat(),
                "cpu_percent": round(m.cpu_percent, 1),
            }
            for m in sorted_metrics[:50]   # 50 recent points — sufficient for trend, avoids TPM limits
        ]
    else:
        context["cpu_history_24h"] = []

    user_prompt = json.dumps(context, indent=2)

    # Call Groq
    analysis = query_llm(
        user_prompt=user_prompt,
        system_prompt=VM_SYSTEM_PROMPT,
        model=model,
        temperature=0.2,
        max_tokens=2048,
        retries=1,
    )

    is_fallback = analysis is None
    if is_fallback:
        logger.warning("Groq unavailable for VM %s — returning fallback.", vm_id)
        analysis = VM_FALLBACK

    result = {
        "vm_id": vm_id,
        "vm_name": vm.name,
        **analysis,
        "analysis_timestamp": datetime.now(timezone.utc).isoformat(),
        "model_used": model,
        "is_fallback": is_fallback,
    }

    if not is_fallback:
        cache_set(cache_key, result, ttl=600)
        logger.info("Cached VM analysis for %s for 600s.", vm_id)

    return result


# ---------------------------------------------------------------------------
# DELETE /api/v1/ai/cache — manual cache bust for the Analyse button
# ---------------------------------------------------------------------------
@router.delete("/cache")
async def clear_ai_cache(_: User = Depends(get_current_user)):
    """Clear all cached AI insights. Called by the frontend Analyse button."""
    try:
        r = get_redis_client()
        keys = r.keys("ai:*")
        if keys:
            r.delete(*keys)
            logger.info("Cleared %d AI cache keys.", len(keys))
        return {"cleared": len(keys) if keys else 0, "message": "AI cache cleared."}
    except Exception as e:
        logger.error("Failed to clear AI cache: %s", e)
        raise HTTPException(status_code=500, detail=f"Cache clear failed: {e}")