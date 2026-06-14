"""
FastAPI main application entry point for Project Fortify.
"""
import logging
import os
import time
import uuid
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pythonjsonlogger import jsonlogger
from sqlalchemy.exc import IntegrityError, OperationalError, SQLAlchemyError
from starlette.middleware.base import BaseHTTPMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.config import settings
from app.limiter import limiter
from app.routers import health, metrics, vms, security, optimization, ai, auth, audit
from app.audit import log_request

logger = logging.getLogger(__name__)

# Configure root logger to emit structured JSON so all uvicorn and app log
# lines are parseable by log aggregators without regex.
_handler = logging.StreamHandler()
_handler.setFormatter(jsonlogger.JsonFormatter(
    fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
    rename_fields={"asctime": "timestamp", "levelname": "level", "name": "logger"},
))
logging.root.setLevel(logging.INFO)
logging.root.handlers = [_handler]

# Apply JSON formatter to uvicorn loggers so their access/error lines are
# also structured JSON rather than uvicorn's default plain-text format.
for _name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
    _uvicorn_logger = logging.getLogger(_name)
    _uvicorn_logger.handlers = [_handler]
    _uvicorn_logger.propagate = False

# JWTs signed with the shipped default key can be forged by anyone who has
# read the source — refuse to let that slip into a real deployment silently.
if settings.SECRET_KEY == "change-me-in-production":
    logging.getLogger(__name__).critical(
        "SECRET_KEY is set to the insecure default — JWT tokens are forgeable. "
        "Set SECRET_KEY in the environment before any non-local deployment."
    )

app = FastAPI(
    title="Project Fortify API",
    description="AI-assisted AI-Ops solution for infrastructure monitoring",
    version="1.1.1",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


def _error_response(request: Request, status_code: int, message: str) -> JSONResponse:
    """Consistent JSON error envelope. Carries the request id so a client can
    quote it when reporting a failure, and never echoes raw internals."""
    request_id = getattr(request.state, "request_id", None)
    return JSONResponse(
        status_code=status_code,
        content={"detail": message, "request_id": request_id},
        headers={"X-Request-ID": request_id} if request_id else None,
    )


@app.exception_handler(IntegrityError)
async def _integrity_error_handler(request: Request, exc: IntegrityError):
    # e.g. a concurrent insert losing the race on a unique constraint after a
    # check-then-insert — surface as a conflict rather than an opaque 500.
    logger.warning(
        "Integrity error on %s %s [request_id=%s]: %s",
        request.method, request.url.path, getattr(request.state, "request_id", None), exc,
    )
    return _error_response(
        request, 409,
        "The operation conflicts with existing data (a uniqueness or integrity constraint).",
    )


@app.exception_handler(OperationalError)
async def _operational_error_handler(request: Request, exc: OperationalError):
    # DB unreachable / connection dropped — a dependency problem, not a 500.
    logger.error(
        "Database unavailable on %s %s [request_id=%s]: %s",
        request.method, request.url.path, getattr(request.state, "request_id", None), exc,
    )
    return _error_response(
        request, 503,
        "Service temporarily unavailable — a backend dependency could not be reached.",
    )


@app.exception_handler(SQLAlchemyError)
async def _sqlalchemy_error_handler(request: Request, exc: SQLAlchemyError):
    logger.error(
        "Database error on %s %s [request_id=%s]: %s",
        request.method, request.url.path, getattr(request.state, "request_id", None), exc,
    )
    return _error_response(request, 500, "A database error occurred.")


@app.exception_handler(Exception)
async def _unhandled_error_handler(request: Request, exc: Exception):
    # Last line of defence: log the full trace server-side, return a generic
    # body so internals (paths, driver strings) never reach the client.
    logger.exception(
        "Unhandled error on %s %s [request_id=%s]",
        request.method, request.url.path, getattr(request.state, "request_id", None),
    )
    return _error_response(request, 500, "An unexpected error occurred.")


_DOCS_PATHS = {"/docs", "/redoc", "/openapi.json"}

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        # HSTS only takes effect once the API is served over HTTPS (browsers
        # ignore it on plain HTTP); set here so a TLS-terminating deployment
        # is covered without code changes.
        response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains; preload"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=(), payment=()"
        response.headers["Cache-Control"] = "no-store, no-cache"
        if request.url.path not in _DOCS_PATHS:
            response.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
        return response


class RequestAuditMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Correlation id: one per request, echoed in the response header and in
        # error envelopes so a client-visible failure can be tied to a log line.
        request.state.request_id = uuid.uuid4().hex
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000
        username = getattr(request.state, "username", "")
        response.headers["X-Request-ID"] = request.state.request_id
        log_request(request.method, request.url.path, response.status_code, duration_ms, username)
        return response


app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestAuditMiddleware)

ALLOWED_ORIGINS = os.getenv(
    "CORS_ALLOWED_ORIGINS",
    "http://localhost:8501,http://frontend:8501"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

# Include routers
app.include_router(auth.router)
app.include_router(health.router, tags=["health"])
app.include_router(metrics.router)
app.include_router(vms.router)
app.include_router(security.router, tags=["security"])
app.include_router(optimization.router, tags=["optimization"])
app.include_router(ai.router)
app.include_router(audit.router)

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Welcome to Project Fortify API",
        "version": "1.1.1",
        "docs": "/docs"
    }