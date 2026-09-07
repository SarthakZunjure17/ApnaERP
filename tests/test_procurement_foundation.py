import asyncio
from datetime import datetime, timezone
from decimal import Decimal
from typing import AsyncGenerator, Dict, Tuple
import uuid
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.core.security import hash_password
from app.db.seed_rbac import seed_rbac_data
from app.db.session import AsyncSessionLocal
from app.exceptions.base import (
    DuplicateResourceException,
    NotFoundException,
    ValidationException,
)
from app.main import app
from app.models.file import File
from app.models.purchase_order import PurchaseOrder
from app.models.supplier import (
    Supplier,
    SupplierAddress,
    SupplierCategory,
    SupplierContact,
    SupplierDocument,
    SupplierRating,
)
from app.models.user import User
from app.repositories.rbac import permission_repository, role_repository, user_role_repository
from app.repositories.user import user_repository
from app.schemas.procurement import (
    SupplierAddressCreate,
    SupplierAddressUpdate,
    SupplierCategoryCreate,
    SupplierCategoryUpdate,
    SupplierContactCreate,
    SupplierContactUpdate,
    SupplierCreate,
    SupplierDocumentCreate,
    SupplierDocumentUpdate,
    SupplierRatingCreate,
    SupplierUpdate,
)
from app.services.audit_log import audit_log_service
from app.services.supplier_services import supplier_service


@pytest_asyncio.fixture(scope="function")
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


async def create_user_with_role(
    async_client: AsyncClient, role_name: str, is_superuser: bool = False
) -> Tuple[User, Dict[str, str]]:
    unique_id = uuid.uuid4().hex[:6]
    email = f"user_{role_name.lower().replace(' ', '_')}_{unique_id}@example.com"
    username = f"u_{role_name.lower().replace(' ', '_')}_{unique_id}"
    password = "TestPassword123!"

    reg_payload = {
        "full_name": f"Test {role_name}",
        "email": email,
        "username": username,
        "password": password,
    }
    reg_resp = await async_client.post("/api/v1/auth/register", json=reg_payload)
    assert reg_resp.status_code == 201, reg_resp.text
    user_id = uuid.UUID(reg_resp.json()["id"])

    async with AsyncSessionLocal() as session:
        await seed_rbac_data(session)
        user = await user_repository.get_by_id(session, user_id)
        role = await role_repository.get_by_name(session, role_name)
        if user and is_superuser:
            user.is_superuser = True
            session.add(user)
        if user and role:
            await user_role_repository.assign_role_to_user(session, user_id=user.id, role_id=role.id)
        await session.commit()

    # Login to get JWT
    login_resp = await async_client.post(
        "/api/v1/auth/login",
        json={"username_or_email": email, "password": password},
    )
    assert login_resp.status_code == 200, login_resp.text
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    return user, headers


async def create_test_file(session, user_id: uuid.UUID) -> File:
    file_obj = File(
        original_filename="supplier_tax_cert.pdf",
        stored_filename=f"doc_{uuid.uuid4().hex[:8]}.pdf",
        file_extension="pdf",
        mime_type="application/pdf",
        file_size=1024,
        storage_path="uploads/suppliers/doc.pdf",
        uploaded_by_id=user_id,
        checksum=uuid.uuid4().hex,
        is_public=False,
    )
    session.add(file_obj)
    await session.commit()
    await session.refresh(file_obj)
    return file_obj


