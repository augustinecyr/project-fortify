import json
import logging
import time
from datetime import datetime, timezone

audit_logger = logging.getLogger("fortify.audit")


def log_auth_event(event: str, username: str, success: bool, ip: str = "") -> None:
    audit_logger.info(json.dumps({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event": event,
        "username": username,
        "success": success,
        "ip": ip,
    }))


def log_request(method: str, path: str, status_code: int, duration_ms: float, username: str = "") -> None:
    audit_logger.info(json.dumps({
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event": "api_request",
        "method": method,
        "path": path,
        "status_code": status_code,
        "duration_ms": round(duration_ms, 2),
        "username": username,
    }))
