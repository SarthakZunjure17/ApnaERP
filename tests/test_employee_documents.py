import datetime
import uuid
import pytest
import pytest_asyncio
from httpx import AsyncClient

from app.core.celery import celery_app
from app.db.session import AsyncSessionLocal
from app.models.department import Department
from app.models.employee import Employee
from app.repositories.department import department_repository
from app.repositories.employee import employee_repository
from app.repositories.employee_document import employee_document_repository
from app.repositories.file import file_repository
from app.repositories.user import user_repository
from app.schemas.employee_document import (
    DocumentRejectRequest,
    DocumentType,
    DocumentVerifyRequest,
    EmployeeDocumentCreate,
    EmployeeDocumentUpdate,
    VerificationStatus,
)
from app.services.employee_document import EmployeeDocumentService


@pytest_asyncio.fixture
async def admin_token(async_client: AsyncClient) -> str:
    """Fixture creating Super Admin and returning Bearer token."""
    unique_id = uuid.uuid4().hex[:6]
    email = f"docadmin_{unique_id}@example.com"
    username = f"docadmin_{unique_id}"

    reg_payload = {
        "full_name": "Document Admin",
        "email": email,
        "username": username,
        "password": "AdminPassword123!",
    }
    reg_resp = await async_client.post("/api/v1/auth/register", json=reg_payload)
    user_id = uuid.UUID(reg_resp.json()["id"])

    async with AsyncSessionLocal() as session:
        user = await user_repository.get_by_id(session, user_id)
        if user:
            user.is_superuser = True
            await session.commit()

    login_resp = await async_client.post("/api/v1/auth/login", json={
        "username_or_email": email,
        "password": "AdminPassword123!",
    })
    return login_resp.json()["access_token"]


@pytest_asyncio.fixture
async def test_employee() -> Employee:
    """Fixture creating an active department and employee."""
    async with AsyncSessionLocal() as session:
        dept = await department_repository.create(session, obj_in={
            "code": f"DEPT-DOC-{uuid.uuid4().hex[:6]}",
            "name": f"Dept for Docs {uuid.uuid4().hex[:6]}",
            "is_active": True,
        })
        emp = await employee_repository.create(session, obj_in={
            "employee_code": f"EMP-DOC-{uuid.uuid4().hex[:6]}",
            "first_name": "Doc",
            "last_name": "Testing",
            "work_email": f"doctest_{uuid.uuid4().hex[:6]}@example.com",
            "department_id": dept.id,
            "joining_date": datetime.date(2026, 1, 1),
            "is_active": True,
        })
        return emp


@pytest_asyncio.fixture
async def test_file_id() -> uuid.UUID:
    """Fixture creating a user and storage file record, returning file UUID."""
    async with AsyncSessionLocal() as session:
        uploader = await user_repository.create(session, obj_in={
            "full_name": "Uploader User",
            "email": f"fileup_{uuid.uuid4().hex[:6]}@example.com",
            "username": f"fileup_{uuid.uuid4().hex[:6]}",
            "password_hash": "hash",
            "is_active": True,
        })
        storage_file = await file_repository.create(session, obj_in={
            "original_filename": "passport.pdf",
            "stored_filename": f"stored_{uuid.uuid4().hex}.pdf",
            "file_extension": "pdf",
            "mime_type": "application/pdf",
            "file_size": 1024,
            "storage_path": "/uploads/test/passport.pdf",
            "checksum": f"checksum_{uuid.uuid4().hex}",
            "is_public": False,
            "uploaded_by_id": uploader.id,
        })
        return storage_file.id


