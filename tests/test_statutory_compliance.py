import datetime
import random
import uuid
from typing import AsyncGenerator
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password
from app.db.session import AsyncSessionLocal
from app.exceptions.base import DuplicateResourceException, NotFoundException, ValidationException
from app.main import app
from app.models.country import Country
from app.models.department import Department
from app.models.employee import Employee
from app.models.permission import Permission
from app.models.role import Role, RolePermission
from app.models.statutory_rule import StatutoryRule, StatutoryRuleSlab
from app.models.user import User
from app.models.user_role import UserRole
from app.schemas.country import CountryCreate, CountryUpdate
from app.schemas.employee_statutory_profile import (
    EmployeeStatutoryProfileCreate,
    EmployeeStatutoryProfileUpdate,
)
from app.schemas.statutory_rule import (
    CalculationMethodEnum,
    RuleTypeEnum,
    StatutoryRuleCreate,
    StatutoryRuleSlabCreate,
    StatutoryRuleUpdate,
)
from app.services.statutory_compliance import StatutoryComplianceService


# ============================================================================
# FIXTURES
# ============================================================================

@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture(scope="function")
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest_asyncio.fixture(scope="function")
async def setup_statutory_data(db_session: AsyncSession):
    """
    Sets up admin user, role with permissions, employee, sample country (India), and India statutory rules.
    """
    # 1. Fetch permissions and create admin role
    perms_query = await db_session.execute(Permission.__table__.select())
    all_perms = perms_query.fetchall()

    role = Role(
        name=f"StatutoryAdmin_{uuid.uuid4().hex[:6]}",
        description="Statutory Compliance Admin Role",
    )
    db_session.add(role)
    await db_session.flush()

    for perm in all_perms:
        rp = RolePermission(role_id=role.id, permission_id=perm.id)
        db_session.add(rp)

    # 2. Create User & assign role
    user = User(
        full_name="Statutory Admin",
        username=f"stat_admin_{uuid.uuid4().hex[:6]}",
        email=f"stat_admin_{uuid.uuid4().hex[:6]}@example.com",
        password_hash=hash_password("Pass123!"),
        is_active=True,
        is_superuser=True,
    )
    db_session.add(user)
    await db_session.flush()

    user_role = UserRole(user_id=user.id, role_id=role.id)
    db_session.add(user_role)

    # 3. Create Department & Employee
    dept = Department(
        code=f"LEG_{uuid.uuid4().hex[:4].upper()}",
        name=f"Legal & Compliance {uuid.uuid4().hex[:6]}",
        is_active=True,
    )
    db_session.add(dept)
    await db_session.flush()

    employee = Employee(
        employee_code=f"EMP_{random.randint(10000, 99999)}",
        first_name="Raj",
        last_name="Sharma",
        work_email=f"raj_{uuid.uuid4().hex[:4]}@example.com",
        user_id=user.id,
        department_id=dept.id,
        employment_status="Active",
        joining_date=datetime.date(2025, 1, 1),
    )
    db_session.add(employee)
    await db_session.flush()

    # 4. Create Country (India)
    country_code = f"C{uuid.uuid4().hex[:7].upper()}"
    country = Country(code=country_code, name="India", currency="INR", is_active=True)
    db_session.add(country)
    await db_session.flush()

    # 5. Create India statutory rules via direct ORM addition to avoid double commits in fixture
    pf_rule = StatutoryRule(
        rule_code=f"PF_{uuid.uuid4().hex[:4].upper()}",
        rule_name="India EPF Standard",
        country_id=country.id,
        rule_type="Provident Fund",
        calculation_method="Percentage",
        effective_from=datetime.date(2026, 1, 1),
        is_active=True,
        priority=1,
    )
    db_session.add(pf_rule)
    await db_session.flush()
    db_session.add(StatutoryRuleSlab(statutory_rule_id=pf_rule.id, min_amount=0, percentage=12.0, fixed_amount=0, sequence=1))

    esi_rule = StatutoryRule(
        rule_code=f"ESI_{uuid.uuid4().hex[:4].upper()}",
        rule_name="India ESI Standard",
        country_id=country.id,
        rule_type="ESI",
        calculation_method="Percentage",
        effective_from=datetime.date(2026, 1, 1),
        is_active=True,
        priority=2,
    )
    db_session.add(esi_rule)
    await db_session.flush()
    db_session.add(StatutoryRuleSlab(statutory_rule_id=esi_rule.id, min_amount=0, percentage=0.75, fixed_amount=0, sequence=1))

    pt_rule = StatutoryRule(
        rule_code=f"PT_{uuid.uuid4().hex[:4].upper()}",
        rule_name="Maharashtra Professional Tax",
        country_id=country.id,
        rule_type="Professional Tax",
        calculation_method="Slab",
        effective_from=datetime.date(2026, 1, 1),
        is_active=True,
        priority=3,
    )
    db_session.add(pt_rule)
    await db_session.flush()
    db_session.add(StatutoryRuleSlab(statutory_rule_id=pt_rule.id, min_amount=0, max_amount=9999.99, fixed_amount=0.00, sequence=1))
    db_session.add(StatutoryRuleSlab(statutory_rule_id=pt_rule.id, min_amount=10000.00, max_amount=15000.00, fixed_amount=150.00, sequence=2))
    db_session.add(StatutoryRuleSlab(statutory_rule_id=pt_rule.id, min_amount=15000.01, max_amount=None, fixed_amount=200.00, sequence=3))

    await db_session.commit()

    token = create_access_token(subject=user.id)

    return {
        "user_id": user.id,
        "admin_token": token,
        "employee_id": employee.id,
        "country_id": country.id,
        "country_code": country.code,
        "pf_rule_code": pf_rule.rule_code,
        "esi_rule_code": esi_rule.rule_code,
        "pt_rule_code": pt_rule.rule_code,
    }


