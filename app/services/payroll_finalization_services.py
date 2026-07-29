import csv
import datetime
from decimal import Decimal
import io
import math
from typing import Any, Dict, List, Optional
import uuid
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import redis_manager
from app.exceptions.base import (
    DuplicateResourceException,
    NotFoundException,
    ValidationException,
)
from app.models.department import Department
from app.models.employee import Employee
from app.models.financial_posting_queue import FinancialPostingQueue
from app.models.payroll_adjustment import PayrollAdjustment
from app.models.payroll_closing import PayrollClosing
from app.models.payroll_period import PayrollPeriod, PayrollRecord
from app.models.payroll_report_snapshot import PayrollReportSnapshot
from app.models.payroll_run import PayrollRun
from app.models.user import User
from app.repositories.payroll_adjustment import PayrollAdjustmentRepository
from app.repositories.payroll_finalization_repos import (
    FinancialPostingQueueRepository,
    PayrollClosingRepository,
    PayrollReportSnapshotRepository,
)
from app.schemas.payroll_finalization import (
    BankExportRequest,
    BankExportResponse,
    DepartmentPayrollCost,
    PayrollAdjustmentCreate,
    PayrollAdjustmentUpdate,
    PayrollAnalyticsResponse,
    PayrollClosingRequest,
    PayrollReopenRequest,
    PayrollReportGenerateRequest,
    PayrollTrendItem,
)
from app.services.audit_log import audit_log_service
from app.services.file import file_service
from app.tasks.payroll_finalization_tasks import send_payroll_finalization_notification_task


