# ADR-0004: Enterprise Employee Domain Core Architecture & Reporting Structure

- **Status**: Accepted
- **Deciders**: Principal Backend Engineer & Enterprise Software Architect
- **Date**: 2026-07-26
- **Milestone**: HR-2 (Release v0.3.0)

---

## Context and Problem Statement

Following the completion of Department Management (Milestone HR-1), ApnaERP requires a centralized, robust Employee domain to serve as the core entity for the entire Human Resources (HR) platform.

All future HR modules (Attendance, Leave, Payroll, Performance, Recruitment, and Assets) will directly depend on and build upon the Employee model. We require an enterprise-grade data model, reporting hierarchy structure, comprehensive validations (employee code, work email, date constraints, active department check, circular reporting prevention), Redis caching strategy, Celery background tasks, and seamless integration with existing platform infrastructure.

---

## Decision Drivers

1. **Central Workforce Entity**: The `Employee` model must cleanly encapsulate personal, contact, employment type/status, department placement, user link, and profile picture references.
2. **Reporting Hierarchy Structure**: Self-referential manager relationship (`manager_id` -> `employees.id`) to model direct reports and organization-wide manager hierarchy trees (`GET /api/v1/employees/hierarchy`).
3. **Strict Domain Validations**:
   - Unique `employee_code` and `work_email`.
   - Date sanity check (`joining_date` <= `exit_date`).
   - Self-management prohibition (`manager_id != employee_id`).
   - Circular reporting hierarchy prevention (ancestor traversal loop check).
   - Active and non-deleted department validation (`department.is_active == True`, `department.is_deleted == False`).
4. **Redis Caching & Invalidation**: Caches hierarchy tree (`employee:hierarchy`) and department employee lists (`employee:department:{id}`). Automatically invalidates affected caches on any mutation operation.
5. **Asynchronous Background Processing**: Enqueues background events (`send_employee_notification_task`) via Celery.
6. **Audit & RBAC Integration**: Logs structured audit entries (`EMPLOYEE_CREATE`, `EMPLOYEE_UPDATE`, `EMPLOYEE_DELETE`, `EMPLOYEE_RESTORE`) and enforces granular RBAC permissions (`employee.create`, `employee.read`, `employee.update`, `employee.delete`, `employee.restore`).

---

## Decision

We implemented the `Employee` model using SQLAlchemy 2.0 Typed ORM:

```python
class Employee(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "employees"

    employee_code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    work_email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)

    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), unique=True)
    department_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("departments.id"))
    manager_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("employees.id"))

    employment_type: Mapped[str] = mapped_column(String(50), default="Full Time")
    employment_status: Mapped[str] = mapped_column(String(50), default="Active")
    joining_date: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    profile_photo_file_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("files.id"))

    department = relationship("Department")
    manager = relationship("Employee", remote_side="Employee.id", back_populates="direct_reports")
    direct_reports = relationship("Employee", back_populates="manager")
    user = relationship("User")
    profile_photo = relationship("File")
```

---

## Consequences

### Positive
- Solid, extensible core entity ready for Attendance, Leave, Payroll, Performance, Recruitment, and Asset modules.
- Complete reporting hierarchy tree with circular reference protection.
- High-performance cached endpoints for organization charts and department lists.
- Full compliance with Clean Architecture, SOLID, Audit Logging, and RBAC standards.

### Tradeoffs
- Hierarchy tree serialization requires clean in-memory assembly to prevent async SQLAlchemy lazy-loading overhead.

---

## Future Module Integrations

- **Attendance**: Will link attendance records to `employee_id`.
- **Leave**: Will link leave applications, balances, and manager approval workflows to `employee_id` and `manager_id`.
- **Payroll**: Will link salary structures, payslips, and tax details to `employee_id`.