@pytest.mark.asyncio
async def test_employee_document_repository_crud(test_employee: Employee, test_file_id: uuid.UUID):
    """Tests EmployeeDocumentRepository direct operations."""
    async with AsyncSessionLocal() as session:
        repo = employee_document_repository
        doc = await repo.create(session, obj_in={
            "employee_id": test_employee.id,
            "file_id": test_file_id,
            "document_type": DocumentType.PASSPORT.value,
            "document_number": "P1234567",
            "issue_date": datetime.date(2020, 1, 1),
            "expiry_date": datetime.date(2030, 1, 1),
            "is_mandatory": True,
        })
        assert doc.id is not None
        assert doc.document_number == "P1234567"

        fetched_list = await repo.get_by_employee(session, test_employee.id)
        assert len(fetched_list) >= 1

        by_file = await repo.get_by_file(session, test_file_id)
        assert by_file is not None
        assert by_file.id == doc.id

        assert await repo.exists_mandatory_document_type(session, test_employee.id, DocumentType.PASSPORT.value) is True

        await repo.soft_delete(session, id=doc.id)
        assert await repo.get_by_file(session, test_file_id) is None

        await repo.restore(session, id=doc.id)
        assert await repo.get_by_file(session, test_file_id) is not None


@pytest.mark.asyncio
async def test_employee_document_service_business_rules(test_employee: Employee, test_file_id: uuid.UUID):
    """
    Tests EmployeeDocumentService business rules:
    - Date validation (expiry_date < issue_date)
    - Duplicate mandatory document check
    - Verification and rejection workflows
    """
    async with AsyncSessionLocal() as session:
        service = EmployeeDocumentService(session)

        # 1. Create Valid Document
        doc = await service.create_document(EmployeeDocumentCreate(
            employee_id=test_employee.id,
            file_id=test_file_id,
            document_type=DocumentType.AADHAAR,
            document_number="1234-5678-9012",
            issue_date=datetime.date(2021, 1, 1),
            expiry_date=datetime.date(2031, 1, 1),
            is_mandatory=True,
        ))
        assert doc.verification_status == VerificationStatus.PENDING.value

        # 2. Expiry earlier than Issue Date Error
        with pytest.raises(Exception) as exc_info:
            await service.create_document(EmployeeDocumentCreate(
                employee_id=test_employee.id,
                file_id=test_file_id,
                document_type=DocumentType.PAN,
                issue_date=datetime.date(2025, 1, 1),
                expiry_date=datetime.date(2020, 1, 1),
            ))
        assert "Expiry date cannot be earlier than issue date" in str(exc_info.value)

        # 3. Duplicate Mandatory Document Error
        with pytest.raises(Exception) as exc_info:
            await service.create_document(EmployeeDocumentCreate(
                employee_id=test_employee.id,
                file_id=test_file_id,
                document_type=DocumentType.AADHAAR,
                is_mandatory=True,
            ))
        assert "already exists for this employee" in str(exc_info.value)

        # 4. Verification Workflow
        verifier_user = await user_repository.create(session, obj_in={
            "full_name": "Verifier User",
            "email": f"verifier_{uuid.uuid4().hex[:6]}@example.com",
            "username": f"verifier_{uuid.uuid4().hex[:6]}",
            "password_hash": "hash",
            "is_active": True,
        })

        verified_doc = await service.verify_document(
            doc.id, payload=DocumentVerifyRequest(notes="Approved valid Aadhaar"), current_user=verifier_user
        )
        assert verified_doc.verification_status == VerificationStatus.VERIFIED.value
        assert verified_doc.verified_by == verifier_user.id
        assert verified_doc.verified_at is not None

        # 5. Rejection Workflow
        pan_file = await file_repository.create(session, obj_in={
            "original_filename": "pan.pdf",
            "stored_filename": f"stored_{uuid.uuid4().hex}.pdf",
            "file_extension": "pdf",
            "mime_type": "application/pdf",
            "file_size": 1024,
            "storage_path": "/uploads/test/pan.pdf",
            "checksum": f"checksum_{uuid.uuid4().hex}",
            "is_public": False,
            "uploaded_by_id": verifier_user.id,
        })
        doc2 = await service.create_document(EmployeeDocumentCreate(
            employee_id=test_employee.id,
            file_id=pan_file.id,
            document_type=DocumentType.PAN,
            is_mandatory=False,
        ))
        rejected_doc = await service.reject_document(
            doc2.id, payload=DocumentRejectRequest(notes="Blurred photo ID"), current_user=verifier_user
        )
        assert rejected_doc.verification_status == VerificationStatus.REJECTED.value
        assert "Blurred photo ID" in rejected_doc.notes


