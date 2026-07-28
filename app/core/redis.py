import asyncio
import logging
import time
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Dict, List, Optional, Tuple, Union

import redis.asyncio as aioredis
from redis.asyncio.client import PubSub, Redis
from redis.asyncio.connection import ConnectionPool
from redis.exceptions import ConnectionError as RedisPyConnectionError, RedisError, TimeoutError as RedisPyTimeoutError

from app.core.config import settings
from app.exceptions.base import ApnaERPException

logger = logging.getLogger("app.core.redis")


class RedisConnectionError(ApnaERPException):
    """Exception raised when Redis connection fails."""
    def __init__(self, message: str = "Unable to connect to Redis server."):
        super().__init__(message=message, status_code=503, error_code="REDIS_CONNECTION_ERROR")


class RedisOperationError(ApnaERPException):
    """Exception raised when a Redis command operation fails."""
    def __init__(self, message: str = "Redis operation failed."):
        super().__init__(message=message, status_code=500, error_code="REDIS_OPERATION_ERROR")


class RedisManager:
    """
    Enterprise Redis Infrastructure Manager.
    Manages connection pooling, async client lifecycle, health checks, and operational wrappers.
    """
    def __init__(self):
        self._pool: Optional[ConnectionPool] = None
        self._client: Optional[Redis] = None

    async def init_redis(self, retries: int = 3, retry_delay: float = 1.0) -> None:
        """
        Initializes the async Redis connection pool with retry mechanism and connectivity test.
        """
        logger.info(f"[RedisManager] Initializing Redis connection pool -> {settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}")
        self._pool = ConnectionPool.from_url(
            settings.redis_url,
            max_connections=settings.REDIS_MAX_CONNECTIONS,
            socket_timeout=settings.REDIS_SOCKET_TIMEOUT,
            retry_on_timeout=settings.REDIS_RETRY_ON_TIMEOUT,
            decode_responses=True,
        )
        self._client = Redis(connection_pool=self._pool)

        # Test connectivity with retries
        for attempt in range(1, retries + 1):
            try:
                pong = await self._client.ping()
                if pong:
                    logger.info("[RedisManager] Redis connected successfully (PING -> PONG).")
                    return
            except (RedisPyConnectionError, RedisPyTimeoutError, OSError) as e:
                logger.warning(f"[RedisManager] Connection attempt {attempt}/{retries} failed: {e}")
                if attempt < retries:
                    await asyncio.sleep(retry_delay)
                else:
                    logger.error("[RedisManager] Exceeded maximum connection retries. Redis initialized in offline mode.")

    async def close_redis(self) -> None:
        """
        Gracefully closes the async Redis client and connection pool.
        """
        logger.info("[RedisManager] Closing Redis client and connection pool.")
        if self._client:
            await self._client.aclose()
            self._client = None
        if self._pool:
            await self._pool.disconnect()
            self._pool = None
        logger.info("[RedisManager] Redis connection pool closed.")

    def get_client(self) -> Redis:
        """
        Returns the active async Redis client instance.
        """
        if self._client is None:
            raise RedisConnectionError(message="Redis client is not initialized.")
        return self._client

    async def check_redis_health(self) -> Dict[str, Any]:
        """
        Executes ping and info commands to return detailed health telemetry.
        """
        timestamp = datetime.now(timezone.utc).isoformat()
        if not self._client:
            return {
                "status": "unhealthy",
                "latency_ms": None,
                "connection_state": "disconnected",
                "redis_version": None,
                "timestamp": timestamp,
            }

        start_time = time.perf_counter()
        try:
            pong = await self._client.ping()
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            
            info = {}
            try:
                info = await self._client.info(section="server")
            except Exception:
                pass

            redis_version = info.get("redis_version", "unknown") if isinstance(info, dict) else "unknown"

            return {
                "status": "healthy" if pong else "unhealthy",
                "latency_ms": latency_ms,
                "connection_state": "connected",
                "redis_version": redis_version,
                "timestamp": timestamp,
            }
        except Exception as e:
            logger.error(f"[RedisManager] Health check failure: {e}")
            return {
                "status": "unhealthy",
                "latency_ms": round((time.perf_counter() - start_time) * 1000, 2),
                "connection_state": "disconnected",
                "redis_version": None,
                "timestamp": timestamp,
                "error": str(e),
            }

    # -------------------------------------------------------------------------
    # Helper Operation Wrappers
    # -------------------------------------------------------------------------

    async def ping(self) -> bool:
        """Pings Redis server."""
        try:
            return await self.get_client().ping()
        except RedisError as e:
            raise RedisConnectionError(f"Redis ping failed: {e}")

    async def set(
        self, key: str, value: Any, ex: Optional[int] = None, px: Optional[int] = None, nx: bool = False, xx: bool = False
    ) -> bool:
        """Sets string value for key with optional expiration."""
        try:
            res = await self.get_client().set(name=key, value=value, ex=ex, px=px, nx=nx, xx=xx)
            return bool(res)
        except RedisError as e:
            raise RedisOperationError(f"Redis set failed for key '{key}': {e}")

    async def get(self, key: str) -> Optional[str]:
        """Gets string value by key."""
        try:
            return await self.get_client().get(name=key)
        except RedisError as e:
            raise RedisOperationError(f"Redis get failed for key '{key}': {e}")

    async def delete(self, *keys: str) -> int:
        """Deletes one or more keys."""
        try:
            if not keys:
                return 0
            return await self.get_client().delete(*keys)
        except RedisError as e:
            raise RedisOperationError(f"Redis delete failed for keys {keys}: {e}")

    async def delete_pattern(self, pattern: str) -> int:
        """Deletes all keys matching the given pattern using SCAN."""
        try:
            client = self.get_client()
            keys = []
            async for key in client.scan_iter(match=pattern):
                keys.append(key)
            if keys:
                return await client.delete(*keys)
            return 0
        except Exception as e:
            logger.warning(f"Redis delete_pattern failed for pattern '{pattern}': {e}")
            return 0

    async def exists(self, *keys: str) -> int:
        """Returns count of existing keys."""
        try:
            if not keys:
                return 0
            return await self.get_client().exists(*keys)
        except RedisError as e:
            raise RedisOperationError(f"Redis exists failed for keys {keys}: {e}")

    async def expire(self, key: str, time_seconds: int) -> bool:
        """Sets expiration timeout on key in seconds."""
        try:
            return bool(await self.get_client().expire(name=key, time=time_seconds))
        except RedisError as e:
            raise RedisOperationError(f"Redis expire failed for key '{key}': {e}")

    async def ttl(self, key: str) -> int:
        """Returns remaining TTL of key in seconds."""
        try:
            return await self.get_client().ttl(name=key)
        except RedisError as e:
            raise RedisOperationError(f"Redis ttl failed for key '{key}': {e}")

    async def increment(self, key: str, amount: int = 1) -> int:
        """Increments numeric key value by amount."""
        try:
            return await self.get_client().incrby(name=key, amount=amount)
        except RedisError as e:
            raise RedisOperationError(f"Redis increment failed for key '{key}': {e}")

    async def decrement(self, key: str, amount: int = 1) -> int:
        """Decrements numeric key value by amount."""
        try:
            return await self.get_client().decrby(name=key, amount=amount)
        except RedisError as e:
            raise RedisOperationError(f"Redis decrement failed for key '{key}': {e}")

    # Hash Operations
    async def hash_set(self, name: str, key: str, value: Any) -> int:
        """Sets field in hash."""
        try:
            return await self.get_client().hset(name=name, key=key, value=value)
        except RedisError as e:
            raise RedisOperationError(f"Redis hash_set failed for hash '{name}', key '{key}': {e}")

    async def hash_get(self, name: str, key: str) -> Optional[str]:
        """Gets field value from hash."""
        try:
            return await self.get_client().hget(name=name, key=key)
        except RedisError as e:
            raise RedisOperationError(f"Redis hash_get failed for hash '{name}', key '{key}': {e}")

    async def hash_delete(self, name: str, *keys: str) -> int:
        """Deletes one or more fields from hash."""
        try:
            if not keys:
                return 0
            return await self.get_client().hdel(name, *keys)
        except RedisError as e:
            raise RedisOperationError(f"Redis hash_delete failed for hash '{name}', keys {keys}: {e}")

    # Pub/Sub Operations
    async def publish(self, channel: str, message: str) -> int:
        """Publishes message to pub/sub channel."""
        try:
            return await self.get_client().publish(channel=channel, message=message)
        except RedisError as e:
            raise RedisOperationError(f"Redis publish failed on channel '{channel}': {e}")

    async def subscribe(self, *channels: str) -> PubSub:
        """Subscribes to pub/sub channels and returns PubSub listener object."""
        try:
            pubsub = self.get_client().pubsub()
            await pubsub.subscribe(*channels)
            return pubsub
        except RedisError as e:
            raise RedisOperationError(f"Redis subscribe failed on channels {channels}: {e}")

    # Maintenance & Admin Operations
    async def scan(self, cursor: int = 0, match: Optional[str] = None, count: Optional[int] = None) -> Tuple[int, List[str]]:
        """Iteratively scans keys in current DB."""
        try:
            res = await self.get_client().scan(cursor=cursor, match=match, count=count)
            return res[0], res[1]
        except RedisError as e:
            raise RedisOperationError(f"Redis scan failed: {e}")

    async def flushdb(self) -> bool:
        """Flushes current DB."""
        try:
            return bool(await self.get_client().flushdb())
        except RedisError as e:
            raise RedisOperationError(f"Redis flushdb failed: {e}")


# Singleton RedisManager instance
redis_manager = RedisManager()


async def get_redis_client() -> Redis:
    """
    Dependency injection provider returning active Redis client.
    """
    return redis_manager.get_client()
