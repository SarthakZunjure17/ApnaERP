from typing import Any, Dict, List, Optional, Tuple
import uuid
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.brand import Brand
from app.models.inventory_policy import InventoryPolicy
from app.models.product import Product
from app.models.product_attribute import ProductAttribute, ProductAttributeValue
from app.models.product_category import ProductCategory
from app.models.product_document import ProductDocument
from app.models.product_warehouse import ProductWarehouse
from app.models.storage_location import StorageLocation
from app.models.unit_of_measure import UnitOfMeasure
from app.models.warehouse import Warehouse
from app.repositories.base_repository import BaseRepository
from app.schemas.inventory import (
    BrandCreate,
    BrandUpdate,
    InventoryPolicyCreate,
    InventoryPolicyUpdate,
    ProductAttributeCreate,
    ProductAttributeUpdate,
    ProductCategoryCreate,
    ProductCategoryUpdate,
    ProductCreate,
    ProductUpdate,
    ProductWarehouseCreate,
    ProductWarehouseUpdate,
    StorageLocationCreate,
    StorageLocationUpdate,
    UnitOfMeasureCreate,
    UnitOfMeasureUpdate,
    WarehouseCreate,
    WarehouseUpdate,
)


class ProductCategoryRepository(BaseRepository[ProductCategory, ProductCategoryCreate, ProductCategoryUpdate]):
    def __init__(self):
        super().__init__(ProductCategory)

    async def get_by_code(self, db: AsyncSession, code: str) -> Optional[ProductCategory]:
        stmt = select(ProductCategory).where(ProductCategory.code == code)
        res = await db.execute(stmt)
        return res.scalar_one_or_none()

    async def get_by_name(self, db: AsyncSession, name: str) -> Optional[ProductCategory]:
        stmt = select(ProductCategory).where(ProductCategory.name == name)
        res = await db.execute(stmt)
        return res.scalar_one_or_none()

    async def get_root_categories(self, db: AsyncSession) -> List[ProductCategory]:
        stmt = select(ProductCategory).where(ProductCategory.parent_id.is_(None))
        res = await db.execute(stmt)
        return list(res.scalars().all())

    async def get_children(self, db: AsyncSession, parent_id: uuid.UUID) -> List[ProductCategory]:
        stmt = select(ProductCategory).where(ProductCategory.parent_id == parent_id)
        res = await db.execute(stmt)
        return list(res.scalars().all())


class UnitOfMeasureRepository(BaseRepository[UnitOfMeasure, UnitOfMeasureCreate, UnitOfMeasureUpdate]):
    def __init__(self):
        super().__init__(UnitOfMeasure)

    async def get_by_code(self, db: AsyncSession, code: str) -> Optional[UnitOfMeasure]:
        stmt = select(UnitOfMeasure).where(
            or_(
                UnitOfMeasure.code == code,
                UnitOfMeasure.code == code.upper(),
                UnitOfMeasure.symbol == code,
            )
        )
        res = await db.execute(stmt)
        return res.scalar_one_or_none()

    async def get_by_name(self, db: AsyncSession, name: str) -> Optional[UnitOfMeasure]:
        stmt = select(UnitOfMeasure).where(UnitOfMeasure.name == name)
        res = await db.execute(stmt)
        return res.scalar_one_or_none()

    async def get_by_symbol(self, db: AsyncSession, symbol: str) -> Optional[UnitOfMeasure]:
        stmt = select(UnitOfMeasure).where(UnitOfMeasure.symbol == symbol)
        res = await db.execute(stmt)
        return res.scalar_one_or_none()


class BrandRepository(BaseRepository[Brand, BrandCreate, BrandUpdate]):
    def __init__(self):
        super().__init__(Brand)

    async def get_by_name(self, db: AsyncSession, name: str) -> Optional[Brand]:
        stmt = select(Brand).where(Brand.name == name)
        res = await db.execute(stmt)
        return res.scalar_one_or_none()


class WarehouseRepository(BaseRepository[Warehouse, WarehouseCreate, WarehouseUpdate]):
    def __init__(self):
        super().__init__(Warehouse)

    async def get_by_code(self, db: AsyncSession, code: str) -> Optional[Warehouse]:
        stmt = select(Warehouse).where(Warehouse.code == code)
        res = await db.execute(stmt)
        return res.scalar_one_or_none()

    async def get_active_warehouses(self, db: AsyncSession) -> List[Warehouse]:
        stmt = select(Warehouse).where(Warehouse.is_active == True)
        res = await db.execute(stmt)
        return list(res.scalars().all())


