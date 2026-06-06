"""
Audit-trail endpoint.

Exposes the persisted security audit log (authentication, authorization
denials, and state changes) for review. Read access is gated at the operator
level so operators and admins can review activity; viewers cannot.
"""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import AuditLog
from app.models.user import User
from app.models.schemas import AuditLogListResponse
from app.auth.dependencies import require_operator

router = APIRouter(prefix="/api/v1", tags=["audit"])


@router.get("/audit", response_model=AuditLogListResponse)
async def list_audit_events(
    db: Session = Depends(get_db),
    _: User = Depends(require_operator),
    limit: int = Query(50, ge=1, le=200, description="Page size (max 200)"),
    offset: int = Query(0, ge=0, description="Rows to skip"),
    event: Optional[str] = Query(None, description="Filter by exact event type"),
    actor: Optional[str] = Query(None, description="Filter by acting username"),
    since: Optional[datetime] = Query(None, description="Only events at/after this time"),
    until: Optional[datetime] = Query(None, description="Only events at/before this time"),
):
    """Return audit entries, newest first, with optional filters and paging."""
    query = db.query(AuditLog)
    if event:
        query = query.filter(AuditLog.event == event)
    if actor:
        query = query.filter(AuditLog.actor == actor)
    if since:
        query = query.filter(AuditLog.timestamp >= since)
    if until:
        query = query.filter(AuditLog.timestamp <= until)

    total = query.count()
    entries = (
        query.order_by(AuditLog.timestamp.desc(), AuditLog.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return AuditLogListResponse(total=total, limit=limit, offset=offset, entries=entries)
