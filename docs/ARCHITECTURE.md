# ApnaERP Architecture Overview

## Design Principles
ApnaERP is engineered following enterprise-grade software architecture principles:

- **Repository Pattern**: Abstracts data persistence mechanisms from business logic.
- **Service Layer Pattern**: Encapsulates business logic, domain rules, and orchestrations.
- **Dependency Injection**: Promotes loose coupling and facilitates automated unit & integration testing.
- **Clean Architecture & SOLID**: Layered isolation ensuring UI/Web framework and Database infrastructure depend on core abstractions.
- **Pydantic v2**: Type checking, data validation, and high-performance serialization.

## Layer Responsibilities

```
[ HTTP Requests / Clients ]
           │
           ▼
┌─────────────────────────┐
│     API Routers         │ (app/api/)
└──────────┬──────────────┘
           │
           ▼
┌─────────────────────────┐
│     Services Layer      │ (app/services/)
└──────────┬──────────────┘
           │
           ▼
┌─────────────────────────┐
│    Repositories Layer   │ (app/repositories/)
└──────────┬──────────────┘
           │
           ▼
┌─────────────────────────┐
│  Database / Persistence │ (PostgreSQL / Redis / Celery)
└─────────────────────────┘
```
