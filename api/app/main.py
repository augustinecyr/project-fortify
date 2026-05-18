"""
FastAPI main application entry point for Project Fortify.
"""
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from app.limiter import limiter
from app.routers import health, metrics, vms, security, optimization, ai, auth

app = FastAPI(
    title="Project Fortify API",
    description="AI-assisted AI-Ops solution for infrastructure monitoring",
    version="0.7.0",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

ALLOWED_ORIGINS = os.getenv(
    "CORS_ALLOWED_ORIGINS",
    "http://localhost:8501,http://frontend:8501"
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
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

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Welcome to Project Fortify API",
        "version": "0.7.0",
        "docs": "/docs"
    }