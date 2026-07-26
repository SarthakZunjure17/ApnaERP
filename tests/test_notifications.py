import uuid
import pytest
import pytest_asyncio
from httpx import AsyncClient

from app.db.session import AsyncSessionLocal
from app.repositories.user import user_repository


@pytest_asyncio.fixture
async def user_a_data(async_client: AsyncClient):
    """
    Fixture registering User A and returning user ID and Bearer authorization headers.
    """
    unique_id = uuid.uuid4().hex[:6]
    email = f"usera_{unique_id}@example.com"
    username = f"usera_{unique_id}"

    reg_resp = await async_client.post("/auth/register", json={
        "full_name": "User Alpha",
        "email": email,
        "username": username,
        "password": "Password123!",
    })
    user_id = uuid.UUID(reg_resp.json()["id"])

    login_resp = await async_client.post("/auth/login", json={
        "username_or_email": email,
        "password": "Password123!",
    })
    token = login_resp.json()["access_token"]
    return {
        "id": user_id,
        "headers": {"Authorization": f"Bearer {token}"},
        "username": username,
        "email": email,
    }


@pytest_asyncio.fixture
async def user_b_data(async_client: AsyncClient):
    """
    Fixture registering User B and returning user ID and Bearer authorization headers.
    """
    unique_id = uuid.uuid4().hex[:6]
    email = f"userb_{unique_id}@example.com"
    username = f"userb_{unique_id}"

    reg_resp = await async_client.post("/auth/register", json={
        "full_name": "User Beta",
        "email": email,
        "username": username,
        "password": "Password123!",
    })
    user_id = uuid.UUID(reg_resp.json()["id"])

    login_resp = await async_client.post("/auth/login", json={
        "username_or_email": email,
        "password": "Password123!",
    })
    token = login_resp.json()["access_token"]
    return {
        "id": user_id,
        "headers": {"Authorization": f"Bearer {token}"},
        "username": username,
        "email": email,
    }


@pytest_asyncio.fixture
async def notif_superuser_data(async_client: AsyncClient):
    """
    Fixture registering a Super Admin user.
    """
    unique_id = uuid.uuid4().hex[:6]
    email = f"supernotif_{unique_id}@example.com"
    username = f"supernotif_{unique_id}"

    reg_resp = await async_client.post("/auth/register", json={
        "full_name": "Super Notif Admin",
        "email": email,
        "username": username,
        "password": "SuperPassword123!",
    })
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
    return {
        "id": user_id,
        "headers": {"Authorization": f"Bearer {token}"},
        "username": username,
        "email": email,
    }


@pytest.mark.asyncio
async def test_send_in_app_notification(async_client: AsyncClient, user_a_data: dict):
    """
    Test sending a direct In-App notification to User A.
    """
    payload = {
        "user_id": str(user_a_data["id"]),
        "title": "Welcome to ApnaERP",
        "message": "Your enterprise workspace is ready.",
        "notification_type": "IN_APP",
        "priority": "HIGH",
    }
    response = await async_client.post("/notifications/send", json=payload, headers=user_a_data["headers"])
    assert response.status_code == 201
    data = response.json()["data"]
    assert data["title"] == "Welcome to ApnaERP"
    assert data["message"] == "Your enterprise workspace is ready."
    assert data["is_read"] is False
    assert data["notification_type"] == "IN_APP"
    assert data["priority"] == "HIGH"


@pytest.mark.asyncio
async def test_send_email_notification_with_template(
    async_client: AsyncClient, user_a_data: dict, notif_superuser_data: dict
):
    """
    Test creating a notification template with Jinja2 variables and dispatching an email notification.
    """
    # 1. Create Template as Super Admin
    tpl_payload = {
        "name": f"invoice_notice_{uuid.uuid4().hex[:6]}",
        "subject": "Invoice {{invoice_number}} Due Notice for {{user_name}}",
        "template_body": "Hello {{user_name}}, your invoice {{invoice_number}} for amount {{amount}} is due on {{date}}.",
        "template_type": "EMAIL",
    }
    tpl_resp = await async_client.post("/templates", json=tpl_payload, headers=notif_superuser_data["headers"])
    assert tpl_resp.status_code == 201
    template_name = tpl_payload["name"]

    # 2. Dispatch notification using Template
    send_payload = {
        "user_id": str(user_a_data["id"]),
        "template_name": template_name,
        "template_data": {
            "user_name": "User Alpha",
            "invoice_number": "INV-2026-99",
            "amount": "$4,500.00",
            "date": "2026-08-01",
        },
        "notification_type": "EMAIL",
    }
    send_resp = await async_client.post("/notifications/send", json=send_payload, headers=user_a_data["headers"])
    assert send_resp.status_code == 201
    data = send_resp.json()["data"]
    assert "INV-2026-99" in data["title"]
    assert "User Alpha" in data["title"]
    assert "$4,500.00" in data["message"]
    assert "2026-08-01" in data["message"]


