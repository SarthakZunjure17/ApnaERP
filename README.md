# ApnaERP - Enterprise Resource Planning Backend API

[![FastAPI](https://img.shields.io/badge/FastAPI-0.111+-009688.svg?style=flat&logo=FastAPI&logoColor=white)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB.svg?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![SQLAlchemy 2.0](https://img.shields.io/badge/SQLAlchemy-2.0+-D71F00.svg?style=flat&logo=sqlalchemy&logoColor=white)](https://www.sqlalchemy.org/)
[![Pydantic v2](https://img.shields.io/badge/Pydantic-v2-E92063.svg?style=flat&logo=pydantic&logoColor=white)](https://docs.pydantic.dev/)

ApnaERP is a production-grade, modular, high-performance Enterprise Resource Planning (ERP) backend built using Python, FastAPI, PostgreSQL, Redis, Celery, Alembic, JWT, Role-Based Access Control (RBAC), and Docker.

---

## Technical Architecture & Core Principles

- **Repository Pattern**: Decouples domain logic from database access mechanisms (`app/repositories/`).
- **Service Layer**: Encapsulates business processes, authentication rules, and authorization (`app/services/`).
- **Dependency Injection**: Utilizes FastAPI's native `Depends` system for DB sessions, JWT authentication, and permission enforcement (`app/api/deps.py`).
- **Role-Based Access Control (RBAC)**: Fine-grained enterprise authorization engine supporting dynamic roles, module-level permission codes (`users.*`, `employees.*`, `inventory.*`, `admin.full_access`), and multi-role assignments (`app/models/role.py`, `app/models/permission.py`).
- **JWT & Bcrypt Security**: State-of-the-art JWT access/refresh tokens with bcrypt password hashing (`app/core/security.py`).
- **SQLAlchemy 2.0 Typed ORM**: Declarative base models with explicit PostgreSQL constraint naming conventions (`app/db/base.py`).
- **Timestamp & UUID Mixins**: Standardized `UUIDMixin` (v4 primary keys) and `TimestampMixin` (`created_at`, `updated_at` with UTC timezone support).
- **Alembic Migrations**: Fully configured transactional database schema migrations (`alembic/`).
- **Pydantic v2**: High-performance data validation and configuration management (`pydantic-settings`).
- **Clean Architecture & SOLID**: Layered separation of concerns with clear domain boundaries.

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
│   │   ├── mixins.py         # UUIDMixin and TimestampMixin
│   │   ├── seed_rbac.py      # Automated default roles & permissions seeder
│   │   └── session.py        # Async & Sync SQLAlchemy session factories
│   ├── middleware/           # FastAPI request timing & CORS middleware
│   │   └── logging_middleware.py
│   ├── models/               # SQLAlchemy ORM models
│   │   ├── permission.py     # Permission ORM model
│   │   ├── role.py           # Role & RolePermission ORM models
│   │   ├── user.py           # User ORM model
│   │   └── user_role.py      # UserRole association model
│   ├── repositories/         # Clean Architecture repository layer
│   │   ├── base.py           # Generic BaseRepository interface
│   │   ├── rbac.py           # Role, Permission, UserRole, RolePermission repositories
│   │   └── user.py           # UserRepository implementation
│   ├── schemas/              # Pydantic v2 data models & validation
│   │   ├── auth.py           # Token & auth request schemas
│   │   ├── health.py         # Health check schemas
│   │   ├── rbac.py           # Role & Permission create/response schemas
│   │   └── user.py           # User create/response/update schemas
│   ├── services/             # Clean Architecture business service layer
│   │   ├── base.py           # Generic BaseService contract
│   │   ├── auth.py           # AuthService implementation
│   │   └── rbac.py           # RBACService implementation
│   ├── utils/                # Helper utilities
│   └── main.py               # FastAPI application entrypoint
├── docker/                   # Docker deployment configurations
│   ├── Dockerfile            # Container build instructions
│   └── docker-compose.yml    # Multi-service stack (API, DB, Redis, Celery, Prometheus)
├── scripts/                  # Shell launcher scripts
├── tests/                    # Pytest test suite
│   ├── conftest.py           # Pytest fixtures and DB auto-setup/seed
│   ├── test_auth.py          # Authentication & User Management unit tests
│   ├── test_db_health.py     # Database connectivity tests
│   ├── test_health.py        # Health endpoint tests
│   ├── test_rbac.py          # Role-Based Access Control unit tests
│   └── test_root.py          # Root endpoint tests
├── .env.example              # Environment variables template
├── alembic.ini               # Alembic configuration
├── requirements.txt          # Python production dependencies
└── README.md                 # Project documentation
```

---

## Authorization Engine (RBAC Architecture)

ApnaERP provides a reusable Role-Based Access Control (RBAC) engine usable across all future ERP modules:

- **Roles**: System roles (`Super Admin`, `HR Manager`, `HR Executive`, `Inventory Manager`, `Sales Manager`, `Employee`).
- **Permissions**: Fine-grained permissions identified by unique strings (`code`) like `users.create`, `employees.read`, `inventory.manage`, `admin.full_access`.
- **Superuser Access**: Users with `is_superuser = True` or `Super Admin` role automatically bypass permission checks.
- **Dependency Guard Factories**:
  - `has_permission("users.create")`: Ensures the user possesses the required permission code (or superuser privileges).
  - `has_role("HR Manager")`: Ensures the user holds the specified role.

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
