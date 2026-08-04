import json
import logging
from typing import Any, Dict, List, Optional, Tuple
import uuid
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import redis_manager
from app.exceptions.base import (
    DuplicateResourceException,
    NotFoundException,
    ValidationException,
)
from app.repositories.file import file_repository
from app.repositories.inventory_repos import (
    brand_repository,
    category_repository,
    product_attribute_repository,
    product_attribute_value_repository,
    product_document_repository,
    product_repository,
    storage_location_repository,
    unit_of_measure_repository,
    warehouse_repository,
)
from app.schemas.inventory import (
    BrandCreate,
    BrandUpdate,
    ProductAttributeCreate,
    ProductAttributeUpdate,
    ProductAttributeValueCreate,
    ProductCategoryCreate,
    ProductCategoryUpdate,
    ProductCreate,
    ProductDocumentCreate,
    ProductStatusEnum,
    ProductUpdate,
    StorageLocationCreate,
    StorageLocationUpdate,
    UnitOfMeasureCreate,
    UnitOfMeasureUpdate,
    WarehouseCreate,
    WarehouseUpdate,
)
from app.services.audit_log import audit_log_service
from app.tasks.inventory_tasks import send_inventory_notification_task

logger = logging.getLogger("app.services.inventory")


class CategoryService:
    async def create_category(
        self, db: AsyncSession, *, obj_in: ProductCategoryCreate, current_user_id: Optional[uuid.UUID] = None
    ):
        existing = await category_repository.get_by_code(db, obj_in.code)
        if existing:
            raise DuplicateResourceException(f"Category code '{obj_in.code}' already exists.")

        if obj_in.parent_id:
            parent = await category_repository.get_by_id(db, obj_in.parent_id)
            if not parent:
                raise NotFoundException(f"Parent Category ID '{obj_in.parent_id}' not found.")

        cat = await category_repository.create(db, obj_in=obj_in)
        await audit_log_service.log_event(
            db, action="CATEGORY_CREATE", entity_type="ProductCategory", entity_id=cat.id, user_id=current_user_id
        )
        await redis_manager.delete_pattern("category:*")
        return cat

    async def get_category(self, db: AsyncSession, id: uuid.UUID):
        cat = await category_repository.get_by_id(db, id)
        if not cat:
            raise NotFoundException(f"ProductCategory ID '{id}' not found.")
        return cat

    async def get_categories(self, db: AsyncSession, skip: int = 0, limit: int = 100):
        return await category_repository.get_all(db, skip=skip, limit=limit)

    async def update_category(
        self, db: AsyncSession, id: uuid.UUID, *, obj_in: ProductCategoryUpdate, current_user_id: Optional[uuid.UUID] = None
    ):
        cat = await self.get_category(db, id)

        if obj_in.code and obj_in.code != cat.code:
            existing = await category_repository.get_by_code(db, obj_in.code)
            if existing:
                raise DuplicateResourceException(f"Category code '{obj_in.code}' already exists.")

        if obj_in.parent_id:
            if obj_in.parent_id == id:
                raise ValidationException("Category cannot be its own parent.")
            parent = await category_repository.get_by_id(db, obj_in.parent_id)
            if not parent:
                raise NotFoundException(f"Parent Category ID '{obj_in.parent_id}' not found.")

            # Circular hierarchy check
            curr = parent
            while curr and curr.parent_id:
                if curr.parent_id == id:
                    raise ValidationException("Circular parent category relationship detected.")
                curr = await category_repository.get_by_id(db, curr.parent_id)

        updated_cat = await category_repository.update(db, db_obj=cat, obj_in=obj_in)
        await audit_log_service.log_event(
            db, action="CATEGORY_UPDATE", entity_type="ProductCategory", entity_id=id, user_id=current_user_id
        )
        await redis_manager.delete_pattern("category:*")
        return updated_cat

    async def delete_category(self, db: AsyncSession, id: uuid.UUID, current_user_id: Optional[uuid.UUID] = None):
        cat = await self.get_category(db, id)
        res = await category_repository.delete(db, id=id)
        await audit_log_service.log_event(
            db, action="CATEGORY_DELETE", entity_type="ProductCategory", entity_id=id, user_id=current_user_id
        )
        await redis_manager.delete_pattern("category:*")
        return res

    async def get_category_tree(self, db: AsyncSession) -> List[Dict[str, Any]]:
        cached = await redis_manager.get("category:tree")
        if cached:
            try:
                return json.loads(cached)
            except Exception:
                pass

        categories = await category_repository.get_all(db, limit=1000)
        cat_dict = {cat.id: cat for cat in categories}
        children_map: Dict[Optional[uuid.UUID], List[Any]] = {}

        for cat in categories:
            children_map.setdefault(cat.parent_id, []).append(cat)

        def build_node(cat):
            return {
                "id": str(cat.id),
                "name": cat.name,
                "code": cat.code,
                "description": cat.description,
                "parent_id": str(cat.parent_id) if cat.parent_id else None,
                "is_active": cat.is_active,
                "children": [build_node(child) for child in children_map.get(cat.id, [])],
            }

        roots = children_map.get(None, [])
        tree = [build_node(r) for r in roots]

        await redis_manager.set("category:tree", json.dumps(tree), ex=300)
        return tree


