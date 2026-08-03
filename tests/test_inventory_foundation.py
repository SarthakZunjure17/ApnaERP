from typing import AsyncGenerator
from unittest.mock import patch
import uuid
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.db.session import AsyncSessionLocal
from app.main import app
from app.models.file import File
from app.repositories.user import user_repository
from app.schemas.inventory import (
    BrandCreate,
    ProductCategoryCreate,
    ProductCreate,
    UnitOfMeasureCreate,
    WarehouseCreate,
)
from app.services.inventory_services import (
    brand_service,
    category_service,
    product_service,
    unit_of_measure_service,
    warehouse_service,
)


@pytest_asyncio.fixture(scope="function")
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest_asyncio.fixture(scope="function")
async def auth_headers(async_client: AsyncClient):
    unique_id = uuid.uuid4().hex[:6]
    email = f"invadmin_{unique_id}@example.com"
    username = f"invadmin_{unique_id}"

    reg_payload = {
        "full_name": "Inventory Admin User",
        "email": email,
        "username": username,
        "password": "AdminPassword123!",
    }
    reg_resp = await async_client.post("/api/v1/auth/register", json=reg_payload)
    assert reg_resp.status_code == 201, reg_resp.text
    user_id = uuid.UUID(reg_resp.json()["id"])

    # Mark user as superuser and assign Super Admin role in DB
    async with AsyncSessionLocal() as session:
        from app.db.seed_rbac import seed_rbac_data
        from app.repositories.rbac import role_repository, user_role_repository
        user = await user_repository.get_by_id(session, user_id)
        role = await role_repository.get_by_name(session, "Super Admin")
        if not role:
            await seed_rbac_data(session)
            role = await role_repository.get_by_name(session, "Super Admin")
        if user and role:
            user.is_superuser = True
            await user_role_repository.assign_role_to_user(session, user_id=user.id, role_id=role.id)
            await session.commit()


    login_resp = await async_client.post(
        "/api/v1/auth/login",
        json={
            "username_or_email": email,
            "password": "AdminPassword123!",
        },
    )
    token = login_resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_product_category_hierarchy_and_tree(
    async_client: AsyncClient,
    auth_headers: dict,
):
    """Test category creation, infinite tree hierarchy resolution, duplicate codes, and circular parent prevention."""
    # 1. Create Parent Category
    res1 = await async_client.post(
        "/api/v1/categories",
        headers=auth_headers,
        json={
            "name": "Electronics",
            "code": f"CAT_ELEC_{uuid.uuid4().hex[:4]}",
            "description": "Electronic Devices & Accessories",
        },
    )
    assert res1.status_code == 201, res1.text
    parent_cat = res1.json()
    parent_id = parent_cat["id"]
    code1 = parent_cat["code"]

    # 2. Duplicate code check
    res_dup = await async_client.post(
        "/api/v1/categories",
        headers=auth_headers,
        json={
            "name": "Electronics Duplicate",
            "code": code1,
        },
    )
    assert res_dup.status_code == 409

    # 3. Create Child Category
    res2 = await async_client.post(
        "/api/v1/categories",
        headers=auth_headers,
        json={
            "name": "Smartphones",
            "code": f"CAT_SMART_{uuid.uuid4().hex[:4]}",
            "parent_id": parent_id,
        },
    )
    assert res2.status_code == 201, res2.text
    child_cat = res2.json()
    child_id = child_cat["id"]

    # 4. Fetch Category Tree
    res_tree = await async_client.get("/api/v1/categories/tree", headers=auth_headers)
    assert res_tree.status_code == 200, res_tree.text
    tree_data = res_tree.json()
    parent_node = next((node for node in tree_data if node["id"] == parent_id), None)
    assert parent_node is not None
    assert len(parent_node["children"]) == 1
    assert parent_node["children"][0]["id"] == child_id

    # 5. Circular hierarchy check: Setting parent's parent to child
    res_circ = await async_client.put(
        f"/api/v1/categories/{parent_id}",
        headers=auth_headers,
        json={"parent_id": child_id},
    )
    assert res_circ.status_code == 400


@pytest.mark.asyncio
async def test_unit_of_measure_and_brand_crud(
    async_client: AsyncClient,
    auth_headers: dict,
):
    """Test CRUD operations and uniqueness rules for Units of Measure and Brands."""
    # 1. Create Unit of Measure
    unique_symbol = f"kg_{uuid.uuid4().hex[:4]}"
    res_uom = await async_client.post(
        "/api/v1/units-of-measure",
        headers=auth_headers,
        json={
            "name": f"Kilogram_{uuid.uuid4().hex[:4]}",
            "symbol": unique_symbol,
            "category": "Weight",
            "precision": 3,
            "base_unit": "kg",
        },
    )
    assert res_uom.status_code == 201, res_uom.text

    # Duplicate symbol check
    res_uom_dup = await async_client.post(
        "/api/v1/units-of-measure",
        headers=auth_headers,
        json={
            "name": f"Kilo_{uuid.uuid4().hex[:4]}",
            "symbol": unique_symbol,
            "category": "Weight",
        },
    )
    assert res_uom_dup.status_code == 409

    # 2. Create Brand
    unique_brand_name = f"Samsung_{uuid.uuid4().hex[:4]}"
    res_brand = await async_client.post(
        "/api/v1/brands",
        headers=auth_headers,
        json={
            "name": unique_brand_name,
            "description": "Global tech manufacturer",
        },
    )
    assert res_brand.status_code == 201, res_brand.text

    # Duplicate brand name check
    res_brand_dup = await async_client.post(
        "/api/v1/brands",
        headers=auth_headers,
        json={"name": unique_brand_name},
    )
    assert res_brand_dup.status_code == 409


