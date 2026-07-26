# Changelog

All notable changes to the **ApnaERP** platform will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [v0.2.1] - 2026-07-26

### Milestone 0.2.1 — Redis Infrastructure

#### Added
- **Redis Infrastructure Layer (`app/core/redis.py`)**: Implemented `RedisManager` with `redis.asyncio` connection pooling, client lifecycle management, and custom exception handling (`RedisConnectionError`, `RedisOperationError`).
- **Operation Helper Wrappers**: Added async helpers for Key/Value (`set`, `get`, `delete`, `exists`, `expire`, `ttl`, `increment`, `decrement`), Hash (`hash_get`, `hash_set`, `hash_delete`), Pub/Sub (`publish`, `subscribe`), and Admin commands (`scan`, `flushdb`, `ping`).
- **Health Telemetry (`GET /health/redis`)**: Exposed dedicated Redis health diagnostic endpoint returning status (`healthy`/`unhealthy`), latency in milliseconds, connection state, Redis version, and timestamp.
- **FastAPI Lifespan Integration (`app/core/events.py`)**: Integrated automated Redis connection pool startup and graceful shutdown into application lifespan events.
- **Docker Compose Integration**: Added `redis:7-alpine` container service with health checks (`redis-cli ping`), persistent volumes (`redis_data`), restart policy, and network isolation.
- **Architecture Decision Record**: Created `docs/adr/ADR-0001-redis-infrastructure.md`.
- **Test Suite (`tests/test_redis.py`)**: Built comprehensive pytest suite covering connection ping, CRUD operations, TTL, Hash operations, Pub/Sub, health endpoint, and connection pool resilience.

---

## [v0.2.0] - 2026-07-26

### Core Platform Infrastructure

#### Added
- **Authentication & User Management**: JWT access/refresh tokens, Bcrypt password hashing, `/auth` endpoints (`register`, `login`, `refresh`, `logout`, `me`).
- **Role-Based Access Control (RBAC)**: Flexible roles, permissions, association models, `has_permission`/`has_role` dependency injection guards, and default seed data.
- **Generic CRUD Framework**: Reusable `BaseRepository` and `BaseService` with pagination, dynamic filtering, sorting, multi-column search, and soft deletion (`SoftDeleteMixin`).
- **Enterprise Audit Logging**: Centralized `AuditLog` ORM model, `RequestContextMiddleware` tracking correlation `X-Request-ID`, non-blocking audit logging service, and Super Admin inspection endpoints (`/audit/logs`).
- **File Management Service**: Pluggable `StorageProvider` abstraction (`LocalStorageProvider`), SHA256 checksum deduplication, file validation, binary streaming downloads, and audit integration.
- **Enterprise Notification System**: `Notification` and `NotificationTemplate` ORM models, Jinja2 template engine, SMTP `EmailService` with fallback, user-isolated notification management, and Super Admin template endpoints.
