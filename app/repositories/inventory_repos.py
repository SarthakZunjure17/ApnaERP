from typing import List, Optional, Tuple
import uuid
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.brand import Brand
from app.models.product import Product
from app.models.product_attribute import ProductAttribute, ProductAttributeValue
from app.models.product_category import ProductCategory
from app.models.product_document import ProductDocument
from app.models.storage_location import StorageLocation
from app.models.unit_of_measure import UnitOfMeasure
from app.models.warehouse import Warehouse
from app.repositories.base_repository import BaseRepository
from app.schemas.inventory import (
    BrandCreate,
    BrandUpdate,
    ProductAttributeCreate,
    ProductAttributeUpdate,
    ProductCategoryCreate,
    ProductCategoryUpdate,
    ProductCreate,
    ProductUpdate,
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


class UnitOfMeasureRepository(BaseRepository[UnitOfMeasure, UnitOfMeasureCreate, UnitOfMeasureUpdate]):
    def __init__(self):
        super().__init__(UnitOfMeasure)

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


class StorageLocationRepository(BaseRepository[StorageLocation, StorageLocationCreate, StorageLocationUpdate]):
    def __init__(self):
        super().__init__(StorageLocation)

    async def get_by_warehouse_and_code(self, db: AsyncSession, warehouse_id: uuid.UUID, code: str) -> Optional[StorageLocation]:
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
        status: Optional[str] = None,
        track_inventory: Optional[bool] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[Product], int]:
        stmt = select(Product)

        if category_id:
            stmt = stmt.where(Product.category_id == category_id)
        if brand_id:
            stmt = stmt.where(Product.brand_id == brand_id)
        if warehouse_id:
            stmt = stmt.where(Product.default_warehouse_id == warehouse_id)
        if status:
            stmt = stmt.where(Product.status == status)
        if track_inventory is not None:
            stmt = stmt.where(Product.track_inventory == track_inventory)

        if search_term:
            term = f"%{search_term}%"
            stmt = stmt.where(
                or_(
                    Product.sku.ilike(term),
                    Product.barcode.ilike(term),
                    Product.name.ilike(term),
                    Product.description.ilike(term),
                )
            )

        # Count total
        count_stmt = select(Product.id).select_from(stmt.subquery())
        count_res = await db.execute(count_stmt)
        total = len(count_res.scalars().all())

        stmt = stmt.offset(skip).limit(limit)
        res = await db.execute(stmt)
        items = list(res.scalars().all())
        return items, total


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
product_attribute_repository = ProductAttributeRepository()
product_attribute_value_repository = ProductAttributeValueRepository()
product_document_repository = ProductDocumentRepository()