class PayrollAdjustmentService:
    """
    Domain service for managing Payroll Adjustments, Variable Pay, Bonuses, Arrears, and Loan Recoveries.
    """
    def __init__(self, db: AsyncSession):
        self.db = db
        self.adj_repo = PayrollAdjustmentRepository()
        self.closing_repo = PayrollClosingRepository()

    async def _check_period_not_closed(self, period_id: uuid.UUID) -> None:
        closing = await self.closing_repo.get_by_period_id(self.db, period_id)
        if closing and closing.status in ("Closed", "Archived"):
            raise ValidationException(
                message=f"Payroll period is {closing.status.lower()} and immutable. Adjustments cannot be modified."
            )

    async def create_adjustment(
        self,
        data: PayrollAdjustmentCreate,
        current_user: Optional[User] = None,
    ) -> PayrollAdjustment:
        await self._check_period_not_closed(data.payroll_period_id)

        # Check employee & period exist
        period = await self.db.get(PayrollPeriod, data.payroll_period_id)
        if not period:
            raise NotFoundException(message=f"PayrollPeriod {data.payroll_period_id} not found.")

        emp = await self.db.get(Employee, data.employee_id)
        if not emp:
            raise NotFoundException(message=f"Employee {data.employee_id} not found.")

        adj = PayrollAdjustment(
            employee_id=data.employee_id,
            payroll_period_id=data.payroll_period_id,
            adjustment_type=data.adjustment_type.value,
            amount=data.amount,
            currency=data.currency,
            description=data.description,
            status="Pending",
        )
        adj = await self.adj_repo.create(self.db, obj_in=adj)

        if current_user:
            await audit_log_service.log_event(
                db=self.db,
                user_id=current_user.id,
                action="PAYROLL_ADJUSTMENT_CREATE",
                entity_type="PayrollAdjustment",
                entity_id=str(adj.id),
                new_data={
                    "employee_id": str(data.employee_id),
                    "payroll_period_id": str(data.payroll_period_id),
                    "type": data.adjustment_type.value,
                    "amount": float(data.amount),
                },
            )

        send_payroll_finalization_notification_task.delay(
            "PAYROLL_ADJUSTMENT_CREATED",
            str(adj.id),
            {"employee_id": str(data.employee_id), "amount": float(data.amount)},
        )

        return adj

    async def get_adjustment(self, adjustment_id: uuid.UUID) -> PayrollAdjustment:
        adj = await self.adj_repo.get_by_id(self.db, adjustment_id)
        if not adj:
            raise NotFoundException(message=f"PayrollAdjustment {adjustment_id} not found.")
        return adj

    async def update_adjustment(
        self,
        adjustment_id: uuid.UUID,
        data: PayrollAdjustmentUpdate,
        current_user: Optional[User] = None,
    ) -> PayrollAdjustment:
        adj = await self.get_adjustment(adjustment_id)
        await self._check_period_not_closed(adj.payroll_period_id)

        update_dict = data.model_dump(exclude_unset=True)
        if "status" in update_dict and isinstance(update_dict["status"], Enum):
            update_dict["status"] = update_dict["status"].value

        updated = await self.adj_repo.update(self.db, db_obj=adj, obj_in=update_dict)

        if current_user:
            await audit_log_service.log_event(
                db=self.db,
                user_id=current_user.id,
                action="PAYROLL_ADJUSTMENT_UPDATE",
                entity_type="PayrollAdjustment",
                entity_id=str(adj.id),
                new_data=update_dict,
            )
        return updated

    async def approve_adjustment(
        self,
        adjustment_id: uuid.UUID,
        current_user: User,
    ) -> PayrollAdjustment:
        adj = await self.get_adjustment(adjustment_id)
        await self._check_period_not_closed(adj.payroll_period_id)

        if adj.status == "Approved":
            return adj

        adj.status = "Approved"
        adj.approved_by = current_user.id
        adj.approved_at = datetime.datetime.now(datetime.timezone.utc)

        await self.db.commit()
        await self.db.refresh(adj)

        await audit_log_service.log_event(
            db=self.db,
            user_id=current_user.id,
            action="PAYROLL_ADJUSTMENT_APPROVE",
            entity_type="PayrollAdjustment",
            entity_id=str(adj.id),
            new_data={"status": "Approved", "approved_by": str(current_user.id)},
        )

        send_payroll_finalization_notification_task.delay(
            "PAYROLL_ADJUSTMENT_APPROVED",
            str(adj.id),
            {"employee_id": str(adj.employee_id), "amount": float(adj.amount)},
        )

        return adj

    async def reject_adjustment(
        self,
        adjustment_id: uuid.UUID,
        current_user: User,
    ) -> PayrollAdjustment:
        adj = await self.get_adjustment(adjustment_id)
        await self._check_period_not_closed(adj.payroll_period_id)

        adj.status = "Rejected"
        await self.db.commit()
        await self.db.refresh(adj)

        await audit_log_service.log_event(
            db=self.db,
            user_id=current_user.id,
            action="PAYROLL_ADJUSTMENT_REJECT",
            entity_type="PayrollAdjustment",
            entity_id=str(adj.id),
            new_data={"status": "Rejected"},
        )

        return adj

    async def delete_adjustment(
        self,
        adjustment_id: uuid.UUID,
        current_user: Optional[User] = None,
    ) -> bool:
        adj = await self.get_adjustment(adjustment_id)
        await self._check_period_not_closed(adj.payroll_period_id)

        await self.adj_repo.delete(self.db, id=adjustment_id)

        if current_user:
            await audit_log_service.log_event(
                db=self.db,
                user_id=current_user.id,
                action="PAYROLL_ADJUSTMENT_DELETE",
                entity_type="PayrollAdjustment",
                entity_id=str(adjustment_id),
                new_data={"deleted": True},
            )
        return True


