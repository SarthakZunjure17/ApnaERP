# ApnaERP - Enterprise Resource Planning Backend API

[![FastAPI](https://img.shields.io/badge/FastAPI-0.111+-009688.svg?style=flat&logo=FastAPI&logoColor=white)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB.svg?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![SQLAlchemy 2.0](https://img.shields.io/badge/SQLAlchemy-2.0+-D71F00.svg?style=flat&logo=sqlalchemy&logoColor=white)](https://www.sqlalchemy.org/)
[![Pydantic v2](https://img.shields.io/badge/Pydantic-v2-E92063.svg?style=flat&logo=pydantic&logoColor=white)](https://docs.pydantic.dev/)

ApnaERP is a production-grade, modular, high-performance Enterprise Resource Planning (ERP) backend built using Python, FastAPI, PostgreSQL, Redis, Celery, Alembic, JWT, and Docker.

---

## Technical Architecture & Core Principles

- **Repository Pattern**: Decouples domain logic from database access mechanisms (`app/repositories/`).
- **Service Layer**: Encapsulates business processes, authentication rules, and validation (`app/services/`).
- **Dependency Injection**: Utilizes FastAPI's native `Depends` system for DB sessions and JWT user authentication (`app/api/deps.py`).
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
│   └── versions/             # Migration revision scripts (users table)
├── app/                      # Application source code
│   ├── api/                  # API endpoints and dependency injection
│   │   ├── deps.py           # Dependency injection providers (get_db, get_current_user)
│   │   └── v1/               # API version 1 routers
│   │       ├── api.py        # Master v1 router
│   │       └── endpoints/    # Route handlers (auth, health, root)
│   ├── core/                 # App configuration, logging, events & security
│   │   ├── config.py         # Pydantic v2 Settings (JWT secrets, DB, Redis)
│   │   ├── events.py         # FastAPI lifespan context manager
│   │   ├── logging.py        # Structured logging setup
│   │   └── security.py       # Bcrypt hashing & JWT token management
│   ├── db/                   # Database session and connection setup
│   │   ├── base.py           # DeclarativeBase & constraint naming conventions
│   │   ├── mixins.py         # UUIDMixin and TimestampMixin
│   │   └── session.py        # Async & Sync SQLAlchemy session factories
│   ├── middleware/           # FastAPI request timing & CORS middleware
│   │   └── logging_middleware.py
│   ├── models/               # SQLAlchemy ORM models
│   │   └── user.py           # User ORM model
│   ├── repositories/         # Clean Architecture repository layer
│   │   ├── base.py           # Generic BaseRepository interface
│   │   └── user.py           # UserRepository implementation
│   ├── schemas/              # Pydantic v2 data models & validation
│   │   ├── auth.py           # Token & auth request schemas
│   │   ├── health.py         # Health check schemas
│   │   └── user.py           # User create/response/update schemas
│   ├── services/             # Clean Architecture business service layer
│   │   ├── base.py           # Generic BaseService contract
│   │   └── auth.py           # AuthService implementation
│   ├── utils/                # Helper utilities
│   └── main.py               # FastAPI application entrypoint
├── docker/                   # Docker deployment configurations
│   ├── Dockerfile            # Container build instructions
│   └── docker-compose.yml    # Multi-service stack (API, DB, Redis, Celery, Prometheus)
├── scripts/                  # Shell launcher scripts
├── tests/                    # Pytest test suite
│   ├── conftest.py           # Pytest fixtures and DB auto-setup
│   ├── test_auth.py          # Authentication & User Management unit tests
│   ├── test_db_health.py     # Database connectivity tests
│   ├── test_health.py        # Health endpoint tests
│   └── test_root.py          # Root endpoint tests
├── .env.example              # Environment variables template
├── alembic.ini               # Alembic configuration
├── requirements.txt          # Python production dependencies
└── README.md                 # Project documentation
```

---

## Authentication Flow & Security Architecture

ApnaERP uses **JSON Web Tokens (JWT)** with **Bcrypt** password hashing for secure authentication:

1. **User Registration (`POST /auth/register`)**:
   - Accepts full name, unique email, unique username, and password.
   - Hashes password using `bcrypt` before database insertion.

2. **User Login (`POST /auth/login`)**:
   - Accepts username or email along with plain password.
   - Verifies credentials and generates a pair of signed JWTs:
     - **Access Token**: Short-lived token (default: 30 minutes) used for API authorization.
     - **Refresh Token**: Long-lived token (default: 7 days) used to obtain new access tokens.
   - Updates `last_login` timestamp.

3. **Protected Endpoints (`GET /auth/me`)**:
   - Requires HTTP `Authorization: Bearer <access_token>` header.
   - Decodes JWT, validates signature, expiration (`exp`), and token type (`access`).
   - Retrieves active user profile from database.

4. **Token Refresh (`POST /auth/refresh`)**:
   - Accepts `refresh_token`.
   - Validates refresh token type and generates a fresh Access Token pair.

---

## Environment & JWT Configuration

Configure the following variables in `.env`:

```env
# Security & JWT Configuration
SECRET_KEY="09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"
ALGORITHM="HS256"
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# PostgreSQL Database Configuration
POSTGRES_SERVER="localhost"
POSTGRES_PORT=5432
POSTGRES_USER="apnaerp_user"
POSTGRES_PASSWORD="apnaerp_password"
POSTGRES_DB="apnaerp_db"
```

---

## Example API Requests (cURL)

### 1. Register User
```bash
curl -X 'POST' \
  'http://127.0.0.1:8000/auth/register' \
  -H 'Content-Type: application/json' \
  -d '{
  "email": "john.doe@example.com",
  "username": "johndoe",
  "full_name": "John Doe",
  "password": "SecurePassword123!"
}'
```

### 2. Login & Obtain Tokens
```bash
curl -X 'POST' \
  'http://127.0.0.1:8000/auth/login' \
  -H 'Content-Type: application/json' \
  -d '{
  "username_or_email": "john.doe@example.com",
  "password": "SecurePassword123!"
}'
```

### 3. Access Protected Profile (`GET /auth/me`)
```bash
curl -X 'GET' \
  'http://127.0.0.1:8000/auth/me' \
  -H 'Authorization: Bearer <YOUR_ACCESS_TOKEN>'
```

### 4. Refresh Token
```bash
curl -X 'POST' \
  'http://127.0.0.1:8000/auth/refresh' \
  -H 'Content-Type: application/json' \
  -d '{
  "refresh_token": "<YOUR_REFRESH_TOKEN>"
}'
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
| `GET` | `/health` | System health check | No |
| `GET` | `/health/db` | Database connectivity health check | No |

---

## Testing

Run the full automated test suite using `pytest`:

```bash
pytest
```

---

## License

Copyright © 2026 ApnaERP Team. All rights reserved.
