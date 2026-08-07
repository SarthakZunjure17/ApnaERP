import uuid
import pytest
from httpx import ASGITransport, AsyncClient
from app.db.session import AsyncSessionLocal
from app.models.user import User
from app.core.security import create_access_token
from app.main import app


async def get_test_user_headers() -> dict:
    async with AsyncSessionLocal() as session:
        user = User(
            username=f"testint_{uuid.uuid4().hex[:6]}",
            email=f"testint_{uuid.uuid4().hex[:6]}@example.com",
            full_name="Integration Test User",
            password_hash="hashedpassword123",
            is_active=True,
            is_superuser=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        token = create_access_token(subject=str(user.id))
        return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_health_and_liveness_endpoints():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/api/v1/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "Healthy"
        assert data["version"] == "v1.3.0"
        assert "checks" in data

        liveness_resp = await ac.get("/api/v1/health/liveness")
        assert liveness_resp.status_code == 200
        readiness_resp = await ac.get("/api/v1/health/readiness")
        assert readiness_resp.status_code == 200


@pytest.mark.asyncio
async def test_prometheus_metrics_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        resp = await ac.get("/api/v1/monitoring/metrics")
        assert resp.status_code == 200
        assert "erp_http_requests_total" in resp.text


@pytest.mark.asyncio
async def test_api_keys_workflow():
    headers = await get_test_user_headers()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Create API key
        payload = {
            "name": "Integration Test Key",
            "scopes": ["system.read", "finance.read"],
            "expires_in_days": 30,
        }
        create_resp = await ac.post("/api/v1/api-keys", json=payload, headers=headers)
        assert create_resp.status_code == 201
        data = create_resp.json()
        assert "raw_api_key" in data
        assert data["name"] == "Integration Test Key"
        key_id = data["id"]

        # Rotate key
        rotate_resp = await ac.post(f"/api/v1/api-keys/{key_id}/rotate", headers=headers)
        assert rotate_resp.status_code == 200
        rotated_data = rotate_resp.json()
        assert "raw_api_key" in rotated_data

        # Revoke key
        revoke_resp = await ac.delete(f"/api/v1/api-keys/{key_id}", headers=headers)
        assert revoke_resp.status_code == 204


@pytest.mark.asyncio
async def test_webhooks_workflow():
    headers = await get_test_user_headers()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        payload = {
            "name": "Order Notifications Webhook",
            "target_url": "https://hooks.example.com/orders",
            "event_types": ["sales.order_created", "inventory.stock_adjusted"],
            "headers_json": {"X-Custom-Header": "TestValue"},
        }
        resp = await ac.post("/api/v1/webhooks", json=payload, headers=headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Order Notifications Webhook"
        assert "secret_token" in data


@pytest.mark.asyncio
async def test_storage_and_provider_configurations():
    headers = await get_test_user_headers()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Create Provider Configuration
        provider_payload = {
            "provider_type": "Storage",
            "provider_name": "MinIO",
            "settings_json": {"endpoint": "localhost:9000", "bucket": "apnaerp"},
            "is_active": True,
            "is_default": True,
        }
        p_resp = await ac.post("/api/v1/providers", json=provider_payload, headers=headers)
        assert p_resp.status_code == 201
        p_data = p_resp.json()
        assert p_data["provider_name"] == "MinIO"


@pytest.mark.asyncio
async def test_backups_and_system_config_workflow():
    headers = await get_test_user_headers()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Create Backup
        b_payload = {"backup_name": "test_auto_backup.sql", "backup_type": "FullDatabase"}
        b_resp = await ac.post("/api/v1/backups", json=b_payload, headers=headers)
        assert b_resp.status_code == 201
        b_data = b_resp.json()
        assert b_data["status"] == "Completed"
        backup_id = b_data["id"]

        # Restore Backup
        r_resp = await ac.post(f"/api/v1/backups/{backup_id}/restore", headers=headers)
        assert r_resp.status_code == 200

        # System Config
        cfg_payload = {
            "config_key": "system.maintenance_mode",
            "config_value": "false",
            "value_type": "Boolean",
            "category": "Security",
        }
        cfg_resp = await ac.post("/api/v1/system/config", json=cfg_payload, headers=headers)
        assert cfg_resp.status_code == 200
        assert cfg_resp.json()["config_value"] == "false"
