# ApnaERP - Enterprise Resource Planning Backend API

[![FastAPI](https://img.shields.io/badge/FastAPI-0.111+-009688.svg?style=flat&logo=FastAPI&logoColor=white)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB.svg?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![SQLAlchemy 2.0](https://img.shields.io/badge/SQLAlchemy-2.0+-D71F00.svg?style=flat&logo=sqlalchemy&logoColor=white)](https://www.sqlalchemy.org/)
[![Pydantic v2](https://img.shields.io/badge/Pydantic-v2-E92063.svg?style=flat&logo=pydantic&logoColor=white)](https://docs.pydantic.dev/)

ApnaERP is a production-grade, modular, high-performance Enterprise Resource Planning (ERP) backend built using Python, FastAPI, PostgreSQL, Redis, Celery, Alembic, JWT, Role-Based Access Control (RBAC), Generic CRUD Framework, Enterprise Audit Logging, Enterprise File Management, Enterprise Notification System, and Docker.

---

## Notification Architecture & Email Configuration

### Notification Architecture
ApnaERP features a modular Notification & Template Engine (`app/services/notification_service.py`):
- **Channel Support**: Supports both **In-App Notifications** (`IN_APP`) persisted in PostgreSQL and **Email Notifications** (`EMAIL`) delivered via SMTP.
- **Priority Levels**: Categorized by priority (`LOW`, `MEDIUM`, `HIGH`, `URGENT`).
- **User Isolation Security**: Users have access strictly to their own notifications (`user_id == current_user.id`).
- **Template Engine**: Powered by Jinja2 (`app/services/template_service.py`) for dynamic variable substitution in titles, subjects, and text/HTML bodies.
- **Celery-Ready Service Design**: Designed with clean service interfaces (`EmailService`, `NotificationService`) so notification dispatching can be offloaded to async Celery workers in future phases without breaking API contracts.

### Email Configuration & Environment Variables
Configure SMTP credentials in `.env` or environment variables:
```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=notifications@apnaerp.com
SMTP_PASSWORD=your_secure_app_password
EMAILS_FROM_EMAIL=noreply@apnaerp.com
EMAILS_FROM_NAME=ApnaERP System
SMTP_TLS=True
```
*Note: If `SMTP_HOST` is unconfigured (e.g., during development or automated tests), `EmailService` safely logs email payloads without throwing connection failures.*

### Supported Jinja2 Template Variables
When creating notification templates (`POST /templates`), you can use standard Jinja2 syntax:
- `{{user_name}}`: Recipient full name or username
- `{{employee_name}}`: Target employee name
- `{{department}}`: Department name
- `{{date}}`: Due date / event date
- `{{invoice_number}}`: Invoice identification code
- `{{amount}}`: Monetary amount formatted string

### Notification API Examples

#### 1. Dispatch Notification with Jinja2 Template (`POST /notifications/send`)
```json
{
  "user_id": "93cdd305-5a32-4826-b3a0-5d11aad42056",
  "template_name": "invoice_due_notice",
  "template_data": {
    "user_name": "Sarthak Zunjure",
    "invoice_number": "INV-2026-001",
    "amount": "$12,500.00",
    "date": "2026-08-01"
  },
  "notification_type": "EMAIL",
  "priority": "HIGH"
}
```

#### 2. Mark All Notifications as Read (`PUT /notifications/read-all`)
```json
{
  "message": "Marked 5 notifications as read."
}
```

#### 3. Create Notification Template (Super Admin) (`POST /templates`)
```json
{
  "name": "payroll_alert",
  "subject": "Payroll Processed for {{employee_name}}",
  "template_body": "Hi {{employee_name}}, your {{department}} salary for amount {{amount}} has been credited.",
  "template_type": "EMAIL"
}
```

---

## Directory Structure

```
ApnaERP/
├── alembic/                  # Alembic database migrations
│   ├── env.py                # Migration runtime environment
│   └── versions/             # Migration revision scripts (users, RBAC, AuditLog, File, & Notification tables)
├── app/                      # Application source code
│   ├── api/                  # API endpoints and dependency injection
│   │   ├── deps.py           # Dependency injection providers
│   │   └── v1/               # API version 1 routers
│   │       ├── api.py        # Master v1 router
│   │       └── endpoints/    # Route handlers (audit, auth, files, health, notifications, rbac, root, templates)
│   ├── core/                 # App configuration, logging, events, security & storage
│   │   ├── config.py         # Settings (JWT, DB, Redis, File limits, SMTP settings)
│   │   └── storage/          # Storage Provider Abstraction layer
│   ├── db/                   # Database session and connection setup
│   ├── dependencies/         # Reusable dependency injection helpers
│   ├── exceptions/           # Domain exception hierarchy and FastAPI handlers
│   ├── middleware/           # FastAPI request timing, context & CORS middleware
│   ├── models/               # SQLAlchemy ORM models
│   │   ├── audit_log.py      # AuditLog ORM model
│   │   ├── file.py           # File ORM model
│   │   ├── notification.py   # Notification & NotificationTemplate ORM models
│   │   ├── permission.py     # Permission ORM model
│   │   ├── role.py           # Role & RolePermission ORM models
│   │   └── user.py           # User ORM model
│   ├── repositories/         # Clean Architecture repository layer
│   │   ├── audit_log.py      # AuditLogRepository
│   │   ├── base_repository.py# Generic BaseRepository
│   │   ├── file.py           # FileRepository
│   │   ├── notification.py   # NotificationRepository & NotificationTemplateRepository
│   │   ├── rbac.py           # RBAC repositories
│   │   └── user.py           # UserRepository
│   ├── schemas/              # Pydantic v2 data models & validation
│   │   ├── audit_log.py      # AuditLog schemas
│   │   ├── auth.py           # Token & auth request schemas
│   │   ├── base.py           # Base/UUID/Timestamp schemas
│   │   ├── file.py           # File schemas
│   │   ├── health.py         # Health check schemas
│   │   ├── notification.py   # Notification & Template schemas
│   │   ├── rbac.py           # Role & Permission schemas
│   │   └── responses.py      # SuccessResponse, PaginatedResponse, ErrorResponse
│   ├── services/             # Clean Architecture business service layer
│   │   ├── audit_log.py      # AuditLogService
│   │   ├── auth.py           # AuthService
│   │   ├── base_service.py   # Generic BaseService
│   │   ├── email_service.py  # EmailService (SMTP delivery & fallback)
│   │   ├── file.py           # FileService
│   │   ├── notification_service.py # NotificationService (dispatch & read status)
│   │   ├── rbac.py           # RBACService
│   │   └── template_service.py # TemplateService (Jinja2 dynamic rendering)
│   ├── utils/                # Helper utilities
│   └── main.py               # FastAPI application entrypoint
├── docker/                   # Docker deployment configurations
├── tests/                    # Pytest test suite
│   ├── test_audit_log.py     # Audit Logging unit tests
│   ├── test_auth.py          # Authentication unit tests
│   ├── test_db_health.py     # Database connectivity tests
│   ├── test_files.py         # File Management unit tests
│   ├── test_generic_crud.py  # Generic CRUD Framework unit tests
│   ├── test_health.py        # Health endpoint tests
│   ├── test_notifications.py # Enterprise Notification System unit tests
│   ├── test_rbac.py          # Role-Based Access Control unit tests
│   └── test_root.py          # Root endpoint tests
├── uploads/                  # Local storage root directory
├── alembic.ini               # Alembic configuration
├── requirements.txt          # Python production dependencies
└── README.md                 # Project documentation
```

---

## API Endpoints Overview

| HTTP Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `GET` | `/notifications` | List user's notifications (paginated & filtered) | Yes (Bearer) |
| `GET` | `/notifications/unread` | List user's unread notifications | Yes (Bearer) |
| `POST` | `/notifications/send` | Dispatch In-App or Email notification | Yes (Bearer) |
| `PUT` | `/notifications/read/{id}` | Mark specific notification as read | Yes (Bearer) |
| `PUT` | `/notifications/read-all` | Mark all unread notifications as read | Yes (Bearer) |
| `DELETE` | `/notifications/{id}` | Delete notification | User (Own) / Super Admin |
| `GET` | `/templates` | List notification templates | Yes (Bearer) |
| `POST` | `/templates` | Create notification template | Super Admin |
| `PUT` | `/templates/{id}` | Update notification template | Super Admin |
| `DELETE` | `/templates/{id}` | Delete notification template | Super Admin |
| `POST` | `/files/upload` | Multipart file upload with SHA256 deduplication | Yes (Bearer) |
| `POST` | `/auth/login` | Login with username/email & password | No |
| `GET` | `/audit/logs` | List audit logs | Yes (Super Admin) |
| `GET` | `/health` | System health check | No |

---

## Testing

Run the complete automated test suite using `pytest`:

```bash
pytest
```

---

## License

Copyright © 2026 ApnaERP Team. All rights reserved.