@pytest.mark.asyncio
async def test_warehouse_and_storage_location_hierarchy(
    async_client: AsyncClient,
    auth_headers: dict,
):
    """Test Warehouse CRUD, Storage Location hierarchy, tree resolution, and validation."""
    with patch("app.services.inventory_services.send_inventory_notification_task.delay") as mock_celery:
        wh_code = f"WH_CENTRAL_{uuid.uuid4().hex[:4]}"
        # 1. Create Warehouse
        res_wh = await async_client.post(
            "/api/v1/warehouses",
            headers=auth_headers,
            json={
                "code": wh_code,
                "name": "Central Logistics Hub",
                "address": "100 Logistics Blvd",
                "contact_person": "Jane Doe",
                "phone": "+15550199",
                "email": "wh_central@apnaerp.com",
            },
        )
        assert res_wh.status_code == 201, res_wh.text
        wh_data = res_wh.json()
        wh_id = wh_data["id"]
        assert mock_celery.called

        # 2. Create Root Storage Location (Rack A)
        res_loc1 = await async_client.post(
            "/api/v1/storage-locations",
            headers=auth_headers,
            json={
                "warehouse_id": wh_id,
                "code": f"RACK_A_{uuid.uuid4().hex[:4]}",
                "name": "Main Storage Rack A",
                "location_type": "Rack",
            },
        )
        assert res_loc1.status_code == 201, res_loc1.text
        loc1_data = res_loc1.json()
        loc1_id = loc1_data["id"]

        # 3. Create Child Storage Location (Shelf A1)
        res_loc2 = await async_client.post(
            "/api/v1/storage-locations",
            headers=auth_headers,
            json={
                "warehouse_id": wh_id,
                "parent_id": loc1_id,
                "code": f"SHELF_A1_{uuid.uuid4().hex[:4]}",
                "name": "Shelf A1",
                "location_type": "Shelf",
            },
        )
        assert res_loc2.status_code == 201, res_loc2.text
        loc2_data = res_loc2.json()
        loc2_id = loc2_data["id"]

        # 4. Fetch Storage Location Tree
        res_tree = await async_client.get(
            f"/api/v1/storage-locations/tree?warehouse_id={wh_id}",
            headers=auth_headers,
        )
        assert res_tree.status_code == 200, res_tree.text
        tree_data = res_tree.json()
        root_node = next((n for n in tree_data if n["id"] == loc1_id), None)
        assert root_node is not None
        assert len(root_node["children"]) == 1
        assert root_node["children"][0]["id"] == loc2_id


