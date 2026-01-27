"""
Health check endpoints.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db.database import get_db

router = APIRouter()


@router.get("/health")
async def health_check():
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "service": "Project Fortify API"
    }


@router.get("/api/v1/status")
async def system_status(db: Session = Depends(get_db)):
    """
    System status endpoint with database connectivity check.
    """
    # Test database connection
    try:
        db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    return {
        "status": "operational",
        "database": db_status,
        "version": "0.1.0"
    }