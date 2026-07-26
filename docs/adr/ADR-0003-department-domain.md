# ADR-0003: Department Management Domain & Hierarchical Tree Architecture

- **Status**: Accepted
- **Deciders**: Principal Backend Engineer & Core Architecture Team
- **Date**: 2026-07-26
- **Milestone**: HR-1 (Release v0.3.0)

---

## Context and Problem Statement

ApnaERP is initiating the Human Resources (HR) domain. We require an organizational hierarchy structure to represent companies, divisions, departments, sub-departments, and teams.

The Department entity serves as the root parent node for Employees, Cost Centers, Approvals, and future HR operations. We need a design that supports flexible nested hierarchies, prevents invalid states (e.g. circular parent loops or deleting parent departments with active children), integrates seamlessly with platform infrastructure (Redis caching, Celery background tasks, Audit Logging, RBAC), and provides high performance for tree queries.

---

## Decision Drivers

1. **Self-Referential Tree Representation**: Departments can have a `parent_id` linking to another `Department` ID.
2. **Circular Reference Safeguard**: When creating or modifying a department's parent, the service must traverse ancestry to reject circular parent references (e.g. A -> B -> C -> A).
3. **Active Children Deletion Protection**: A department with active child sub-departments cannot be soft-deleted until its children are moved or deleted.
4. **Redis Cache Performance**: Hierarchical tree queries (`GET /departments/tree`) read from a Redis cache (`department:tree`). All mutation operations (Create, Update, Soft Delete, Restore) automatically invalidate the cache.
5. **Asynchronous Background Processing**: Mutation events trigger Celery background tasks (`send_department_notification_task`) without blocking HTTP response times.
6. **Audit & RBAC Enforcement**: All actions create structured audit logs (`DEPARTMENT_CREATE`, `DEPARTMENT_UPDATE`, etc.) and require RBAC permissions (`department.create`, `department.read`, `department.update`, `department.delete`, `department.restore`).

---

## Decision

We decided to implement the `Department` model using SQLAlchemy 2.0 Typed ORM with self-referential relationships:

```python
class Department(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "departments"
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    parent_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("departments.id", ondelete="SET NULL"))
    manager_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))

    parent = relationship("Department", remote_side="Department.id", back_populates="children")
    children = relationship("Department", back_populates="parent", cascade="all, delete-orphan")
```

---

## Consequences

### Positive
- Flexible organizational tree supporting arbitrary depth (e.g. Company -> Division -> Department -> Sub-department -> Team).
- Fast tree rendering via Redis caching.
- Enforced integrity preventing orphan loops or accidental deletion of parent departments.
- Future HR modules (Employees, Positions, Payroll) can cleanly reference `department_id`.

### Negative / Trade-offs
- Deeply nested trees require careful recursion handling during serialization (handled via Pydantic v2 `DepartmentTreeResponse.model_rebuild()`).

---

## Alternatives Considered

1. **Adjacency List vs Nested Set Model**: Selected Adjacency List with `selectinload` for simplicity, readability, and compatibility with standard relational ORM patterns.
