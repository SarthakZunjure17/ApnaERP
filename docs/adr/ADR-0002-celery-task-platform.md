# ADR-0002: Centralized Asynchronous Task Processing Platform (Celery)

- **Status**: Accepted
- **Deciders**: Senior Staff Backend Engineer & Core Architecture Team
- **Date**: 2026-07-26
- **Milestone**: 0.2.2 (Release v0.2.0)

---

## Context and Problem Statement

ApnaERP requires an enterprise-grade asynchronous background task processing platform to offload long-running operations (e.g., email notifications, file processing, report generation, payroll batch jobs) from synchronous HTTP request threads. 

Executing expensive tasks inside HTTP handlers causes request timeouts, degrades API throughput, and risks data loss during server restarts. We need a robust, queue-based, distributed task processing platform.

---

## Decision Drivers

1. **Clean Architecture & Separation of Concerns**: Isolate task registration, Kombu queue routing, and retry policies from FastAPI HTTP route handlers.
2. **Standardized Task Base Classes**: Provide reusable base classes (`BaseTask`, `RetryTask`, `PeriodicTask`, `LoggingTask`) enforcing structured logging, correlation tracking, and failure/retry hooks across all future ERP modules.
3. **Priority Queue Routing**: Implement Kombu priority queues (`default`, `high_priority`, `low_priority`, `periodic`) to ensure critical tasks (e.g., system health, security alerts) are processed ahead of bulk operations.
4. **Resilience & Exponential Backoff**: Enforce automatic retries with exponential backoff and jitter (`retry_backoff=True`, `max_retries=3`) for transient failures.
5. **Observability & Inspection**: Provide dedicated health inspection endpoints (`GET /health/celery` and `GET /health/workers`) for live monitoring.

---

## Decision

We decided to implement a centralized Celery task processing platform using Redis as broker and result backend:

- **Celery Application Configuration (`app/core/celery.py`)**: Configured with JSON serialization, time limits (`task_time_limit=300`, `task_soft_time_limit=240`), and auto-task discovery (`app.tasks`).
- **Reusable Base Tasks (`app/tasks/base.py`)**: `BaseTask` (lifecycle hooks), `RetryTask` (exponential backoff), `PeriodicTask` (Celery Beat scheduled jobs), and `LoggingTask` (execution timing telemetry).
- **Infrastructure System Tasks (`app/tasks/system_tasks.py`)**: `system_ping_task` and `system_health_check_task` for worker verification.
- **Worker Entrypoint (`workers/celery_worker.py`)**: Dedicated entrypoint for background worker containers (`celery -A workers.celery_worker.celery_app worker`).
- **Docker Compose Integration (`docker/docker-compose.yml`)**: Containerized `celery_worker` and `celery_beat` services connected via `apnaerp_network`.

---

## Consequences

### Positive
- Heavy background processing is completely decoupled from HTTP request threads.
- Kombu priority queue routing guarantees predictable latency SLAs for critical operations.
- Future ERP modules need only register tasks inheriting from `BaseTask`/`RetryTask`.
- Detailed worker statistics are accessible via API endpoints and Prometheus/Grafana dashboards.

### Negative / Trade-offs
- Requires running background worker processes (`celery_worker` and `celery_beat`) alongside the main API process.

---

## Alternatives Considered

1. **FastAPI `BackgroundTasks`**: Rejected because `BackgroundTasks` run in the same process/thread loop as the API, lack persistence across server restarts, and do not support distributed scaling or priority queue routing.
2. **RQ (Redis Queue)**: Rejected due to limited periodic task scheduling capabilities and fewer enterprise features compared to Celery.
