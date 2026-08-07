# ApnaERP Administrator Guide (v1.3.0)

Welcome to the ApnaERP Production Administrator Guide.

## System Setup & Initialization
1. Environment Configuration: Ensure `.env.production` is configured.
2. Database Migration: Run `alembic upgrade head`.
3. RBAC Initialization: Execute `python -m app.db.seed_rbac` to seed system roles and permissions.

## Key Management & Webhooks
- API Keys: Admin users can issue, rotate, and revoke API keys via `/api/v1/api-keys`.
- Webhooks: Register webhook endpoints via `/api/v1/webhooks` with HMAC-SHA256 signature verification.

## Backup & Recovery
- Trigger full database backup: `python cli.py backup create` or via `/api/v1/backups`.
