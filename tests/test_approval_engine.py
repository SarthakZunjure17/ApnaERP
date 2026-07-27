import datetime
from typing import AsyncGenerator
import uuid
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password
from app.db.base import Base
from app.db.session import AsyncSessionLocal, engine
from app.main import app
from app.models.approval_workflow import (
    ApprovalHistory,
    ApprovalRequest,
    ApprovalStep,
    ApprovalWorkflow,
)
from app.models.permission import Permission
from app.models.role import Role, RolePermission
from app.models.user import User
from app.models.user_role import UserRole
from app.services.approval_engine import ApprovalEngineService
from app.services.approval_workflow import ApprovalWorkflowService


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
async def setup_approval_fixture(db_session: AsyncSession):
    """
    Creates test Roles, Users, Permissions, and a 2-Step Approval Workflow for testing.
    """
    # 1. Create permissions
    perms = [
        "workflow.create", "workflow.read", "workflow.update", "workflow.delete",
        "approval.read", "approval.approve", "approval.reject"
    ]
    perm_objs = {}
    for p_code in perms:
        stmt = select(Permission).where(Permission.code == p_code)
        res = await db_session.execute(stmt)
        p_obj = res.scalars().first()
        if not p_obj:
            p_obj = Permission(name=p_code.replace(".", " ").title(), code=p_code, module_name="platform")
            db_session.add(p_obj)
            await db_session.flush()
        perm_objs[p_code] = p_obj

    # 2. Create Roles: Manager Role (Step 1) & Finance Role (Step 2)
    role_mgr = Role(name=f"Manager_{uuid.uuid4().hex[:6]}", description="Manager Role")
    role_fin = Role(name=f"Finance_{uuid.uuid4().hex[:6]}", description="Finance Role")
    db_session.add_all([role_mgr, role_fin])
    await db_session.flush()

    # Assign permissions to roles
    for p_obj in perm_objs.values():
        db_session.add_all([
            RolePermission(role_id=role_mgr.id, permission_id=p_obj.id),
            RolePermission(role_id=role_fin.id, permission_id=p_obj.id),
        ])

    # 3. Create Users
    user_submitter = User(
        full_name="Submitter User",
        username=f"sub_{uuid.uuid4().hex[:6]}",
        email=f"sub_{uuid.uuid4().hex[:6]}@example.com",
        password_hash=hash_password("password123"),
        is_active=True,
        is_superuser=True,
    )
    user_mgr = User(
        full_name="Manager User",
        username=f"mgr_{uuid.uuid4().hex[:6]}",
        email=f"mgr_{uuid.uuid4().hex[:6]}@example.com",
        password_hash=hash_password("password123"),
        is_active=True,
        is_superuser=True,
    )
    user_fin = User(
        full_name="Finance User",
        username=f"fin_{uuid.uuid4().hex[:6]}",
        email=f"fin_{uuid.uuid4().hex[:6]}@example.com",
        password_hash=hash_password("password123"),
        is_active=True,
        is_superuser=True,
    )
    db_session.add_all([user_submitter, user_mgr, user_fin])
    await db_session.flush()

    # Assign User Roles
    db_session.add(UserRole(user_id=user_submitter.id, role_id=role_mgr.id))
    db_session.add(UserRole(user_id=user_mgr.id, role_id=role_mgr.id))
    db_session.add(UserRole(user_id=user_fin.id, role_id=role_fin.id))
    await db_session.commit()

    # Refresh users
    await db_session.refresh(user_submitter)
    await db_session.refresh(user_mgr)
    await db_session.refresh(user_fin)

    # 4. Create a 2-Step Approval Workflow Definition
    wf_code = f"WF_EXPENSE_{uuid.uuid4().hex[:6]}"
    workflow = ApprovalWorkflow(
        code=wf_code,
        name="Expense Approval Workflow",
        description="2-step manager and finance approval workflow",
        module_name="expense",
        is_active=True,
    )
    db_session.add(workflow)
    await db_session.flush()

    step1 = ApprovalStep(
        workflow_id=workflow.id,
        step_number=1,
        approver_role_id=role_mgr.id,
        required_approvals=1,
        is_active=True,
    )
    step2 = ApprovalStep(
        workflow_id=workflow.id,
        step_number=2,
        approver_role_id=role_fin.id,
        required_approvals=1,
        is_active=True,
    )
    db_session.add_all([step1, step2])
    await db_session.commit()

    await db_session.refresh(workflow)

    return {
        "workflow": workflow,
        "role_mgr": role_mgr,
        "role_fin": role_fin,
        "user_submitter": user_submitter,
        "user_mgr": user_mgr,
        "user_fin": user_fin,
    }