class UnitOfMeasureService:
    async def create_unit(
        self, db: AsyncSession, *, obj_in: UnitOfMeasureCreate, current_user_id: Optional[uuid.UUID] = None
    ):
        existing_name = await unit_of_measure_repository.get_by_name(db, obj_in.name)
        if existing_name:
            raise DuplicateResourceException(f"Unit name '{obj_in.name}' already exists.")
        existing_symbol = await unit_of_measure_repository.get_by_symbol(db, obj_in.symbol)
        if existing_symbol:
            raise DuplicateResourceException(f"Unit symbol '{obj_in.symbol}' already exists.")

        unit = await unit_of_measure_repository.create(db, obj_in=obj_in)
        await audit_log_service.log_event(
            db, action="UNIT_CREATE", entity_type="UnitOfMeasure", entity_id=unit.id, user_id=current_user_id
        )
        return unit

    async def get_unit(self, db: AsyncSession, id: uuid.UUID):
        unit = await unit_of_measure_repository.get_by_id(db, id)
        if not unit:
            raise NotFoundException(f"UnitOfMeasure ID '{id}' not found.")
        return unit

    async def get_units(self, db: AsyncSession, skip: int = 0, limit: int = 100):
        return await unit_of_measure_repository.get_all(db, skip=skip, limit=limit)

    async def update_unit(
        self, db: AsyncSession, id: uuid.UUID, *, obj_in: UnitOfMeasureUpdate, current_user_id: Optional[uuid.UUID] = None
    ):
        unit = await self.get_unit(db, id)

        if obj_in.name and obj_in.name != unit.name:
            existing = await unit_of_measure_repository.get_by_name(db, obj_in.name)
            if existing:
                raise DuplicateResourceException(f"Unit name '{obj_in.name}' already exists.")
        if obj_in.symbol and obj_in.symbol != unit.symbol:
            existing = await unit_of_measure_repository.get_by_symbol(db, obj_in.symbol)
            if existing:
                raise DuplicateResourceException(f"Unit symbol '{obj_in.symbol}' already exists.")

        updated_unit = await unit_of_measure_repository.update(db, db_obj=unit, obj_in=obj_in)
        await audit_log_service.log_event(
            db, action="UNIT_UPDATE", entity_type="UnitOfMeasure", entity_id=id, user_id=current_user_id
        )
        return updated_unit

    async def delete_unit(self, db: AsyncSession, id: uuid.UUID, current_user_id: Optional[uuid.UUID] = None):
        await self.get_unit(db, id)
        res = await unit_of_measure_repository.delete(db, id=id)
        await audit_log_service.log_event(
            db, action="UNIT_DELETE", entity_type="UnitOfMeasure", entity_id=id, user_id=current_user_id
        )
        return res