class StorageLocationRepository(BaseRepository[StorageLocation, StorageLocationCreate, StorageLocationUpdate]):
    def __init__(self):
        super().__init__(StorageLocation)

    async def get_by_warehouse_and_code(
        self, db: AsyncSession, warehouse_id: uuid.UUID, code: str
    ) -> Optional[StorageLocation]:
        stmt = select(StorageLocation).where(
            StorageLocation.warehouse_id == warehouse_id,
            StorageLocation.code == code,
        )
        res = await db.execute(stmt)
        return res.scalar_one_or_none()

    async def get_root_locations_by_warehouse(self, db: AsyncSession, warehouse_id: uuid.UUID) -> List[StorageLocation]:
        stmt = select(StorageLocation).where(
            StorageLocation.warehouse_id == warehouse_id,
            StorageLocation.parent_id.is_(None),
        )
        res = await db.execute(stmt)
        return list(res.scalars().all())

    async def list_by_warehouse(
        self, db: AsyncSession, warehouse_id: uuid.UUID, skip: int = 0, limit: int = 100
    ) -> List[StorageLocation]:
        stmt = (
            select(StorageLocation)
            .where(StorageLocation.warehouse_id == warehouse_id)
            .offset(skip)
            .limit(limit)
        )
        res = await db.execute(stmt)
        return list(res.scalars().all())

    async def get_children(self, db: AsyncSession, parent_id: uuid.UUID) -> List[StorageLocation]:
        stmt = select(StorageLocation).where(StorageLocation.parent_id == parent_id)
        res = await db.execute(stmt)
        return list(res.scalars().all())


class ProductRepository(BaseRepository[Product, ProductCreate, ProductUpdate]):
    def __init__(self):
        super().__init__(Product)

    async def get_by_sku(self, db: AsyncSession, sku: str) -> Optional[Product]:
        stmt = select(Product).where(Product.sku == sku)
        res = await db.execute(stmt)
        return res.scalar_one_or_none()

    async def get_by_barcode(self, db: AsyncSession, barcode: str) -> Optional[Product]:
        stmt = select(Product).where(Product.barcode == barcode)
        res = await db.execute(stmt)
        return res.scalar_one_or_none()

    async def search_and_filter(
        self,
        db: AsyncSession,
        *,
        search_term: Optional[str] = None,
        category_id: Optional[uuid.UUID] = None,
        brand_id: Optional[uuid.UUID] = None,
        warehouse_id: Optional[uuid.UUID] = None,
        product_type: Optional[str] = None,
        status: Optional[str] = None,
        is_active: Optional[bool] = None,
        is_stockable: Optional[bool] = None,
        is_sellable: Optional[bool] = None,
        is_purchasable: Optional[bool] = None,
        track_inventory: Optional[bool] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[Product], int]:
        filters = []

        if category_id:
            filters.append(Product.category_id == category_id)
        if brand_id:
            filters.append(Product.brand_id == brand_id)
        if warehouse_id:
            filters.append(Product.default_warehouse_id == warehouse_id)
        if product_type:
            filters.append(Product.product_type == product_type)
        if status:
            filters.append(Product.status == status)
        if is_active is not None:
            filters.append(Product.is_active == is_active)
        if is_stockable is not None:
            filters.append(Product.is_stockable == is_stockable)
        elif track_inventory is not None:
            filters.append(Product.track_inventory == track_inventory)
        if is_sellable is not None:
            filters.append(Product.is_sellable == is_sellable)
        if is_purchasable is not None:
            filters.append(Product.is_purchasable == is_purchasable)

        if search_term:
            term = f"%{search_term}%"
            filters.append(
                or_(
                    Product.sku.ilike(term),
                    Product.barcode.ilike(term),
                    Product.name.ilike(term),
                    Product.description.ilike(term),
                    Product.model_number.ilike(term),
                )
            )

        # Count query
        count_stmt = select(func.count(Product.id))
        if filters:
            count_stmt = count_stmt.where(*filters)
        count_res = await db.execute(count_stmt)
        total = count_res.scalar_one() or 0

        # Items query
        stmt = select(Product)
        if filters:
            stmt = stmt.where(*filters)
        stmt = stmt.offset(skip).limit(limit)
        res = await db.execute(stmt)
        items = list(res.scalars().all())
        return items, total


class ProductWarehouseRepository(BaseRepository[ProductWarehouse, ProductWarehouseCreate, ProductWarehouseUpdate]):
    def __init__(self):
        super().__init__(ProductWarehouse)

    async def get_by_product_and_warehouse(
        self, db: AsyncSession, product_id: uuid.UUID, warehouse_id: uuid.UUID
    ) -> Optional[ProductWarehouse]:
        stmt = select(ProductWarehouse).where(
            ProductWarehouse.product_id == product_id,
            ProductWarehouse.warehouse_id == warehouse_id,
        )
        res = await db.execute(stmt)
        return res.scalar_one_or_none()

    async def list_by_product(
        self, db: AsyncSession, product_id: uuid.UUID, skip: int = 0, limit: int = 100
    ) -> List[ProductWarehouse]:
        stmt = (
            select(ProductWarehouse)
            .where(ProductWarehouse.product_id == product_id)
            .offset(skip)
            .limit(limit)
        )
        res = await db.execute(stmt)
        return list(res.scalars().all())

    async def list_by_warehouse(
        self, db: AsyncSession, warehouse_id: uuid.UUID, skip: int = 0, limit: int = 100
    ) -> List[ProductWarehouse]:
        stmt = (
            select(ProductWarehouse)
            .where(ProductWarehouse.warehouse_id == warehouse_id)
            .offset(skip)
            .limit(limit)
        )
        res = await db.execute(stmt)
        return list(res.scalars().all())


