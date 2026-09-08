import uuid
from decimal import Decimal
import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.main import app
from app.models.user import User


@pytest.mark.asyncio
async def test_openapi_schema_generation_and_routes():
    """Verify that OpenAPI schema generates cleanly and contains all domain tags and routes."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/openapi.json")
        assert response.status_code == 200
        schema = response.json()
        assert schema["info"]["title"] == settings.PROJECT_NAME
        assert schema["info"]["version"] == settings.VERSION
        assert "paths" in schema
        assert len(schema["paths"]) > 50

        # Verify docs UI endpoints
        docs_res = await client.get("/docs")
        assert docs_res.status_code == 200


@pytest.mark.asyncio
async def test_system_health_and_readiness_endpoints():
    """Verify health, liveness, readiness, and database probe endpoints."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Root
        root_res = await client.get("/")
        assert root_res.status_code == 200
        assert root_res.json()["app_name"] == settings.PROJECT_NAME

        # 2. Health / Liveness / Readiness
        health_res = await client.get("/health")
        assert health_res.status_code == 200
        assert health_res.json()["status"] in ["healthy", "ok", "operational"]

        liveness_res = await client.get("/health/liveness")
        assert liveness_res.status_code == 200

        readiness_res = await client.get("/health/readiness")
        assert readiness_res.status_code == 200

        # 3. Database connectivity
        db_res = await client.get("/health/db")
        assert db_res.status_code == 200
        assert db_res.json()["status"] == "connected"


@pytest.mark.asyncio
async def test_authentication_and_authorization_smoke():
    """Verify registration, login, and JWT access across protected endpoints."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        unique = uuid.uuid4().hex[:6]
        user_email = f"smoketest_{unique}@apnaerp.com"
        username = f"smokeuser_{unique}"
        password = "SecurePassword123!"

        # 1. Register User
        reg_res = await client.post(
            "/auth/register",
            json={
                "email": user_email,
                "username": username,
                "password": password,
                "full_name": "Integration Smoke Analyst",
            },
        )
        assert reg_res.status_code in [200, 201]

        # 2. Login with JSON payload to obtain access token
        login_res = await client.post(
            "/auth/login",
            json={
                "username_or_email": user_email,
                "password": password,
            },
        )
        assert login_res.status_code == 200
        tokens = login_res.json()
        assert "access_token" in tokens
        access_token = tokens["access_token"]

        headers = {"Authorization": f"Bearer {access_token}"}

        # 3. Access current user profile
        me_res = await client.get("/auth/me", headers=headers)
        assert me_res.status_code == 200
        assert me_res.json()["email"] == user_email


@pytest.mark.asyncio
async def test_cross_domain_api_smoke():
    """Verify representative API endpoints across all ERP domains."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create Superuser for cross-domain API smoke checks
        async with AsyncSessionLocal() as session:
            unique = uuid.uuid4().hex[:6]
            admin_user = User(
                username=f"admin_{unique}",
                email=f"admin_{unique}@test.com",
                full_name="Smoke Admin",
                password_hash="testpass123",
                is_active=True,
                is_superuser=True,
            )
            session.add(admin_user)
            await session.commit()
            await session.refresh(admin_user)

        from app.core.security import create_access_token
        token = create_access_token(subject=str(admin_user.id))
        headers = {"Authorization": f"Bearer {token}"}

        # 1. HR
        dept_res = await client.get("/api/v1/departments", headers=headers)
        assert dept_res.status_code == 200

        # 2. Payroll
        comp_res = await client.get("/api/v1/salary-components", headers=headers)
        assert comp_res.status_code == 200

        # 3. Inventory
        prod_res = await client.get("/api/v1/products", headers=headers)
        assert prod_res.status_code == 200

        # 4. Procurement
        supp_res = await client.get("/api/v1/suppliers", headers=headers)
        assert supp_res.status_code == 200

        # 5. Sales
        cust_res = await client.get("/api/v1/customers", headers=headers)
        assert cust_res.status_code == 200

        # 6. CRM
        lead_res = await client.get("/api/v1/crm/leads", headers=headers)
        assert lead_res.status_code == 200

        # 7. Finance
        acc_res = await client.get("/api/v1/finance/accounts", headers=headers)
        assert acc_res.status_code == 200

        # 8. Reporting
        dash_res = await client.get("/api/v1/reports/dashboard", headers=headers)
        assert dash_res.status_code == 200
        assert "finance" in dash_res.json()
        assert "sales" in dash_res.json()
        assert "procurement" in dash_res.json()
        assert "inventory" in dash_res.json()
        assert "hr" in dash_res.json()
        assert "payroll" in dash_res.json()
        assert "crm" in dash_res.json()

        # 9. Reporting CSV Export
        export_res = await client.get("/api/v1/reports/export?report_type=dashboard", headers=headers)
        assert export_res.status_code == 200
        assert "text/csv" in export_res.headers.get("content-type", "")
