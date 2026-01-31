"""
FastAPI main application entry point for Project Fortify.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import health
from app.routers import metrics          # Add this line

app = FastAPI(
    title="Project Fortify API",
    description="AI-assisted AI-Ops solution for infrastructure monitoring",
    version="0.1.0",
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
app.include_router(health.router, tags=["health"])
app.include_router(metrics.router)       # Add this line


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Welcome to Project Fortify API",
        "version": "0.1.0",
        "docs": "/docs"
    }