"""
FastAPI main application entry point for Project Fortify.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import health, metrics, vms, security, optimization, ai, auth

app = FastAPI(
    title="Project Fortify API",
    description="AI-assisted AI-Ops solution for infrastructure monitoring",
    version="0.7.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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