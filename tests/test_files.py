import io
import uuid
import pytest
import pytest_asyncio
from httpx import AsyncClient

from app.db.session import AsyncSessionLocal
from app.repositories.user import user_repository


@pytest_asyncio.fixture
async def file_uploader_headers(async_client: AsyncClient):
    """
    Fixture registering a user who uploads files and returning Bearer authorization headers.
    """
    unique_id = uuid.uuid4().hex[:6]
    email = f"uploader_{unique_id}@example.com"
    username = f"uploader_{unique_id}"

    reg_payload = {
        "full_name": "File Uploader User",
        "email": email,
        "username": username,
        "password": "Password123!",
    }
    await async_client.post("/auth/register", json=reg_payload)
    login_resp = await async_client.post("/auth/login", json={
        "username_or_email": email,
        "password": "Password123!",
    })
    token = login_resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def file_other_user_headers(async_client: AsyncClient):
    """
    Fixture registering a separate regular user.
    """
    unique_id = uuid.uuid4().hex[:6]
    email = f"otheruser_{unique_id}@example.com"
    username = f"otheruser_{unique_id}"

    reg_payload = {
        "full_name": "Other Regular User",
        "email": email,
        "username": username,
        "password": "Password123!",
    }
    await async_client.post("/auth/register", json=reg_payload)
    login_resp = await async_client.post("/auth/login", json={
        "username_or_email": email,
        "password": "Password123!",
    })
    token = login_resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def file_superuser_headers(async_client: AsyncClient):
    """
    Fixture registering a superuser.
    """
    unique_id = uuid.uuid4().hex[:6]
    email = f"superfile_{unique_id}@example.com"
    username = f"superfile_{unique_id}"

    reg_payload = {
        "full_name": "Super File Admin",
        "email": email,
        "username": username,
        "password": "SuperPassword123!",
    }
    reg_resp = await async_client.post("/auth/register", json=reg_payload)
    user_id = uuid.UUID(reg_resp.json()["id"])

    async with AsyncSessionLocal() as session:
        user = await user_repository.get_by_id(session, user_id)
        if user:
            user.is_superuser = True
            await session.commit()

    login_resp = await async_client.post("/auth/login", json={
        "username_or_email": email,
        "password": "SuperPassword123!",
    })
    token = login_resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_file_upload_success(async_client: AsyncClient, file_uploader_headers: dict):
    """
    Test uploading a valid PDF document.
    """
    unique_content = b"%PDF-1.4 sample pdf content " + uuid.uuid4().bytes
    files = {"file": ("test_doc.pdf", unique_content, "application/pdf")}
    data = {"entity_type": "Invoice", "entity_id": "INV-1001", "is_public": "false"}

    response = await async_client.post("/files/upload", files=files, data=data, headers=file_uploader_headers)
    assert response.status_code == 201
    json_data = response.json()["data"]
    assert json_data["original_filename"] == "test_doc.pdf"
    assert json_data["file_extension"] == "pdf"
    assert json_data["mime_type"] == "application/pdf"
    assert json_data["entity_type"] == "Invoice"
    assert json_data["checksum"] is not None
    # Verify internal storage path is NOT exposed
    assert "storage_path" not in json_data


@pytest.mark.asyncio
async def test_file_download_success(async_client: AsyncClient, file_uploader_headers: dict):
    """
    Test uploading and downloading raw file bytes.
    """
    raw_bytes = b"Hello, ApnaERP File Storage Engine! " + uuid.uuid4().bytes
    files = {"file": ("notes.txt", raw_bytes, "text/plain")}

    upload_resp = await async_client.post("/files/upload", files=files, headers=file_uploader_headers)
    assert upload_resp.status_code == 201
    file_id = upload_resp.json()["data"]["id"]

    # Download file
    download_resp = await async_client.get(f"/files/download/{file_id}", headers=file_uploader_headers)
    assert download_resp.status_code == 200
    assert download_resp.content == raw_bytes
    assert "attachment; filename=\"notes.txt\"" in download_resp.headers["content-disposition"]