class PayrollAnalyticsService:
    """
    Domain service for calculating executive payroll analytics dashboard metrics.
    """
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_analytics(
        self,
        payroll_period_id: Optional[uuid.UUID] = None,
    ) -> PayrollAnalyticsResponse:
        cache_key = f"payroll_analytics:{payroll_period_id or 'all'}"
        try:
            cached = await redis_manager.get(cache_key)
            if cached:
                import json
                data = json.loads(cached)
                return PayrollAnalyticsResponse(**data)
        except Exception:
            pass

        # Query payroll records
        query = select(PayrollRecord)
        if payroll_period_id:
            query = query.where(PayrollRecord.payroll_period_id == payroll_period_id)

        res = await self.db.execute(query)
        records = list(res.scalars().all())

        if not records:
            empty_resp = PayrollAnalyticsResponse(
                total_payroll_cost=Decimal("0.00"),
                average_salary=Decimal("0.00"),
                total_earnings=Decimal("0.00"),
                total_deductions=Decimal("0.00"),
                employee_count=0,
                highest_salary=Decimal("0.00"),
                lowest_salary=Decimal("0.00"),
                department_costs=[],
                payroll_trends=[],
            )
            return empty_resp

        emp_count = len(records)
        total_cost = sum(Decimal(str(r.gross_salary)) for r in records)
        total_earnings = total_cost
        total_deductions = sum(Decimal(str(r.total_deductions)) for r in records)
        avg_salary = (total_cost / emp_count) if emp_count > 0 else Decimal("0.00")
        highest = max(Decimal(str(r.gross_salary)) for r in records)
        lowest = min(Decimal(str(r.gross_salary)) for r in records)

        # Department cost breakdown
        dept_map: Dict[str, Dict[str, Any]] = {}
        for r in records:
            emp = await self.db.get(Employee, r.employee_id)
            dept_id_str = str(emp.department_id) if emp and emp.department_id else "Unassigned"
            dept_name = "Unassigned"
            if emp and emp.department_id:
                dept = await self.db.get(Department, emp.department_id)
                if dept:
                    dept_name = dept.name

            if dept_id_str not in dept_map:
                dept_map[dept_id_str] = {
                    "department_id": dept_id_str,
                    "department_name": dept_name,
                    "employee_count": 0,
                    "total_gross_pay": Decimal("0.00"),
                    "total_net_pay": Decimal("0.00"),
                }
            dept_map[dept_id_str]["employee_count"] += 1
            dept_map[dept_id_str]["total_gross_pay"] += Decimal(str(r.gross_salary))
            dept_map[dept_id_str]["total_net_pay"] += Decimal(str(r.net_salary))

        dept_costs = [
            DepartmentPayrollCost(
                department_id=v["department_id"],
                department_name=v["department_name"],
                employee_count=v["employee_count"],
                total_gross_pay=v["total_gross_pay"],
                total_net_pay=v["total_net_pay"],
            )
            for v in dept_map.values()
        ]

        # Trends across periods
        trend_query = select(
            PayrollRecord.payroll_period_id,
            func.sum(PayrollRecord.gross_salary).label("total_cost"),
            func.count(PayrollRecord.id).label("emp_count"),
        ).group_by(PayrollRecord.payroll_period_id)

        trend_res = await self.db.execute(trend_query)
        trend_items: List[PayrollTrendItem] = []
        for row in trend_res.all():
            p_id = row[0]
            p = await self.db.get(PayrollPeriod, p_id)
            p_name = p.period_code if p else str(p_id)
            trend_items.append(
                PayrollTrendItem(
                    payroll_period_id=str(p_id),
                    period_name=p_name,
                    total_cost=Decimal(str(row[1] or 0)),
                    employee_count=row[2],
                )
            )

        resp = PayrollAnalyticsResponse(
            total_payroll_cost=total_cost,
            average_salary=avg_salary,
            total_earnings=total_earnings,
            total_deductions=total_deductions,
            employee_count=emp_count,
            highest_salary=highest,
            lowest_salary=lowest,
            department_costs=dept_costs,
            payroll_trends=trend_items,
        )

        try:
            import json
            await redis_manager.set(cache_key, json.dumps(resp.model_dump(mode="json")), ex=300)
        except Exception:
            pass
        return resp


