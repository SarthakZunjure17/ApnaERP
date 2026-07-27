from typing import AsyncGenerator
import uuid
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password
from app.db.session import AsyncSessionLocal
from app.exceptions.base import ApnaERPException
from app.main import app
from app.models.permission import Permission
from app.models.role import Role, RolePermission
from app.models.salary_component import SalaryComponent
from app.models.user import User
from app.models.user_role import UserRole
from app.schemas.salary_component import (
    CalculationMethodEnum,
    ComponentTypeEnum,
    SalaryComponentCreate,
    SalaryComponentUpdate,
)
from app.services.salary_component import SalaryComponentService


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
async def setup_payroll_fixture(db_session: AsyncSession):
    """
    Creates test Roles, Users, Permissions for testing Salary Components.
    """
    perms = [
        "salary_component.create", "salary_component.read",
        "salary_component.update", "salary_component.delete", "salary_component.restore"
    ]
    perm_objs = {}
    for p_code in perms:
        stmt = select(Permission).where(Permission.code == p_code)
        res = await db_session.execute(stmt)
        p_obj = res.scalars().first()
        if not p_obj:
            p_obj = Permission(name=p_code.replace(".", " ").title(), code=p_code, module_name="payroll")
            db_session.add(p_obj)
            await db_session.flush()
        perm_objs[p_code] = p_obj

    role_admin = Role(name=f"PayrollAdmin_{uuid.uuid4().hex[:6]}", description="Payroll Admin Role")
    db_session.add(role_admin)
    await db_session.flush()

    for p_obj in perm_objs.values():
        db_session.add(RolePermission(role_id=role_admin.id, permission_id=p_obj.id))

    user_admin = User(
        full_name="Payroll Admin",
        username=f"padmin_{uuid.uuid4().hex[:6]}",
        email=f"padmin_{uuid.uuid4().hex[:6]}@example.com",
        password_hash=hash_password("password123"),
        is_active=True,
        is_superuser=True,
    )
    db_session.add(user_admin)
    await db_session.flush()

    db_session.add(UserRole(user_id=user_admin.id, role_id=role_admin.id))
    await db_session.commit()
    await db_session.refresh(user_admin)

    return {
        "role_admin": role_admin,
        "user_admin": user_admin,
    }


@pytest.mark.asyncio
async def test_salary_component_crud_and_validations(db_session: AsyncSession, setup_payroll_fixture):
    """
    Tests CRUD operations and business rule validations for Salary Components.
    """
    fix = setup_payroll_fixture
    service = SalaryComponentService(db_session)

    code = f"BASIC_{uuid.uuid4().hex[:4].upper()}"
    name = f"Basic Salary {uuid.uuid4().hex[:4]}"
    display_order = 100 + int(uuid.uuid4().int % 1000)

    create_dto = SalaryComponentCreate(
        code=code,
        name=name,
        description="Standard Basic Salary Earning Component",
        type=ComponentTypeEnum.EARNING,
        calculation_method=CalculationMethodEnum.FIXED,
        default_value=50000.00,
        is_taxable=True,
        is_pf_applicable=True,
        is_esi_applicable=True,
        is_active=True,
        display_order=display_order,
    )

    # 1. Create Component
    comp = await service.create_component(data=create_dto, current_user=fix["user_admin"])
    assert comp.id is not None
    assert comp.code == code
    assert comp.name == name
    assert comp.type == "Earning"
    assert comp.calculation_method == "Fixed"
    assert float(comp.default_value) == 50000.00

    # 2. Duplicate Code Rejection
    dup_dto = create_dto.model_copy(update={"name": f"Other {uuid.uuid4().hex[:4]}", "display_order": display_order + 1})
    with pytest.raises(ApnaERPException) as exc_info:
        await service.create_component(data=dup_dto, current_user=fix["user_admin"])
    assert exc_info.value.error_code == "DUPLICATE_COMPONENT_CODE"

    # 3. Percentage Validation Rejection
    perc_code = f"HRA_{uuid.uuid4().hex[:4].upper()}"
    invalid_perc_dto = SalaryComponentCreate(
        code=perc_code,
        name=f"HRA {uuid.uuid4().hex[:4]}",
        type=ComponentTypeEnum.EARNING,
        calculation_method=CalculationMethodEnum.PERCENTAGE,
        default_value=0.0,
        percentage_value=None,  # Missing percentage_value
        is_active=True,
        display_order=display_order + 2,
    )
    with pytest.raises(ApnaERPException) as exc_info2:
        await service.create_component(data=invalid_perc_dto, current_user=fix["user_admin"])
    assert exc_info2.value.error_code == "INVALID_CALCULATION_METHOD_CONFIG"

    # 4. Valid Percentage Component Creation
    valid_perc_dto = invalid_perc_dto.model_copy(update={"percentage_value": 50.00})
    perc_comp = await service.create_component(data=valid_perc_dto, current_user=fix["user_admin"])
    assert perc_comp.calculation_method == "Percentage"
    assert float(perc_comp.percentage_value) == 50.00

    # 5. Soft Delete and Restore
    deleted = await service.delete_component(id=comp.id, current_user=fix["user_admin"])
    assert deleted is True

    restored = await service.restore_component(id=comp.id, current_user=fix["user_admin"])
    assert restored.is_deleted is False


@pytest.mark.asyncio
async def test_salary_component_api_endpoints(async_client: AsyncClient, db_session: AsyncSession, setup_payroll_fixture):
    """
    Tests REST API endpoints for Salary Components.
    """
    fix = setup_payroll_fixture
    token = create_access_token(subject=str(fix["user_admin"].id))
    headers = {"Authorization": f"Bearer {token}"}

    code = f"PF_{uuid.uuid4().hex[:4].upper()}"
    display_order = 200 + int(uuid.uuid4().int % 1000)

    payload = {
        "code": code,
        "name": f"Provident Fund {uuid.uuid4().hex[:4]}",
        "description": "Statutory PF Deduction",
        "type": "Deduction",
        "calculation_method": "Percentage",
        "default_value": 0.0,
        "percentage_value": 12.00,
        "is_taxable": False,
        "is_pf_applicable": True,
        "is_esi_applicable": False,
        "is_active": True,
        "display_order": display_order,
    }

    # 1. POST /api/v1/salary-components
    res_create = await async_client.post("/api/v1/salary-components", json=payload, headers=headers)
    assert res_create.status_code == 201
    body_create = res_create.json()
    assert body_create["code"] == code
    comp_id = body_create["id"]

    # 2. GET /api/v1/salary-components/{id}
    res_get = await async_client.get(f"/api/v1/salary-components/{comp_id}", headers=headers)
    assert res_get.status_code == 200
    assert res_get.json()["id"] == comp_id

    # 3. GET /api/v1/salary-components
    res_list = await async_client.get("/api/v1/salary-components", headers=headers)
    assert res_list.status_code == 200
    assert res_list.json()["total"] >= 1

    # 4. DELETE /api/v1/salary-components/{id}
    res_del = await async_client.delete(f"/api/v1/salary-components/{comp_id}", headers=headers)
    assert res_del.status_code == 204

    # 5. PATCH /api/v1/salary-components/{id}/restore
    res_res = await async_client.patch(f"/api/v1/salary-components/{comp_id}/restore", headers=headers)
    assert res_res.status_code == 200
    assert res_res.json()["code"] == code