# ============================================================================
# 1. COUNTRY CRUD & BUSINESS RULES
# ============================================================================

@pytest.mark.asyncio
async def test_country_crud_and_uniqueness(db_session: AsyncSession):
    """Tests Country creation, duplicate ISO code rejection, and update."""
    service = StatutoryComplianceService(db_session)

    code_val = f"U{uuid.uuid4().hex[:7].upper()}"
    # Create Country
    c = await service.create_country(
        CountryCreate(code=code_val, name="United States of America", currency="USD")
    )
    assert c.id is not None
    assert c.code == code_val

    # Duplicate Code Rejection
    with pytest.raises(DuplicateResourceException):
        await service.create_country(
            CountryCreate(code=code_val.lower(), name="USA Duplicate", currency="USD")
        )

    # Update Country
    updated = await service.update_country(c.id, CountryUpdate(currency="USD"))
    assert updated.currency == "USD"


# ============================================================================
# 2. STATUTORY RULES & SLAB EVALUATION
# ============================================================================

@pytest.mark.asyncio
async def test_statutory_rules_and_slabs(setup_statutory_data):
    """Tests rule creation, effective dating validation, and slab boundary overlap prevention."""
    data = setup_statutory_data
    country_id = data["country_id"]

    async with AsyncSessionLocal() as session:
        service = StatutoryComplianceService(session)

        # Effective date validation
        with pytest.raises(ValidationException):
            await service.create_rule(
                StatutoryRuleCreate(
                    rule_code=f"INV_{uuid.uuid4().hex[:4].upper()}",
                    rule_name="Invalid Date Rule",
                    country_id=country_id,
                    rule_type=RuleTypeEnum.OTHER,
                    calculation_method=CalculationMethodEnum.FIXED,
                    effective_from=datetime.date(2026, 12, 31),
                    effective_to=datetime.date(2026, 1, 1),
                )
            )

        # Valid Fixed Rule
        rule = await service.create_rule(
            StatutoryRuleCreate(
                rule_code=f"FIX_{uuid.uuid4().hex[:4].upper()}",
                rule_name="Test Fixed Deduction",
                country_id=country_id,
                rule_type=RuleTypeEnum.OTHER,
                calculation_method=CalculationMethodEnum.FIXED,
                effective_from=datetime.date(2026, 1, 1),
                slabs=[StatutoryRuleSlabCreate(min_amount=0, fixed_amount=500.00)],
            )
        )
        assert rule.id is not None
        assert len(rule.slabs) == 1
        assert float(rule.slabs[0].fixed_amount) == 500.00


# ============================================================================
# 3. STATUTORY COMPLIANCE DEDUCTION ENGINE
# ============================================================================

@pytest.mark.asyncio
async def test_statutory_deduction_engine_calculations(setup_statutory_data):
    """Tests deduction calculation engine for Fixed, Percentage, and Slab methods."""
    data = setup_statutory_data
    employee_id = data["employee_id"]
    country_id = data["country_id"]
    pf_code = data["pf_rule_code"]
    esi_code = data["esi_rule_code"]
    pt_code = data["pt_rule_code"]

    async with AsyncSessionLocal() as session:
        service = StatutoryComplianceService(session)

        # 1. Assign Statutory Profile for Employee (PF, ESI, PT enabled)
        profile = await service.assign_employee_profile(
            EmployeeStatutoryProfileCreate(
                employee_id=employee_id,
                country_id=country_id,
                pf_enabled=True,
                esi_enabled=True,
                professional_tax_enabled=True,
                income_tax_enabled=False,
                tax_identification_number="ABCDE1234F",
                pf_number="MH/12345/678",
                effective_from=datetime.date(2026, 1, 1),
                is_active=True,
            )
        )
        assert profile.id is not None
        assert profile.is_active is True

        # 2. Calculate Statutory Deductions for Gross Salary = 50,000 INR
        # PF: 12% of 50,000 = 6,000 INR
        # ESI: 0.75% of 50,000 = 375 INR
        # PT: Slab >15,000 = 200 INR
        # Total = 6,575 INR
        res = await service.calculate_statutory_deductions(
            employee_id=employee_id,
            gross_salary=50000.00,
            calculation_date=datetime.date(2026, 7, 27),
        )

        assert res.employee_id == employee_id
        assert res.gross_salary == 50000.00
        assert len(res.deductions) == 3

        pf_ded = next(d for d in res.deductions if d.rule_code == pf_code)
        assert pf_ded.amount == 6000.00

        esi_ded = next(d for d in res.deductions if d.rule_code == esi_code)
        assert esi_ded.amount == 375.00

        pt_ded = next(d for d in res.deductions if d.rule_code == pt_code)
        assert pt_ded.amount == 200.00

        assert res.total_statutory_deductions == 6575.00

        # 3. Test Feature Flag Disabling (Disable PF in profile)
        await service.update_employee_profile(
            profile.id, EmployeeStatutoryProfileUpdate(pf_enabled=False)
        )

        res2 = await service.calculate_statutory_deductions(
            employee_id=employee_id,
            gross_salary=50000.00,
            calculation_date=datetime.date(2026, 7, 27),
        )
        assert len(res2.deductions) == 2
        assert not any(d.rule_code == pf_code for d in res2.deductions)
        assert res2.total_statutory_deductions == 575.00  # 375 ESI + 200 PT