class BrandService:
    async def create_brand(
        self, db: AsyncSession, *, obj_in: BrandCreate, current_user_id: Optional[uuid.UUID] = None
    ):
        existing = await brand_repository.get_by_name(db, obj_in.name)
        if existing:
            raise DuplicateResourceException(f"Brand name '{obj_in.name}' already exists.")

        brand = await brand_repository.create(db, obj_in=obj_in)
        await audit_log_service.log_event(
            db, action="BRAND_CREATE", entity_type="Brand", entity_id=brand.id, user_id=current_user_id
        )
        return brand

    async def get_brand(self, db: AsyncSession, id: uuid.UUID):
        brand = await brand_repository.get_by_id(db, id)
        if not brand:
            raise NotFoundException(f"Brand ID '{id}' not found.")
        return brand

    async def get_brands(self, db: AsyncSession, skip: int = 0, limit: int = 100):
        return await brand_repository.get_all(db, skip=skip, limit=limit)

    async def update_brand(
        self, db: AsyncSession, id: uuid.UUID, *, obj_in: BrandUpdate, current_user_id: Optional[uuid.UUID] = None
    ):
        brand = await self.get_brand(db, id)

        if obj_in.name and obj_in.name != brand.name:
            existing = await brand_repository.get_by_name(db, obj_in.name)
            if existing:
                raise DuplicateResourceException(f"Brand name '{obj_in.name}' already exists.")

        updated_brand = await brand_repository.update(db, db_obj=brand, obj_in=obj_in)
        await audit_log_service.log_event(
            db, action="BRAND_UPDATE", entity_type="Brand", entity_id=id, user_id=current_user_id
        )
        return updated_brand

    async def delete_brand(self, db: AsyncSession, id: uuid.UUID, current_user_id: Optional[uuid.UUID] = None):
        await self.get_brand(db, id)
        res = await brand_repository.delete(db, id=id)
        await audit_log_service.log_event(
            db, action="BRAND_DELETE", entity_type="Brand", entity_id=id, user_id=current_user_id
        )
        return res


class WarehouseService:
    async def create_warehouse(
        self, db: AsyncSession, *, obj_in: WarehouseCreate, current_user_id: Optional[uuid.UUID] = None
    ):
        existing = await warehouse_repository.get_by_code(db, obj_in.code)
        if existing:
            raise DuplicateResourceException(f"Warehouse code '{obj_in.code}' already exists.")

        wh = await warehouse_repository.create(db, obj_in=obj_in)
        await audit_log_service.log_event(
            db, action="WAREHOUSE_CREATE", entity_type="Warehouse", entity_id=wh.id, user_id=current_user_id
        )
        try:
            send_inventory_notification_task.delay(
                "WAREHOUSE_CREATED", {"warehouse_id": str(wh.id), "code": wh.code, "name": wh.name}
            )
        except Exception as e:
            logger.warning(f"Failed to dispatch Celery warehouse creation notification: {e}")

        await redis_manager.delete_pattern("warehouse:*")
        return wh

    async def get_warehouse(self, db: AsyncSession, id: uuid.UUID):
        wh = await warehouse_repository.get_by_id(db, id)
        if not wh:
            raise NotFoundException(f"Warehouse ID '{id}' not found.")
        return wh

    async def get_warehouses(self, db: AsyncSession, skip: int = 0, limit: int = 100):
        return await warehouse_repository.get_all(db, skip=skip, limit=limit)

    async def update_warehouse(
        self, db: AsyncSession, id: uuid.UUID, *, obj_in: WarehouseUpdate, current_user_id: Optional[uuid.UUID] = None
    ):
        wh = await self.get_warehouse(db, id)

        if obj_in.code and obj_in.code != wh.code:
            existing = await warehouse_repository.get_by_code(db, obj_in.code)
            if existing:
                raise DuplicateResourceException(f"Warehouse code '{obj_in.code}' already exists.")

        updated_wh = await warehouse_repository.update(db, db_obj=wh, obj_in=obj_in)
        await audit_log_service.log_event(
            db, action="WAREHOUSE_UPDATE", entity_type="Warehouse", entity_id=id, user_id=current_user_id
        )
        try:
            send_inventory_notification_task.delay(
                "WAREHOUSE_UPDATED", {"warehouse_id": str(id), "code": updated_wh.code, "name": updated_wh.name}
            )
        except Exception as e:
            logger.warning(f"Failed to dispatch Celery warehouse update notification: {e}")

        await redis_manager.delete_pattern("warehouse:*")
        return updated_wh

    async def delete_warehouse(self, db: AsyncSession, id: uuid.UUID, current_user_id: Optional[uuid.UUID] = None):
        await self.get_warehouse(db, id)
        res = await warehouse_repository.delete(db, id=id)
        await audit_log_service.log_event(
            db, action="WAREHOUSE_DELETE", entity_type="Warehouse", entity_id=id, user_id=current_user_id
        )
        await redis_manager.delete_pattern("warehouse:*")
        return res


