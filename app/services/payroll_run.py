import datetime
import logging
from typing import Any, List, Optional, Tuple
import uuid
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import redis_manager
from app.exceptions.base import (
    ApnaERPException,
    DuplicateResourceException,
    ForbiddenException,
    NotFoundException,
    ValidationException,
)
from app.models.file import File
from app.models.payroll_run import PayrollRun
from app.models.payslip import Payslip
from app.models.user import User
from app.repositories.employee import employee_repository
from app.repositories.payroll_period import payroll_period_repository, payroll_record_repository
from app.repositories.payroll_run import payroll_run_repository
from app.repositories.payslip import payslip_repository
from app.schemas.payroll_run import PayrollRunCreate, PayrollRunUpdate
from app.services.base_service import BaseService
from app.services.file import file_service
from app.tasks.payroll_run_tasks import (
    send_payslip_published_notification_task,
    send_payroll_run_notification_task,
)
from app.utils.audit import log_audit
from app.utils.pagination import PaginatedResult, PaginationParams
from app.utils.pdf_generator import generate_payslip_pdf_bytes
from app.utils.sorting import SortCriterion

logger = logging.getLogger("app.services.payroll_run")

CACHE_PREFIX_RUN = "payroll_run"
CACHE_PREFIX_PAYSLIP = "payslip"


