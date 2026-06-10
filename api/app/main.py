"""
FastAPI main application entry point for Project Fortify.
"""
import logging
import os
import time
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pythonjsonlogger import jsonlogger
from starlette.middleware.base import BaseHTTPMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.config import settings
from app.limiter import limiter
from app.routers import health, metrics, vms, security, optimization, ai, auth, audit
from app.audit import log_request

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
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000
        username = getattr(request.state, "username", "")
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