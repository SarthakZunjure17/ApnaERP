import asyncio
import pytest
from httpx import AsyncClient

from app.core.redis import RedisConnectionError, RedisOperationError, redis_manager


@pytest.mark.asyncio
async def test_redis_ping():
    """
    Test live Redis ping connectivity.
    """
    pong = await redis_manager.ping()
    assert pong is True


@pytest.mark.asyncio
async def test_redis_crud_operations():
    """
    Test Key/Value set, get, delete, exists, expire, ttl, increment, decrement operations.
    """
    key = "test:key:1"
    value = "Hello Redis"

    # Set
    assert await redis_manager.set(key, value) is True

    # Exists & Get
    assert await redis_manager.exists(key) == 1
    assert await redis_manager.get(key) == value

    # Expire & TTL
    assert await redis_manager.expire(key, 60) is True
    ttl = await redis_manager.ttl(key)
    assert 0 < ttl <= 60

    # Delete
    assert await redis_manager.delete(key) == 1
    assert await redis_manager.get(key) is None

    # Increment & Decrement
    counter_key = "test:counter"
    await redis_manager.delete(counter_key)
    
    assert await redis_manager.increment(counter_key, 5) == 5
    assert await redis_manager.decrement(counter_key, 2) == 3
    await redis_manager.delete(counter_key)


@pytest.mark.asyncio
async def test_redis_hash_operations():
    """
    Test Redis Hash operations (hash_set, hash_get, hash_delete).
    """
    hash_name = "test:hash:user1"
    await redis_manager.delete(hash_name)

    # Set
    assert await redis_manager.hash_set(hash_name, "name", "Sarthak") == 1
    assert await redis_manager.hash_set(hash_name, "role", "Admin") == 1

    # Get
    assert await redis_manager.hash_get(hash_name, "name") == "Sarthak"
    assert await redis_manager.hash_get(hash_name, "role") == "Admin"

    # Delete field
    assert await redis_manager.hash_delete(hash_name, "role") == 1
    assert await redis_manager.hash_get(hash_name, "role") is None
    await redis_manager.delete(hash_name)


@pytest.mark.asyncio
async def test_redis_pubsub_operations():
    """
    Test Redis Pub/Sub publishing and channel subscription.
    """
    channel = "test:channel:1"
    pubsub = await redis_manager.subscribe(channel)

    # Publish message
    listeners = await redis_manager.publish(channel, "Hello Channel!")
    assert listeners >= 0

    # Read message from pubsub listener
    message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
    if message:
        assert message["data"] == "Hello Channel!"

    await pubsub.unsubscribe(channel)
    await pubsub.aclose()


@pytest.mark.asyncio
async def test_redis_health_endpoint(async_client: AsyncClient):
    """
    Test GET /health/redis endpoint returning latency, connection state, version, timestamp.
    """
    response = await async_client.get("/health/redis")
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["status"] == "healthy"
    assert json_data["connection_state"] == "connected"
    assert json_data["latency_ms"] is not None
    assert "timestamp" in json_data
