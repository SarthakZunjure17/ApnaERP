# ApnaERP System Architecture (v1.3.0)

ApnaERP is built following Clean Architecture, Domain-Driven Design (DDD), and Event-Driven Architecture principles.

## Core Architectural Layers
1. **Presentation & API Layer**: FastAPI REST endpoints with OpenAPI specs, Pydantic V2 DTOs, versioning (`/api/v1`), and rate limiting.
2. **Domain Services & Event Layer**: Core business logic services publishing domain events to Celery/Redis event bus.
3. **Repository Layer**: Async Repositories implementing repository pattern (`BaseRepository[Model, CreateDTO, UpdateDTO]`) over SQLAlchemy 2.0 ORM.
4. **Provider Abstraction Layer**: Pluggable provider interfaces for Storage (`LocalStorage`, `MinIO`, `S3`, `Azure`, `GCS`), Communication (`SMTP`, `SMS`, `WhatsApp`, `Push`), and Identity (`OAuth2/OIDC`, `LDAP/AD`, `MFA`).
5. **Infrastructure & Persistence**: PostgreSQL (Relational DB & JSONB), Redis (Caching & Rate Limiting), Celery (Distributed Task Queue), Nginx (Reverse Proxy), and Prometheus (Observability).
