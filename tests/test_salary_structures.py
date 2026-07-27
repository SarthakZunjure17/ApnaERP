import datetime
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
from app.models.salary_structure import SalaryStructure, SalaryStructureComponent
from app.models.user import User
from app.models.user_role import UserRole
from app.schemas.salary_component import (
    CalculationMethodEnum,
    ComponentTypeEnum,
    SalaryComponentCreate,
)
from app.schemas.salary_structure import (
    SalaryStructureComponentCreate,
    SalaryStructureComponentUpdate,
    SalaryStructureCreate,
    SalaryStructureUpdate,
)
from app.services.salary_component import SalaryComponentService
from app.services.salary_structure import SalaryStructureService


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
async def setup_structure_fixture(db_session: AsyncSession):
    """
    Creates test Roles, Users, Permissions, and Salary Components for testing Salary Structures.
    """
    perms = [
        "salary_structure.create", "salary_structure.read",
        "salary_structure.update", "salary_structure.delete", "salary_structure.restore",
        "salary_component.create", "salary_component.read"
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

    # Create dummy salary component
    comp_service = SalaryComponentService(db_session)
    comp = await comp_service.create_component(
        SalaryComponentCreate(
            code=f"BASIC_{uuid.uuid4().hex[:4].upper()}",
            name=f"Basic {uuid.uuid4().hex[:4]}",
            type=ComponentTypeEnum.EARNING,
            calculation_method=CalculationMethodEnum.FIXED,
            default_value=60000.0,
            display_order=int(uuid.uuid4().int % 1000) + 1,
        ),
        current_user=user_admin,
    )

    return {
        "role_admin": role_admin,
        "user_admin": user_admin,
        "component": comp,
    }


@pytest.mark.asyncio
async def test_salary_structure_crud_and_validations(db_session: AsyncSession, setup_structure_fixture):
    """
    Tests CRUD operations and business validations for Salary Structures & Components.
    """
    fix = setup_structure_fixture
    service = SalaryStructureService(db_session)

    code = f"EXEC_{uuid.uuid4().hex[:4].upper()}"
    name = f"Executive Package {uuid.uuid4().hex[:4]}"

    create_dto = SalaryStructureCreate(
        code=code,
        name=name,
        description="Standard Executive Package Structure",
        currency="INR",
        is_active=True,
        effective_from=datetime.date(2026, 1, 1),
        effective_to=datetime.date(2026, 12, 31),
    )

    # 1. Create Structure
    struct = await service.create_structure(data=create_dto, current_user=fix["user_admin"])
    assert struct.id is not None
    assert struct.code == code
    assert struct.name == name

    # 2. Date Range Validation Rejection
    invalid_date_dto = create_dto.model_copy(
        update={
            "code": f"INV_{uuid.uuid4().hex[:4].upper()}",
            "name": f"Inv Date {uuid.uuid4().hex[:4]}",
            "effective_from": datetime.date(2026, 12, 31),
            "effective_to": datetime.date(2026, 1, 1),
        }
    )
    with pytest.raises(ApnaERPException) as exc_info:
        await service.create_structure(data=invalid_date_dto, current_user=fix["user_admin"])
    assert exc_info.value.error_code == "INVALID_DATE_RANGE"

    # 3. Add Component to Structure
    map_dto = SalaryStructureComponentCreate(
        salary_component_id=fix["component"].id,
        component_order=1,
        component_value=65000.00,
        is_active=True,
    )
    mapping = await service.add_component_to_structure(
        structure_id=struct.id, data=map_dto, current_user=fix["user_admin"]
    )
    assert mapping.id is not None
    assert mapping.salary_structure_id == struct.id
    assert mapping.salary_component_id == fix["component"].id
    assert float(mapping.component_value) == 65000.00

    # 4. Duplicate Component Mapping Rejection
    with pytest.raises(ApnaERPException) as exc_info2:
        await service.add_component_to_structure(
            structure_id=struct.id, data=map_dto, current_user=fix["user_admin"]
        )
    assert exc_info2.value.error_code == "DUPLICATE_STRUCTURE_COMPONENT"

    # 5. Soft Delete and Restore
    deleted = await service.delete_structure(id=struct.id, current_user=fix["user_admin"])
    assert deleted is True

    restored = await service.restore_structure(id=struct.id, current_user=fix["user_admin"])
    assert restored.is_deleted is False


@pytest.mark.asyncio
async def test_salary_structure_api_endpoints(async_client: AsyncClient, db_session: AsyncSession, setup_structure_fixture):
    """
    Tests REST API endpoints for Salary Structures.
    """
    fix = setup_structure_fixture
    token = create_access_token(subject=str(fix["user_admin"].id))
    headers = {"Authorization": f"Bearer {token}"}

    code = f"ENG_{uuid.uuid4().hex[:4].upper()}"
    payload = {
        "code": code,
        "name": f"Engineering Structure {uuid.uuid4().hex[:4]}",
        "description": "Standard Engineering Compensation Template",
        "currency": "INR",
        "is_active": True,
        "effective_from": "2026-01-01",
        "effective_to": "2026-12-31",
    }

    # 1. POST /api/v1/salary-structures
    res_create = await async_client.post("/api/v1/salary-structures", json=payload, headers=headers)
    assert res_create.status_code == 201
    body_create = res_create.json()
    assert body_create["code"] == code
    struct_id = body_create["id"]

    # 2. POST /api/v1/salary-structures/{id}/components
    comp_payload = {
        "salary_component_id": str(fix["component"].id),
        "component_order": 1,
        "component_value": 70000.00,
        "is_active": True,
    }
    res_comp = await async_client.post(f"/api/v1/salary-structures/{struct_id}/components", json=comp_payload, headers=headers)
    assert res_comp.status_code == 201
    comp_map_id = res_comp.json()["id"]

    # 3. GET /api/v1/salary-structures/{id}
    res_get = await async_client.get(f"/api/v1/salary-structures/{struct_id}", headers=headers)
    assert res_get.status_code == 200
    assert len(res_get.json()["components"]) == 1

    # 4. DELETE /api/v1/salary-structures/{id}/components/{componentId}
    res_del_comp = await async_client.delete(f"/api/v1/salary-structures/{struct_id}/components/{comp_map_id}", headers=headers)
    assert res_del_comp.status_code == 204

    # 5. DELETE /api/v1/salary-structures/{id}
    res_del = await async_client.delete(f"/api/v1/salary-structures/{struct_id}", headers=headers)
    assert res_del.status_code == 204

    # 6. PATCH /api/v1/salary-structures/{id}/restore
    res_res = await async_client.patch(f"/api/v1/salary-structures/{struct_id}/restore", headers=headers)
    assert res_res.status_code == 200
    assert res_res.json()["code"] == code
