"""Redis sliding-window rate limiter with automatic in-memory fallback for local dev."""

from __future__ import annotations

import time
from collections import defaultdict, deque

import redis.asyncio as aioredis

from app.config import get_settings
from app.core.exceptions import AppError
from app.utils.logger import get_logger

settings = get_settings()
logger = get_logger("vayumesh.ratelimit")


class RateLimiter:
    def __init__(self) -> None:
        self._redis: aioredis.Redis | None = None
        self._redis_available: bool | None = None
        self._memory_windows: dict[str, deque[float]] = defaultdict(deque)

    async def _get_redis(self) -> aioredis.Redis | None:
        if self._redis_available is False:
            return None
        if self._redis is None:
            try:
                client = aioredis.from_url(
                    settings.REDIS_URL,
                    encoding="utf-8",
                    decode_responses=True,
                    socket_connect_timeout=1.0,
                )
                await client.ping()
                self._redis = client
                self._redis_available = True
                logger.info("Connected to Redis for rate limiting and grid cache.")
            except Exception:
                self._redis_available = False
                logger.warning("Redis unavailable locally; using in-memory sliding-window rate limiter.")
                return None
        return self._redis

    async def enforce_ingest_limit(
        self,
        key_hash: str,
        limit: int | None = None,
        window_sec: int | None = None,
    ) -> dict:
        max_req = limit or settings.INGEST_RATE_LIMIT_PER_MIN
        window = window_sec or settings.INGEST_RATE_WINDOW_SEC
        now = time.time()

        client = await self._get_redis()
        if client is not None:
            try:
                redis_key = f"rl:ingest:{key_hash}"
                pipe = client.pipeline()
                pipe.zremrangebyscore(redis_key, 0, now - window)
                pipe.zadd(redis_key, {f"{now:.6f}": now})
                pipe.zcard(redis_key)
                pipe.expire(redis_key, window)
                results = await pipe.execute()
                count = int(results[2])
            except Exception:
                count = self._check_memory(key_hash, now, window)
        else:
            count = self._check_memory(key_hash, now, window)

        if count > max_req:
            raise AppError(
                status_code=429,
                code="RATE_LIMIT_EXCEEDED",
                message=f"Sensor ingest rate limit exceeded ({max_req} req/{window}s).",
                details={"limit": max_req, "window_sec": window, "retry_after_sec": window},
            )
        return {"remaining": max(0, max_req - count), "limit": max_req, "window_sec": window}

    def _check_memory(self, key_hash: str, now: float, window: int) -> int:
        q = self._memory_windows[key_hash]
        cutoff = now - window
        while q and q[0] < cutoff:
            q.popleft()
        q.append(now)
        return len(q)

    def reset_memory(self) -> None:
        self._memory_windows.clear()

    async def cache_set(self, key: str, value: str, ttl_sec: int = 30) -> None:
        client = await self._get_redis()
        if client is not None:
            try:
                await client.setex(key, ttl_sec, value)
            except Exception:
                pass

    async def cache_get(self, key: str) -> str | None:
        client = await self._get_redis()
        if client is not None:
            try:
                return await client.get(key)
            except Exception:
                return None
        return None


rate_limiter = RateLimiter()