class StorageLocationService:
    async def create_location(
        self, db: AsyncSession, *, obj_in: StorageLocationCreate, current_user_id: Optional[uuid.UUID] = None
    ):
        wh = await warehouse_repository.get_by_id(db, obj_in.warehouse_id)
        if not wh:
            raise NotFoundException(f"Warehouse ID '{obj_in.warehouse_id}' not found.")

        existing = await storage_location_repository.get_by_warehouse_and_code(
            db, obj_in.warehouse_id, obj_in.code
        )
        if existing:
            raise DuplicateResourceException(
                f"StorageLocation code '{obj_in.code}' already exists in Warehouse ID '{obj_in.warehouse_id}'."
            )

        if obj_in.parent_id:
            parent = await storage_location_repository.get_by_id(db, obj_in.parent_id)
            if not parent:
                raise NotFoundException(f"Parent StorageLocation ID '{obj_in.parent_id}' not found.")
            if parent.warehouse_id != obj_in.warehouse_id:
                raise ValidationException("Parent storage location must belong to the same warehouse.")

        loc = await storage_location_repository.create(db, obj_in=obj_in)
        await audit_log_service.log_event(
            db, action="STORAGE_LOCATION_CREATE", entity_type="StorageLocation", entity_id=loc.id, user_id=current_user_id
        )
        await redis_manager.delete_pattern("location:*")
        return loc

    async def get_location(self, db: AsyncSession, id: uuid.UUID):
        loc = await storage_location_repository.get_by_id(db, id)
        if not loc:
            raise NotFoundException(f"StorageLocation ID '{id}' not found.")
        return loc

    async def get_locations(self, db: AsyncSession, skip: int = 0, limit: int = 100):
        return await storage_location_repository.get_all(db, skip=skip, limit=limit)

    async def update_location(
        self, db: AsyncSession, id: uuid.UUID, *, obj_in: StorageLocationUpdate, current_user_id: Optional[uuid.UUID] = None
    ):
        loc = await self.get_location(db, id)

        wh_id = obj_in.warehouse_id or loc.warehouse_id
        if obj_in.warehouse_id and obj_in.warehouse_id != loc.warehouse_id:
            wh = await warehouse_repository.get_by_id(db, obj_in.warehouse_id)
            if not wh:
                raise NotFoundException(f"Warehouse ID '{obj_in.warehouse_id}' not found.")

        if obj_in.code and obj_in.code != loc.code:
            existing = await storage_location_repository.get_by_warehouse_and_code(db, wh_id, obj_in.code)
            if existing:
                raise DuplicateResourceException(f"StorageLocation code '{obj_in.code}' already exists in warehouse.")

        if obj_in.parent_id:
            if obj_in.parent_id == id:
                raise ValidationException("StorageLocation cannot be its own parent.")
            parent = await storage_location_repository.get_by_id(db, obj_in.parent_id)
            if not parent:
                raise NotFoundException(f"Parent StorageLocation ID '{obj_in.parent_id}' not found.")
            if parent.warehouse_id != wh_id:
                raise ValidationException("Parent storage location must belong to the same warehouse.")

            curr = parent
            while curr and curr.parent_id:
                if curr.parent_id == id:
                    raise ValidationException("Circular parent location relationship detected.")
                curr = await storage_location_repository.get_by_id(db, curr.parent_id)

        updated_loc = await storage_location_repository.update(db, db_obj=loc, obj_in=obj_in)
        await audit_log_service.log_event(
            db, action="STORAGE_LOCATION_UPDATE", entity_type="StorageLocation", entity_id=id, user_id=current_user_id
        )
        await redis_manager.delete_pattern("location:*")
        return updated_loc

    async def delete_location(self, db: AsyncSession, id: uuid.UUID, current_user_id: Optional[uuid.UUID] = None):
        await self.get_location(db, id)
        res = await storage_location_repository.delete(db, id=id)
        await audit_log_service.log_event(
            db, action="STORAGE_LOCATION_DELETE", entity_type="StorageLocation", entity_id=id, user_id=current_user_id
        )
        await redis_manager.delete_pattern("location:*")
        return res

    async def get_location_tree(self, db: AsyncSession, warehouse_id: Optional[uuid.UUID] = None) -> List[Dict[str, Any]]:
        locations = await storage_location_repository.get_all(db, limit=1000)
        if warehouse_id:
            locations = [l for l in locations if l.warehouse_id == warehouse_id]

        children_map: Dict[Optional[uuid.UUID], List[Any]] = {}
        for loc in locations:
            children_map.setdefault(loc.parent_id, []).append(loc)

        def build_node(l):
            return {
                "id": str(l.id),
                "warehouse_id": str(l.warehouse_id),
                "parent_id": str(l.parent_id) if l.parent_id else None,
                "code": l.code,
                "name": l.name,
                "location_type": l.location_type,
                "is_active": l.is_active,
                "children": [build_node(c) for c in children_map.get(l.id, [])],
            }

        roots = children_map.get(None, [])
        return [build_node(r) for r in roots]


