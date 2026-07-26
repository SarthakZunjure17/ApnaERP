# ADR-0005: Employee Documents & Digital Personnel Files Architecture

- **Status**: Accepted
- **Deciders**: Principal Backend Engineer & Enterprise Software Architect
- **Date**: 2026-07-26
- **Milestone**: HR-3 (Release v0.3.0)

---

## Context and Problem Statement

Following Core Employee Domain (Milestone HR-2), ApnaERP requires a digital personnel file system to manage employee compliance documents (Aadhaar, PAN, Passport, Driving License, Offer Letters, Contracts, NDAs, Experience Letters, Education Certificates).

Rather than creating duplicate file upload endpoints and redundant physical file handling, we need an architecture that reuses the existing platform File Management service (`File` model, local/cloud storage providers), manages document metadata, tracks verification workflows (`Pending`, `Verified`, `Rejected`), supports mandatory document constraints, and enforces strict RBAC permissions and audit trails.

---

## Decision Drivers

1. **Storage Provider Reuse**: Reuse the existing `File` management service for binary file upload, storage paths, checksums, and MIME validation. `EmployeeDocument` references `file_id` (FK to `files.id`).
2. **Verification & Audit Workflow**: Support formal verification actions (`PATCH /employee-documents/{id}/verify` and `PATCH /employee-documents/{id}/reject`) that record `verified_by`, `verified_at`, and verification notes while logging structured audit events (`DOCUMENT_VERIFY`, `DOCUMENT_REJECT`).
3. **Mandatory & Expiry Controls**:
   - Prevent duplicate active mandatory documents of the same category per employee.
   - Enforce date integrity (`expiry_date` >= `issue_date`).
   - Expiry querying framework for compliance reporting (`get_expiring_documents`).
4. **Redis Caching**: Cache employee document lists (`employee_document:list:{employee_id}`) with automatic invalidation on any mutation operation.
5. **Asynchronous Task Telemetry**: Dispatch Celery background tasks (`send_document_notification_task`) upon document upload, verification, or rejection.

---

## Decision

We implemented the `EmployeeDocument` model using SQLAlchemy 2.0 Typed ORM:

```python
class EmployeeDocument(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "employee_documents"

    employee_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("employees.id", ondelete="CASCADE"), nullable=False)
    file_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("files.id", ondelete="RESTRICT"), nullable=False)
    document_type: Mapped[str] = mapped_column(String(50), nullable=False)
    document_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    issue_date: Mapped[Optional[datetime.date]] = mapped_column(Date, nullable=True)
    expiry_date: Mapped[Optional[datetime.date]] = mapped_column(Date, nullable=True)

    verification_status: Mapped[str] = mapped_column(String(50), default="Pending")
    verified_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    verified_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(timezone=True))
    notes: Mapped[Optional[str]] = mapped_column(Text)
    is_mandatory: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    employee = relationship("Employee")
    file = relationship("File")
    verifier = relationship("User", foreign_keys=[verified_by])
```

---

## Consequences

### Positive
- Zero duplication of file storage or upload logic.
- Strong compliance audit trail and verification accountability.
- High performance via Redis document list caching.
- Enforced permission checks for verification actions (`employee_document.verify`).

### Future Extensions
- Automated cron/periodic Celery tasks for sending document expiration warning emails.