class InventoryPolicyRepository(BaseRepository[InventoryPolicy, InventoryPolicyCreate, InventoryPolicyUpdate]):
    def __init__(self):
        super().__init__(InventoryPolicy)

    async def get_by_warehouse_id(self, db: AsyncSession, warehouse_id: uuid.UUID) -> Optional[InventoryPolicy]:
        stmt = (
            select(InventoryPolicy)
            .where(InventoryPolicy.warehouse_id == warehouse_id, InventoryPolicy.is_active == True)
            .order_by(InventoryPolicy.created_at.desc())
            .limit(1)
        )
        res = await db.execute(stmt)
        return res.scalars().first()

    async def get_global_policy(self, db: AsyncSession) -> Optional[InventoryPolicy]:
        stmt = (
            select(InventoryPolicy)
            .where(InventoryPolicy.warehouse_id.is_(None), InventoryPolicy.is_active == True)
            .order_by(InventoryPolicy.created_at.desc())
            .limit(1)
        )
        res = await db.execute(stmt)
        return res.scalars().first()



class ProductAttributeRepository(BaseRepository[ProductAttribute, ProductAttributeCreate, ProductAttributeUpdate]):
    def __init__(self):
        super().__init__(ProductAttribute)

    async def get_by_code(self, db: AsyncSession, code: str) -> Optional[ProductAttribute]:
        stmt = select(ProductAttribute).where(ProductAttribute.code == code)
        res = await db.execute(stmt)
        return res.scalar_one_or_none()


class ProductAttributeValueRepository:
    async def get_by_product_and_attribute(
        self, db: AsyncSession, product_id: uuid.UUID, attribute_id: uuid.UUID
    ) -> Optional[ProductAttributeValue]:
        stmt = select(ProductAttributeValue).where(
            ProductAttributeValue.product_id == product_id,
            ProductAttributeValue.attribute_id == attribute_id,
        )
        res = await db.execute(stmt)
        return res.scalar_one_or_none()

    async def get_by_product_id(self, db: AsyncSession, product_id: uuid.UUID) -> List[ProductAttributeValue]:
        stmt = select(ProductAttributeValue).where(ProductAttributeValue.product_id == product_id)
        res = await db.execute(stmt)
        return list(res.scalars().all())

    async def create_or_update(
        self, db: AsyncSession, product_id: uuid.UUID, attribute_id: uuid.UUID, value: str
    ) -> ProductAttributeValue:
        existing = await self.get_by_product_and_attribute(db, product_id, attribute_id)
        if existing:
            existing.value = value
            db.add(existing)
            await db.commit()
            await db.refresh(existing)
            return existing
        else:
            attr_val = ProductAttributeValue(
                id=uuid.uuid4(),
                product_id=product_id,
                attribute_id=attribute_id,
                value=value,
            )
            db.add(attr_val)
            await db.commit()
            await db.refresh(attr_val)
            return attr_val

    async def delete(self, db: AsyncSession, product_id: uuid.UUID, attribute_id: uuid.UUID) -> bool:
        existing = await self.get_by_product_and_attribute(db, product_id, attribute_id)
        if not existing:
            return False
        await db.delete(existing)
        await db.commit()
        return True


class ProductDocumentRepository:
    async def get_by_id(self, db: AsyncSession, id: uuid.UUID) -> Optional[ProductDocument]:
        stmt = select(ProductDocument).where(ProductDocument.id == id)
        res = await db.execute(stmt)
        return res.scalar_one_or_none()

    async def get_by_product_id(self, db: AsyncSession, product_id: uuid.UUID) -> List[ProductDocument]:
        stmt = select(ProductDocument).where(ProductDocument.product_id == product_id)
        res = await db.execute(stmt)
        return list(res.scalars().all())

    async def create(
        self, db: AsyncSession, product_id: uuid.UUID, file_id: uuid.UUID, document_type: str
    ) -> ProductDocument:
        doc = ProductDocument(
            id=uuid.uuid4(),
            product_id=product_id,
            file_id=file_id,
            document_type=document_type,
        )
        db.add(doc)
        await db.commit()
        await db.refresh(doc)
        return doc

    async def delete(self, db: AsyncSession, id: uuid.UUID) -> bool:
        doc = await self.get_by_id(db, id)
        if not doc:
            return False
        await db.delete(doc)
        await db.commit()
        return True


# Repository Instances
category_repository = ProductCategoryRepository()
unit_of_measure_repository = UnitOfMeasureRepository()
brand_repository = BrandRepository()
warehouse_repository = WarehouseRepository()
storage_location_repository = StorageLocationRepository()
product_repository = ProductRepository()
product_warehouse_repository = ProductWarehouseRepository()
inventory_policy_repository = InventoryPolicyRepository()
product_attribute_repository = ProductAttributeRepository()
product_attribute_value_repository = ProductAttributeValueRepository()
product_document_repository = ProductDocumentRepository()