class ProductService:
    async def create_product(
        self, db: AsyncSession, *, obj_in: ProductCreate, current_user_id: Optional[uuid.UUID] = None
    ):
        existing_sku = await product_repository.get_by_sku(db, obj_in.sku)
        if existing_sku:
            raise DuplicateResourceException(f"Product SKU '{obj_in.sku}' already exists.")

        if obj_in.barcode:
            existing_bc = await product_repository.get_by_barcode(db, obj_in.barcode)
            if existing_bc:
                raise DuplicateResourceException(f"Product Barcode '{obj_in.barcode}' already exists.")

        cat = await category_repository.get_by_id(db, obj_in.category_id)
        if not cat:
            raise NotFoundException(f"ProductCategory ID '{obj_in.category_id}' not found.")

        unit = await unit_of_measure_repository.get_by_id(db, obj_in.base_unit_id)
        if not unit:
            raise NotFoundException(f"Base UnitOfMeasure ID '{obj_in.base_unit_id}' not found.")

        if obj_in.brand_id:
            brand = await brand_repository.get_by_id(db, obj_in.brand_id)
            if not brand:
                raise NotFoundException(f"Brand ID '{obj_in.brand_id}' not found.")

        if obj_in.default_warehouse_id:
            wh = await warehouse_repository.get_by_id(db, obj_in.default_warehouse_id)
            if not wh:
                raise NotFoundException(f"Default Warehouse ID '{obj_in.default_warehouse_id}' not found.")

        prod_data = obj_in.model_dump(exclude={"attributes"})
        product = await product_repository.create(db, obj_in=prod_data)

        if obj_in.attributes:
            for attr_in in obj_in.attributes:
                attr_def = await product_attribute_repository.get_by_id(db, attr_in.attribute_id)
                if not attr_def:
                    raise NotFoundException(f"ProductAttribute ID '{attr_in.attribute_id}' not found.")
                await product_attribute_value_repository.create_or_update(
                    db, product.id, attr_in.attribute_id, attr_in.value
                )

        await audit_log_service.log_event(
            db, action="PRODUCT_CREATE", entity_type="Product", entity_id=product.id, user_id=current_user_id
        )
        await redis_manager.delete_pattern("product:*")
        return await self.get_product_detail(db, product.id)

    async def get_product(self, db: AsyncSession, id: uuid.UUID):
        prod = await product_repository.get_by_id(db, id)
        if not prod:
            raise NotFoundException(f"Product ID '{id}' not found.")
        return prod

    async def get_product_detail(self, db: AsyncSession, id: uuid.UUID) -> Dict[str, Any]:
        prod = await self.get_product(db, id)
        attrs = await product_attribute_value_repository.get_by_product_id(db, id)
        docs = await product_document_repository.get_by_product_id(db, id)

        attr_responses = []
        for a in attrs:
            attr_def = await product_attribute_repository.get_by_id(db, a.attribute_id)
            attr_responses.append({
                "id": str(a.id),
                "product_id": str(a.product_id),
                "attribute_id": str(a.attribute_id),
                "value": a.value,
                "attribute_code": attr_def.code if attr_def else None,
                "attribute_name": attr_def.name if attr_def else None,
                "data_type": attr_def.data_type if attr_def else None,
            })

        doc_responses = []
        for d in docs:
            file_rec = await file_repository.get_by_id(db, d.file_id)
            doc_responses.append({
                "id": str(d.id),
                "product_id": str(d.product_id),
                "file_id": str(d.file_id),
                "document_type": d.document_type,
                "file_name": file_rec.file_name if file_rec else None,
                "mime_type": file_rec.mime_type if file_rec else None,
                "created_at": d.created_at,
            })

        return {
            "id": prod.id,
            "sku": prod.sku,
            "barcode": prod.barcode,
            "name": prod.name,
            "description": prod.description,
            "category_id": prod.category_id,
            "category_name": prod.category.name if prod.category else None,
            "brand_id": prod.brand_id,
            "brand_name": prod.brand.name if prod.brand else None,
            "base_unit_id": prod.base_unit_id,
            "base_unit_name": prod.base_unit.name if prod.base_unit else None,
            "purchase_unit_id": prod.purchase_unit_id,
            "sales_unit_id": prod.sales_unit_id,
            "product_type": prod.product_type,
            "track_inventory": prod.track_inventory,
            "allow_negative_stock": prod.allow_negative_stock,
            "default_warehouse_id": prod.default_warehouse_id,
            "default_warehouse_name": prod.default_warehouse.name if prod.default_warehouse else None,
            "weight": prod.weight,
            "height": prod.height,
            "width": prod.width,
            "length": prod.length,
            "volume": prod.volume,
            "image_file_id": prod.image_file_id,
            "status": prod.status,
            "created_at": prod.created_at,
            "updated_at": prod.updated_at,
            "attributes": attr_responses,
            "documents": doc_responses,
        }

    async def get_products(
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
    ) -> Tuple[List[Dict[str, Any]], int]:
        items, total = await product_repository.search_and_filter(
            db,
            search_term=search_term,
            category_id=category_id,
            brand_id=brand_id,
            warehouse_id=warehouse_id,
            status=status,
            track_inventory=track_inventory,
            skip=skip,
            limit=limit,
        )

        res = []
        for prod in items:
            res.append({
                "id": prod.id,
                "sku": prod.sku,
                "barcode": prod.barcode,
                "name": prod.name,
                "description": prod.description,
                "category_id": prod.category_id,
                "category_name": prod.category.name if prod.category else None,
                "brand_id": prod.brand_id,
                "brand_name": prod.brand.name if prod.brand else None,
                "base_unit_id": prod.base_unit_id,
                "base_unit_name": prod.base_unit.name if prod.base_unit else None,
                "purchase_unit_id": prod.purchase_unit_id,
                "sales_unit_id": prod.sales_unit_id,
                "product_type": prod.product_type,
                "track_inventory": prod.track_inventory,
                "allow_negative_stock": prod.allow_negative_stock,
                "default_warehouse_id": prod.default_warehouse_id,
                "default_warehouse_name": prod.default_warehouse.name if prod.default_warehouse else None,
                "weight": prod.weight,
                "height": prod.height,
                "width": prod.width,
                "length": prod.length,
                "volume": prod.volume,
                "image_file_id": prod.image_file_id,
                "status": prod.status,
                "created_at": prod.created_at,
                "updated_at": prod.updated_at,
            })

        return res, total

    async def update_product(
        self, db: AsyncSession, id: uuid.UUID, *, obj_in: ProductUpdate, current_user_id: Optional[uuid.UUID] = None
    ):
        prod = await self.get_product(db, id)

        if prod.status == ProductStatusEnum.ARCHIVED:
            raise ValidationException("Archived products are read-only and cannot be modified.")

        if obj_in.sku and obj_in.sku != prod.sku:
            existing = await product_repository.get_by_sku(db, obj_in.sku)
            if existing:
                raise DuplicateResourceException(f"Product SKU '{obj_in.sku}' already exists.")

        if obj_in.barcode and obj_in.barcode != prod.barcode:
            existing = await product_repository.get_by_barcode(db, obj_in.barcode)
            if existing:
                raise DuplicateResourceException(f"Product Barcode '{obj_in.barcode}' already exists.")

        if obj_in.category_id and obj_in.category_id != prod.category_id:
            cat = await category_repository.get_by_id(db, obj_in.category_id)
            if not cat:
                raise NotFoundException(f"ProductCategory ID '{obj_in.category_id}' not found.")

        if obj_in.base_unit_id and obj_in.base_unit_id != prod.base_unit_id:
            unit = await unit_of_measure_repository.get_by_id(db, obj_in.base_unit_id)
            if not unit:
                raise NotFoundException(f"Base UnitOfMeasure ID '{obj_in.base_unit_id}' not found.")

        updated_prod = await product_repository.update(db, db_obj=prod, obj_in=obj_in)

        if obj_in.status == ProductStatusEnum.ARCHIVED:
            try:
                send_inventory_notification_task.delay(
                    "PRODUCT_ARCHIVED", {"product_id": str(id), "sku": updated_prod.sku, "name": updated_prod.name}
                )
            except Exception as e:
                logger.warning(f"Failed to dispatch Celery product archival notification: {e}")

        await audit_log_service.log_event(
            db, action="PRODUCT_UPDATE", entity_type="Product", entity_id=id, user_id=current_user_id
        )
        await redis_manager.delete_pattern("product:*")
        return await self.get_product_detail(db, id)

    async def delete_product(self, db: AsyncSession, id: uuid.UUID, current_user_id: Optional[uuid.UUID] = None):
        await self.get_product(db, id)
        res = await product_repository.delete(db, id=id)
        await audit_log_service.log_event(
            db, action="PRODUCT_DELETE", entity_type="Product", entity_id=id, user_id=current_user_id
        )
        await redis_manager.delete_pattern("product:*")
        return res