# =============================================================================
# 1-5. SUPPLIER CATEGORY TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_01_category_create(async_client: AsyncClient):
    _, headers = await create_user_with_role(async_client, "Procurement Manager")
    cat_code = f"CAT-IND-{uuid.uuid4().hex[:4]}"
    payload = {"code": cat_code, "name": "Industrial Fasteners", "description": "High-tensile nuts and bolts"}
    resp = await async_client.post("/api/v1/suppliers/categories", json=payload, headers=headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["code"] == cat_code
    assert data["name"] == "Industrial Fasteners"
    assert "id" in data


@pytest.mark.asyncio
async def test_02_duplicate_category_code_rejection(async_client: AsyncClient):
    _, headers = await create_user_with_role(async_client, "Procurement Manager")
    cat_code = f"CAT-DUP-{uuid.uuid4().hex[:4]}"
    payload = {"code": cat_code, "name": "Plastics", "description": "Polymers"}
    resp1 = await async_client.post("/api/v1/suppliers/categories", json=payload, headers=headers)
    assert resp1.status_code == 201

    resp2 = await async_client.post("/api/v1/suppliers/categories", json=payload, headers=headers)
    assert resp2.status_code in (400, 409)


@pytest.mark.asyncio
async def test_03_category_update(async_client: AsyncClient):
    _, headers = await create_user_with_role(async_client, "Procurement Manager")
    cat_code = f"CAT-UPD-{uuid.uuid4().hex[:4]}"
    resp = await async_client.post(
        "/api/v1/suppliers/categories",
        json={"code": cat_code, "name": "Metals Initial"},
        headers=headers,
    )
    cat_id = resp.json()["id"]

    upd_resp = await async_client.patch(
        f"/api/v1/suppliers/categories/{cat_id}",
        json={"name": "Metals & Alloys", "description": "Updated description"},
        headers=headers,
    )
    assert upd_resp.status_code == 200
    assert upd_resp.json()["name"] == "Metals & Alloys"


@pytest.mark.asyncio
async def test_04_category_safe_deletion_and_protection(async_client: AsyncClient):
    _, headers = await create_user_with_role(async_client, "Procurement Manager")
    cat_code = f"CAT-DEL-{uuid.uuid4().hex[:4]}"
    resp = await async_client.post(
        "/api/v1/suppliers/categories",
        json={"code": cat_code, "name": "Temporary Category"},
        headers=headers,
    )
    cat_id = resp.json()["id"]

    # 1. Unreferenced category can be deleted
    del_resp = await async_client.delete(f"/api/v1/suppliers/categories/{cat_id}", headers=headers)
    assert del_resp.status_code == 200

    # 2. Referenced category cannot be deleted
    cat2 = await async_client.post(
        "/api/v1/suppliers/categories",
        json={"code": f"CAT-REF-{uuid.uuid4().hex[:4]}", "name": "Protected Category"},
        headers=headers,
    )
    cat2_id = cat2.json()["id"]

    sup_resp = await async_client.post(
        "/api/v1/suppliers",
        json={"name": "Dependent Supplier", "category_id": cat2_id},
        headers=headers,
    )
    assert sup_resp.status_code == 201

    del_fail = await async_client.delete(f"/api/v1/suppliers/categories/{cat2_id}", headers=headers)
    assert del_fail.status_code in (400, 422)


@pytest.mark.asyncio
async def test_05_category_rbac(async_client: AsyncClient):
    _, mgr_headers = await create_user_with_role(async_client, "Procurement Manager")
    _, view_headers = await create_user_with_role(async_client, "Procurement Viewer")

    # Viewer cannot create
    fail_resp = await async_client.post(
        "/api/v1/suppliers/categories",
        json={"code": f"CAT-NO-{uuid.uuid4().hex[:4]}", "name": "Unauthorized"},
        headers=view_headers,
    )
    assert fail_resp.status_code == 403

    # Viewer can read list
    read_resp = await async_client.get("/api/v1/suppliers/categories", headers=view_headers)
    assert read_resp.status_code == 200
    assert isinstance(read_resp.json(), list)


# =============================================================================
# 6-16. SUPPLIER MASTER & LIFECYCLE TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_06_supplier_create_autocode_and_custom_code(async_client: AsyncClient):
    _, headers = await create_user_with_role(async_client, "Procurement Manager")

    # 1. Auto code generation
    resp1 = await async_client.post(
        "/api/v1/suppliers",
        json={
            "name": "Apex Engineering Ltd",
            "payment_terms": "Net 30",
            "credit_limit": 25000.0,
            "currency": "USD",
        },
        headers=headers,
    )
    assert resp1.status_code == 201
    data1 = resp1.json()
    assert data1["code"].startswith("SUP-")
    assert data1["status"] == "Active"

    # 2. Custom code
    custom_code = f"SUP-CUSTOM-{uuid.uuid4().hex[:4]}"
    resp2 = await async_client.post(
        "/api/v1/suppliers",
        json={"code": custom_code, "name": "Custom Code Supplier"},
        headers=headers,
    )
    assert resp2.status_code == 201
    assert resp2.json()["code"] == custom_code


@pytest.mark.asyncio
async def test_07_duplicate_supplier_code_rejection(async_client: AsyncClient):
    _, headers = await create_user_with_role(async_client, "Procurement Manager")
    sup_code = f"SUP-DUP-{uuid.uuid4().hex[:4]}"
    resp1 = await async_client.post(
        "/api/v1/suppliers",
        json={"code": sup_code, "name": "Original Supplier"},
        headers=headers,
    )
    assert resp1.status_code == 201

    resp2 = await async_client.post(
        "/api/v1/suppliers",
        json={"code": sup_code, "name": "Duplicate Supplier"},
        headers=headers,
    )
    assert resp2.status_code in (400, 409)


@pytest.mark.asyncio
async def test_08_supplier_retrieval(async_client: AsyncClient):
    _, headers = await create_user_with_role(async_client, "Procurement Manager")
    resp = await async_client.post(
        "/api/v1/suppliers",
        json={"name": "Retrieval Test Supplier", "currency": "EUR"},
        headers=headers,
    )
    sup_id = resp.json()["id"]

    get_resp = await async_client.get(f"/api/v1/suppliers/{sup_id}", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == sup_id
    assert get_resp.json()["name"] == "Retrieval Test Supplier"


@pytest.mark.asyncio
async def test_09_supplier_update(async_client: AsyncClient):
    _, headers = await create_user_with_role(async_client, "Procurement Manager")
    resp = await async_client.post(
        "/api/v1/suppliers",
        json={"name": "Pre-update Supplier", "payment_terms": "Net 30"},
        headers=headers,
    )
    sup_id = resp.json()["id"]

    upd_resp = await async_client.patch(
        f"/api/v1/suppliers/{sup_id}",
        json={"name": "Post-update Supplier", "payment_terms": "Net 60", "credit_limit": 75000.0},
        headers=headers,
    )
    assert upd_resp.status_code == 200
    assert upd_resp.json()["name"] == "Post-update Supplier"
    assert upd_resp.json()["payment_terms"] == "Net 60"
    assert float(upd_resp.json()["credit_limit"]) == 75000.0


@pytest.mark.asyncio
async def test_10_supplier_search(async_client: AsyncClient):
    _, headers = await create_user_with_role(async_client, "Procurement Manager")
    unique_term = f"FindMe{uuid.uuid4().hex[:6]}"
    await async_client.post(
        "/api/v1/suppliers",
        json={"name": f"Global {unique_term} Corp", "gst_vat_number": "GST123SEARCH"},
        headers=headers,
    )

    search_resp = await async_client.get(f"/api/v1/suppliers?search={unique_term}", headers=headers)
    assert search_resp.status_code == 200
    data = search_resp.json()
    assert data["total"] >= 1
    assert any(unique_term in s["name"] for s in data["items"])


@pytest.mark.asyncio
async def test_11_supplier_pagination(async_client: AsyncClient):
    _, headers = await create_user_with_role(async_client, "Procurement Manager")
    resp = await async_client.get("/api/v1/suppliers?page=1&size=2", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data
    assert data["page"] == 1
    assert data["size"] == 2
    assert len(data["items"]) <= 2


@pytest.mark.asyncio
async def test_12_supplier_activation(async_client: AsyncClient):
    _, headers = await create_user_with_role(async_client, "Procurement Manager")
    resp = await async_client.post("/api/v1/suppliers", json={"name": "Active Test Supplier"}, headers=headers)
    sup_id = resp.json()["id"]

    # Deactivate then activate
    await async_client.post(f"/api/v1/suppliers/{sup_id}/deactivate", headers=headers)
    act_resp = await async_client.post(f"/api/v1/suppliers/{sup_id}/activate", headers=headers)
    assert act_resp.status_code == 200
    assert act_resp.json()["status"] == "Active"


@pytest.mark.asyncio
async def test_13_supplier_deactivation(async_client: AsyncClient):
    _, headers = await create_user_with_role(async_client, "Procurement Manager")
    resp = await async_client.post("/api/v1/suppliers", json={"name": "Deactivate Test Supplier"}, headers=headers)
    sup_id = resp.json()["id"]

    deact_resp = await async_client.post(
        f"/api/v1/suppliers/{sup_id}/deactivate?reason=Temporary+Closure", headers=headers
    )
    assert deact_resp.status_code == 200
    assert deact_resp.json()["status"] == "Inactive"


@pytest.mark.asyncio
async def test_14_supplier_blacklisting(async_client: AsyncClient):
    _, headers = await create_user_with_role(async_client, "Procurement Manager")
    resp = await async_client.post("/api/v1/suppliers", json={"name": "Blacklist Target"}, headers=headers)
    sup_id = resp.json()["id"]

    bl_resp = await async_client.post(
        f"/api/v1/suppliers/{sup_id}/blacklist?reason=Severe+Quality+Defects", headers=headers
    )
    assert bl_resp.status_code == 200
    assert bl_resp.json()["status"] == "Blacklisted"


@pytest.mark.asyncio
async def test_15_invalid_status_transition_rejection(async_client: AsyncClient):
    _, headers = await create_user_with_role(async_client, "Procurement Manager")
    resp = await async_client.post("/api/v1/suppliers", json={"name": "Status Guard Supplier"}, headers=headers)
    sup_id = resp.json()["id"]

    # Activating already active supplier rejected
    dup_act = await async_client.post(f"/api/v1/suppliers/{sup_id}/activate", headers=headers)
    assert dup_act.status_code in (400, 422)


@pytest.mark.asyncio
async def test_16_protected_delete_behavior(async_client: AsyncClient):
    _, headers = await create_user_with_role(async_client, "Procurement Manager")
    resp = await async_client.post("/api/v1/suppliers", json={"name": "Soft Delete Target"}, headers=headers)
    sup_id = resp.json()["id"]

    del_resp = await async_client.delete(f"/api/v1/suppliers/{sup_id}", headers=headers)
    assert del_resp.status_code == 200

    # Getting soft-deleted supplier returns 404
    get_resp = await async_client.get(f"/api/v1/suppliers/{sup_id}", headers=headers)
    assert get_resp.status_code == 404


# =============================================================================
# 17-21. SUPPLIER CONTACTS TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_17_create_contact(async_client: AsyncClient):
    _, headers = await create_user_with_role(async_client, "Procurement Manager")
    sup = await async_client.post("/api/v1/suppliers", json={"name": "Contact Host"}, headers=headers)
    sup_id = sup.json()["id"]

    c_payload = {
        "contact_name": "Alice Johnson",
        "designation": "Sales Director",
        "email": "alice@contacthost.com",
        "phone": "+1-555-0100",
        "is_primary": True,
    }
    resp = await async_client.post(f"/api/v1/suppliers/{sup_id}/contacts", json=c_payload, headers=headers)
    assert resp.status_code == 201
    assert resp.json()["contact_name"] == "Alice Johnson"
    assert resp.json()["is_primary"] is True


@pytest.mark.asyncio
async def test_18_update_contact(async_client: AsyncClient):
    _, headers = await create_user_with_role(async_client, "Procurement Manager")
    sup = await async_client.post("/api/v1/suppliers", json={"name": "Contact Update Host"}, headers=headers)
    sup_id = sup.json()["id"]

    c_resp = await async_client.post(
        f"/api/v1/suppliers/{sup_id}/contacts",
        json={"contact_name": "Bob", "email": "bob@test.com"},
        headers=headers,
    )
    contact_id = c_resp.json()["id"]

    upd_resp = await async_client.patch(
        f"/api/v1/suppliers/{sup_id}/contacts/{contact_id}",
        json={"contact_name": "Robert Smith", "phone": "+1-555-9999"},
        headers=headers,
    )
    assert upd_resp.status_code == 200
    assert upd_resp.json()["contact_name"] == "Robert Smith"


@pytest.mark.asyncio
async def test_19_one_primary_contact_rule(async_client: AsyncClient):
    _, headers = await create_user_with_role(async_client, "Procurement Manager")
    sup = await async_client.post("/api/v1/suppliers", json={"name": "Primary Contact Test"}, headers=headers)
    sup_id = sup.json()["id"]

    # Add contact 1 as primary
    c1 = await async_client.post(
        f"/api/v1/suppliers/{sup_id}/contacts",
        json={"contact_name": "First Primary", "email": "p1@test.com", "is_primary": True},
        headers=headers,
    )
    assert c1.json()["is_primary"] is True

    # Add contact 2 as non-primary
    c2 = await async_client.post(
        f"/api/v1/suppliers/{sup_id}/contacts",
        json={"contact_name": "Secondary", "email": "p2@test.com", "is_primary": False},
        headers=headers,
    )
    assert c2.json()["is_primary"] is False

    contacts_list = await async_client.get(f"/api/v1/suppliers/{sup_id}/contacts", headers=headers)
    primaries = [c for c in contacts_list.json() if c["is_primary"]]
    assert len(primaries) == 1
    assert primaries[0]["contact_name"] == "First Primary"


@pytest.mark.asyncio
async def test_20_replace_primary_contact(async_client: AsyncClient):
    _, headers = await create_user_with_role(async_client, "Procurement Manager")
    sup = await async_client.post("/api/v1/suppliers", json={"name": "Swap Primary Host"}, headers=headers)
    sup_id = sup.json()["id"]

    c1 = await async_client.post(
        f"/api/v1/suppliers/{sup_id}/contacts",
        json={"contact_name": "Old Primary", "email": "old@test.com", "is_primary": True},
        headers=headers,
    )
    c1_id = c1.json()["id"]

    c2 = await async_client.post(
        f"/api/v1/suppliers/{sup_id}/contacts",
        json={"contact_name": "New Primary", "email": "new@test.com", "is_primary": True},
        headers=headers,
    )
    c2_id = c2.json()["id"]

    # Verify c1 is no longer primary and c2 is primary
    c1_check = await async_client.get(f"/api/v1/suppliers/{sup_id}/contacts/{c1_id}", headers=headers)
    c2_check = await async_client.get(f"/api/v1/suppliers/{sup_id}/contacts/{c2_id}", headers=headers)
    assert c1_check.json()["is_primary"] is False
    assert c2_check.json()["is_primary"] is True


@pytest.mark.asyncio
async def test_21_cross_supplier_contact_rejection(async_client: AsyncClient):
    _, headers = await create_user_with_role(async_client, "Procurement Manager")
    sup1 = await async_client.post("/api/v1/suppliers", json={"name": "Supplier One"}, headers=headers)
    sup2 = await async_client.post("/api/v1/suppliers", json={"name": "Supplier Two"}, headers=headers)
    sup1_id = sup1.json()["id"]
    sup2_id = sup2.json()["id"]

    c1 = await async_client.post(
        f"/api/v1/suppliers/{sup1_id}/contacts",
        json={"contact_name": "One Contact", "email": "c1@s1.com"},
        headers=headers,
    )
    c1_id = c1.json()["id"]

    # Accessing c1 via sup2 must 404
    cross_resp = await async_client.get(f"/api/v1/suppliers/{sup2_id}/contacts/{c1_id}", headers=headers)
    assert cross_resp.status_code == 404


# =============================================================================
# 22-25. SUPPLIER ADDRESSES TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_22_create_address(async_client: AsyncClient):
    _, headers = await create_user_with_role(async_client, "Procurement Manager")
    sup = await async_client.post("/api/v1/suppliers", json={"name": "Address Host"}, headers=headers)
    sup_id = sup.json()["id"]

    addr_payload = {
        "address_type": "Billing",
        "address_line1": "100 Innovation Way",
        "address_line2": "Suite 400",
        "city": "San Jose",
        "state": "CA",
        "country": "USA",
        "postal_code": "95134",
        "is_primary": True,
    }
    resp = await async_client.post(f"/api/v1/suppliers/{sup_id}/addresses", json=addr_payload, headers=headers)
    assert resp.status_code == 201
    assert resp.json()["city"] == "San Jose"
    assert resp.json()["address_type"] == "Billing"


@pytest.mark.asyncio
async def test_23_update_address(async_client: AsyncClient):
    _, headers = await create_user_with_role(async_client, "Procurement Manager")
    sup = await async_client.post("/api/v1/suppliers", json={"name": "Address Update Host"}, headers=headers)
    sup_id = sup.json()["id"]

    addr = await async_client.post(
        f"/api/v1/suppliers/{sup_id}/addresses",
        json={
            "address_type": "Shipping",
            "address_line1": "123 Old St",
            "city": "Austin",
            "state": "TX",
            "country": "USA",
            "postal_code": "78701",
        },
        headers=headers,
    )
    addr_id = addr.json()["id"]

    upd_resp = await async_client.patch(
        f"/api/v1/suppliers/{sup_id}/addresses/{addr_id}",
        json={"address_line1": "456 New Blvd", "postal_code": "78702"},
        headers=headers,
    )
    assert upd_resp.status_code == 200
    assert upd_resp.json()["address_line1"] == "456 New Blvd"
    assert upd_resp.json()["postal_code"] == "78702"


@pytest.mark.asyncio
async def test_24_address_type_validation(async_client: AsyncClient):
    _, headers = await create_user_with_role(async_client, "Procurement Manager")
    sup = await async_client.post("/api/v1/suppliers", json={"name": "Bad Address Host"}, headers=headers)
    sup_id = sup.json()["id"]

    resp = await async_client.post(
        f"/api/v1/suppliers/{sup_id}/addresses",
        json={
            "address_type": "InvalidTypeXYZ",
            "address_line1": "123 St",
            "city": "Dallas",
            "state": "TX",
            "country": "USA",
            "postal_code": "75001",
        },
        headers=headers,
    )
    assert resp.status_code in (400, 422)


@pytest.mark.asyncio
async def test_25_cross_supplier_address_rejection(async_client: AsyncClient):
    _, headers = await create_user_with_role(async_client, "Procurement Manager")
    sup1 = await async_client.post("/api/v1/suppliers", json={"name": "Supplier A"}, headers=headers)
    sup2 = await async_client.post("/api/v1/suppliers", json={"name": "Supplier B"}, headers=headers)
    sup1_id = sup1.json()["id"]
    sup2_id = sup2.json()["id"]

    addr = await async_client.post(
        f"/api/v1/suppliers/{sup1_id}/addresses",
        json={
            "address_type": "Head Office",
            "address_line1": "1 Alpha Way",
            "city": "Denver",
            "state": "CO",
            "country": "USA",
            "postal_code": "80202",
        },
        headers=headers,
    )
    addr_id = addr.json()["id"]

    # Cross delete attempt
    del_resp = await async_client.delete(f"/api/v1/suppliers/{sup2_id}/addresses/{addr_id}", headers=headers)
    assert del_resp.status_code == 404


# =============================================================================
# 26-29. SUPPLIER DOCUMENTS TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_26_attach_canonical_file(async_client: AsyncClient):
    user, headers = await create_user_with_role(async_client, "Procurement Manager")
    sup = await async_client.post("/api/v1/suppliers", json={"name": "Doc Host"}, headers=headers)
    sup_id = sup.json()["id"]

    async with AsyncSessionLocal() as session:
        file_obj = await create_test_file(session, user.id)
        file_id = file_obj.id

    doc_payload = {
        "file_id": str(file_id),
        "document_type": "Tax Identification Certificate",
        "description": "Form W-9 equivalent",
    }
    resp = await async_client.post(f"/api/v1/suppliers/{sup_id}/documents", json=doc_payload, headers=headers)
    assert resp.status_code == 201
    assert resp.json()["document_type"] == "Tax Identification Certificate"
    assert resp.json()["file_id"] == str(file_id)


@pytest.mark.asyncio
async def test_27_document_metadata_update(async_client: AsyncClient):
    user, headers = await create_user_with_role(async_client, "Procurement Manager")
    sup = await async_client.post("/api/v1/suppliers", json={"name": "Doc Update Host"}, headers=headers)
    sup_id = sup.json()["id"]

    async with AsyncSessionLocal() as session:
        file_obj = await create_test_file(session, user.id)
        file_id = file_obj.id

    doc = await async_client.post(
        f"/api/v1/suppliers/{sup_id}/documents",
        json={"file_id": str(file_id), "document_type": "ISO 9001", "description": "Initial draft"},
        headers=headers,
    )
    doc_id = doc.json()["id"]

    upd_resp = await async_client.patch(
        f"/api/v1/suppliers/{sup_id}/documents/{doc_id}",
        json={"description": "Verified ISO 9001:2015 Quality Certificate"},
        headers=headers,
    )
    assert upd_resp.status_code == 200
    assert upd_resp.json()["description"] == "Verified ISO 9001:2015 Quality Certificate"


@pytest.mark.asyncio
async def test_28_invalid_file_rejection(async_client: AsyncClient):
    _, headers = await create_user_with_role(async_client, "Procurement Manager")
    sup = await async_client.post("/api/v1/suppliers", json={"name": "Doc Fail Host"}, headers=headers)
    sup_id = sup.json()["id"]

    fake_file_id = uuid.uuid4()
    resp = await async_client.post(
        f"/api/v1/suppliers/{sup_id}/documents",
        json={"file_id": str(fake_file_id), "document_type": "Tax Exemption"},
        headers=headers,
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_29_document_retrieval_and_expiry_metadata(async_client: AsyncClient):
    user, headers = await create_user_with_role(async_client, "Procurement Manager")
    sup = await async_client.post("/api/v1/suppliers", json={"name": "Doc Meta Host"}, headers=headers)
    sup_id = sup.json()["id"]

    async with AsyncSessionLocal() as session:
        file_obj = await create_test_file(session, user.id)
        file_id = file_obj.id

    await async_client.post(
        f"/api/v1/suppliers/{sup_id}/documents",
        json={"file_id": str(file_id), "document_type": "Business License", "description": "Expires 2030"},
        headers=headers,
    )

    list_resp = await async_client.get(f"/api/v1/suppliers/{sup_id}/documents", headers=headers)
    assert list_resp.status_code == 200
    assert len(list_resp.json()) >= 1


# =============================================================================
# 30-33. SUPPLIER RATINGS TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_30_create_rating(async_client: AsyncClient):
    _, headers = await create_user_with_role(async_client, "Procurement Manager")
    sup = await async_client.post("/api/v1/suppliers", json={"name": "Rating Host"}, headers=headers)
    sup_id = sup.json()["id"]

    resp = await async_client.post(
        f"/api/v1/suppliers/{sup_id}/ratings",
        json={"score": 4.5, "comments": "Prompt delivery and great product tolerances"},
        headers=headers,
    )
    assert resp.status_code == 201
    assert float(resp.json()["score"]) == 4.5


@pytest.mark.asyncio
async def test_31_rating_score_validation(async_client: AsyncClient):
    _, headers = await create_user_with_role(async_client, "Procurement Manager")
    sup = await async_client.post("/api/v1/suppliers", json={"name": "Rating Range Host"}, headers=headers)
    sup_id = sup.json()["id"]

    # Score below 1.0
    low_resp = await async_client.post(
        f"/api/v1/suppliers/{sup_id}/ratings", json={"score": 0.5, "comments": "Too low"}, headers=headers
    )
    assert low_resp.status_code == 422

    # Score above 5.0
    high_resp = await async_client.post(
        f"/api/v1/suppliers/{sup_id}/ratings", json={"score": 5.5, "comments": "Too high"}, headers=headers
    )
    assert high_resp.status_code == 422


@pytest.mark.asyncio
async def test_32_rating_history_preservation(async_client: AsyncClient):
    _, headers = await create_user_with_role(async_client, "Procurement Manager")
    sup = await async_client.post("/api/v1/suppliers", json={"name": "Rating History Host"}, headers=headers)
    sup_id = sup.json()["id"]

    await async_client.post(
        f"/api/v1/suppliers/{sup_id}/ratings", json={"score": 3.0, "comments": "First review"}, headers=headers
    )
    await async_client.post(
        f"/api/v1/suppliers/{sup_id}/ratings", json={"score": 5.0, "comments": "Second review"}, headers=headers
    )

    ratings = await async_client.get(f"/api/v1/suppliers/{sup_id}/ratings", headers=headers)
    assert ratings.status_code == 200
    assert len(ratings.json()) == 2


@pytest.mark.asyncio
async def test_33_average_rating_correctness(async_client: AsyncClient):
    _, headers = await create_user_with_role(async_client, "Procurement Manager")
    sup = await async_client.post("/api/v1/suppliers", json={"name": "Avg Rating Host"}, headers=headers)
    sup_id = sup.json()["id"]

    await async_client.post(
        f"/api/v1/suppliers/{sup_id}/ratings", json={"score": 3.0, "comments": "Review 1"}, headers=headers
    )
    await async_client.post(
        f"/api/v1/suppliers/{sup_id}/ratings", json={"score": 4.0, "comments": "Review 2"}, headers=headers
    )

    updated_sup = await async_client.get(f"/api/v1/suppliers/{sup_id}", headers=headers)
    # Average of 3.0 and 4.0 is 3.50
    assert float(updated_sup.json()["rating"]) == 3.50


# =============================================================================
# 34-38. RBAC PERMISSIONS TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_34_unauthorized_supplier_create_rejected(async_client: AsyncClient):
    _, view_headers = await create_user_with_role(async_client, "Procurement Viewer")
    resp = await async_client.post("/api/v1/suppliers", json={"name": "Unauthorized Inc"}, headers=view_headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_35_unauthorized_supplier_update_rejected(async_client: AsyncClient):
    _, mgr_headers = await create_user_with_role(async_client, "Procurement Manager")
    _, view_headers = await create_user_with_role(async_client, "Procurement Viewer")

    sup = await async_client.post("/api/v1/suppliers", json={"name": "Protected Supplier"}, headers=mgr_headers)
    sup_id = sup.json()["id"]

    resp = await async_client.patch(f"/api/v1/suppliers/{sup_id}", json={"name": "Hacked Name"}, headers=view_headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_36_unauthorized_blacklist_rejected(async_client: AsyncClient):
    _, mgr_headers = await create_user_with_role(async_client, "Procurement Manager")
    _, view_headers = await create_user_with_role(async_client, "Procurement Viewer")

    sup = await async_client.post("/api/v1/suppliers", json={"name": "Target Supplier"}, headers=mgr_headers)
    sup_id = sup.json()["id"]

    resp = await async_client.post(
        f"/api/v1/suppliers/{sup_id}/blacklist?reason=Unauthorized+Attempt", headers=view_headers
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_37_viewer_can_read(async_client: AsyncClient):
    _, mgr_headers = await create_user_with_role(async_client, "Procurement Manager")
    _, view_headers = await create_user_with_role(async_client, "Procurement Viewer")

    sup = await async_client.post("/api/v1/suppliers", json={"name": "Visible Supplier"}, headers=mgr_headers)
    sup_id = sup.json()["id"]

    get_resp = await async_client.get(f"/api/v1/suppliers/{sup_id}", headers=view_headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["name"] == "Visible Supplier"


@pytest.mark.asyncio
async def test_38_viewer_cannot_mutate(async_client: AsyncClient):
    _, mgr_headers = await create_user_with_role(async_client, "Procurement Manager")
    _, view_headers = await create_user_with_role(async_client, "Procurement Viewer")

    sup = await async_client.post("/api/v1/suppliers", json={"name": "Mutation Target"}, headers=mgr_headers)
    sup_id = sup.json()["id"]

    del_resp = await async_client.delete(f"/api/v1/suppliers/{sup_id}", headers=view_headers)
    assert del_resp.status_code == 403


# =============================================================================
# 39-40. AUDIT LOGGING TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_39_supplier_lifecycle_audit(async_client: AsyncClient):
    user, headers = await create_user_with_role(async_client, "Procurement Manager")
    resp = await async_client.post("/api/v1/suppliers", json={"name": "Audited Supplier"}, headers=headers)
    sup_id = uuid.UUID(resp.json()["id"])

    await async_client.post(f"/api/v1/suppliers/{sup_id}/blacklist?reason=Audit+Verification", headers=headers)

    async with AsyncSessionLocal() as session:
        from app.models.audit_log import AuditLog
        stmt = select(AuditLog).where(AuditLog.entity_id == str(sup_id)).order_by(AuditLog.created_at.asc())
        logs = (await session.execute(stmt)).scalars().all()
        actions = [log.action for log in logs]
        assert "SUPPLIER_CREATE" in actions
        assert "SUPPLIER_BLACKLIST" in actions


@pytest.mark.asyncio
async def test_40_contact_address_document_rating_audit(async_client: AsyncClient):
    user, headers = await create_user_with_role(async_client, "Procurement Manager")
    sup = await async_client.post("/api/v1/suppliers", json={"name": "Subentity Audit Host"}, headers=headers)
    sup_id = uuid.UUID(sup.json()["id"])

    # Contact
    await async_client.post(
        f"/api/v1/suppliers/{sup_id}/contacts",
        json={"contact_name": "Audit Contact", "email": "audit@test.com"},
        headers=headers,
    )
    # Address
    await async_client.post(
        f"/api/v1/suppliers/{sup_id}/addresses",
        json={
            "address_type": "Billing",
            "address_line1": "1 Audit Way",
            "city": "Boston",
            "state": "MA",
            "country": "USA",
            "postal_code": "02108",
        },
        headers=headers,
    )
    # Rating
    await async_client.post(
        f"/api/v1/suppliers/{sup_id}/ratings", json={"score": 4.0, "comments": "Audit Rating"}, headers=headers
    )

    async with AsyncSessionLocal() as session:
        from app.models.audit_log import AuditLog
        stmt = select(AuditLog).where(AuditLog.user_id == user.id).order_by(AuditLog.created_at.desc())
        logs = (await session.execute(stmt)).scalars().all()
        actions = [log.action for log in logs]
        assert "SUPPLIER_CONTACT_CREATE" in actions
        assert "SUPPLIER_ADDRESS_CREATE" in actions
        assert "SUPPLIER_RATING_CREATE" in actions


# =============================================================================
# 41-42. CONCURRENCY HARDENING TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_41_concurrent_supplier_creation_same_code():
    async with AsyncSessionLocal() as session1, AsyncSessionLocal() as session2:
        code = f"SUP-RACE-{uuid.uuid4().hex[:6]}"
        sup_in1 = SupplierCreate(code=code, name="Racer 1")
        sup_in2 = SupplierCreate(code=code, name="Racer 2")

        # One must succeed, one must fail with DuplicateResourceException
        results = await asyncio.gather(
            supplier_service.create_supplier(session1, sup_in1),
            supplier_service.create_supplier(session2, sup_in2),
            return_exceptions=True,
        )

        successes = [r for r in results if isinstance(r, Supplier)]
        failures = [r for r in results if isinstance(r, Exception)]
        assert len(successes) == 1
        assert len(failures) == 1


@pytest.mark.asyncio
async def test_42_concurrent_primary_contact_assignment():
    async with AsyncSessionLocal() as session:
        admin_user, _ = await create_user_with_role(
            AsyncClient(transport=ASGITransport(app=app), base_url="http://test"), "Procurement Manager"
        )
        sup = await supplier_service.create_supplier(
            session, SupplierCreate(name="Concurrent Contact Host"), current_user_id=admin_user.id
        )
        sup_id = sup.id

    async with AsyncSessionLocal() as session1, AsyncSessionLocal() as session2:
        c1_in = SupplierContactCreate(contact_name="Racer Contact 1", email="rc1@test.com", is_primary=True)
        c2_in = SupplierContactCreate(contact_name="Racer Contact 2", email="rc2@test.com", is_primary=True)

        await asyncio.gather(
            supplier_service.add_contact(session1, sup_id, c1_in, current_user_id=admin_user.id),
            supplier_service.add_contact(session2, sup_id, c2_in, current_user_id=admin_user.id),
        )

    async with AsyncSessionLocal() as verify_session:
        contacts = await supplier_service.list_contacts(verify_session, sup_id)
        primaries = [c for c in contacts if c.is_primary]
        # At most 1 primary contact remains authoritative
        assert len(primaries) <= 1


# =============================================================================
# 43-44. REGRESSION & BOUNDARY COMPATIBILITY TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_43_inventory_v064_compatibility(async_client: AsyncClient):
    _, headers = await create_user_with_role(async_client, "Super Admin", is_superuser=True)
    # Verify inventory categories still function completely
    inv_resp = await async_client.get("/api/v1/inventory/categories", headers=headers)
    assert inv_resp.status_code == 200

    # Verify inventory warehouses still function completely
    wh_resp = await async_client.get("/api/v1/inventory/warehouses", headers=headers)
    assert wh_resp.status_code == 200


@pytest.mark.asyncio
async def test_44_platform_rbac_compatibility(async_client: AsyncClient):
    _, headers = await create_user_with_role(async_client, "Super Admin", is_superuser=True)
    roles_resp = await async_client.get("/api/v1/rbac/roles", headers=headers)
    assert roles_resp.status_code == 200
    role_names = [r["name"] for r in roles_resp.json()]
    assert "Procurement Manager" in role_names
    assert "Procurement Viewer" in role_names
