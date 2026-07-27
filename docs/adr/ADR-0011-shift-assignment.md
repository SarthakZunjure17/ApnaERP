# ADR-0011: Enterprise Shift Assignment & Effective-Dated Scheduling

## Status
**Accepted**

## Context
In early releases of ApnaERP, employee shift scheduling relied on a static foreign key reference `Employee.shift_id`. This static binding prevented organization support for:
1. Dynamic shift rotation (e.g., Morning, Night, Afternoon weekly rotations).
2. Historical shift auditing (determining what shift an employee was scheduled for on any past date).
3. Temporary shift overrides without destroying historical schedule context.

Milestone **HR-9** introduces effective-dated `ShiftAssignment` entities to resolve shift schedules dynamically by target date.

## Decision
1. **ShiftAssignment Entity**:
   - Model `ShiftAssignment` storing `employee_id`, `shift_id`, `effective_from` (inclusive), `effective_to` (inclusive, `NULL` for open-ended assignments), `assignment_type` (`Permanent`, `Temporary`, `Rotation`), `reason`, `assigned_by`, and `is_active`.
2. **Interval Overlap Validation**:
   - For any active shift assignment of an employee, date ranges `[effective_from, effective_to]` must not overlap.
   - Overlap check enforces: `proposed.effective_from <= (existing.effective_to or INFINITY)` AND `(proposed.effective_to or INFINITY) >= existing.effective_from`.
3. **Attendance Engine Integration**:
   - When evaluating attendance for target date `D`:
     - **Primary**: Query active `ShiftAssignment` matching `effective_from <= D <= effective_to (or effective_to IS NULL)`.
     - **Fallback**: Query `Employee.shift_id` for backwards compatibility if no shift assignment exists for date `D`.
     - **Default**: Resolve `None` if unassigned.
4. **Attendance Lock Guard**:
   - Historical shift assignments overlapping date `D` cannot be edited, ended prior to `D`, or soft-deleted if an `Attendance` record exists for date `D` with `is_locked == True`.
5. **Caching & Invalidation Strategy**:
   - High-throughput attendance resolution queries Redis cache `shift_assignment:active:{employee_id}:{date}` with a TTL of 1 hour.
   - Any create, update, end, or soft-delete operation on shift assignments invalidates all keys matching `shift_assignment:active:{employee_id}:*`.

## Consequences
- Attendance calculations reflect exact historical shift schedules regardless of present shift re-assignments.
- Open-ended assignments seamlessly extend into future dates.
- Locked attendance records remain immutable, preserving payroll fidelity.
- Fast attendance processing via Redis caching.