class ProductAttributeService:
    async def create_attribute(
        self, db: AsyncSession, *, obj_in: ProductAttributeCreate, current_user_id: Optional[uuid.UUID] = None
    ):
        existing = await product_attribute_repository.get_by_code(db, obj_in.code)
        if existing:
            raise DuplicateResourceException(f"ProductAttribute code '{obj_in.code}' already exists.")

        attr = await product_attribute_repository.create(db, obj_in=obj_in)
        await audit_log_service.log_event(
            db, action="PRODUCT_ATTRIBUTE_CREATE", entity_type="ProductAttribute", entity_id=attr.id, user_id=current_user_id
        )
        return attr

    async def get_attribute(self, db: AsyncSession, id: uuid.UUID):
        attr = await product_attribute_repository.get_by_id(db, id)
        if not attr:
            raise NotFoundException(f"ProductAttribute ID '{id}' not found.")
        return attr

    async def get_attributes(self, db: AsyncSession, skip: int = 0, limit: int = 100):
        return await product_attribute_repository.get_all(db, skip=skip, limit=limit)

    async def update_attribute(
        self, db: AsyncSession, id: uuid.UUID, *, obj_in: ProductAttributeUpdate, current_user_id: Optional[uuid.UUID] = None
    ):
        attr = await self.get_attribute(db, id)
        if obj_in.code and obj_in.code != attr.code:
            existing = await product_attribute_repository.get_by_code(db, obj_in.code)
            if existing:
                raise DuplicateResourceException(f"ProductAttribute code '{obj_in.code}' already exists.")

        updated_attr = await product_attribute_repository.update(db, db_obj=attr, obj_in=obj_in)
        await audit_log_service.log_event(
            db, action="PRODUCT_ATTRIBUTE_UPDATE", entity_type="ProductAttribute", entity_id=id, user_id=current_user_id
        )
        return updated_attr

    async def delete_attribute(self, db: AsyncSession, id: uuid.UUID, current_user_id: Optional[uuid.UUID] = None):
        await self.get_attribute(db, id)
        res = await product_attribute_repository.delete(db, id=id)
        await audit_log_service.log_event(
            db, action="PRODUCT_ATTRIBUTE_DELETE", entity_type="ProductAttribute", entity_id=id, user_id=current_user_id
        )
        return res

    async def set_product_attribute(
        self, db: AsyncSession, product_id: uuid.UUID, *, obj_in: ProductAttributeValueCreate, current_user_id: Optional[uuid.UUID] = None
    ):
        prod = await product_repository.get_by_id(db, product_id)
        if not prod:
            raise NotFoundException(f"Product ID '{product_id}' not found.")
        if prod.status == ProductStatusEnum.ARCHIVED:
            raise ValidationException("Archived products are read-only and cannot be modified.")

        attr = await product_attribute_repository.get_by_id(db, obj_in.attribute_id)
        if not attr:
            raise NotFoundException(f"ProductAttribute ID '{obj_in.attribute_id}' not found.")

        res = await product_attribute_value_repository.create_or_update(
            db, product_id, obj_in.attribute_id, obj_in.value
        )
        await audit_log_service.log_event(
            db, action="PRODUCT_ATTRIBUTE_VALUE_SET", entity_type="ProductAttributeValue", entity_id=res.id, user_id=current_user_id
        )
        return res

    async def delete_product_attribute(
        self, db: AsyncSession, product_id: uuid.UUID, attribute_id: uuid.UUID, current_user_id: Optional[uuid.UUID] = None
    ):
        prod = await product_repository.get_by_id(db, product_id)
        if not prod:
            raise NotFoundException(f"Product ID '{product_id}' not found.")
        if prod.status == ProductStatusEnum.ARCHIVED:
            raise ValidationException("Archived products are read-only and cannot be modified.")

        res = await product_attribute_value_repository.delete(db, product_id, attribute_id)
        if not res:
            raise NotFoundException("Product attribute value mapping not found.")

        await audit_log_service.log_event(
            db, action="PRODUCT_ATTRIBUTE_VALUE_DELETE", entity_type="ProductAttributeValue", entity_id=attribute_id, user_id=current_user_id
        )
        return res


