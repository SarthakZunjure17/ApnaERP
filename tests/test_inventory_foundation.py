from decimal import Decimal
from typing import AsyncGenerator
from unittest.mock import patch
import uuid
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.main import app
from app.models.file import File
from app.models.user import User
from app.repositories.user import user_repository
from app.schemas.inventory import (
    BrandCreate,
    InventoryPolicyCreate,
    ProductCategoryCreate,
    ProductCreate,
    ProductWarehouseCreate,
    StorageLocationCreate,
    UnitOfMeasureCreate,
    WarehouseCreate,
)
from app.services.inventory_services import (
    brand_service,
    category_service,
    inventory_policy_service,
    product_service,
    product_warehouse_service,
    storage_location_service,
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
    """Test category creation, infinite tree hierarchy resolution, children listing, duplicate codes, and circular parent prevention."""
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
    assert res_dup.status_code in (400, 409)

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

    # 4. Fetch Category Children
    res_children = await async_client.get(f"/api/v1/categories/{parent_id}/children", headers=auth_headers)
    assert res_children.status_code == 200, res_children.text
    children_list = res_children.json()
    assert len(children_list) == 1
    assert children_list[0]["id"] == child_id

    # 5. Fetch Category Tree
    res_tree = await async_client.get("/api/v1/categories/tree", headers=auth_headers)
    assert res_tree.status_code == 200, res_tree.text
    tree_data = res_tree.json()
    parent_node = next((node for node in tree_data if node["id"] == parent_id), None)
    assert parent_node is not None
    assert len(parent_node["children"]) == 1
    assert parent_node["children"][0]["id"] == child_id

    # 6. Circular hierarchy check: Setting parent's parent to child
    res_circ = await async_client.put(
        f"/api/v1/categories/{parent_id}",
        headers=auth_headers,
        json={"parent_id": child_id},
    )
    assert res_circ.status_code in (400, 422)


@pytest.mark.asyncio
async def test_unit_of_measure_and_brand_crud(
    async_client: AsyncClient,
    auth_headers: dict,
):
    """Test CRUD operations, code lookup, precision boundaries, and uniqueness rules for Units of Measure and Brands."""
    # 1. Create Unit of Measure with code
    unique_symbol = f"kg_{uuid.uuid4().hex[:4]}"
    unique_code = f"KG_{uuid.uuid4().hex[:4]}".upper()
    res_uom = await async_client.post(
        "/api/v1/units-of-measure",
        headers=auth_headers,
        json={
            "name": f"Kilogram_{uuid.uuid4().hex[:4]}",
            "symbol": unique_symbol,
            "code": unique_code,
            "category": "Weight",
            "precision": 3,
            "base_unit": "kg",
        },
    )
    assert res_uom.status_code == 201, res_uom.text
    uom_data = res_uom.json()
    assert uom_data["code"] == unique_code
    assert uom_data["precision"] == 3

    # Fetch by code
    res_code_lookup = await async_client.get(f"/api/v1/units-of-measure/code/{unique_code}", headers=auth_headers)
    assert res_code_lookup.status_code == 200
    assert res_code_lookup.json()["id"] == uom_data["id"]

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
    assert res_uom_dup.status_code in (400, 409)

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
    assert res_brand_dup.status_code in (400, 409)


@pytest.mark.asyncio
async def test_warehouse_and_storage_location_hierarchy(
    async_client: AsyncClient,
    auth_headers: dict,
):
    """Test Warehouse CRUD with address/type fields, Storage Location hierarchy, tree resolution, and validation."""
    with patch("app.services.inventory_services.send_inventory_notification_task.delay") as mock_celery:
        wh_code = f"WH_CENTRAL_{uuid.uuid4().hex[:4]}"
        # 1. Create Warehouse with structured fields
        res_wh = await async_client.post(
            "/api/v1/warehouses",
            headers=auth_headers,
            json={
                "code": wh_code,
                "name": "Central Logistics Hub",
                "description": "Primary regional distribution facility",
                "warehouse_type": "DISTRIBUTION",
                "address_line_1": "100 Logistics Blvd",
                "address_line_2": "Suite 400",
                "city": "Mumbai",
                "state": "Maharashtra",
                "country": "India",
                "postal_code": "400001",
                "timezone": "Asia/Kolkata",
                "contact_person": "Jane Doe",
                "phone": "+919876543210",
                "email": "wh_central@apnaerp.com",
            },
        )
        assert res_wh.status_code == 201, res_wh.text
        wh_data = res_wh.json()
        wh_id = wh_data["id"]
        assert wh_data["warehouse_type"] == "DISTRIBUTION"
        assert wh_data["city"] == "Mumbai"
        assert mock_celery.called

        # 2. Create Root Storage Location (Rack A)
        loc_code = f"RACK_A_{uuid.uuid4().hex[:4]}"
        res_loc1 = await async_client.post(
            "/api/v1/storage-locations",
            headers=auth_headers,
            json={
                "warehouse_id": wh_id,
                "code": loc_code,
                "name": "Main Storage Rack A",
                "description": "High-density heavy pallet rack",
                "location_type": "Rack",
            },
        )
        assert res_loc1.status_code == 201, res_loc1.text
        loc1_data = res_loc1.json()
        loc1_id = loc1_data["id"]

        # Duplicate location code in same warehouse check
        res_dup_loc = await async_client.post(
            "/api/v1/storage-locations",
            headers=auth_headers,
            json={
                "warehouse_id": wh_id,
                "code": loc_code,
                "name": "Duplicate Rack",
                "location_type": "Rack",
            },
        )
        assert res_dup_loc.status_code in (400, 409)

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

        # 4. Fetch Warehouse Locations list endpoint
        res_wh_locs = await async_client.get(f"/api/v1/warehouses/{wh_id}/locations", headers=auth_headers)
        assert res_wh_locs.status_code == 200
        assert len(res_wh_locs.json()) >= 2

        # 5. Fetch Storage Location Tree (via /storage-locations/tree and /warehouses/{id}/locations/tree)
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

        res_wh_tree = await async_client.get(
            f"/api/v1/warehouses/{wh_id}/locations/tree",
            headers=auth_headers,
        )
        assert res_wh_tree.status_code == 200, res_wh_tree.text
        wh_tree_data = res_wh_tree.json()
        wh_root_node = next((n for n in wh_tree_data if n["id"] == loc1_id), None)
        assert wh_root_node is not None
        assert len(wh_root_node["children"]) == 1
        assert wh_root_node["children"][0]["id"] == loc2_id


@pytest.mark.asyncio
async def test_product_master_workflow(
    async_client: AsyncClient,
    auth_headers: dict,
):
    """Test Product creation with v0.6.0 master fields, SKU/Barcode uniqueness, status transition rules, and multi-parameter search/filtering."""
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
    # 1. Create Product with v0.6.0 fields
    res_prod = await async_client.post(
        "/api/v1/products",
        headers=auth_headers,
        json={
            "sku": sku,
            "barcode": f"88590998{uuid.uuid4().hex[:4]}",
            "name": "Logitech MX Master 3S Mouse",
            "description": "Performance Wireless Mouse",
            "model_number": "MX-3S-BLK",
            "category_id": cat_id,
            "brand_id": brand_id,
            "base_unit_id": uom_id,
            "default_warehouse_id": wh_id,
            "product_type": "Inventory",
            "is_active": True,
            "is_stockable": True,
            "is_sellable": True,
            "is_purchasable": True,
            "track_inventory": True,
            "allow_negative_stock": False,
            "reorder_level": 15.0,
            "reorder_quantity": 50.0,
            "minimum_stock": 10.0,
            "maximum_stock": 200.0,
            "lead_time_days": 7,
            "default_unit_price": 99.99,
            "metadata_json": {"color": "Graphite", "dpi": 8000},
            "status": "Draft",
        },
    )

    assert res_prod.status_code == 201, res_prod.text
    prod_data = res_prod.json()
    prod_id = prod_data["id"]
    assert prod_data["sku"] == sku
    assert prod_data["model_number"] == "MX-3S-BLK"
    assert prod_data["is_stockable"] is True
    assert prod_data["lead_time_days"] == 7
    assert Decimal(str(prod_data["reorder_level"])) == Decimal("15.0")
    assert prod_data["metadata_json"]["color"] == "Graphite"

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
    assert res_dup_sku.status_code in (400, 409)

    # 3. Dedicated Search & Multi-filter search
    res_search_endpoint = await async_client.get(
        f"/api/v1/products/search?q=MX-3S-BLK",
        headers=auth_headers,
    )
    assert res_search_endpoint.status_code == 200
    assert any(item["id"] == prod_id for item in res_search_endpoint.json()["items"])

    res_filter = await async_client.get(
        f"/api/v1/products?is_stockable=true&is_sellable=true&status=Draft",
        headers=auth_headers,
    )
    assert res_filter.status_code == 200
    assert any(item["id"] == prod_id for item in res_filter.json()["items"])

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
    assert res_readonly.status_code in (400, 422)


@pytest.mark.asyncio
async def test_product_warehouse_stocking_parameters_and_policies(
    async_client: AsyncClient,
    auth_headers: dict,
):
    """Test multi-warehouse stocking configuration, threshold validations, location consistency, and inventory policies."""
    async with AsyncSessionLocal() as session:
        cat = await category_service.create_category(
            session, obj_in=ProductCategoryCreate(name=f"Industrial_{uuid.uuid4().hex[:4]}", code=f"CAT_IND_{uuid.uuid4().hex[:4]}")
        )
        uom = await unit_of_measure_service.create_unit(
            session, obj_in=UnitOfMeasureCreate(name=f"Unit_{uuid.uuid4().hex[:4]}", symbol=f"un_{uuid.uuid4().hex[:4]}", category="Count")
        )
        wh1 = await warehouse_service.create_warehouse(
            session, obj_in=WarehouseCreate(code=f"WH_NORTH_{uuid.uuid4().hex[:4]}", name="North Facility")
        )
        wh2 = await warehouse_service.create_warehouse(
            session, obj_in=WarehouseCreate(code=f"WH_SOUTH_{uuid.uuid4().hex[:4]}", name="South Facility")
        )
        loc1 = await storage_location_service.create_location(
            session, obj_in=StorageLocationCreate(warehouse_id=wh1.id, code=f"BIN_N1_{uuid.uuid4().hex[:4]}", name="Bin N1")
        )
        loc2 = await storage_location_service.create_location(
            session, obj_in=StorageLocationCreate(warehouse_id=wh2.id, code=f"BIN_S1_{uuid.uuid4().hex[:4]}", name="Bin S1")
        )
        prod = await product_service.create_product(
            session,
            obj_in=ProductCreate(
                sku=f"VALVE-IND-{uuid.uuid4().hex[:4]}",
                name="Industrial Ball Valve",
                category_id=cat.id,
                base_unit_id=uom.id,
                is_stockable=True,
            ),
        )
        prod_id = str(prod["id"]) if isinstance(prod, dict) else str(prod.id)
        wh1_id = str(wh1.id)
        wh2_id = str(wh2.id)
        loc1_id = str(loc1.id)
        loc2_id = str(loc2.id)

    # 1. Create ProductWarehouse configuration with preferred location
    res_pw1 = await async_client.post(
        "/api/v1/product-warehouses",
        headers=auth_headers,
        json={
            "product_id": prod_id,
            "warehouse_id": wh1_id,
            "preferred_location_id": loc1_id,
            "reorder_level": 25.0,
            "reorder_quantity": 100.0,
            "minimum_stock": 20.0,
            "maximum_stock": 500.0,
            "safety_stock": 15.0,
        },
    )
    assert res_pw1.status_code == 201, res_pw1.text
    pw1_data = res_pw1.json()
    assert Decimal(str(pw1_data["reorder_level"])) == Decimal("25.0")
    assert pw1_data["preferred_location_id"] == loc1_id

    # 2. Location mismatch validation: assigning WH2 location to WH1 config
    res_loc_mismatch = await async_client.post(
        "/api/v1/product-warehouses",
        headers=auth_headers,
        json={
            "product_id": prod_id,
            "warehouse_id": wh1_id,
            "preferred_location_id": loc2_id,  # loc2 belongs to wh2!
        },
    )
    assert res_loc_mismatch.status_code in (400, 422)

    # 3. Duplicate configuration check
    res_dup_pw = await async_client.post(
        "/api/v1/product-warehouses",
        headers=auth_headers,
        json={
            "product_id": prod_id,
            "warehouse_id": wh1_id,
        },
    )
    assert res_dup_pw.status_code in (400, 409)

    # 4. Invalid threshold check: minimum_stock > maximum_stock
    res_bad_threshold = await async_client.post(
        "/api/v1/product-warehouses",
        headers=auth_headers,
        json={
            "product_id": prod_id,
            "warehouse_id": wh2_id,
            "minimum_stock": 200.0,
            "maximum_stock": 50.0,
        },
    )
    assert res_bad_threshold.status_code in (400, 422)

    # 5. List product's warehouse configs via /products/{id}/warehouses
    res_prod_whs = await async_client.get(f"/api/v1/products/{prod_id}/warehouses", headers=auth_headers)
    assert res_prod_whs.status_code == 200
    assert len(res_prod_whs.json()) == 1

    # 6. List warehouse's product configs via /warehouses/{id}/products
    res_wh_prods = await async_client.get(f"/api/v1/warehouses/{wh1_id}/products", headers=auth_headers)
    assert res_wh_prods.status_code == 200
    assert len(res_wh_prods.json()) == 1

    # 7. Inventory Policies: Set Global Policy & Warehouse Specific Policy
    res_global_pol = await async_client.post(
        "/api/v1/inventory/policies",
        headers=auth_headers,
        json={
            "valuation_method": "FIFO",
            "costing_method": "STANDARD",
            "negative_stock_allowed": False,
            "default_reorder_strategy": "MIN_MAX",
            "default_reservation_behavior": "STRICT",
            "low_stock_alert_enabled": True,
        },
    )
    assert res_global_pol.status_code == 200, res_global_pol.text
    global_pol = res_global_pol.json()
    assert global_pol["valuation_method"] == "FIFO"

    res_wh_pol = await async_client.post(
        "/api/v1/inventory/policies",
        headers=auth_headers,
        json={
            "warehouse_id": wh1_id,
            "valuation_method": "WEIGHTED_AVERAGE",
            "costing_method": "ACTUAL",
            "negative_stock_allowed": False,
        },
    )
    assert res_wh_pol.status_code == 200, res_wh_pol.text
    wh_pol = res_wh_pol.json()
    assert wh_pol["valuation_method"] == "WEIGHTED_AVERAGE"

    # Get policy for WH1 (should return WH1 specific)
    res_get_wh1_pol = await async_client.get(f"/api/v1/inventory/policies/{wh1_id}", headers=auth_headers)
    assert res_get_wh1_pol.status_code == 200
    assert res_get_wh1_pol.json()["valuation_method"] == "WEIGHTED_AVERAGE"


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
        prod_id = prod["id"] if isinstance(prod, dict) else prod.id

        user_res = await session.execute(select(User))
        user = user_res.scalars().first()
        if not user:
            user = User(
                full_name="Test User",
                email=f"testuser_{uuid.uuid4().hex[:4]}@example.com",
                username=f"testuser_{uuid.uuid4().hex[:4]}",
                password_hash="secret",
            )
            session.add(user)
            await session.commit()

        test_file = File(
            id=uuid.uuid4(),
            original_filename="spec_sheet.pdf",
            stored_filename=f"spec_{uuid.uuid4().hex[:6]}.pdf",
            file_extension="pdf",
            mime_type="application/pdf",
            file_size=1024,
            storage_path="/uploads/spec_sheet.pdf",
            uploaded_by_id=user.id,
            checksum=f"abc123sha256_{uuid.uuid4().hex[:4]}",
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