class PayrollRunService(BaseService[payroll_run_repository.__class__]):
    """
    Domain service for Payroll Runs & Payslips Management.
    Handles run creation, execution workflow, ReportLab PDF generation,
    File Storage integration, publishing, downloading, caching, and Celery notifications.
    """

    def __init__(self, db: AsyncSession):
        super().__init__(payroll_run_repository)
        self.db = db
        self.run_repository = payroll_run_repository
        self.payslip_repository = payslip_repository
        self.period_repository = payroll_period_repository
        self.record_repository = payroll_record_repository
        self.employee_repository = employee_repository
        self.file_service = file_service

    async def get_run_by_id(self, run_id: uuid.UUID) -> PayrollRun:
        """Retrieves a PayrollRun by ID or raises NotFoundException."""
        run = await self.run_repository.get_by_id(self.db, run_id)
        if not run:
            raise NotFoundException(message=f"PayrollRun with ID '{run_id}' not found.")
        return run

    async def _invalidate_cache(self, run_id: Optional[uuid.UUID] = None, employee_id: Optional[uuid.UUID] = None):
        """Clears Payroll Run and Payslip Redis caches."""
        try:
            await redis_manager.delete_pattern(f"{CACHE_PREFIX_RUN}:*")
            await redis_manager.delete_pattern(f"{CACHE_PREFIX_PAYSLIP}:*")
            if run_id:
                await redis_manager.delete(f"{CACHE_PREFIX_RUN}:id:{run_id}")
            if employee_id:
                await redis_manager.delete(f"{CACHE_PREFIX_PAYSLIP}:employee:{employee_id}")
        except Exception as exc:
            logger.warning(f"Failed to clear Redis payroll run / payslip cache: {exc}")

    async def create_payroll_run(
        self,
        data: PayrollRunCreate,
        current_user: Optional[User] = None,
    ) -> PayrollRun:
        """
        Creates a new Payroll Run for a specified Payroll Period and Run Type.
        """
        period = await self.period_repository.get_by_id(self.db, data.payroll_period_id)
        if not period:
            raise NotFoundException(message=f"PayrollPeriod with ID '{data.payroll_period_id}' not found.")

        # Check unique constraint (period_id, run_type)
        existing_run = await self.run_repository.get_by_period_and_type(
            self.db, data.payroll_period_id, data.run_type.value if hasattr(data.run_type, 'value') else data.run_type
        )
        if existing_run:
            raise DuplicateResourceException(
                message=f"A PayrollRun of type '{data.run_type}' already exists for period '{period.period_code}'."
            )

        # Generate unique run_number
        run_type_str = data.run_type.value if hasattr(data.run_type, 'value') else data.run_type
        run_number = f"RUN-{period.period_code}-{run_type_str[:3].upper()}-{uuid.uuid4().hex[:4].upper()}"

        run_obj = PayrollRun(
            payroll_period_id=data.payroll_period_id,
            run_number=run_number,
            run_type=run_type_str,
            status="Draft",
            remarks=data.remarks,
        )

        self.db.add(run_obj)
        await self.db.commit()
        await self.db.refresh(run_obj)

        await self._invalidate_cache(run_id=run_obj.id)

        user_id = current_user.id if current_user else None
        username = current_user.username if current_user else "system"
        await log_audit(
            self.db,
            action="PAYROLL_RUN_CREATE",
            entity_type="PayrollRun",
            entity_id=run_obj.id,
            user_id=user_id,
            username=username,
            new_data={"run_number": run_number, "period_id": str(data.payroll_period_id), "run_type": run_type_str},
            status_code=201,
        )

        return run_obj

    async def start_payroll_run(
        self,
        run_id: uuid.UUID,
        current_user: Optional[User] = None,
    ) -> PayrollRun:
        """
        Transitions a Payroll Run to 'Processing' state.
        """
        run = await self.run_repository.get_by_id(self.db, run_id)
        if not run:
            raise NotFoundException(message=f"PayrollRun with ID '{run_id}' not found.")

        if run.status == "Locked":
            raise ApnaERPException(message="Locked payroll runs cannot be modified.", error_code="RUN_LOCKED", status_code=400)

        run.status = "Processing"
        run.started_at = datetime.datetime.now(datetime.timezone.utc)
        if current_user:
            run.started_by = current_user.id

        await self.db.commit()
        await self.db.refresh(run)

        await self._invalidate_cache(run_id=run_id)

        user_id = current_user.id if current_user else None
        username = current_user.username if current_user else "system"
        await log_audit(
            self.db,
            action="PAYROLL_RUN_START",
            entity_type="PayrollRun",
            entity_id=run.id,
            user_id=user_id,
            username=username,
            new_data={"status": "Processing", "started_at": run.started_at.isoformat()},
            status_code=200,
        )

        return run

    async def complete_payroll_run(
        self,
        run_id: uuid.UUID,
        current_user: Optional[User] = None,
    ) -> PayrollRun:
        """
        Transitions a Payroll Run to 'Completed' state and dispatches Celery notification to Payroll Team.
        """
        run = await self.run_repository.get_by_id(self.db, run_id)
        if not run:
            raise NotFoundException(message=f"PayrollRun with ID '{run_id}' not found.")

        if run.status == "Locked":
            raise ApnaERPException(message="Locked payroll runs cannot be modified.", error_code="RUN_LOCKED", status_code=400)

        run.status = "Completed"
        run.completed_at = datetime.datetime.now(datetime.timezone.utc)

        await self.db.commit()
        await self.db.refresh(run)

        await self._invalidate_cache(run_id=run_id)

        user_id_str = str(current_user.id) if current_user else "system"
        try:
            send_payroll_run_notification_task.delay(
                action="COMPLETED",
                run_id=str(run.id),
                run_number=run.run_number,
                actor_id=user_id_str,
            )
        except Exception as exc:
            logger.warning(f"Failed to dispatch Celery notification task for payroll run completion: {exc}")

        user_id = current_user.id if current_user else None
        username = current_user.username if current_user else "system"
        await log_audit(
            self.db,
            action="PAYROLL_RUN_COMPLETE",
            entity_type="PayrollRun",
            entity_id=run.id,
            user_id=user_id,
            username=username,
            new_data={"status": "Completed", "completed_at": run.completed_at.isoformat()},
            status_code=200,
        )

        return run

    async def lock_payroll_run(
        self,
        run_id: uuid.UUID,
        current_user: Optional[User] = None,
    ) -> PayrollRun:
        """
        Locks a Payroll Run permanently. Locked runs cannot be modified.
        """
        run = await self.run_repository.get_by_id(self.db, run_id)
        if not run:
            raise NotFoundException(message=f"PayrollRun with ID '{run_id}' not found.")

        if run.status != "Completed":
            raise ValidationException(message=f"Only 'Completed' payroll runs can be locked. Current status: '{run.status}'.")

        run.status = "Locked"
        run.locked_at = datetime.datetime.now(datetime.timezone.utc)

        await self.db.commit()
        await self.db.refresh(run)

        await self._invalidate_cache(run_id=run_id)

        user_id_str = str(current_user.id) if current_user else "system"
        try:
            send_payroll_run_notification_task.delay(
                action="LOCKED",
                run_id=str(run.id),
                run_number=run.run_number,
                actor_id=user_id_str,
            )
        except Exception as exc:
            logger.warning(f"Failed to dispatch Celery notification task for payroll run lock: {exc}")

        user_id = current_user.id if current_user else None
        username = current_user.username if current_user else "system"
        await log_audit(
            self.db,
            action="PAYROLL_RUN_LOCK",
            entity_type="PayrollRun",
            entity_id=run.id,
            user_id=user_id,
            username=username,
            new_data={"status": "Locked", "locked_at": run.locked_at.isoformat()},
            status_code=200,
        )

        return run

    async def generate_payslips(
        self,
        run_id: uuid.UUID,
        current_user: Optional[User] = None,
    ) -> List[Payslip]:
        """
        Generates PDF Payslip documents for all PayrollRecords in the run's PayrollPeriod,
        stores them via FileService, and creates/updates Payslip entities.
        """
        run = await self.run_repository.get_by_id(self.db, run_id)
        if not run:
            raise NotFoundException(message=f"PayrollRun with ID '{run_id}' not found.")

        if run.status == "Locked":
            raise ApnaERPException(message="Locked payroll runs cannot be modified.", error_code="RUN_LOCKED", status_code=400)

        period = await self.period_repository.get_by_id(self.db, run.payroll_period_id)
        records = await self.record_repository.get_records_by_period(self.db, period.id)

        if not records:
            raise ValidationException(message=f"No generated payroll records found for period '{period.period_code}'. Generate payroll first.")

        payslips = []
        gen_time = datetime.datetime.now(datetime.timezone.utc)

        for record in records:
            emp = record.employee
            if not emp:
                continue

            # Build Payslip number: PS-{period_code}-{emp_code}
            payslip_num = f"PS-{period.period_code}-{emp.employee_code}"

            # Format component dicts for ReportLab PDF
            comp_list = []
            if record.components:
                for c in record.components:
                    comp_list.append({
                        "name": c.component_name,
                        "type": c.component_type,
                        "amount": float(c.amount),
                    })

            # Generate ReportLab PDF Bytes
            dept_name = emp.department.name if emp.department else "N/A"
            full_name = f"{emp.first_name} {emp.last_name or ''}".strip()

            pdf_bytes = generate_payslip_pdf_bytes(
                payslip_number=payslip_num,
                employee_code=emp.employee_code,
                employee_name=full_name,
                department_name=dept_name,
                work_email=emp.work_email or "",
                period_code=period.period_code,
                period_start=period.start_date,
                period_end=period.end_date,
                gross_salary=float(record.gross_salary),
                total_earnings=float(record.total_earnings),
                total_deductions=float(record.total_deductions),
                net_salary=float(record.net_salary),
                components=comp_list,
                generated_at=gen_time,
            )

            # Store PDF via FileService
            pdf_filename = f"{payslip_num}.pdf"
            file_record = await self.file_service.upload_bytes(
                self.db,
                content=pdf_bytes,
                filename=pdf_filename,
                mime_type="application/pdf",
                uploader=current_user,
                entity_type="Payslip",
                entity_id=str(record.id),
            )

            # Create or Update Payslip record
            existing_payslip = await self.payslip_repository.get_by_payroll_record_id(self.db, record.id)
            if existing_payslip:
                existing_payslip.payslip_number = payslip_num
                existing_payslip.gross_salary = record.gross_salary
                existing_payslip.total_earnings = record.total_earnings
                existing_payslip.total_deductions = record.total_deductions
                existing_payslip.net_salary = record.net_salary
                existing_payslip.pdf_file_id = file_record.id
                existing_payslip.generated_at = gen_time
                existing_payslip.status = "Generated"
                payslips.append(existing_payslip)
            else:
                payslip_obj = Payslip(
                    payroll_record_id=record.id,
                    payslip_number=payslip_num,
                    employee_id=emp.id,
                    payroll_period_id=period.id,
                    gross_salary=record.gross_salary,
                    total_earnings=record.total_earnings,
                    total_deductions=record.total_deductions,
                    net_salary=record.net_salary,
                    pdf_file_id=file_record.id,
                    generated_at=gen_time,
                    status="Generated",
                )
                self.db.add(payslip_obj)
                payslips.append(payslip_obj)

        await self.db.commit()

        # Re-fetch payslips with selectinload to prevent expired state attribute access issues in async handlers
        payslips = await self.payslip_repository.get_by_period_id(self.db, period.id)

        await self._invalidate_cache(run_id=run_id)

        user_id = current_user.id if current_user else None
        username = current_user.username if current_user else "system"
        await log_audit(
            self.db,
            action="PAYSLIP_GENERATE",
            entity_type="PayrollRun",
            entity_id=run.id,
            user_id=user_id,
            username=username,
            new_data={"run_id": str(run.id), "total_payslips": len(payslips)},
            status_code=200,
        )

        return payslips

    async def publish_payslips(
        self,
        run_id: uuid.UUID,
        current_user: Optional[User] = None,
    ) -> List[Payslip]:
        """
        Publishes payslips for a Payroll Run and dispatches Celery notifications to employees.
        """
        run = await self.run_repository.get_by_id(self.db, run_id)
        if not run:
            raise NotFoundException(message=f"PayrollRun with ID '{run_id}' not found.")

        if run.status == "Locked":
            raise ApnaERPException(message="Locked payroll runs cannot be modified.", error_code="RUN_LOCKED", status_code=400)

        payslips = await self.payslip_repository.get_by_period_id(self.db, run.payroll_period_id)
        if not payslips:
            raise ValidationException(message="No payslips generated for this run yet. Run generate-payslips first.")

        pub_time = datetime.datetime.now(datetime.timezone.utc)
        emp_ids = []

        for payslip in payslips:
            payslip.status = "Published"
            payslip.published_at = pub_time
            emp_ids.append(str(payslip.employee_id))

        await self.db.commit()

        # Re-fetch payslips with selectinload to prevent expired state attribute access issues in async handlers
        payslips = await self.payslip_repository.get_by_period_id(self.db, run.payroll_period_id)

        await self._invalidate_cache(run_id=run_id)

        user_id_str = str(current_user.id) if current_user else "system"
        try:
            send_payslip_published_notification_task.delay(
                run_id=str(run.id),
                employee_ids=emp_ids,
                actor_id=user_id_str,
            )
        except Exception as exc:
            logger.warning(f"Failed to dispatch Celery notification task for published payslips: {exc}")

        user_id = current_user.id if current_user else None
        username = current_user.username if current_user else "system"
        await log_audit(
            self.db,
            action="PAYSLIP_PUBLISH",
            entity_type="PayrollRun",
            entity_id=run.id,
            user_id=user_id,
            username=username,
            new_data={"run_id": str(run.id), "total_published": len(payslips)},
            status_code=200,
        )

        return payslips

    async def regenerate_failed_payslips(
        self,
        run_id: uuid.UUID,
        current_user: Optional[User] = None,
    ) -> List[Payslip]:
        """
        Retries PDF generation for any payslips missing PDF files or stuck in Draft state.
        """
        return await self.generate_payslips(run_id=run_id, current_user=current_user)

    async def get_payslip_by_id(self, payslip_id: uuid.UUID) -> Payslip:
        """Retrieves a Payslip by ID."""
        payslip = await self.payslip_repository.get_by_id(self.db, payslip_id)
        if not payslip:
            raise NotFoundException(message=f"Payslip with ID '{payslip_id}' not found.")
        return payslip

    async def get_employee_payslips(self, employee_id: uuid.UUID) -> List[Payslip]:
        """Retrieves all payslips for an employee."""
        emp = await self.employee_repository.get_by_id(self.db, employee_id)
        if not emp or emp.is_deleted:
            raise NotFoundException(message=f"Employee with ID '{employee_id}' not found.")
        return await self.payslip_repository.get_by_employee_id(self.db, employee_id)

    async def download_payslip_pdf(
        self,
        payslip_id: uuid.UUID,
        current_user: User,
    ) -> Tuple[Payslip, File, bytes]:
        """
        Validates authorization, retrieves File record and PDF bytes for streaming download.
        """
        payslip = await self.get_payslip_by_id(payslip_id)
        if not payslip.pdf_file_id:
            raise NotFoundException(message=f"PDF document not yet generated for payslip '{payslip.payslip_number}'.")

        # Authorization check: Superuser/Admin or employee owner
        is_owner = False
        if current_user.id:
            emp = await self.employee_repository.get_by_user_id(self.db, current_user.id)
            if emp and str(emp.id) == str(payslip.employee_id):
                is_owner = True

        if not current_user.is_superuser and not is_owner:
            # Check if user has explicit HR/Payroll permission (passed from router)
            pass

        file_record, file_bytes = await self.file_service.get_file_for_download(
            self.db, file_id=payslip.pdf_file_id, current_user=current_user
        )

        return payslip, file_record, file_bytes

    async def list_payroll_runs(
        self,
        params: PaginationParams,
        period_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        run_type: Optional[str] = None,
        search_term: Optional[str] = None,
        sorting: Optional[List[SortCriterion]] = None,
    ) -> PaginatedResult[PayrollRun]:
        """Lists payroll runs with pagination, filtering, and sorting."""
        return await self.run_repository.get_filtered_runs(
            self.db,
            params=params,
            period_id=period_id,
            status=status,
            run_type=run_type,
            search_term=search_term,
            sorting=sorting,
        )

    async def list_payslips(
        self,
        params: PaginationParams,
        employee_id: Optional[uuid.UUID] = None,
        period_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        search_term: Optional[str] = None,
        sorting: Optional[List[SortCriterion]] = None,
    ) -> PaginatedResult[Payslip]:
        """Lists payslips with pagination, filtering, and sorting."""
        return await self.payslip_repository.get_filtered_payslips(
            self.db,
            params=params,
            employee_id=employee_id,
            period_id=period_id,
            status=status,
            search_term=search_term,
            sorting=sorting,
        )
