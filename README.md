# ApnaERP - Enterprise Resource Planning Backend API

[![FastAPI](https://img.shields.io/badge/FastAPI-0.111+-009688.svg?style=flat&logo=FastAPI&logoColor=white)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB.svg?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![SQLAlchemy 2.0](https://img.shields.io/badge/SQLAlchemy-2.0+-D71F00.svg?style=flat&logo=sqlalchemy&logoColor=white)](https://www.sqlalchemy.org/)
[![Pydantic v2](https://img.shields.io/badge/Pydantic-v2-E92063.svg?style=flat&logo=pydantic&logoColor=white)](https://docs.pydantic.dev/)

ApnaERP is a production-grade, modular, high-performance Enterprise Resource Planning (ERP) backend built using Python, FastAPI, PostgreSQL, Redis, Celery, Alembic, JWT, Role-Based Access Control (RBAC), Generic CRUD Framework, and Docker.

---

## Technical Architecture & Core Principles

- **Generic Repository Pattern**: Base CRUD implementation (`app/repositories/base_repository.py`) supporting `create`, `get_by_id`, `get_all`, `get_multi_paginated`, `update`, `delete`, `soft_delete`, `restore`, `exists`, and `count`.
- **Generic Service Layer**: Reusable service contracts (`app/services/base_service.py`) with automatic domain exception mapping (`NotFoundException`, `DuplicateResourceException`).
- **Soft Deletion Architecture**: Built-in support for non-destructive record deletion (`SoftDeleteMixin`) with restoration capability (`restore`).
- **Pagination, Filtering & Sorting**: Dynamic SQL query modifiers supporting pagination (`PaginationParams`), filtering (`FilterCriterion` with `EQ`, `NEQ`, `GT`, `GTE`, `LT`, `LTE`, `LIKE`, `ILIKE`, `IN`, `IS_NULL`), sorting (`SortCriterion` with `ASC`/`DESC`), and multi-column ILIKE search.
- **Dependency Injection & Query Parameters**: Common query parameter dependencies (`app/dependencies/query_params.py`) for reusable endpoint parameter parsing.
- **Standardized API Responses**: Consistent response wrappers (`SuccessResponse[T]`, `PaginatedResponse[T]`, `ErrorResponse`) with standardized exception handling across the entire application (`app/exceptions/handlers.py`).
- **Role-Based Access Control (RBAC)**: Fine-grained enterprise authorization engine supporting dynamic roles and module-level permission codes (`users.*`, `employees.*`, `inventory.*`, `admin.full_access`).
- **JWT & Bcrypt Security**: State-of-the-art JWT access/refresh tokens with bcrypt password hashing (`app/core/security.py`).
- **SQLAlchemy 2.0 Typed ORM**: Declarative base models with explicit PostgreSQL constraint naming conventions (`app/db/base.py`).
- **Timestamp, SoftDelete & UUID Mixins**: Standardized `UUIDMixin` (v4 primary keys), `TimestampMixin` (`created_at`, `updated_at`), and `SoftDeleteMixin` (`is_deleted`, `deleted_at`).
- **Clean Architecture & SOLID**: Layered separation of concerns with reusable, decoupled components.

---

## Directory Structure

```
ApnaERP/
├── alembic/                  # Alembic database migrations
│   ├── env.py                # Migration runtime environment
│   └── versions/             # Migration revision scripts (users & RBAC tables)
├── app/                      # Application source code
│   ├── api/                  # API endpoints and dependency injection
│   │   ├── deps.py           # Dependency injection providers (get_db, get_current_user, has_permission, has_role)
│   │   └── v1/               # API version 1 routers
│   │       ├── api.py        # Master v1 router
│   │       └── endpoints/    # Route handlers (auth, health, rbac, root)
│   ├── core/                 # App configuration, logging, events & security
│   │   ├── config.py         # Pydantic v2 Settings (JWT secrets, DB, Redis)
│   │   ├── events.py         # FastAPI lifespan context manager & DB auto-seeding
│   │   ├── logging.py        # Structured logging setup
│   │   └── security.py       # Bcrypt hashing & JWT token management
│   ├── db/                   # Database session and connection setup
│   │   ├── base.py           # DeclarativeBase & constraint naming conventions
│   │   ├── mixins.py         # UUIDMixin, TimestampMixin, SoftDeleteMixin
│   │   ├── seed_rbac.py      # Automated default roles & permissions seeder
│   │   └── session.py        # Async & Sync SQLAlchemy session factories
│   ├── dependencies/         # Reusable dependency injection helpers
│   │   └── query_params.py   # CommonQueryParams, get_pagination_params, get_sorting_params, get_search_params
│   ├── exceptions/           # Domain exception hierarchy and FastAPI handlers
│   │   ├── base.py           # Custom exceptions (NotFoundException, ValidationException, etc.)
│   │   └── handlers.py       # Global FastAPI exception handlers
│   ├── middleware/           # FastAPI request timing & CORS middleware
│   │   └── logging_middleware.py
│   ├── models/               # SQLAlchemy ORM models
│   │   ├── permission.py     # Permission ORM model
│   │   ├── role.py           # Role & RolePermission ORM models
│   │   ├── user.py           # User ORM model
│   │   └── user_role.py      # UserRole association model
│   ├── repositories/         # Clean Architecture repository layer
│   │   ├── base.py           # Re-export BaseRepository interface
│   │   ├── base_repository.py# Generic BaseRepository implementation
│   │   ├── rbac.py           # Role, Permission, UserRole, RolePermission repositories
│   │   └── user.py           # UserRepository implementation
│   ├── schemas/              # Pydantic v2 data models & validation
│   │   ├── auth.py           # Token & auth request schemas
│   │   ├── base.py           # BaseSchema, UUIDSchema, TimestampSchema, SoftDeleteSchema
│   │   ├── health.py         # Health check schemas
│   │   ├── rbac.py           # Role & Permission create/response schemas
│   │   ├── responses.py      # SuccessResponse, PaginatedResponse, ErrorResponse builders
│   │   └── user.py           # User create/response/update schemas
│   ├── services/             # Clean Architecture business service layer
│   │   ├── base.py           # Re-export BaseService contract
│   │   ├── base_service.py   # Generic BaseService implementation
│   │   ├── auth.py           # AuthService implementation
│   │   └── rbac.py           # RBACService implementation
│   ├── utils/                # Helper utilities
│   │   ├── filters.py        # Dynamic FilterCriterion & apply_filters
│   │   ├── pagination.py     # PaginationParams & PaginatedResult
│   │   ├── search.py         # Multi-column ILIKE apply_search
│   │   ├── sorting.py        # SortCriterion & apply_sorting
│   │   └── validation.py     # General validation helpers (UUID, email, sanitize)
│   └── main.py               # FastAPI application entrypoint
├── docker/                   # Docker deployment configurations
│   ├── Dockerfile            # Container build instructions
│   └── docker-compose.yml    # Multi-service stack (API, DB, Redis, Celery, Prometheus)
├── scripts/                  # Shell launcher scripts
├── tests/                    # Pytest test suite
│   ├── conftest.py           # Pytest fixtures and DB auto-setup/seed
│   ├── test_auth.py          # Authentication & User Management unit tests
│   ├── test_db_health.py     # Database connectivity tests
│   ├── test_generic_crud.py  # Generic CRUD Framework unit tests
│   ├── test_health.py        # Health endpoint tests
│   ├── test_rbac.py          # Role-Based Access Control unit tests
│   └── test_root.py          # Root endpoint tests
├── .env.example              # Environment variables template
├── alembic.ini               # Alembic configuration
├── requirements.txt          # Python production dependencies
└── README.md                 # Project documentation
```

---

## Response Structure

### Success Response (`SuccessResponse[T]`)
```json
{
  "success": true,
  "message": "Operation completed successfully.",
  "data": { ... }
}
```

### Paginated Response (`PaginatedResponse[T]`)
```json
{
  "success": true,
  "message": "Paginated records retrieved successfully.",
  "data": [ ... ],
  "total": 100,
  "page": 1,
  "page_size": 20,
  "total_pages": 5,
  "has_next": true,
  "has_prev": false
}
```

### Error Response (`ErrorResponse`)
```json
{
  "success": false,
  "message": "Resource with ID 'xxx' not found.",
  "detail": "Resource with ID 'xxx' not found.",
  "error_code": "RESOURCE_NOT_FOUND",
  "details": null
}
```

---

## API Endpoints Overview

| HTTP Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `POST` | `/auth/register` | Register new user account | No |
| `POST` | `/auth/login` | Login with username/email & password | No |
| `POST` | `/auth/refresh` | Exchange refresh token for new access token | No |
| `POST` | `/auth/logout` | Logout user session | Yes (Bearer) |
| `GET` | `/auth/me` | Get current authenticated user profile | Yes (Bearer) |
| `GET` | `/roles` | List all roles and assigned permissions | Yes (Bearer) |
| `POST` | `/roles` | Create security role | Yes (`roles.create` / Super Admin) |
| `PUT` | `/roles/{id}` | Update role details | Yes (`roles.update` / Super Admin) |
| `DELETE` | `/roles/{id}` | Delete security role | Yes (`roles.delete` / Super Admin) |
| `GET` | `/permissions` | List all registered permission codes | Yes (Bearer) |
| `POST` | `/permissions` | Register new permission code | Yes (`admin.full_access` / Super Admin) |
| `POST` | `/users/{user_id}/roles` | Assign role to user | Yes (`roles.update` / Super Admin) |
| `DELETE` | `/users/{user_id}/roles/{role_id}` | Remove role from user | Yes (`roles.update` / Super Admin) |
| `POST` | `/roles/{role_id}/permissions` | Assign permission code to role | Yes (`roles.update` / Super Admin) |
| `DELETE` | `/roles/{role_id}/permissions/{permission_id}` | Revoke permission code from role | Yes (`roles.update` / Super Admin) |
| `GET` | `/health` | System health check | No |
| `GET` | `/health/db` | Database connectivity health check | No |

---

## Testing

Run the complete automated test suite using `pytest`:

```bash
pytest
```

---

## License

Copyright © 2026 ApnaERP Team. All rights reserved.
