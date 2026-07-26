# ADR-0001: Centralized Redis Infrastructure Integration

- **Status**: Accepted
- **Deciders**: Senior Staff Backend Engineer & Core Architecture Team
- **Date**: 2026-07-26
- **Milestone**: 0.2.1 (Release v0.2.0)

---

## Context and Problem Statement

ApnaERP requires an asynchronous, high-performance, in-memory data store infrastructure to support future platform requirements such as caching, rate-limiting, session management, Pub/Sub event broadcasting, and Celery background task queuing. 

Directly coupling business services to raw Redis drivers creates anti-patterns, duplicate connection pools, and unhandled connection failures. We need a centralized, decoupled Redis connection manager and operations wrapper interface.

---

## Decision Drivers

1. **Clean Architecture**: Isolate all Redis connection handling, lifecycle management, and error handling into `app/core/redis.py`.
2. **Asynchronous First**: Use `redis.asyncio` with explicit `ConnectionPool` management to prevent thread starvation under high concurrency.
3. **Resilience & Telemetry**: Provide automatic retry logic during startup, graceful teardown on shutdown, and a dedicated health check endpoint (`GET /health/redis`).
4. **Environment-Driven Configuration**: Configure host, port, credentials, and connection limits strictly via environment variables.

---

## Decision

We decided to implement a centralized `RedisManager` in `app/core/redis.py` utilizing `redis.asyncio`:

- **Connection Pooling**: Managed via `redis.asyncio.ConnectionPool` with configurable `max_connections` (default 20) and socket timeouts.
- **Lifecycle Integration**: Integrated into FastAPI's `lifespan` context manager (`app/core/events.py`).
- **Operation Wrappers**: Provided helper methods (`get`, `set`, `delete`, `exists`, `expire`, `ttl`, `increment`, `decrement`, `hash_get`, `hash_set`, `hash_delete`, `publish`, `subscribe`, `scan`, `flushdb`, `ping`).
- **Telemetry**: Implemented `check_redis_health()` and `GET /health/redis` endpoint measuring latency, version, and connection state.

---

## Consequences

### Positive
- Centralized connection pooling prevents connection leakage across requests.
- Business services will consume Redis via clean dependency injection (`get_redis_client`) or wrapper methods without importing raw driver internals.
- System diagnostics are exposed via standard health endpoints.

### Negative / Trade-offs
- Adds a required infrastructure component to local development stacks (managed seamlessly via Docker Compose).

---

## Alternatives Considered

1. **Direct `aioredis` Calls in Route Handlers**: Rejected due to tight coupling, lack of connection pool reuse, and code duplication.
2. **Synchronous `redis-py`**: Rejected as blocking I/O calls degrade FastAPI async event loop performance.