class PayrollReportService:
    """
    Domain service for generating multi-format payroll reports.
    """
    def __init__(self, db: AsyncSession):
        self.db = db
        self.snapshot_repo = PayrollReportSnapshotRepository()

    async def generate_report(
        self,
        request: PayrollReportGenerateRequest,
        current_user: User,
    ) -> PayrollReportSnapshot:
        period = await self.db.get(PayrollPeriod, request.payroll_period_id)
        if not period:
            raise NotFoundException(message=f"PayrollPeriod {request.payroll_period_id} not found.")

        # Fetch payroll records
        query = select(PayrollRecord).where(PayrollRecord.payroll_period_id == request.payroll_period_id)
        if request.employee_id:
            query = query.where(PayrollRecord.employee_id == request.employee_id)

        res = await self.db.execute(query)
        records = list(res.scalars().all())

        # Generate report content
        report_content = f"--- APNAERP {request.report_type.value.upper()} ---\n"
        report_content += f"Period: {period.period_code} ({period.start_date} to {period.end_date})\n"
        report_content += f"Generated At: {datetime.datetime.now(datetime.timezone.utc).isoformat()}\n"
        report_content += "---------------------------------------------------------\n"
        report_content += "Employee Code | Employee Name | Gross Pay | Deductions | Net Pay\n"

        total_gross = Decimal("0.00")
        total_ded = Decimal("0.00")
        total_net = Decimal("0.00")

        for r in records:
            emp = await self.db.get(Employee, r.employee_id)
            code = emp.employee_code if emp else "N/A"
            name = f"{emp.first_name} {emp.last_name}" if emp else "Unknown"
            gross_val = Decimal(str(r.gross_salary))
            ded_val = Decimal(str(r.total_deductions))
            net_val = Decimal(str(r.net_salary))
            report_content += f"{code} | {name} | {gross_val:.2f} | {ded_val:.2f} | {net_val:.2f}\n"
            total_gross += gross_val
            total_ded += ded_val
            total_net += net_val

        report_content += "---------------------------------------------------------\n"
        report_content += f"TOTALS: Gross={total_gross:.2f}, Deductions={total_ded:.2f}, Net={total_net:.2f}\n"

        file_bytes = report_content.encode("utf-8")
        ext = "csv" if request.format.value == "CSV" else ("txt" if request.format.value == "PDF" else "xlsx")
        filename = f"report_{request.report_type.value.replace(' ', '_').lower()}_{period.id}.{ext}"

        file_obj = await file_service.upload_bytes(
            db=self.db,
            content=file_bytes,
            filename=filename,
            mime_type="text/plain" if request.format.value != "CSV" else "text/csv",
            uploader=current_user,
        )

        snapshot = PayrollReportSnapshot(
            payroll_period_id=request.payroll_period_id,
            report_type=request.report_type.value,
            format=request.format.value,
            generated_by=current_user.id,
            generated_at=datetime.datetime.now(datetime.timezone.utc),
            file_id=file_obj.id,
            metadata_json={
                "record_count": len(records),
                "total_gross": float(total_gross),
                "total_net": float(total_net),
            },
        )
        snapshot = await self.snapshot_repo.create(self.db, obj_in=snapshot)

        await audit_log_service.log_event(
            db=self.db,
            user_id=current_user.id,
            action="PAYROLL_REPORT_GENERATE",
            entity_type="PayrollReportSnapshot",
            entity_id=str(snapshot.id),
            new_data={
                "report_type": request.report_type.value,
                "format": request.format.value,
                "period_id": str(request.payroll_period_id),
            },
        )

        return snapshot


