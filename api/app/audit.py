import logging

audit_logger = logging.getLogger("fortify.audit")


def _persist(event: str, *, actor: str = "", role: str = "", target: str = "",
             detail: str = "", ip: str = "", success=None) -> None:
    """
    Best-effort persistence of a security event to the audit_logs table.

    Auditing must never break the request path, so any failure here is
    swallowed — the stdout log line (emitted by the callers below) remains the
    fallback record. Each write uses its own short-lived session so the audit
    entry is independent of the caller's transaction (the attempt is recorded
    even if the business transaction later rolls back).
    """
    try:
        from app.db.database import SessionLocal
        from app.db.models import AuditLog
        db = SessionLocal()
        try:
            db.add(AuditLog(
                event=event,
                actor=actor or None,
                role=role or None,
                target=target or None,
                detail=detail or None,
                ip=ip or None,
                success=success,
            ))
            db.commit()
        finally:
            db.close()
    except Exception:
        audit_logger.warning("", extra={"event": "audit_persist_failed", "failed_event": event})


def log_auth_event(event: str, username: str, success: bool, ip: str = "", role: str = "") -> None:
    """Authentication / authorization event — logged to stdout and persisted."""
    audit_logger.info("", extra={
        "event": event,
        "username": username,
        "success": success,
        "ip": ip,
    })
    _persist(event, actor=username, role=role, ip=ip, success=success)


def log_action(event: str, username: str, target: str = "", detail: str = "", ip: str = "") -> None:
    """Audit a security-relevant state change, attributed to the acting user."""
    audit_logger.info("", extra={
        "event": event,
        "username": username,
        "target": target,
        "detail": detail,
    })
    _persist(event, actor=username, target=target, detail=detail, ip=ip)


def log_request(method: str, path: str, status_code: int, duration_ms: float, username: str = "") -> None:
    """Per-request access log. Stdout only — not stored in the audit table."""
    audit_logger.info("", extra={
        "event": "api_request",
        "method": method,
        "path": path,
        "status_code": status_code,
        "duration_ms": round(duration_ms, 2),
        "username": username,
    })
