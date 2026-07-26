# ADR-0006: Position Management & Employment Structure Architecture

- **Status**: Accepted
- **Deciders**: Principal Software Architect & Enterprise Backend Engineer
- **Date**: 2026-07-26
- **Milestone**: HR-4 (Release v0.3.0)

---

## Context and Problem Statement

Following Core Employee Domain (HR-2) and Digital Personnel Files (HR-3), ApnaERP requires a structured **Position Management** module (`Position` model) to decouple organizational job definitions from individual employees.

In an enterprise ERP, employees do not exist in isolation—they occupy specific Job Positions (e.g. `CTO`, `Engineering Manager`, `Senior Backend Engineer`). Positions belong to Departments, support reporting hierarchies, enforce headcount capacity limits (`maximum_headcount` vs `current_headcount`), and define employment contract categories (`Permanent`, `Contract`, `Temporary`, `Internship`).

Future HR modules (Attendance, Leave, Payroll, Recruitment, Performance) must build upon this foundation.

---

## Decision Drivers

1. **Decoupled Role Definition**: Positions represent enterprise job roles owned by Departments. Employees occupy positions, allowing role definitions and reporting structures to persist even as staff turn over.
2. **Headcount Capacity Controls**: Enforce automatic `current_headcount` increments and decrements when employees are assigned or removed. Prevent over-allocation (`current_headcount` <= `maximum_headcount`) with HTTP 400 (`HEADCOUNT_LIMIT_EXCEEDED`) errors and trigger Celery background telemetry notifications (`HEADCOUNT_LIMIT_REACHED`).
3. **Position Reporting Hierarchy**: Support self-referential parent positions (`parent_position_id`) with loop prevention (`_validate_no_circular_position`) and nested tree responses (`GET /api/v1/positions/tree`).
4. **Uniqueness Constraints**:
   - Position Code is globally unique (`code`).
   - Position Title is unique within each Department (`(department_id, title)`).
5. **Department Placement Guard**: Prevent position creation or update under deleted or inactive departments.
6. **Redis Caching & Telemetry**: Cache position hierarchy trees (`position:tree`) and department position lists (`position:list:{department_id}`) with automatic invalidation. Dispatch Celery tasks for background notifications.

---

## Decision

We implemented the `Position` model using SQLAlchemy 2.0 Typed ORM and extended the `Employee` model:

```python
class Position(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "positions"

    code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    title: Mapped[str] = mapped_column(String(150), index=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    department_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("departments.id", ondelete="CASCADE"), nullable=False, index=True)
    parent_position_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("positions.id", ondelete="SET NULL"), nullable=True, index=True)

    employment_category: Mapped[str] = mapped_column(String(50), nullable=False, default="Permanent")
    grade: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    level: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    maximum_headcount: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    current_headcount: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    is_managerial: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
```

Extended `Employee`:
```python
position_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("positions.id", ondelete="SET NULL"), nullable=True, index=True)
employment_start_date: Mapped[Optional[datetime.date]] = mapped_column(Date, nullable=True)
employment_end_date: Mapped[Optional[datetime.date]] = mapped_column(Date, nullable=True)
```

---

## Consequences

### Positive
- Strict organizational control over position capacity and reporting trees.
- Seamless automatic headcount tracking on employee assignment/removal.
- High performance via Redis tree caching.
- Complete audit logging and RBAC protection (`position.create`, `position.read`, `position.update`, `position.delete`, `position.restore`).

### Future HR Integration Points
- **Attendance Module**: Shift scheduling and attendance rules by Position Grade/Level.
- **Leave Module**: Leave quota entitlement rules mapped to Position Category and Level.
- **Payroll Module**: Salary bands, grade pay structures, and allowance matrices configured per Position Grade.
- **Recruitment Module**: Requisition workflows triggered when `current_headcount` < `maximum_headcount`.
- **Performance Module**: KPI & KRA templates linked to Position Title and Level.
