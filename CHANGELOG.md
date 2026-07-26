# Changelog

All notable changes to the **ApnaERP** platform will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [v0.2.2] - 2026-07-26

### Milestone 0.2.2 — Enterprise Task Processing Platform (Celery Infrastructure)

#### Added
- **Celery Application Infrastructure (`app/core/celery.py`)**: Configured Celery application instance (`celery_app`) with JSON serialization, time limits (`task_time_limit=300`), Kombu priority queues (`default`, `high_priority`, `low_priority`, `periodic`), and task routing.
- **Reusable Task Base Classes (`app/tasks/base.py`)**: Implemented `BaseTask` (lifecycle hooks & correlation logging), `RetryTask` (exponential backoff), `PeriodicTask` (scheduled beat tasks), and `LoggingTask` (execution timing telemetry).
- **Infrastructure System Tasks (`app/tasks/system_tasks.py`)**: Implemented `system_ping_task` and `system_health_check_task` for worker execution verification.
- **Worker Entrypoint Module (`workers/celery_worker.py`)**: Created entrypoint for worker processes (`celery -A workers.celery_worker.celery_app worker`).
- **Health Telemetry Endpoints (`app/api/v1/endpoints/health.py`)**: Added `GET /health/celery` (broker, result backend, registered tasks, queues) and `GET /health/workers` (worker inspection, active worker count, stats).
- **Docker Compose Integration (`docker/docker-compose.yml`)**: Added containerized `celery_worker` and `celery_beat` services with healthchecks, restart policies, and network isolation.
- **Architecture Decision Record**: Created `docs/adr/ADR-0002-celery-task-platform.md`.
- **Test Suite (`tests/test_celery.py`)**: Built comprehensive pytest suite covering task registration, synchronous/eager task execution, base class lifecycle, backoff retries, and health endpoints.

---

## [v0.2.1] - 2026-07-26

### Milestone 0.2.1 — Redis Infrastructure

#### Added
- **Redis Infrastructure Layer (`app/core/redis.py`)**: Implemented `RedisManager` with `redis.asyncio` connection pooling, client lifecycle management, and custom exception handling (`RedisConnectionError`, `RedisOperationError`).
- **Operation Helper Wrappers**: Added async helpers for Key/Value, Hash, Pub/Sub, and Admin commands.
- **Health Telemetry (`GET /health/redis`)**: Exposed dedicated Redis health diagnostic endpoint.
- **Architecture Decision Record**: Created `docs/adr/ADR-0001-redis-infrastructure.md`.

---

## [v0.2.0] - 2026-07-26

### Core Platform Infrastructure

#### Added
- **Authentication & User Management**: JWT access/refresh tokens, Bcrypt password hashing, `/auth` endpoints.
- **Role-Based Access Control (RBAC)**: Flexible roles, permissions, association models, and `has_permission`/`has_role` guards.
- **Generic CRUD Framework**: Reusable `BaseRepository` and `BaseService` with pagination, filtering, sorting, and soft deletion.
- **Enterprise Audit Logging**: Centralized `AuditLog` ORM model, `RequestContextMiddleware` tracking correlation `X-Request-ID`, and audit log inspection endpoints.
- **File Management Service**: Pluggable `StorageProvider` abstraction (`LocalStorageProvider`), SHA256 checksum deduplication, and file security.
- **Enterprise Notification System**: `Notification` and `NotificationTemplate` ORM models, Jinja2 template engine, SMTP `EmailService` with fallback, and user-isolated notification endpoints.