@pytest.mark.asyncio
async def test_product_master_workflow(
    async_client: AsyncClient,
    auth_headers: dict,
):
    """Test Product creation, SKU/Barcode uniqueness, status transition rules, and search/filtering."""
    async with AsyncSessionLocal() as session:
        cat = await category_service.create_category(
            session, obj_in=ProductCategoryCreate(name="Hardware", code=f"CAT_HW_{uuid.uuid4().hex[:4]}")
        )
        uom = await unit_of_measure_service.create_unit(
            session, obj_in=UnitOfMeasureCreate(name=f"Piece_{uuid.uuid4().hex[:4]}", symbol=f"pcs_{uuid.uuid4().hex[:4]}", category="Count")
        )
        brand = await brand_service.create_brand(
            session, obj_in=BrandCreate(name=f"Logitech_{uuid.uuid4().hex[:4]}")
        )
        wh = await warehouse_service.create_warehouse(
            session, obj_in=WarehouseCreate(code=f"WH_HW_{uuid.uuid4().hex[:4]}", name="Hardware Warehouse")
        )
        cat_id = str(cat.id)
        uom_id = str(uom.id)
        brand_id = str(brand.id)
        wh_id = str(wh.id)


    sku = f"PROD-MX-{uuid.uuid4().hex[:4]}"
    # 1. Create Product
    res_prod = await async_client.post(
        "/api/v1/products",
        headers=auth_headers,
        json={
            "sku": sku,
            "barcode": f"88590998{uuid.uuid4().hex[:4]}",
            "name": "Logitech MX Master 3S Mouse",
            "description": "Performance Wireless Mouse",
            "category_id": cat_id,
            "brand_id": brand_id,
            "base_unit_id": uom_id,
            "default_warehouse_id": wh_id,
            "product_type": "Inventory",
            "track_inventory": True,
            "allow_negative_stock": False,
            "status": "Draft",
        },
    )

    assert res_prod.status_code == 201, res_prod.text
    prod_data = res_prod.json()
    prod_id = prod_data["id"]
    assert prod_data["sku"] == sku

    # 2. Duplicate SKU Check
    res_dup_sku = await async_client.post(
        "/api/v1/products",
        headers=auth_headers,
        json={
            "sku": sku,
            "name": "Duplicate SKU Product",
            "category_id": cat_id,
            "base_unit_id": uom_id,

        },
    )
    assert res_dup_sku.status_code == 409

    # 3. Search Products
    res_search = await async_client.get(
        f"/api/v1/products?search={sku}",
        headers=auth_headers,
    )
    assert res_search.status_code == 200
    search_data = res_search.json()
    assert search_data["total"] == 1
    assert search_data["items"][0]["id"] == prod_id

    # 4. Status Transition: Draft -> Active -> Archived
    res_active = await async_client.put(
        f"/api/v1/products/{prod_id}",
        headers=auth_headers,
        json={"status": "Active"},
    )
    assert res_active.status_code == 200
    assert res_active.json()["status"] == "Active"

    with patch("app.services.inventory_services.send_inventory_notification_task.delay") as mock_celery:
        res_archived = await async_client.put(
            f"/api/v1/products/{prod_id}",
            headers=auth_headers,
            json={"status": "Archived"},
        )
        assert res_archived.status_code == 200
        assert res_archived.json()["status"] == "Archived"
        assert mock_celery.called

    # 5. Archived Product is Read-Only
    res_readonly = await async_client.put(
        f"/api/v1/products/{prod_id}",
        headers=auth_headers,
        json={"name": "Attempted Renaming"},
    )
    assert res_readonly.status_code == 400


@pytest.mark.asyncio
async def test_product_attributes_and_documents(
    async_client: AsyncClient,
    auth_headers: dict,
):
    """Test custom product attributes assignment and document file attachments."""
    async with AsyncSessionLocal() as session:
        cat = await category_service.create_category(
            session, obj_in=ProductCategoryCreate(name=f"Apparel_{uuid.uuid4().hex[:4]}", code=f"CAT_APP_{uuid.uuid4().hex[:4]}")
        )
        uom = await unit_of_measure_service.create_unit(
            session, obj_in=UnitOfMeasureCreate(name=f"Pack_{uuid.uuid4().hex[:4]}", symbol=f"pk_{uuid.uuid4().hex[:4]}", category="Count")
        )
        prod = await product_service.create_product(
            session,
            obj_in=ProductCreate(
                sku=f"TSHIRT-COTTON-{uuid.uuid4().hex[:4]}",
                name="Cotton T-Shirt Large",
                category_id=cat.id,
                base_unit_id=uom.id,
            ),
        )
        prod_id = prod.id

        test_file = File(
            id=uuid.uuid4(),
            file_name="spec_sheet.pdf",
            storage_path="/uploads/spec_sheet.pdf",
            mime_type="application/pdf",
            file_size_bytes=1024,
            checksum_sha256=f"abc123sha256_{uuid.uuid4().hex[:4]}",
        )
        session.add(test_file)
        await session.commit()
        file_id = str(test_file.id)

    # 1. Create Attribute Definition (Color)
    res_attr = await async_client.post(
        "/api/v1/product-attributes",
        headers=auth_headers,
        json={
            "name": "Color",
            "code": f"ATTR_COLOR_{uuid.uuid4().hex[:4]}",
            "data_type": "Text",
        },
    )
    assert res_attr.status_code == 201, res_attr.text
    attr_data = res_attr.json()
    attr_id = attr_data["id"]

    # 2. Set Product Attribute Value
    res_val = await async_client.post(
        f"/api/v1/product-attributes/products/{prod_id}/attributes",
        headers=auth_headers,
        json={
            "attribute_id": attr_id,
            "value": "Navy Blue",
        },
    )
    assert res_val.status_code == 201, res_val.text
    assert res_val.json()["value"] == "Navy Blue"

    # 3. Attach Product Document
    res_doc = await async_client.post(
        f"/api/v1/products/{prod_id}/documents",
        headers=auth_headers,
        json={
            "file_id": file_id,
            "document_type": "Specification",
        },
    )
    assert res_doc.status_code == 201, res_doc.text
    doc_data = res_doc.json()
    doc_id = doc_data["id"]

    # 4. List & Delete Document
    res_list_doc = await async_client.get(
        f"/api/v1/products/{prod_id}/documents",
        headers=auth_headers,
    )
    assert res_list_doc.status_code == 200
    assert len(res_list_doc.json()) == 1

    res_del_doc = await async_client.delete(
        f"/api/v1/products/{prod_id}/documents/{doc_id}",
        headers=auth_headers,
    )
    assert res_del_doc.status_code == 204
