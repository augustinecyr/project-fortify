"""
Application configuration management.
"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Database - Updated to use psycopg (version 3)
    DATABASE_URL: str = "postgresql+psycopg://fortify_user:fortify_pass@localhost:5432/fortify"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # API
    API_KEY: str = "dev-api-key-12345"
    LOG_LEVEL: str = "INFO"
    
    # Analytics
    ANOMALY_THRESHOLD: float = 0.7
    SCORE_UPDATE_INTERVAL: int = 300  # seconds
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
