# ApnaERP - Enterprise Resource Planning Backend API

[![FastAPI](https://img.shields.io/badge/FastAPI-0.111+-009688.svg?style=flat&logo=FastAPI&logoColor=white)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB.svg?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![SQLAlchemy 2.0](https://img.shields.io/badge/SQLAlchemy-2.0+-D71F00.svg?style=flat&logo=sqlalchemy&logoColor=white)](https://www.sqlalchemy.org/)
[![Pydantic v2](https://img.shields.io/badge/Pydantic-v2-E92063.svg?style=flat&logo=pydantic&logoColor=white)](https://docs.pydantic.dev/)

ApnaERP is a production-grade, modular, high-performance Enterprise Resource Planning (ERP) backend built using Python, FastAPI, PostgreSQL, Redis, Celery, Alembic, JWT, Role-Based Access Control (RBAC), Generic CRUD Framework, Enterprise Audit Logging, Enterprise File Management, and Docker.

---

## Storage Architecture & File Security

### Storage Architecture
ApnaERP implements a pluggable `StorageProvider` abstraction layer (`app/core/storage/base_provider.py`). The core engine communicates exclusively through standard contracts (`save_file`, `get_file`, `delete_file`, `file_exists`), enabling seamless switching between storage backends:
- **`LocalStorageProvider`** (Default): Local disk storage organizing uploaded assets into date-based subdirectories (`uploads/YYYY/MM/DD/uuid.ext`). Features automatic directory creation, safe filename sanitization, and relative path tracking.
- **Cloud Storage Ready**: Architected to support AWS S3 (`S3StorageProvider`), Azure Blob Storage (`AzureStorageProvider`), and Google Cloud Storage (`GCSStorageProvider`) without altering business logic or database schemas.

### Upload Flow & SHA256 Deduplication
```
[ Client Upload ] ──> POST /files/upload (UploadFile + metadata)
                             │
                             ▼
                    File Validation Engine
                             │  - Size limit check (settings.MAX_UPLOAD_SIZE_MB)
                             │  - Extension whitelist check (settings.ALLOWED_FILE_EXTENSIONS)
                             │  - MIME type check (settings.ALLOWED_MIME_TYPES)
                             ▼
                    SHA256 Checksum Calculation
                             │
            ┌────────────────┴────────────────┐
            ▼                                 ▼
   Checksum Exists in DB?           Checksum New?
   (Return Existing Record)         (Save bytes to StorageProvider)
                                              │
                                              ▼
                                    Insert File DB Record
                                              │
                                              ▼
                                    Log FILE_UPLOAD Audit Event
```

### File Security & Access Controls
- **Physical Path Concealment**: Public API responses (`FileResponse`) strictly omit the internal `storage_path` attribute to prevent server directory layout disclosure.
- **Deletion Authorization**: File deletion (`DELETE /files/{id}`) is strictly restricted to the original file uploader (`uploaded_by_id`) or a **Super Admin** user.
- **Authentication Safeguard**: All file management endpoints require valid Bearer JWT authentication.
- **Audit Integration**: Every file upload (`FILE_UPLOAD`), binary download (`FILE_DOWNLOAD`), and deletion (`FILE_DELETE`) automatically generates a detailed entry in the central audit trail.

### Supported File Extensions & MIME Types
- **Documents**: `.pdf`, `.doc`, `.docx`, `.xls`, `.xlsx`, `.csv`, `.txt`
- **Images**: `.png`, `.jpg`, `.jpeg`
- **Archives**: `.zip`

---

## Directory Structure

```
ApnaERP/
├── alembic/                  # Alembic database migrations
│   ├── env.py                # Migration runtime environment
│   └── versions/             # Migration revision scripts (users, RBAC, AuditLog, & File tables)
├── app/                      # Application source code
│   ├── api/                  # API endpoints and dependency injection
│   │   ├── deps.py           # Dependency injection providers (get_db, get_current_user, has_permission, has_role)
│   │   └── v1/               # API version 1 routers
│   │       ├── api.py        # Master v1 router
│   │       └── endpoints/    # Route handlers (audit, auth, files, health, rbac, root)
│   ├── core/                 # App configuration, logging, events, security & storage
│   │   ├── config.py         # Pydantic v2 Settings (JWT, DB, Redis, File limits)
│   │   ├── events.py         # FastAPI lifespan context manager & DB auto-seeding
│   │   ├── logging.py        # Structured logging setup
│   │   ├── security.py       # Bcrypt hashing & JWT token management
│   │   └── storage/          # Storage Provider Abstraction layer
│   │       ├── base_provider.py # StorageProvider ABC interface
│   │       └── local_provider.py# LocalStorageProvider implementation
│   ├── db/                   # Database session and connection setup
│   │   ├── base.py           # DeclarativeBase & constraint naming conventions
│   │   ├── mixins.py         # UUIDMixin, TimestampMixin, SoftDeleteMixin
│   │   ├── seed_rbac.py      # Automated default roles & permissions seeder
│   │   └── session.py        # Async & Sync SQLAlchemy session factories
│   ├── dependencies/         # Reusable dependency injection helpers
│   │   └── query_params.py   # CommonQueryParams, get_pagination_params, get_sorting_params, get_search_params
│   ├── exceptions/           # Domain exception hierarchy and FastAPI handlers
│   ├── middleware/           # FastAPI request timing, context & CORS middleware
│   ├── models/               # SQLAlchemy ORM models
│   │   ├── audit_log.py      # AuditLog ORM model
│   │   ├── file.py           # File ORM model
│   │   ├── permission.py     # Permission ORM model
│   │   ├── role.py           # Role & RolePermission ORM models
│   │   └── user.py           # User ORM model
│   ├── repositories/         # Clean Architecture repository layer
│   │   ├── audit_log.py      # AuditLogRepository
│   │   ├── base_repository.py# Generic BaseRepository
│   │   ├── file.py           # FileRepository
│   │   ├── rbac.py           # RBAC repositories
│   │   └── user.py           # UserRepository
│   ├── schemas/              # Pydantic v2 data models & validation
│   │   ├── audit_log.py      # AuditLog schemas
│   │   ├── auth.py           # Token & auth request schemas
│   │   ├── base.py           # Base/UUID/Timestamp schemas
│   │   ├── file.py           # FileCreate & FileResponse schemas
│   │   ├── health.py         # Health check schemas
│   │   ├── rbac.py           # Role & Permission schemas
│   │   └── responses.py      # SuccessResponse, PaginatedResponse, ErrorResponse
│   ├── services/             # Clean Architecture business service layer
│   │   ├── audit_log.py      # AuditLogService
│   │   ├── auth.py           # AuthService
│   │   ├── base_service.py   # Generic BaseService
│   │   ├── file.py           # FileService (upload, download, deduplication, deletion)
│   │   └── rbac.py           # RBACService
│   ├── utils/                # Helper utilities
│   │   ├── audit.py          # log_audit(...) helper function
│   │   ├── filters.py        # Dynamic FilterCriterion
│   │   ├── pagination.py     # PaginationParams & PaginatedResult
│   │   ├── search.py         # Multi-column ILIKE apply_search
│   │   ├── sorting.py        # SortCriterion & apply_sorting
│   │   └── validation.py     # General validation helpers
│   └── main.py               # FastAPI application entrypoint
├── docker/                   # Docker deployment configurations
├── tests/                    # Pytest test suite
│   ├── conftest.py           # Pytest fixtures and DB auto-setup/seed
│   ├── test_audit_log.py     # Audit Logging System unit tests
│   ├── test_auth.py          # Authentication unit tests
│   ├── test_db_health.py     # Database connectivity tests
│   ├── test_files.py         # Enterprise File Management unit tests
│   ├── test_generic_crud.py  # Generic CRUD Framework unit tests
│   ├── test_health.py        # Health endpoint tests
│   ├── test_rbac.py          # Role-Based Access Control unit tests
│   └── test_root.py          # Root endpoint tests
├── uploads/                  # Local storage root directory (YYYY/MM/DD structure)
├── alembic.ini               # Alembic configuration
├── requirements.txt          # Python production dependencies
└── README.md                 # Project documentation
```

---

## API Endpoints Overview

| HTTP Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `POST` | `/files/upload` | Multipart file upload with SHA256 deduplication | Yes (Bearer) |
| `GET` | `/files/{id}` | Get file metadata by ID | Yes (Bearer) |
| `GET` | `/files/download/{id}` | Download raw file binary stream | Yes (Bearer) |
| `DELETE` | `/files/{id}` | Delete file from storage and DB | Uploader / Super Admin |
| `GET` | `/files` | Paginated list of uploaded files (filtered & searchable) | Yes (Bearer) |
| `POST` | `/auth/register` | Register new user account | No |
| `POST` | `/auth/login` | Login with username/email & password | No |
| `POST` | `/auth/refresh` | Exchange refresh token for access token | No |
| `POST` | `/auth/logout` | Logout user session | Yes (Bearer) |
| `GET` | `/auth/me` | Get current authenticated user profile | Yes (Bearer) |
| `GET` | `/roles` | List all roles | Yes (Bearer) |
| `POST` | `/roles` | Create security role | Yes (`roles.create` / Super Admin) |
| `GET` | `/audit/logs` | List audit logs | Yes (Super Admin) |
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
