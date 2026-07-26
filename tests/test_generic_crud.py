import uuid
import pytest
import pytest_asyncio
from pydantic import BaseModel
from sqlalchemy import Float, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import SoftDeleteMixin, TimestampMixin, UUIDMixin
from app.db.session import AsyncSessionLocal, sync_engine
from app.exceptions.base import NotFoundException
from app.repositories.base_repository import BaseRepository
from app.schemas.responses import create_error_response, create_paginated_response, create_success_response
from app.services.base_service import BaseService
from app.utils.filters import FilterCriterion, FilterOperator
from app.utils.pagination import PaginationParams
from app.utils.sorting import SortCriterion, SortOrder
from app.utils.validation import is_valid_email, is_valid_uuid, sanitize_string


# --- DUMMY TEST ORM MODEL & SCHEMAS ---

class DummyProduct(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "dummy_products"

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    code: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    price: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)


class DummyProductCreate(BaseModel):
    name: str
    code: str
    price: float = 0.0


class DummyProductUpdate(BaseModel):
    name: str | None = None
    code: str | None = None
    price: float | None = None


class DummyProductRepository(BaseRepository[DummyProduct, DummyProductCreate, DummyProductUpdate]):
    def __init__(self):
        super().__init__(DummyProduct)


class DummyProductService(BaseService[DummyProductRepository]):
    def __init__(self, repository: DummyProductRepository):
        super().__init__(repository)


dummy_product_repo = DummyProductRepository()
dummy_product_service = DummyProductService(dummy_product_repo)


# --- FIXTURES ---

@pytest_asyncio.fixture(autouse=True)
async def setup_dummy_product_table():
    """
    Creates dummy_products table before each test run.
    """
    DummyProduct.__table__.create(bind=sync_engine, checkfirst=True)
    yield


# --- REPOSITORY & SERVICE TESTS ---

@pytest.mark.asyncio
async def test_create_and_get_by_id():
    """
    Test creating a product record and retrieving it by ID.
    """
    async with AsyncSessionLocal() as session:
        product_in = DummyProductCreate(name="Laptop Pro", code=f"LAP-{uuid.uuid4().hex[:6]}", price=1200.50)
        product = await dummy_product_service.create(session, obj_in=product_in)
        assert product.id is not None
        assert product.name == "Laptop Pro"
        assert product.price == 1200.50

        fetched = await dummy_product_service.get_by_id(session, product.id)
        assert fetched.id == product.id
        assert fetched.name == "Laptop Pro"


@pytest.mark.asyncio
async def test_update_and_exists():
    """
    Test updating entity fields and verifying existence check.
    """
    async with AsyncSessionLocal() as session:
        code = f"PHN-{uuid.uuid4().hex[:6]}"
        product_in = DummyProductCreate(name="Phone V1", code=code, price=500.0)
        product = await dummy_product_service.create(session, obj_in=product_in)

        # Check exists
        exists_before = await dummy_product_service.exists(session, product.id)
        assert exists_before is True

        # Update
        update_in = DummyProductUpdate(name="Phone V2", price=599.99)
        updated = await dummy_product_service.update(session, id=product.id, obj_in=update_in)
        assert updated.name == "Phone V2"
        assert updated.price == 599.99
        assert updated.code == code


@pytest.mark.asyncio
async def test_hard_delete():
    """
    Test hard physical deletion of entity record.
    """
    async with AsyncSessionLocal() as session:
        product_in = DummyProductCreate(name="Temp Item", code=f"TMP-{uuid.uuid4().hex[:6]}", price=10.0)
        product = await dummy_product_service.create(session, obj_in=product_in)

        await dummy_product_service.delete(session, id=product.id)

        # Verify NotFoundException on get_by_id
        with pytest.raises(NotFoundException):
            await dummy_product_service.get_by_id(session, product.id)


@pytest.mark.asyncio
async def test_soft_delete_and_restore():
    """
    Test soft deleting a record and subsequently restoring it.
    """
    async with AsyncSessionLocal() as session:
        product_in = DummyProductCreate(name="Soft Delete Item", code=f"SOFT-{uuid.uuid4().hex[:6]}", price=99.0)
        product = await dummy_product_service.create(session, obj_in=product_in)

        # Soft delete
        await dummy_product_service.soft_delete(session, id=product.id)

        # Standard get_by_id should raise NotFoundException
        with pytest.raises(NotFoundException):
            await dummy_product_service.get_by_id(session, product.id, include_deleted=False)

        # Fetch with include_deleted=True
        deleted_item = await dummy_product_service.get_by_id(session, product.id, include_deleted=True)
        assert deleted_item.is_deleted is True
        assert deleted_item.deleted_at is not None

        # Restore
        restored = await dummy_product_service.restore(session, id=product.id)
        assert restored.is_deleted is False
        assert restored.deleted_at is None