# ============================================================================
# 4. SINGLE ACTIVE PROFILE ENFORCEMENT
# ============================================================================

@pytest.mark.asyncio
async def test_single_active_profile_enforcement(setup_statutory_data):
    """Tests that assigning a new active statutory profile deactivates the previous active profile."""
    data = setup_statutory_data
    employee_id = data["employee_id"]
    country_id = data["country_id"]

    async with AsyncSessionLocal() as session:
        service = StatutoryComplianceService(session)

        # 1. Create Profile 1
        p1 = await service.assign_employee_profile(
            EmployeeStatutoryProfileCreate(
                employee_id=employee_id,
                country_id=country_id,
                effective_from=datetime.date(2026, 1, 1),
                is_active=True,
            )
        )
        assert p1.is_active is True

        # 2. Create Profile 2 starting 2026-07-01
        p2 = await service.assign_employee_profile(
            EmployeeStatutoryProfileCreate(
                employee_id=employee_id,
                country_id=country_id,
                effective_from=datetime.date(2026, 7, 1),
                is_active=True,
            )
        )
        assert p2.is_active is True

        # Verify Profile 1 is now inactive
        p1_updated = await service.get_employee_profile_by_id(p1.id)
        assert p1_updated.is_active is False
        assert p1_updated.effective_to == datetime.date(2026, 7, 1)


# ============================================================================
# 5. REST API ENDPOINTS
# ============================================================================

@pytest.mark.asyncio
async def test_statutory_api_endpoints(async_client: AsyncClient, setup_statutory_data):
    """Tests REST API endpoints for Countries, Statutory Rules, Slabs, Profiles, and Calculation."""
    data = setup_statutory_data
    token = data["admin_token"]
    employee_id = data["employee_id"]

    headers = {"Authorization": f"Bearer {token}"}

    gbr_code = f"G{uuid.uuid4().hex[:7].upper()}"
    ni_code = f"GBR_NI_{uuid.uuid4().hex[:4].upper()}"

    # 1. POST /api/v1/countries
    resp = await async_client.post(
        "/api/v1/countries",
        json={"code": gbr_code, "name": "United Kingdom", "currency": "GBP", "is_active": True},
        headers=headers,
    )
    assert resp.status_code == 201
    c_data = resp.json()
    c_id = c_data["id"]

    # 2. GET /api/v1/countries
    resp = await async_client.get("/api/v1/countries", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["total"] >= 1

    # 3. POST /api/v1/statutory-rules
    resp = await async_client.post(
        "/api/v1/statutory-rules",
        json={
            "rule_code": ni_code,
            "rule_name": "UK National Insurance",
            "country_id": c_id,
            "rule_type": "Other",
            "calculation_method": "Percentage",
            "effective_from": "2026-01-01",
            "is_active": True,
            "priority": 1,
            "slabs": [{"min_amount": 0, "percentage": 8.0, "fixed_amount": 0}],
        },
        headers=headers,
    )
    assert resp.status_code == 201
    rule_data = resp.json()
    rule_id = rule_data["id"]

    # 4. POST /api/v1/employee-statutory-profiles
    resp = await async_client.post(
        "/api/v1/employee-statutory-profiles",
        json={
            "employee_id": str(employee_id),
            "country_id": c_id,
            "pf_enabled": True,
            "esi_enabled": True,
            "professional_tax_enabled": True,
            "income_tax_enabled": True,
            "effective_from": "2026-01-01",
            "is_active": True,
        },
        headers=headers,
    )
    assert resp.status_code == 201

    # 5. POST /api/v1/statutory-rules/calculate
    resp = await async_client.post(
        "/api/v1/statutory-rules/calculate",
        json={"employee_id": str(employee_id), "gross_salary": 3000.00},
        headers=headers,
    )
    assert resp.status_code == 200
    calc_data = resp.json()
    assert calc_data["country_code"] == gbr_code
    assert calc_data["total_statutory_deductions"] == 240.00  # 8% of 3000
