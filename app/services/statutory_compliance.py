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
from app.models.country import Country
from app.models.employee_statutory_profile import EmployeeStatutoryProfile
from app.models.statutory_rule import StatutoryRule, StatutoryRuleSlab
from app.models.user import User
from app.repositories.country import country_repository
from app.repositories.employee import employee_repository
from app.repositories.employee_statutory_profile import employee_statutory_profile_repository
from app.repositories.statutory_rule import (
    statutory_rule_repository,
    statutory_rule_slab_repository,
)
from app.schemas.country import CountryCreate, CountryUpdate
from app.schemas.employee_statutory_profile import (
    EmployeeStatutoryProfileCreate,
    EmployeeStatutoryProfileUpdate,
)
from app.schemas.statutory_rule import (
    StatutoryCalculationResponse,
    StatutoryDeductionResult,
    StatutoryRuleCreate,
    StatutoryRuleSlabCreate,
    StatutoryRuleSlabUpdate,
    StatutoryRuleUpdate,
)
from app.services.base_service import BaseService
from app.tasks.statutory_tasks import send_statutory_rule_notification_task
from app.utils.audit import log_audit
from app.utils.pagination import PaginatedResult, PaginationParams
from app.utils.sorting import SortCriterion

logger = logging.getLogger("app.services.statutory_compliance")

CACHE_PREFIX_COUNTRY = "country"
CACHE_PREFIX_RULE = "statutory_rule"
CACHE_PREFIX_PROFILE = "statutory_profile"