class BankExportService:
    """
    Domain service for generating bank-compatible payment export CSV files.
    """
    def __init__(self, db: AsyncSession):
        self.db = db

    async def generate_bank_export(
        self,
        request: BankExportRequest,
        current_user: User,
    ) -> BankExportResponse:
        period = await self.db.get(PayrollPeriod, request.payroll_period_id)
        if not period:
            raise NotFoundException(entity_type="PayrollPeriod", entity_id=request.payroll_period_id)

        res = await self.db.execute(
            select(PayrollRecord).where(PayrollRecord.payroll_period_id == request.payroll_period_id)
        )
        records = list(res.scalars().all())

        if not records:
            raise ValidationException(message="No payroll records found for bank payment export.")

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Employee Code", "Employee Name", "Account Number", "IFSC / Routing", "Amount", "Currency"])

        total_amount = Decimal("0.00")
        for r in records:
            emp = await self.db.get(Employee, r.employee_id)
            code = emp.employee_code if emp else "EMP"
            name = f"{emp.first_name} {emp.last_name}" if emp else "Employee"
            net_val = Decimal(str(r.net_salary))
            writer.writerow([code, name, f"ACC_{code}", "SBIN0001234", f"{net_val:.2f}", "INR"])
            total_amount += net_val

        csv_bytes = output.getvalue().encode("utf-8")
        filename = f"bank_export_{period.id}.csv"

        file_obj = await file_service.upload_bytes(
            db=self.db,
            content=csv_bytes,
            filename=filename,
            mime_type="text/csv",
            uploader=current_user,
        )

        await audit_log_service.log_event(
            db=self.db,
            user_id=current_user.id,
            action="PAYROLL_BANK_EXPORT",
            entity_type="PayrollPeriod",
            entity_id=str(period.id),
            new_data={
                "bank_format": request.bank_format,
                "record_count": len(records),
                "total_amount": float(total_amount),
            },
        )

        return BankExportResponse(
            payroll_period_id=request.payroll_period_id,
            file_id=file_obj.id,
            file_name=filename,
            record_count=len(records),
            total_amount=total_amount,
            generated_at=datetime.datetime.now(datetime.timezone.utc),
        )


class PayrollClosingService:
    """
    Domain service for handling payroll period Closing, Reopening, and Archival.
    """
    def __init__(self, db: AsyncSession):
        self.db = db
        self.closing_repo = PayrollClosingRepository()

    async def close_payroll(
        self,
        payroll_period_id: uuid.UUID,
        remarks: Optional[str],
        current_user: User,
    ) -> PayrollClosing:
        period = await self.db.get(PayrollPeriod, payroll_period_id)
        if not period:
            raise NotFoundException(entity_type="PayrollPeriod", entity_id=payroll_period_id)

        # Check if period already closed
        existing = await self.closing_repo.get_by_period_id(self.db, payroll_period_id)
        if existing and existing.status in ("Closed", "Archived"):
            raise ValidationException(message=f"Payroll period is already {existing.status.lower()}.")

        # Ensure payroll run exists and is Completed or Locked
        run_res = await self.db.execute(
            select(PayrollRun).where(PayrollRun.payroll_period_id == payroll_period_id)
        )
        runs = list(run_res.scalars().all())
        if not runs or not any(r.status in ("Completed", "Locked") for r in runs):
            raise ValidationException(message="Payroll period cannot be closed until payroll execution is completed.")

        if existing:
            existing.status = "Closed"
            existing.closed_by = current_user.id
            existing.closed_at = datetime.datetime.now(datetime.timezone.utc)
            existing.closing_remarks = remarks
            closing = await self.closing_repo.update(self.db, db_obj=existing, obj_in={})
        else:
            closing = PayrollClosing(
                payroll_period_id=payroll_period_id,
                closed_by=current_user.id,
                closed_at=datetime.datetime.now(datetime.timezone.utc),
                closing_remarks=remarks,
                status="Closed",
            )
            closing = await self.closing_repo.create(self.db, obj_in=closing)

        period.status = "Closed"
        await self.db.commit()

        await audit_log_service.log_event(
            db=self.db,
            user_id=current_user.id,
            action="PAYROLL_PERIOD_CLOSE",
            entity_type="PayrollClosing",
            entity_id=str(closing.id),
            new_data={"status": "Closed", "remarks": remarks},
        )

        send_payroll_finalization_notification_task.delay(
            "PAYROLL_PERIOD_CLOSED",
            str(payroll_period_id),
            {"closed_by": str(current_user.id)},
        )

        return closing

    async def reopen_payroll(
        self,
        payroll_period_id: uuid.UUID,
        reopen_reason: str,
        current_user: User,
    ) -> PayrollClosing:
        period = await self.db.get(PayrollPeriod, payroll_period_id)
        if not period:
            raise NotFoundException(entity_type="PayrollPeriod", entity_id=payroll_period_id)

        closing = await self.closing_repo.get_by_period_id(self.db, payroll_period_id)
        if not closing or closing.status != "Closed":
            raise ValidationException(message="Only closed payroll periods can be reopened.")

        closing.status = "Open"
        closing.reopened_by = current_user.id
        closing.reopened_at = datetime.datetime.now(datetime.timezone.utc)

        period.status = "Open"
        await self.db.commit()
        await self.db.refresh(closing)

        await audit_log_service.log_event(
            db=self.db,
            user_id=current_user.id,
            action="PAYROLL_PERIOD_REOPEN",
            entity_type="PayrollClosing",
            entity_id=str(closing.id),
            new_data={"status": "Open", "reopen_reason": reopen_reason},
        )

        send_payroll_finalization_notification_task.delay(
            "PAYROLL_PERIOD_REOPENED",
            str(payroll_period_id),
            {"reopened_by": str(current_user.id), "reason": reopen_reason},
        )

        return closing

    async def archive_payroll(
        self,
        payroll_period_id: uuid.UUID,
        current_user: User,
    ) -> PayrollClosing:
        period = await self.db.get(PayrollPeriod, payroll_period_id)
        if not period:
            raise NotFoundException(entity_type="PayrollPeriod", entity_id=payroll_period_id)

        closing = await self.closing_repo.get_by_period_id(self.db, payroll_period_id)
        if not closing or closing.status != "Closed":
            raise ValidationException(message="Only closed payroll periods can be archived.")

        closing.status = "Archived"
        period.status = "Archived"
        await self.db.commit()
        await self.db.refresh(closing)

        await audit_log_service.log_event(
            db=self.db,
            user_id=current_user.id,
            action="PAYROLL_PERIOD_ARCHIVE",
            entity_type="PayrollClosing",
            entity_id=str(closing.id),
            new_data={"status": "Archived"},
        )

        return closing