@pytest.mark.asyncio
async def test_file_validation_invalid_extension(async_client: AsyncClient, file_uploader_headers: dict):
    """
    Test uploading a file with disallowed extension (e.g. .exe).
    """
    files = {"file": ("malicious.exe", b"binary data", "application/octet-stream")}
    response = await async_client.post("/files/upload", files=files, headers=file_uploader_headers)
    assert response.status_code == 422 or response.status_code == 400
    assert "not permitted" in response.json()["message"].lower() or "extension" in response.json()["message"].lower()


@pytest.mark.asyncio
async def test_file_duplicate_detection(async_client: AsyncClient, file_uploader_headers: dict):
    """
    Test uploading identical content returns existing file record with matching SHA256 checksum.
    """
    duplicate_bytes = b"Exact duplicate content for SHA256 test " + uuid.uuid4().bytes
    files1 = {"file": ("file1.txt", duplicate_bytes, "text/plain")}
    files2 = {"file": ("file2.txt", duplicate_bytes, "text/plain")}

    resp1 = await async_client.post("/files/upload", files=files1, headers=file_uploader_headers)
    assert resp1.status_code == 201
    data1 = resp1.json()["data"]

    resp2 = await async_client.post("/files/upload", files=files2, headers=file_uploader_headers)
    assert resp2.status_code == 201
    data2 = resp2.json()["data"]

    # Both uploads should map to same file ID and checksum
    assert data1["id"] == data2["id"]
    assert data1["checksum"] == data2["checksum"]


@pytest.mark.asyncio
async def test_file_deletion_authorization(
    async_client: AsyncClient,
    file_uploader_headers: dict,
    file_other_user_headers: dict,
    file_superuser_headers: dict,
):
    """
    Test deletion security: non-uploader gets 403 Forbidden, uploader or Super Admin gets 200 OK.
    """
    unique_content = b"%PDF-1.4 auth test data " + uuid.uuid4().bytes
    files = {"file": ("auth_test.pdf", unique_content, "application/pdf")}
    upload_resp = await async_client.post("/files/upload", files=files, headers=file_uploader_headers)
    assert upload_resp.status_code == 201
    file_id = upload_resp.json()["data"]["id"]

    # 1. Other regular user tries to delete -> 403
    del_forbidden = await async_client.delete(f"/files/{file_id}", headers=file_other_user_headers)
    assert del_forbidden.status_code == 403

    # 2. Original uploader deletes -> 200
    del_success = await async_client.delete(f"/files/{file_id}", headers=file_uploader_headers)
    assert del_success.status_code == 200


@pytest.mark.asyncio
async def test_file_audit_logging_integration(
    async_client: AsyncClient, file_uploader_headers: dict, file_superuser_headers: dict
):
    """
    Test uploading, downloading, and deleting files generates FILE_UPLOAD, FILE_DOWNLOAD, FILE_DELETE audit events.
    """
    unique_content = b"Audit content test " + uuid.uuid4().bytes
    files = {"file": ("audit_doc.txt", unique_content, "text/plain")}
    upload_resp = await async_client.post("/files/upload", files=files, headers=file_uploader_headers)
    assert upload_resp.status_code == 201
    file_id = upload_resp.json()["data"]["id"]

    # Download
    await async_client.get(f"/files/download/{file_id}", headers=file_uploader_headers)

    # Delete
    await async_client.delete(f"/files/{file_id}", headers=file_uploader_headers)

    # Check audit logs as Super Admin
    logs_resp = await async_client.get("/audit/logs", headers=file_superuser_headers)
    assert logs_resp.status_code == 200
    actions = [item["action"] for item in logs_resp.json()["data"]]
    assert "FILE_UPLOAD" in actions
    assert "FILE_DOWNLOAD" in actions
    assert "FILE_DELETE" in actions