@pytest.mark.asyncio
async def test_read_notification_and_read_all(async_client: AsyncClient, user_a_data: dict):
    """
    Test marking individual notification read and marking all unread notifications as read.
    """
    # Send 2 notifications to User A
    for i in range(2):
        await async_client.post(
            "/notifications/send",
            json={
                "user_id": str(user_a_data["id"]),
                "title": f"Notification {i}",
                "message": f"Message body {i}",
            },
            headers=user_a_data["headers"],
        )

    # Fetch unread list
    unread_resp = await async_client.get("/notifications/unread", headers=user_a_data["headers"])
    assert unread_resp.status_code == 200
    unread_items = unread_resp.json()["data"]
    assert len(unread_items) >= 2
    target_id = unread_items[0]["id"]

    # Mark single notification read
    read_resp = await async_client.put(f"/notifications/read/{target_id}", headers=user_a_data["headers"])
    assert read_resp.status_code == 200
    assert read_resp.json()["data"]["is_read"] is True
    assert read_resp.json()["data"]["read_at"] is not None

    # Mark all remaining read
    read_all_resp = await async_client.put("/notifications/read-all", headers=user_a_data["headers"])
    assert read_all_resp.status_code == 200

    # Verify unread list is now empty
    unread_empty = await async_client.get("/notifications/unread", headers=user_a_data["headers"])
    assert len(unread_empty.json()["data"]) == 0


@pytest.mark.asyncio
async def test_delete_notification(async_client: AsyncClient, user_a_data: dict):
    """
    Test deleting a notification.
    """
    send_resp = await async_client.post(
        "/notifications/send",
        json={
            "user_id": str(user_a_data["id"]),
            "title": "To be deleted",
            "message": "Temporary notification",
        },
        headers=user_a_data["headers"],
    )
    notif_id = send_resp.json()["data"]["id"]

    del_resp = await async_client.delete(f"/notifications/{notif_id}", headers=user_a_data["headers"])
    assert del_resp.status_code == 200
    assert "deleted successfully" in del_resp.json()["message"]


@pytest.mark.asyncio
async def test_user_notification_isolation(
    async_client: AsyncClient, user_a_data: dict, user_b_data: dict
):
    """
    Test user isolation security: User A cannot see or delete User B's notification.
    """
    # Send notification to User B
    send_resp = await async_client.post(
        "/notifications/send",
        json={
            "user_id": str(user_b_data["id"]),
            "title": "Private Notification for B",
            "message": "Confidential content",
        },
        headers=user_b_data["headers"],
    )
    notif_b_id = send_resp.json()["data"]["id"]

    # 1. User A lists notifications -> User B's notification is not present
    list_a = await async_client.get("/notifications", headers=user_a_data["headers"])
    ids_a = [item["id"] for item in list_a.json()["data"]]
    assert notif_b_id not in ids_a

    # 2. User A tries to delete User B's notification -> 403 Forbidden
    del_forbidden = await async_client.delete(f"/notifications/{notif_b_id}", headers=user_a_data["headers"])
    assert del_forbidden.status_code == 403


@pytest.mark.asyncio
async def test_template_crud_superuser(
    async_client: AsyncClient, user_a_data: dict, notif_superuser_data: dict
):
    """
    Test template CRUD: regular user fails (403), Super Admin succeeds.
    """
    tpl_name = f"payroll_alert_{uuid.uuid4().hex[:6]}"
    tpl_payload = {
        "name": tpl_name,
        "subject": "Payroll Processed for {{employee_name}}",
        "template_body": "Hi {{employee_name}}, your {{department}} salary has been credited.",
        "template_type": "IN_APP",
    }

    # Regular user tries to create -> 403
    create_fail = await async_client.post("/templates", json=tpl_payload, headers=user_a_data["headers"])
    assert create_fail.status_code == 403

    # Super Admin creates -> 201
    create_ok = await async_client.post("/templates", json=tpl_payload, headers=notif_superuser_data["headers"])
    assert create_ok.status_code == 201
    tpl_id = create_ok.json()["data"]["id"]

    # Super Admin updates -> 200
    update_ok = await async_client.put(
        f"/templates/{tpl_id}",
        json={"subject": "Updated Payroll for {{employee_name}}"},
        headers=notif_superuser_data["headers"],
    )
    assert update_ok.status_code == 200
    assert update_ok.json()["data"]["subject"] == "Updated Payroll for {{employee_name}}"

    # Super Admin deletes -> 200
    del_ok = await async_client.delete(f"/templates/{tpl_id}", headers=notif_superuser_data["headers"])
    assert del_ok.status_code == 200


@pytest.mark.asyncio
async def test_notification_audit_logging_integration(
    async_client: AsyncClient, user_a_data: dict, notif_superuser_data: dict
):
    """
    Test notification operations generate NOTIFICATION_SEND, NOTIFICATION_READ, TEMPLATE_CREATE audit events.
    """
    # Send notification
    send_resp = await async_client.post(
        "/notifications/send",
        json={
            "user_id": str(user_a_data["id"]),
            "title": "Audit test notification",
            "message": "Testing audit log integration",
        },
        headers=user_a_data["headers"],
    )
    notif_id = send_resp.json()["data"]["id"]

    # Read notification
    await async_client.put(f"/notifications/read/{notif_id}", headers=user_a_data["headers"])

    # Check audit logs as Super Admin
    logs_resp = await async_client.get("/audit/logs", headers=notif_superuser_data["headers"])
    assert logs_resp.status_code == 200
    actions = [item["action"] for item in logs_resp.json()["data"]]
    assert "NOTIFICATION_SEND" in actions
    assert "NOTIFICATION_READ" in actions