class StatutoryComplianceService(BaseService[statutory_rule_repository.__class__]):
    """
    Domain Service establishing country-independent Statutory Compliance Engine.
    Handles Countries, Statutory Rules & Slabs, Employee Statutory Profiles, Rule Resolution,
    Deduction Calculation, Redis Cache Invalidation, and Audit Logging.
    """

    def __init__(self, db: AsyncSession):
        super().__init__(statutory_rule_repository)
        self.db = db
        self.country_repo = country_repository
        self.rule_repo = statutory_rule_repository
        self.slab_repo = statutory_rule_slab_repository
        self.profile_repo = employee_statutory_profile_repository
        self.employee_repo = employee_repository

    async def _invalidate_cache(self, country_code: Optional[str] = None, employee_id: Optional[uuid.UUID] = None):
        """Clears Statutory Compliance Redis cache entries."""
        try:
            await redis_manager.delete_pattern(f"{CACHE_PREFIX_COUNTRY}:*")
            await redis_manager.delete_pattern(f"{CACHE_PREFIX_RULE}:*")
            await redis_manager.delete_pattern(f"{CACHE_PREFIX_PROFILE}:*")
        except Exception as exc:
            logger.warning(f"Failed to clear Redis statutory compliance cache: {exc}")

    # =========================================================================
    # 1. COUNTRY MANAGEMENT
    # =========================================================================

    async def create_country(
        self, data: CountryCreate, current_user: Optional[User] = None
    ) -> Country:
        """Creates a new Country jurisdiction."""
        existing = await self.country_repo.get_by_code(self.db, data.code)
        if existing:
            raise DuplicateResourceException(message=f"Country with ISO code '{data.code.upper()}' already exists.")

        country = Country(
            code=data.code.upper(),
            name=data.name,
            currency=data.currency.upper(),
            is_active=data.is_active,
        )
        self.db.add(country)
        await self.db.commit()
        await self.db.refresh(country)

        await self._invalidate_cache(country_code=country.code)

        user_id = current_user.id if current_user else None
        username = current_user.username if current_user else "system"
        await log_audit(
            self.db,
            action="COUNTRY_CREATE",
            entity_type="Country",
            entity_id=country.id,
            user_id=user_id,
            username=username,
            new_data={"code": country.code, "name": country.name, "currency": country.currency},
            status_code=201,
        )

        return country

    async def update_country(
        self, id: uuid.UUID, data: CountryUpdate, current_user: Optional[User] = None
    ) -> Country:
        """Updates an existing Country."""
        country = await self.country_repo.get_by_id(self.db, id)
        if not country:
            raise NotFoundException(message=f"Country with ID '{id}' not found.")

        if data.name is not None:
            country.name = data.name
        if data.currency is not None:
            country.currency = data.currency.upper()
        if data.is_active is not None:
            country.is_active = data.is_active

        await self.db.commit()
        await self.db.refresh(country)

        await self._invalidate_cache(country_code=country.code)

        user_id = current_user.id if current_user else None
        username = current_user.username if current_user else "system"
        await log_audit(
            self.db,
            action="COUNTRY_UPDATE",
            entity_type="Country",
            entity_id=country.id,
            user_id=user_id,
            username=username,
            new_data={"code": country.code, "name": country.name, "is_active": country.is_active},
            status_code=200,
        )

        return country

    async def delete_country(
        self, id: uuid.UUID, current_user: Optional[User] = None
    ) -> None:
        """Deletes a Country record."""
        country = await self.country_repo.get_by_id(self.db, id)
        if not country:
            raise NotFoundException(message=f"Country with ID '{id}' not found.")

        code = country.code
        await self.country_repo.delete(self.db, id=id)

        await self._invalidate_cache(country_code=code)

        user_id = current_user.id if current_user else None
        username = current_user.username if current_user else "system"
        await log_audit(
            self.db,
            action="COUNTRY_DELETE",
            entity_type="Country",
            entity_id=id,
            user_id=user_id,
            username=username,
            previous_data={"code": code},
            status_code=200,
        )

    async def get_country_by_id(self, id: uuid.UUID) -> Country:
        """Retrieves a Country by ID."""
        country = await self.country_repo.get_by_id(self.db, id)
        if not country:
            raise NotFoundException(message=f"Country with ID '{id}' not found.")
        return country

    async def list_countries(
        self,
        params: PaginationParams,
        is_active: Optional[bool] = None,
        search_term: Optional[str] = None,
        sorting: Optional[List[SortCriterion]] = None,
    ) -> PaginatedResult[Country]:
        """Lists countries with filtering and pagination."""
        return await self.country_repo.get_filtered_countries(
            self.db,
            params=params,
            is_active=is_active,
            search_term=search_term,
            sorting=sorting,
        )

    # =========================================================================
    # 2. STATUTORY RULES & SLABS MANAGEMENT
    # =========================================================================

    async def create_rule(
        self, data: StatutoryRuleCreate, current_user: Optional[User] = None
    ) -> StatutoryRule:
        """Creates a new StatutoryRule policy."""
        country = await self.country_repo.get_by_id(self.db, data.country_id)
        if not country:
            raise NotFoundException(message=f"Country with ID '{data.country_id}' not found.")

        existing_rule = await self.rule_repo.get_by_code(self.db, data.rule_code)
        if existing_rule:
            raise DuplicateResourceException(message=f"StatutoryRule with code '{data.rule_code}' already exists.")

        if data.effective_to and data.effective_to < data.effective_from:
            raise ValidationException(message="effective_to date cannot be earlier than effective_from date.")

        rule_type_val = data.rule_type.value if hasattr(data.rule_type, "value") else str(data.rule_type)
        calc_method_val = data.calculation_method.value if hasattr(data.calculation_method, "value") else str(data.calculation_method)

        rule = StatutoryRule(
            rule_code=data.rule_code.upper(),
            rule_name=data.rule_name,
            country_id=data.country_id,
            rule_type=rule_type_val,
            calculation_method=calc_method_val,
            effective_from=data.effective_from,
            effective_to=data.effective_to,
            is_active=data.is_active,
            priority=data.priority,
            description=data.description,
        )
        self.db.add(rule)
        await self.db.flush()

        # Add initial slabs if provided
        if data.slabs:
            for slab_in in data.slabs:
                if slab_in.max_amount is not None and slab_in.max_amount < slab_in.min_amount:
                    raise ValidationException(message=f"Slab max_amount ({slab_in.max_amount}) cannot be less than min_amount ({slab_in.min_amount}).")
                slab_obj = StatutoryRuleSlab(
                    statutory_rule_id=rule.id,
                    min_amount=slab_in.min_amount,
                    max_amount=slab_in.max_amount,
                    percentage=slab_in.percentage,
                    fixed_amount=slab_in.fixed_amount,
                    sequence=slab_in.sequence,
                )
                self.db.add(slab_obj)

        await self.db.commit()
        
        # Re-fetch rule with selectin options
        rule = await self.rule_repo.get_by_id(self.db, rule.id)

        await self._invalidate_cache(country_code=country.code)

        actor_id_str = str(current_user.id) if current_user else "system"
        try:
            send_statutory_rule_notification_task.delay(
                action="CREATED",
                rule_id=str(rule.id),
                rule_code=rule.rule_code,
                rule_name=rule.rule_name,
                country_code=country.code,
                actor_id=actor_id_str,
            )
        except Exception as exc:
            logger.warning(f"Failed to dispatch Celery statutory rule notification task: {exc}")

        user_id = current_user.id if current_user else None
        username = current_user.username if current_user else "system"
        await log_audit(
            self.db,
            action="STATUTORY_RULE_CREATE",
            entity_type="StatutoryRule",
            entity_id=rule.id,
            user_id=user_id,
            username=username,
            new_data={"rule_code": rule.rule_code, "rule_type": rule.rule_type, "country": country.code},
            status_code=201,
        )

        return rule

    async def update_rule(
        self, id: uuid.UUID, data: StatutoryRuleUpdate, current_user: Optional[User] = None
    ) -> StatutoryRule:
        """Updates a StatutoryRule policy."""
        rule = await self.rule_repo.get_by_id(self.db, id)
        if not rule or rule.is_deleted:
            raise NotFoundException(message=f"StatutoryRule with ID '{id}' not found.")

        eff_from = data.effective_from or rule.effective_from
        eff_to = data.effective_to if data.effective_to is not None else rule.effective_to
        if eff_to and eff_to < eff_from:
            raise ValidationException(message="effective_to date cannot be earlier than effective_from date.")

        if data.rule_name is not None:
            rule.rule_name = data.rule_name
        if data.effective_from is not None:
            rule.effective_from = data.effective_from
        if data.effective_to is not None:
            rule.effective_to = data.effective_to
        if data.is_active is not None:
            rule.is_active = data.is_active
        if data.priority is not None:
            rule.priority = data.priority
        if data.description is not None:
            rule.description = data.description

        await self.db.commit()
        rule = await self.rule_repo.get_by_id(self.db, id)

        await self._invalidate_cache()

        actor_id_str = str(current_user.id) if current_user else "system"
        try:
            send_statutory_rule_notification_task.delay(
                action="UPDATED",
                rule_id=str(rule.id),
                rule_code=rule.rule_code,
                rule_name=rule.rule_name,
                country_code=rule.country.code if rule.country else "N/A",
                actor_id=actor_id_str,
            )
        except Exception as exc:
            logger.warning(f"Failed to dispatch Celery statutory rule notification task: {exc}")

        user_id = current_user.id if current_user else None
        username = current_user.username if current_user else "system"
        await log_audit(
            self.db,
            action="STATUTORY_RULE_UPDATE",
            entity_type="StatutoryRule",
            entity_id=rule.id,
            user_id=user_id,
            username=username,
            new_data={"rule_code": rule.rule_code, "is_active": rule.is_active, "priority": rule.priority},
            status_code=200,
        )

        return rule

    async def delete_rule(
        self, id: uuid.UUID, current_user: Optional[User] = None
    ) -> None:
        """Soft deletes a StatutoryRule policy."""
        rule = await self.rule_repo.get_by_id(self.db, id)
        if not rule or rule.is_deleted:
            raise NotFoundException(message=f"StatutoryRule with ID '{id}' not found.")

        rule_code = rule.rule_code
        rule_name = rule.rule_name
        country_code = rule.country.code if rule.country else "N/A"

        await self.rule_repo.soft_delete(self.db, id=id)
        await self._invalidate_cache()

        actor_id_str = str(current_user.id) if current_user else "system"
        try:
            send_statutory_rule_notification_task.delay(
                action="DELETED",
                rule_id=str(id),
                rule_code=rule_code,
                rule_name=rule_name,
                country_code=country_code,
                actor_id=actor_id_str,
            )
        except Exception as exc:
            logger.warning(f"Failed to dispatch Celery statutory rule notification task: {exc}")

        user_id = current_user.id if current_user else None
        username = current_user.username if current_user else "system"
        await log_audit(
            self.db,
            action="STATUTORY_RULE_DELETE",
            entity_type="StatutoryRule",
            entity_id=id,
            user_id=user_id,
            username=username,
            previous_data={"rule_code": rule_code},
            status_code=200,
        )

    async def get_rule_by_id(self, id: uuid.UUID) -> StatutoryRule:
        """Retrieves a StatutoryRule by ID."""
        rule = await self.rule_repo.get_by_id(self.db, id)
        if not rule or rule.is_deleted:
            raise NotFoundException(message=f"StatutoryRule with ID '{id}' not found.")
        return rule

    async def list_rules(
        self,
        params: PaginationParams,
        country_id: Optional[uuid.UUID] = None,
        rule_type: Optional[str] = None,
        is_active: Optional[bool] = None,
        search_term: Optional[str] = None,
        sorting: Optional[List[SortCriterion]] = None,
    ) -> PaginatedResult[StatutoryRule]:
        """Lists Statutory Rules with filtering and pagination."""
        return await self.rule_repo.get_filtered_rules(
            self.db,
            params=params,
            country_id=country_id,
            rule_type=rule_type,
            is_active=is_active,
            search_term=search_term,
            sorting=sorting,
        )

    # --- Slabs ---

    async def add_rule_slab(
        self, rule_id: uuid.UUID, data: StatutoryRuleSlabCreate, current_user: Optional[User] = None
    ) -> StatutoryRuleSlab:
        """Adds a new slab boundary to a StatutoryRule."""
        rule = await self.rule_repo.get_by_id(self.db, rule_id)
        if not rule or rule.is_deleted:
            raise NotFoundException(message=f"StatutoryRule with ID '{rule_id}' not found.")

        if data.max_amount is not None and data.max_amount < data.min_amount:
            raise ValidationException(message=f"Slab max_amount ({data.max_amount}) cannot be less than min_amount ({data.min_amount}).")

        # Check overlapping slabs for the rule
        existing_slabs = await self.slab_repo.get_slabs_by_rule_id(self.db, rule_id)
        for s in existing_slabs:
            s_min = float(s.min_amount)
            s_max = float(s.max_amount) if s.max_amount is not None else float("inf")
            n_min = float(data.min_amount)
            n_max = float(data.max_amount) if data.max_amount is not None else float("inf")
            if not (n_max < s_min or n_min > s_max):
                raise ValidationException(message=f"Slab boundary [{data.min_amount}, {data.max_amount}] overlaps with existing slab [{s.min_amount}, {s.max_amount}].")

        slab = StatutoryRuleSlab(
            statutory_rule_id=rule_id,
            min_amount=data.min_amount,
            max_amount=data.max_amount,
            percentage=data.percentage,
            fixed_amount=data.fixed_amount,
            sequence=data.sequence,
        )
        self.db.add(slab)
        await self.db.commit()
        await self.db.refresh(slab)

        await self._invalidate_cache()

        user_id = current_user.id if current_user else None
        username = current_user.username if current_user else "system"
        await log_audit(
            self.db,
            action="STATUTORY_SLAB_CREATE",
            entity_type="StatutoryRuleSlab",
            entity_id=slab.id,
            user_id=user_id,
            username=username,
            new_data={"rule_id": str(rule_id), "min_amount": slab.min_amount, "max_amount": slab.max_amount},
            status_code=201,
        )

        return slab

    async def update_rule_slab(
        self, slab_id: uuid.UUID, data: StatutoryRuleSlabUpdate, current_user: Optional[User] = None
    ) -> StatutoryRuleSlab:
        """Updates an existing StatutoryRuleSlab."""
        slab = await self.slab_repo.get_by_id(self.db, slab_id)
        if not slab:
            raise NotFoundException(message=f"StatutoryRuleSlab with ID '{slab_id}' not found.")

        min_amt = data.min_amount if data.min_amount is not None else float(slab.min_amount)
        max_amt = data.max_amount if data.max_amount is not None else (float(slab.max_amount) if slab.max_amount is not None else None)
        if max_amt is not None and max_amt < min_amt:
            raise ValidationException(message=f"Slab max_amount ({max_amt}) cannot be less than min_amount ({min_amt}).")

        if data.min_amount is not None:
            slab.min_amount = data.min_amount
        if data.max_amount is not None:
            slab.max_amount = data.max_amount
        if data.percentage is not None:
            slab.percentage = data.percentage
        if data.fixed_amount is not None:
            slab.fixed_amount = data.fixed_amount
        if data.sequence is not None:
            slab.sequence = data.sequence

        await self.db.commit()
        await self.db.refresh(slab)

        await self._invalidate_cache()

        user_id = current_user.id if current_user else None
        username = current_user.username if current_user else "system"
        await log_audit(
            self.db,
            action="STATUTORY_SLAB_UPDATE",
            entity_type="StatutoryRuleSlab",
            entity_id=slab.id,
            user_id=user_id,
            username=username,
            new_data={"min_amount": slab.min_amount, "max_amount": slab.max_amount},
            status_code=200,
        )

        return slab

    async def delete_rule_slab(
        self, slab_id: uuid.UUID, current_user: Optional[User] = None
    ) -> None:
        """Deletes a StatutoryRuleSlab."""
        slab = await self.slab_repo.get_by_id(self.db, slab_id)
        if not slab:
            raise NotFoundException(message=f"StatutoryRuleSlab with ID '{slab_id}' not found.")

        await self.slab_repo.delete(self.db, id=slab_id)
        await self._invalidate_cache()

        user_id = current_user.id if current_user else None
        username = current_user.username if current_user else "system"
        await log_audit(
            self.db,
            action="STATUTORY_SLAB_DELETE",
            entity_type="StatutoryRuleSlab",
            entity_id=slab_id,
            user_id=user_id,
            username=username,
            status_code=200,
        )

    # =========================================================================
    # 3. EMPLOYEE STATUTORY PROFILE MANAGEMENT
    # =========================================================================

    async def assign_employee_profile(
        self, data: EmployeeStatutoryProfileCreate, current_user: Optional[User] = None
    ) -> EmployeeStatutoryProfile:
        """
        Assigns or creates an EmployeeStatutoryProfile. Enforces single active profile per employee.
        """
        emp = await self.employee_repo.get_by_id(self.db, data.employee_id)
        if not emp or emp.is_deleted:
            raise NotFoundException(message=f"Employee with ID '{data.employee_id}' not found.")

        country = await self.country_repo.get_by_id(self.db, data.country_id)
        if not country:
            raise NotFoundException(message=f"Country with ID '{data.country_id}' not found.")

        if data.effective_to and data.effective_to < data.effective_from:
            raise ValidationException(message="effective_to date cannot be earlier than effective_from date.")

        # Single Active Profile Enforcement
        if data.is_active:
            active_profile = await self.profile_repo.get_active_profile_by_employee(
                self.db, data.employee_id, target_date=data.effective_from
            )
            if active_profile:
                # Deactivate/expire previous profile
                active_profile.is_active = False
                active_profile.effective_to = data.effective_from

        profile = EmployeeStatutoryProfile(
            employee_id=data.employee_id,
            country_id=data.country_id,
            pf_enabled=data.pf_enabled,
            esi_enabled=data.esi_enabled,
            professional_tax_enabled=data.professional_tax_enabled,
            income_tax_enabled=data.income_tax_enabled,
            tax_identification_number=data.tax_identification_number,
            pf_number=data.pf_number,
            esi_number=data.esi_number,
            effective_from=data.effective_from,
            effective_to=data.effective_to,
            is_active=data.is_active,
        )
        self.db.add(profile)
        await self.db.commit()
        
        profile = await self.profile_repo.get_by_id(self.db, profile.id)

        await self._invalidate_cache(employee_id=data.employee_id)

        user_id = current_user.id if current_user else None
        username = current_user.username if current_user else "system"
        await log_audit(
            self.db,
            action="STATUTORY_PROFILE_CREATE",
            entity_type="EmployeeStatutoryProfile",
            entity_id=profile.id,
            user_id=user_id,
            username=username,
            new_data={"employee_id": str(data.employee_id), "country": country.code},
            status_code=201,
        )

        return profile

    async def update_employee_profile(
        self, id: uuid.UUID, data: EmployeeStatutoryProfileUpdate, current_user: Optional[User] = None
    ) -> EmployeeStatutoryProfile:
        """Updates an EmployeeStatutoryProfile."""
        profile = await self.profile_repo.get_by_id(self.db, id)
        if not profile:
            raise NotFoundException(message=f"EmployeeStatutoryProfile with ID '{id}' not found.")

        eff_from = data.effective_from or profile.effective_from
        eff_to = data.effective_to if data.effective_to is not None else profile.effective_to
        if eff_to and eff_to < eff_from:
            raise ValidationException(message="effective_to date cannot be earlier than effective_from date.")

        if data.pf_enabled is not None:
            profile.pf_enabled = data.pf_enabled
        if data.esi_enabled is not None:
            profile.esi_enabled = data.esi_enabled
        if data.professional_tax_enabled is not None:
            profile.professional_tax_enabled = data.professional_tax_enabled
        if data.income_tax_enabled is not None:
            profile.income_tax_enabled = data.income_tax_enabled
        if data.tax_identification_number is not None:
            profile.tax_identification_number = data.tax_identification_number
        if data.pf_number is not None:
            profile.pf_number = data.pf_number
        if data.esi_number is not None:
            profile.esi_number = data.esi_number
        if data.effective_from is not None:
            profile.effective_from = data.effective_from
        if data.effective_to is not None:
            profile.effective_to = data.effective_to
        if data.is_active is not None:
            profile.is_active = data.is_active

        await self.db.commit()
        profile = await self.profile_repo.get_by_id(self.db, id)

        await self._invalidate_cache(employee_id=profile.employee_id)

        user_id = current_user.id if current_user else None
        username = current_user.username if current_user else "system"
        await log_audit(
            self.db,
            action="STATUTORY_PROFILE_UPDATE",
            entity_type="EmployeeStatutoryProfile",
            entity_id=profile.id,
            user_id=user_id,
            username=username,
            new_data={"is_active": profile.is_active},
            status_code=200,
        )

        return profile

    async def get_employee_profile_by_id(self, id: uuid.UUID) -> EmployeeStatutoryProfile:
        """Retrieves an EmployeeStatutoryProfile by ID."""
        profile = await self.profile_repo.get_by_id(self.db, id)
        if not profile:
            raise NotFoundException(message=f"EmployeeStatutoryProfile with ID '{id}' not found.")
        return profile

    async def get_active_profile_by_employee(
        self, employee_id: uuid.UUID, target_date: Optional[datetime.date] = None
    ) -> EmployeeStatutoryProfile:
        """Retrieves active profile for an employee or raises NotFoundException."""
        profile = await self.profile_repo.get_active_profile_by_employee(self.db, employee_id, target_date=target_date)
        if not profile:
            raise NotFoundException(message=f"No active EmployeeStatutoryProfile found for Employee '{employee_id}'.")
        return profile

    async def list_employee_profiles(
        self,
        params: PaginationParams,
        employee_id: Optional[uuid.UUID] = None,
        country_id: Optional[uuid.UUID] = None,
        is_active: Optional[bool] = None,
        sorting: Optional[List[SortCriterion]] = None,
    ) -> PaginatedResult[EmployeeStatutoryProfile]:
        """Lists Employee Statutory Profiles with filtering and pagination."""
        return await self.profile_repo.get_filtered_profiles(
            self.db,
            params=params,
            employee_id=employee_id,
            country_id=country_id,
            is_active=is_active,
            sorting=sorting,
        )

    # =========================================================================
    # 4. STATUTORY CALCULATION ENGINE & RULE RESOLUTION
    # =========================================================================

    async def resolve_applicable_rules(
        self,
        country_id: uuid.UUID,
        target_date: datetime.date,
        rule_type: Optional[str] = None,
    ) -> List[StatutoryRule]:
        """
        Resolves applicable active statutory rules for a country effective on target_date, ordered by priority.
        """
        return await self.rule_repo.get_applicable_rules(
            self.db, country_id=country_id, target_date=target_date, rule_type=rule_type
        )

    async def calculate_statutory_deductions(
        self,
        employee_id: uuid.UUID,
        gross_salary: float,
        calculation_date: Optional[datetime.date] = None,
    ) -> StatutoryCalculationResponse:
        """
        Calculates all applicable statutory deductions for an employee based on their active statutory profile,
        country jurisdiction, and rule evaluation engine (Fixed, Percentage, Slab).
        """
        target_date = calculation_date or datetime.date.today()

        profile = await self.profile_repo.get_active_profile_by_employee(
            self.db, employee_id, target_date=target_date
        )
        if not profile:
            return StatutoryCalculationResponse(
                employee_id=employee_id,
                country_code="N/A",
                gross_salary=gross_salary,
                calculation_date=target_date,
                total_statutory_deductions=0.00,
                deductions=[],
            )

        country = profile.country or await self.country_repo.get_by_id(self.db, profile.country_id)
        country_code = country.code if country else "IND"

        applicable_rules = await self.rule_repo.get_applicable_rules(
            self.db, country_id=profile.country_id, target_date=target_date
        )

        deductions_list: List[StatutoryDeductionResult] = []
        total_deductions = 0.00

        for rule in applicable_rules:
            # Check feature flags in profile
            if rule.rule_type == "Provident Fund" and not profile.pf_enabled:
                continue
            if rule.rule_type == "ESI" and not profile.esi_enabled:
                continue
            if rule.rule_type == "Professional Tax" and not profile.professional_tax_enabled:
                continue
            if rule.rule_type == "Income Tax" and not profile.income_tax_enabled:
                continue

            deduction_amount = 0.00
            method = rule.calculation_method

            if method == "Fixed":
                # Check slabs first for fixed, or fallback to slab 1 fixed amount
                if rule.slabs:
                    deduction_amount = float(rule.slabs[0].fixed_amount)
                else:
                    deduction_amount = 0.00

            elif method == "Percentage":
                if rule.slabs:
                    pct = float(rule.slabs[0].percentage)
                    deduction_amount = round((gross_salary * pct) / 100.0, 2)
                else:
                    deduction_amount = 0.00

            elif method == "Slab":
                # Evaluate slabs ordered by sequence
                for slab in rule.slabs:
                    s_min = float(slab.min_amount)
                    s_max = float(slab.max_amount) if slab.max_amount is not None else float("inf")
                    if s_min <= gross_salary <= s_max:
                        fixed = float(slab.fixed_amount)
                        pct = float(slab.percentage)
                        deduction_amount = round(fixed + ((gross_salary * pct) / 100.0), 2)
                        break

            total_deductions += deduction_amount
            deductions_list.append(
                StatutoryDeductionResult(
                    rule_code=rule.rule_code,
                    rule_name=rule.rule_name,
                    rule_type=rule.rule_type,
                    calculation_method=rule.calculation_method,
                    amount=deduction_amount,
                )
            )

        return StatutoryCalculationResponse(
            employee_id=employee_id,
            country_code=country_code,
            gross_salary=gross_salary,
            calculation_date=target_date,
            total_statutory_deductions=round(total_deductions, 2),
            deductions=deductions_list,
        )