class FinancialIntegrationService:
    """
    Domain service for generating and publishing financial posting payloads for future GL integration.
    """
    def __init__(self, db: AsyncSession):
        self.db = db
        self.queue_repo = FinancialPostingQueueRepository()

    async def publish_financial_payload(
        self,
        payroll_period_id: uuid.UUID,
        current_user: User,
    ) -> FinancialPostingQueue:
        period = await self.db.get(PayrollPeriod, payroll_period_id)
        if not period:
            raise NotFoundException(entity_type="PayrollPeriod", entity_id=payroll_period_id)

        res = await self.db.execute(
            select(PayrollRecord).where(PayrollRecord.payroll_period_id == payroll_period_id)
        )
        records = list(res.scalars().all())

        if not records:
            raise ValidationException(message="Cannot publish financial payload for an unexecuted payroll period.")

        total_gross = sum(Decimal(str(r.gross_salary)) for r in records)
        total_deductions = sum(Decimal(str(r.total_deductions)) for r in records)
        total_net = sum(Decimal(str(r.net_salary)) for r in records)

        payload_dict = {
            "payroll_period_id": str(payroll_period_id),
            "period_name": period.period_code,
            "currency": "INR",
            "journal_entries_summary": {
                "debit_gross_salary_expense": float(total_gross),
                "credit_statutory_deductions_liability": float(total_deductions),
                "credit_net_payroll_payable": float(total_net),
            },
            "record_count": len(records),
            "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }

        queue_item = FinancialPostingQueue(
            payroll_period_id=payroll_period_id,
            posting_status="Pending",
            payload=payload_dict,
        )
        queue_item = await self.queue_repo.create(self.db, obj_in=queue_item)

        await audit_log_service.log_event(
            db=self.db,
            user_id=current_user.id,
            action="PAYROLL_FINANCIAL_PUBLISH",
            entity_type="FinancialPostingQueue",
            entity_id=str(queue_item.id),
            new_data={"payroll_period_id": str(payroll_period_id), "total_gross": float(total_gross)},
        )

        send_payroll_finalization_notification_task.delay(
            "PAYROLL_FINANCIAL_PAYLOAD_PUBLISHED",
            str(queue_item.id),
            {"payroll_period_id": str(payroll_period_id)},
        )

        return queue_item