@pytest.mark.asyncio
async def test_employee_document_api_endpoints(
    async_client: AsyncClient, admin_token: str, test_employee: Employee, test_file_id: uuid.UUID
):
    """
    Tests full API workflow for Employee Document Management:
    - POST /api/v1/employee-documents
    - GET /api/v1/employees/{employee_id}/documents
    - GET /api/v1/employee-documents
    - GET /api/v1/employee-documents/{id}
    - PUT /api/v1/employee-documents/{id}
    - PATCH /api/v1/employee-documents/{id}/verify
    - PATCH /api/v1/employee-documents/{id}/reject
    - DELETE /api/v1/employee-documents/{id}
    - PATCH /api/v1/employee-documents/{id}/restore
    """
    headers = {"Authorization": f"Bearer {admin_token}"}
    celery_app.conf.task_always_eager = True

    # 1. POST /api/v1/employee-documents
    res = await async_client.post(
        "/api/v1/employee-documents",
        json={
            "employee_id": str(test_employee.id),
            "file_id": str(test_file_id),
            "document_type": "Passport",
            "document_number": "API-P99999",
            "issue_date": "2022-01-01",
            "expiry_date": "2032-01-01",
            "is_mandatory": True,
        },
        headers=headers,
    )
    assert res.status_code == 201
    doc_data = res.json()
    doc_id = doc_data["id"]

    # 2. GET /api/v1/employees/{employee_id}/documents
    res = await async_client.get(f"/api/v1/employees/{test_employee.id}/documents", headers=headers)
    assert res.status_code == 200
    docs = res.json()
    assert len(docs) >= 1

    # 3. GET /api/v1/employee-documents (List)
    res = await async_client.get("/api/v1/employee-documents?search=Passport", headers=headers)
    assert res.status_code == 200
    list_data = res.json()
    assert list_data["total"] >= 1

    # 4. GET /api/v1/employee-documents/{id}
    res = await async_client.get(f"/api/v1/employee-documents/{doc_id}", headers=headers)
    assert res.status_code == 200
    assert res.json()["document_number"] == "API-P99999"

    # 5. PUT /api/v1/employee-documents/{id}
    res = await async_client.put(
        f"/api/v1/employee-documents/{doc_id}",
        json={"notes": "Updated API notes"},
        headers=headers,
    )
    assert res.status_code == 200
    assert res.json()["notes"] == "Updated API notes"

    # 6. PATCH /api/v1/employee-documents/{id}/verify
    res = await async_client.patch(
        f"/api/v1/employee-documents/{doc_id}/verify",
        json={"notes": "Looks valid"},
        headers=headers,
    )
    assert res.status_code == 200
    assert res.json()["verification_status"] == "Verified"

    # 7. PATCH /api/v1/employee-documents/{id}/reject
    res = await async_client.patch(
        f"/api/v1/employee-documents/{doc_id}/reject",
        json={"notes": "Re-rejected test"},
        headers=headers,
    )
    assert res.status_code == 200
    assert res.json()["verification_status"] == "Rejected"

    # 8. DELETE /api/v1/employee-documents/{id}
    res = await async_client.delete(f"/api/v1/employee-documents/{doc_id}", headers=headers)
    assert res.status_code == 200
    assert res.json()["is_deleted"] is True

    # 9. PATCH /api/v1/employee-documents/{id}/restore
    res = await async_client.patch(f"/api/v1/employee-documents/{doc_id}/restore", headers=headers)
    assert res.status_code == 200
    assert res.json()["is_deleted"] is False


@pytest.mark.asyncio
async def test_employee_document_rbac_unauthorized(async_client: AsyncClient):
    """Tests 401 Unauthorized for unauthenticated requests."""
    res = await async_client.get("/api/v1/employee-documents")
    assert res.status_code == 401

    res = await async_client.post("/api/v1/employee-documents", json={"document_type": "PAN"})
    assert res.status_code == 401
