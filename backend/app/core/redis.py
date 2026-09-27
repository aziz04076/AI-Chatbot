import time
import json
import logging
from typing import Optional, Any
from app.config import settings

logger = logging.getLogger("NexusAI-Cache")

class CacheAndRateLimiter:
    """
    Unified Redis caching and rate-limiting system with
    transparent in-memory fallback for local development or disconnected mode.
    """
    def __init__(self):
        self._memory_cache = {}
        self._rate_limits = {}
        self._redis_client = None
        self._is_redis_connected = False

    async def initialize(self):
        try:
            import redis.asyncio as aioredis
            self._redis_client = aioredis.from_url(
                settings.REDIS_URL,
                decode_responses=True,
                socket_timeout=2.0
            )
            await self._redis_client.ping()
            self._is_redis_connected = True
            logger.info("Connected to Redis instance successfully.")
        except Exception as e:
            self._is_redis_connected = False
            logger.info("Redis not detected or unavailable. Using resilient high-speed In-Memory cache & rate limiter fallback.")

    async def get(self, key: str) -> Optional[str]:
        if self._is_redis_connected and self._redis_client:
            try:
                return await self._redis_client.get(key)
            except Exception:
                pass
        
        # Memory fallback with TTL check
        item = self._memory_cache.get(key)
        if item:
            val, expire_at = item
            if time.time() < expire_at:
                return val
            del self._memory_cache[key]
        return None

    async def set(self, key: str, value: str, expire_seconds: Optional[int] = None):
        ttl = expire_seconds or settings.CACHE_EXPIRATION_SECONDS
        if self._is_redis_connected and self._redis_client:
            try:
                await self._redis_client.set(key, value, ex=ttl)
                return
            except Exception:
                pass

        # Memory fallback
        self._memory_cache[key] = (value, time.time() + ttl)

    async def is_rate_limited(self, identifier: str, max_requests: int = 60, window_seconds: int = 60) -> bool:
        """
        Token-bucket sliding window rate limiter.
        Returns True if request exceeds limit.
        """
        now = time.time()
        key = f"rate_limit:{identifier}"

        if self._is_redis_connected and self._redis_client:
            try:
                pipe = self._redis_client.pipeline()
                pipe.zremrangebyscore(key, 0, now - window_seconds)
                pipe.zadd(key, {str(now): now})
                pipe.zcard(key)
                pipe.expire(key, window_seconds)
                _, _, count, _ = await pipe.execute()
                return count > max_requests
            except Exception:
                pass

        # Memory fallback sliding window
        window_start = now - window_seconds
        records = self._rate_limits.get(identifier, [])
        valid_records = [t for t in records if t > window_start]
        valid_records.append(now)
        self._rate_limits[identifier] = valid_records
        return len(valid_records) > max_requests

cache_manager = CacheAndRateLimiter()