@pytest.mark.asyncio
async def test_start_workflow_and_sequential_approvals(db_session: AsyncSession, setup_approval_fixture):
    """
    Tests initiating an approval workflow and completing a 2-step sequential approval sequence.
    """
    fix = setup_approval_fixture
    engine = ApprovalEngineService(db_session)

    from app.schemas.approval_workflow import ApprovalActionRequest, ApprovalRequestCreate

    # 1. Start Workflow
    target_entity_id = str(uuid.uuid4())
    create_dto = ApprovalRequestCreate(
        workflow_code=fix["workflow"].code,
        entity_type="ExpenseClaim",
        entity_id=target_entity_id,
        comments="Please approve travel expenses",
    )

    request_obj = await engine.start_workflow(
        data=create_dto, current_user=fix["user_submitter"]
    )

    assert request_obj.id is not None
    assert request_obj.status == "Pending"
    assert request_obj.current_step_number == 1
    assert request_obj.submitted_by == fix["user_submitter"].id
    assert len(request_obj.history) == 1
    assert request_obj.history[0].action == "Submitting"

    # 2. Step 1 Approval by Manager
    action_dto = ApprovalActionRequest(comments="Manager approved Step 1")
    approved_step1 = await engine.approve_step(
        id=request_obj.id, data=action_dto, current_user=fix["user_mgr"]
    )

    assert approved_step1.status == "Pending"
    assert approved_step1.current_step_number == 2
    assert len(approved_step1.history) == 2
    assert approved_step1.history[1].action == "Approved Step"

    # 3. Step 2 Approval by Finance
    action_dto_2 = ApprovalActionRequest(comments="Finance approved Step 2")
    completed_wf = await engine.approve_step(
        id=request_obj.id, data=action_dto_2, current_user=fix["user_fin"]
    )

    assert completed_wf.status == "Approved"
    assert completed_wf.completed_at is not None
    assert len(completed_wf.history) == 4  # Submitting, Approved Step 1, Approved Step 2, Completed Workflow


@pytest.mark.asyncio
async def test_unauthorized_approver_rejection(db_session: AsyncSession, setup_approval_fixture):
    """
    Verifies that a user lacking the required approver role is rejected with HTTP 403 / UNAUTHORIZED_APPROVER.
    """
    fix = setup_approval_fixture
    engine = ApprovalEngineService(db_session)
    from app.schemas.approval_workflow import ApprovalActionRequest, ApprovalRequestCreate
    from app.exceptions.base import ApnaERPException

    create_dto = ApprovalRequestCreate(
        workflow_code=fix["workflow"].code,
        entity_type="ExpenseClaim",
        entity_id=str(uuid.uuid4()),
        comments="Test unauthorized approval",
    )
    req_obj = await engine.start_workflow(data=create_dto, current_user=fix["user_submitter"])

    # Create a non-superuser user without Manager role
    unauth_user = User(
        full_name="Unauthorized User",
        username=f"unauth_{uuid.uuid4().hex[:6]}",
        email=f"unauth_{uuid.uuid4().hex[:6]}@example.com",
        password_hash=hash_password("password123"),
        is_active=True,
        is_superuser=False,
    )
    db_session.add(unauth_user)
    await db_session.commit()
    await db_session.refresh(unauth_user)

    action_dto = ApprovalActionRequest(comments="Attempting unauthorized approval")
    with pytest.raises(ApnaERPException) as exc_info:
        await engine.approve_step(id=req_obj.id, data=action_dto, current_user=unauth_user)

    assert exc_info.value.status_code == 403
    assert exc_info.value.error_code == "UNAUTHORIZED_APPROVER"


