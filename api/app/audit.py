import logging

audit_logger = logging.getLogger("fortify.audit")


def log_auth_event(event: str, username: str, success: bool, ip: str = "") -> None:
    audit_logger.info("", extra={
        "event": event,
        "username": username,
        "success": success,
        "ip": ip,
    })


def log_action(event: str, username: str, target: str = "", detail: str = "") -> None:
    """Audit a security-relevant state change, attributed to the acting user."""
    audit_logger.info("", extra={
        "event": event,
        "username": username,
        "target": target,
        "detail": detail,
    })


def log_request(method: str, path: str, status_code: int, duration_ms: float, username: str = "") -> None:
    audit_logger.info("", extra={
        "event": "api_request",
        "method": method,
        "path": path,
        "status_code": status_code,
        "duration_ms": round(duration_ms, 2),
        "username": username,
    })