class ProductDocumentService:
    async def add_document(
        self, db: AsyncSession, product_id: uuid.UUID, *, obj_in: ProductDocumentCreate, current_user_id: Optional[uuid.UUID] = None
    ):
        prod = await product_repository.get_by_id(db, product_id)
        if not prod:
            raise NotFoundException(f"Product ID '{product_id}' not found.")
        if prod.status == ProductStatusEnum.ARCHIVED:
            raise ValidationException("Archived products are read-only and cannot be modified.")

        file_rec = await file_repository.get_by_id(db, obj_in.file_id)
        if not file_rec:
            raise NotFoundException(f"File ID '{obj_in.file_id}' not found.")

        doc = await product_document_repository.create(db, product_id, obj_in.file_id, obj_in.document_type)
        await audit_log_service.log_event(
            db, action="PRODUCT_DOCUMENT_UPLOAD", entity_type="ProductDocument", entity_id=doc.id, user_id=current_user_id
        )
        return doc

    async def get_documents(self, db: AsyncSession, product_id: uuid.UUID):
        prod = await product_repository.get_by_id(db, product_id)
        if not prod:
            raise NotFoundException(f"Product ID '{product_id}' not found.")

        docs = await product_document_repository.get_by_product_id(db, product_id)
        res = []
        for d in docs:
            file_rec = await file_repository.get_by_id(db, d.file_id)
            res.append({
                "id": d.id,
                "product_id": d.product_id,
                "file_id": d.file_id,
                "document_type": d.document_type,
                "file_name": file_rec.original_filename if file_rec else None,
                "mime_type": file_rec.mime_type if file_rec else None,
                "created_at": d.created_at,
            })
        return res

    async def delete_document(
        self, db: AsyncSession, product_id: uuid.UUID, document_id: uuid.UUID, current_user_id: Optional[uuid.UUID] = None
    ):
        prod = await product_repository.get_by_id(db, product_id)
        if not prod:
            raise NotFoundException(f"Product ID '{product_id}' not found.")
        if prod.status == ProductStatusEnum.ARCHIVED:
            raise ValidationException("Archived products are read-only and cannot be modified.")

        doc = await product_document_repository.get_by_id(db, document_id)
        if not doc or doc.product_id != product_id:
            raise NotFoundException(f"ProductDocument ID '{document_id}' not found for product.")

        res = await product_document_repository.delete(db, document_id)
        await audit_log_service.log_event(
            db, action="PRODUCT_DOCUMENT_DELETE", entity_type="ProductDocument", entity_id=document_id, user_id=current_user_id
        )
        return res


# Service Instances
category_service = CategoryService()
unit_of_measure_service = UnitOfMeasureService()
brand_service = BrandService()
warehouse_service = WarehouseService()
storage_location_service = StorageLocationService()
product_service = ProductService()
product_attribute_service = ProductAttributeService()
product_document_service = ProductDocumentService()