@pytest.mark.asyncio
async def test_reject_workflow_at_step1(db_session: AsyncSession, setup_approval_fixture):
    """
    Tests rejecting an approval request at Step 1 by authorized approver.
    """
    fix = setup_approval_fixture
    engine = ApprovalEngineService(db_session)
    from app.schemas.approval_workflow import ApprovalActionRequest, ApprovalRequestCreate

    create_dto = ApprovalRequestCreate(
        workflow_code=fix["workflow"].code,
        entity_type="ExpenseClaim",
        entity_id=str(uuid.uuid4()),
        comments="Test rejection path",
    )
    req_obj = await engine.start_workflow(data=create_dto, current_user=fix["user_submitter"])

    # Manager rejects step 1
    action_dto = ApprovalActionRequest(comments="Over budget limits")
    rejected_req = await engine.reject_step(id=req_obj.id, data=action_dto, current_user=fix["user_mgr"])

    assert rejected_req.status == "Rejected"
    assert rejected_req.completed_at is not None
    assert len(rejected_req.history) == 2
    assert rejected_req.history[1].action == "Rejected"


@pytest.mark.asyncio
async def test_cancel_workflow_by_submitter(db_session: AsyncSession, setup_approval_fixture):
    """
    Tests cancelling a pending approval request by the submitter.
    """
    fix = setup_approval_fixture
    engine = ApprovalEngineService(db_session)
    from app.schemas.approval_workflow import ApprovalActionRequest, ApprovalRequestCreate

    create_dto = ApprovalRequestCreate(
        workflow_code=fix["workflow"].code,
        entity_type="ExpenseClaim",
        entity_id=str(uuid.uuid4()),
        comments="Test cancellation path",
    )
    req_obj = await engine.start_workflow(data=create_dto, current_user=fix["user_submitter"])

    action_dto = ApprovalActionRequest(comments="Withdrawing expense request")
    cancelled_req = await engine.cancel_workflow(id=req_obj.id, data=action_dto, current_user=fix["user_submitter"])

    assert cancelled_req.status == "Cancelled"
    assert cancelled_req.completed_at is not None
    assert len(cancelled_req.history) == 2
    assert cancelled_req.history[1].action == "Cancelled"


@pytest.mark.asyncio
async def test_approval_api_endpoints(async_client: AsyncClient, db_session: AsyncSession, setup_approval_fixture):
    """
    Tests REST API endpoints for approval workflow creation, listing, starting, and approving requests.
    """
    fix = setup_approval_fixture
    token = create_access_token(subject=str(fix["user_submitter"].id))
    headers = {"Authorization": f"Bearer {token}"}

    # 1. GET /api/v1/approval-workflows
    res_list = await async_client.get("/api/v1/approval-workflows", headers=headers)
    assert res_list.status_code == 200
    body_list = res_list.json()
    assert "items" in body_list
    assert body_list["total"] >= 1

    # 2. POST /api/v1/approval-requests
    req_payload = {
        "workflow_code": fix["workflow"].code,
        "entity_type": "PurchaseOrder",
        "entity_id": str(uuid.uuid4()),
        "comments": "API PO approval request",
    }
    res_start = await async_client.post("/api/v1/approval-requests", json=req_payload, headers=headers)
    assert res_start.status_code == 201
    body_start = res_start.json()
    assert body_start["status"] == "Pending"
    assert body_start["current_step_number"] == 1
    req_id = body_start["id"]

    # 3. POST /api/v1/approval-requests/{id}/approve by Manager
    mgr_token = create_access_token(subject=str(fix["user_mgr"].id))
    mgr_headers = {"Authorization": f"Bearer {mgr_token}"}

    res_app = await async_client.post(
        f"/api/v1/approval-requests/{req_id}/approve",
        json={"comments": "Approved via API"},
        headers=mgr_headers,
    )
    assert res_app.status_code == 200
    body_app = res_app.json()
    assert body_app["current_step_number"] == 2
    assert body_app["status"] == "Pending"
