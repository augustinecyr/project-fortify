"""
Redis cache client utility.
Uses a module-level singleton so the connection is reused across requests,
consistent with how SQLAlchemy's engine is managed in database.py.
"""
import json
import redis
from app.config import settings

# Module-level singleton — created once on import, reused for every request
_redis_client: redis.Redis | None = None


def get_redis_client() -> redis.Redis:
    """
    Return the shared Redis client instance.
    Initialised on first call, reused on all subsequent calls.
    """
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis_client


def cache_get(key: str) -> dict | list | None:
    """
    Retrieve and deserialise a cached value.
    Returns None if the key does not exist or Redis is unavailable.
    """
    try:
        raw = get_redis_client().get(key)
        return json.loads(raw) if raw else None
    except Exception:
        return None


def cache_set(key: str, value: dict | list, ttl: int) -> None:
    """
    Serialise and store a value with a TTL (seconds).
    Silently ignores errors so a Redis outage never breaks an endpoint.
    """
    try:
        get_redis_client().setex(key, ttl, json.dumps(value))
    except Exception:
        pass