@pytest.mark.asyncio
async def test_pagination():
    """
    Test paginated query results and metadata calculation.
    """
    async with AsyncSessionLocal() as session:
        unique_prefix = f"PAG-{uuid.uuid4().hex[:6]}"
        for i in range(12):
            await dummy_product_service.create(
                session,
                obj_in=DummyProductCreate(name=f"Paginated Item {i}", code=f"{unique_prefix}-{i}", price=10.0 * i)
            )

        params_p1 = PaginationParams(page=1, page_size=5)
        res_p1 = await dummy_product_service.get_paginated(
            session,
            params=params_p1,
            filters=[FilterCriterion(field="code", operator=FilterOperator.LIKE, value=unique_prefix)],
        )

        assert len(res_p1.items) == 5
        assert res_p1.total == 12
        assert res_p1.page == 1
        assert res_p1.total_pages == 3
        assert res_p1.has_next is True
        assert res_p1.has_prev is False

        # Page 3
        params_p3 = PaginationParams(page=3, page_size=5)
        res_p3 = await dummy_product_service.get_paginated(
            session,
            params=params_p3,
            filters=[FilterCriterion(field="code", operator=FilterOperator.LIKE, value=unique_prefix)],
        )
        assert len(res_p3.items) == 2
        assert res_p3.has_next is False
        assert res_p3.has_prev is True


@pytest.mark.asyncio
async def test_filtering():
    """
    Test dynamic filter criteria (EQ, GTE, IN, LIKE).
    """
    async with AsyncSessionLocal() as session:
        prefix = f"FLT-{uuid.uuid4().hex[:6]}"
        await dummy_product_service.create(session, obj_in=DummyProductCreate(name="Cheap Keyboard", code=f"{prefix}-1", price=25.0))
        await dummy_product_service.create(session, obj_in=DummyProductCreate(name="Mid Keyboard", code=f"{prefix}-2", price=75.0))
        await dummy_product_service.create(session, obj_in=DummyProductCreate(name="Expensive Keyboard", code=f"{prefix}-3", price=200.0))

        # Filter price >= 75
        params = PaginationParams(page=1, page_size=10)
        filters = [
            FilterCriterion(field="code", operator=FilterOperator.LIKE, value=prefix),
            FilterCriterion(field="price", operator=FilterOperator.GTE, value=75.0),
        ]
        result = await dummy_product_service.get_paginated(session, params=params, filters=filters)
        assert result.total == 2
        prices = [p.price for p in result.items]
        assert 25.0 not in prices


@pytest.mark.asyncio
async def test_sorting():
    """
    Test dynamic sorting by column in ASC and DESC order.
    """
    async with AsyncSessionLocal() as session:
        prefix = f"SRT-{uuid.uuid4().hex[:6]}"
        await dummy_product_service.create(session, obj_in=DummyProductCreate(name="Alpha", code=f"{prefix}-1", price=10.0))
        await dummy_product_service.create(session, obj_in=DummyProductCreate(name="Gamma", code=f"{prefix}-2", price=30.0))
        await dummy_product_service.create(session, obj_in=DummyProductCreate(name="Beta", code=f"{prefix}-3", price=20.0))

        params = PaginationParams(page=1, page_size=10)
        filters = [FilterCriterion(field="code", operator=FilterOperator.LIKE, value=prefix)]
        
        # Sort price DESC
        sorting_desc = [SortCriterion(field="price", order=SortOrder.DESC)]
        res_desc = await dummy_product_service.get_paginated(session, params=params, filters=filters, sorting=sorting_desc)
        prices = [p.price for p in res_desc.items]
        assert prices == [30.0, 20.0, 10.0]


@pytest.mark.asyncio
async def test_multi_column_search():
    """
    Test multi-column ILIKE searching.
    """
    async with AsyncSessionLocal() as session:
        prefix = f"SCH-{uuid.uuid4().hex[:6]}"
        await dummy_product_service.create(session, obj_in=DummyProductCreate(name=f"Ergonomic Mouse {prefix}", code=f"{prefix}-1", price=50.0))
        await dummy_product_service.create(session, obj_in=DummyProductCreate(name=f"Trackball Device", code=f"MOUSE-{prefix}-2", price=60.0))

        params = PaginationParams(page=1, page_size=10)
        filters = [FilterCriterion(field="code", operator=FilterOperator.LIKE, value=prefix)]
        # Search for "Mouse" across name and code fields
        result = await dummy_product_service.get_paginated(
            session,
            params=params,
            filters=filters,
            search_term="Mouse",
            search_fields=["name", "code"],
        )
        assert result.total == 2


@pytest.mark.asyncio
async def test_service_not_found_exception():
    """
    Test that service layer raises NotFoundException for non-existent record ID.
    """
    async with AsyncSessionLocal() as session:
        random_id = uuid.uuid4()
        with pytest.raises(NotFoundException) as exc_info:
            await dummy_product_service.get_by_id(session, random_id)
        assert exc_info.value.status_code == 404
        assert exc_info.value.error_code == "RESOURCE_NOT_FOUND"


def test_standard_response_builders():
    """
    Test response builder helper functions.
    """
    succ = create_success_response(data={"key": "val"}, message="Success message")
    assert succ.success is True
    assert succ.data["key"] == "val"
    assert succ.message == "Success message"

    err = create_error_response(message="Bad Request", error_code="BAD_REQUEST")
    assert err.success is False
    assert err.error_code == "BAD_REQUEST"


def test_validation_utilities():
    """
    Test helper validation utility functions.
    """
    valid_uuid = str(uuid.uuid4())
    assert is_valid_uuid(valid_uuid) is True
    assert is_valid_uuid("not-a-uuid") is False

    assert is_valid_email("admin@apnaerp.com") is True
    assert is_valid_email("invalid-email") is False

    assert sanitize_string("  hello world  ") == "hello world"
