from decimal import Decimal
from typing import List, Optional, Tuple
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions.base import DuplicateResourceException, NotFoundException, ValidationException
from app.models.customer import (
    CustomerCategory,
    Customer,
    CustomerContact,
    CustomerAddress,
    CustomerDocument,
)
from app.models.file import File
from app.repositories.sales_repos import (
    customer_category_repository,
    customer_repository,
    customer_contact_repository,
    customer_address_repository,
    customer_document_repository,
)
from app.repositories.file import file_repository
from app.schemas.sales import (
    CustomerAddressCreate,
    CustomerCategoryCreate,
    CustomerCategoryUpdate,
    CustomerContactCreate,
    CustomerCreate,
    CustomerDocumentCreate,
    CustomerUpdate,
)
from app.services.audit_log import audit_log_service


class CustomerService:
    async def create_category(
        self, db: AsyncSession, obj_in: CustomerCategoryCreate, current_user_id: Optional[uuid.UUID] = None
    ) -> CustomerCategory:
        existing = await customer_category_repository.get_by_code(db, obj_in.code)
        if existing:
            raise DuplicateResourceException(f"Customer Category code '{obj_in.code}' already exists.")

        cat = await customer_category_repository.create(db, obj_in=obj_in.model_dump())
        await audit_log_service.log_event(
            db=db,
            user_id=current_user_id,
            action="CUSTOMER_CATEGORY_CREATE",
            entity_type="CustomerCategory",
            entity_id=str(cat.id),
            new_data=obj_in.model_dump(),
        )
        return cat

    async def list_categories(self, db: AsyncSession) -> List[CustomerCategory]:
        return await customer_category_repository.get_multi(db, limit=200)

    async def create_customer(
        self, db: AsyncSession, obj_in: CustomerCreate, current_user_id: Optional[uuid.UUID] = None
    ) -> Customer:
        existing = await customer_repository.get_by_code(db, obj_in.customer_code)
        if existing:
            raise DuplicateResourceException(f"Customer code '{obj_in.customer_code}' already exists.")

        if obj_in.category_id:
            cat = await customer_category_repository.get_by_id(db, obj_in.category_id)
            if not cat:
                raise NotFoundException(f"Customer Category ID '{obj_in.category_id}' not found.")

        cust_dict = obj_in.model_dump(exclude={"contacts", "addresses"})
        customer = await customer_repository.create(db, obj_in=cust_dict)

        if obj_in.contacts:
            for c in obj_in.contacts:
                c_data = c.model_dump()
                c_data["customer_id"] = customer.id
                customer.contacts.append(CustomerContact(**c_data))

        if obj_in.addresses:
            for a in obj_in.addresses:
                a_data = a.model_dump()
                a_data["customer_id"] = customer.id
                customer.addresses.append(CustomerAddress(**a_data))

        await db.commit()
        await db.refresh(customer)
        await audit_log_service.log_event(
            db=db,
            user_id=current_user_id,
            action="CUSTOMER_CREATE",
            entity_type="Customer",
            entity_id=str(customer.id),
            new_data={"customer_code": customer.customer_code, "name": customer.name},
        )
        return customer

    async def update_customer(
        self, db: AsyncSession, customer_id: uuid.UUID, obj_in: CustomerUpdate, current_user_id: Optional[uuid.UUID] = None
    ) -> Customer:
        customer = await customer_repository.get_by_id(db, customer_id)
        if not customer or customer.is_deleted:
            raise NotFoundException(f"Customer ID '{customer_id}' not found.")

        if obj_in.category_id:
            cat = await customer_category_repository.get_by_id(db, obj_in.category_id)
            if not cat:
                raise NotFoundException(f"Customer Category ID '{obj_in.category_id}' not found.")

        update_data = obj_in.model_dump(exclude_unset=True)
        updated_cust = await customer_repository.update(db, db_obj=customer, obj_in=update_data)

        await audit_log_service.log_event(
            db=db,
            user_id=current_user_id,
            action="CUSTOMER_UPDATE",
            entity_type="Customer",
            entity_id=str(customer_id),
            new_data=update_data,
        )
        return updated_cust

    async def get_customer(self, db: AsyncSession, customer_id: uuid.UUID) -> Customer:
        cust = await customer_repository.get_by_id(db, customer_id)
        if not cust or cust.is_deleted:
            raise NotFoundException(f"Customer ID '{customer_id}' not found.")
        return cust

    async def list_customers(
        self,
        db: AsyncSession,
        query: Optional[str] = None,
        status: Optional[str] = None,
        category_id: Optional[uuid.UUID] = None,
        is_preferred: Optional[bool] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[Customer], int]:
        return await customer_repository.search_customers(
            db, query=query, status=status, category_id=category_id, is_preferred=is_preferred, skip=skip, limit=limit
        )

    async def delete_customer(
        self, db: AsyncSession, customer_id: uuid.UUID, current_user_id: Optional[uuid.UUID] = None
    ) -> Customer:
        cust = await customer_repository.get_by_id(db, customer_id)
        if not cust or cust.is_deleted:
            raise NotFoundException(f"Customer ID '{customer_id}' not found.")

        cust.is_deleted = True
        await db.commit()

        await audit_log_service.log_event(
            db=db,
            user_id=current_user_id,
            action="CUSTOMER_DELETE",
            entity_type="Customer",
            entity_id=str(customer_id),
        )
        return cust

    async def add_contact(
        self, db: AsyncSession, customer_id: uuid.UUID, obj_in: CustomerContactCreate
    ) -> CustomerContact:
        cust = await self.get_customer(db, customer_id)
        c_data = obj_in.model_dump()
        c_data["customer_id"] = cust.id
        return await customer_contact_repository.create(db, obj_in=c_data)

    async def list_contacts(self, db: AsyncSession, customer_id: uuid.UUID) -> List[CustomerContact]:
        await self.get_customer(db, customer_id)
        return await customer_contact_repository.get_by_customer_id(db, customer_id)

    async def add_address(
        self, db: AsyncSession, customer_id: uuid.UUID, obj_in: CustomerAddressCreate
    ) -> CustomerAddress:
        cust = await self.get_customer(db, customer_id)
        a_data = obj_in.model_dump()
        a_data["customer_id"] = cust.id
        return await customer_address_repository.create(db, obj_in=a_data)

    async def list_addresses(self, db: AsyncSession, customer_id: uuid.UUID) -> List[CustomerAddress]:
        await self.get_customer(db, customer_id)
        return await customer_address_repository.get_by_customer_id(db, customer_id)

    async def attach_document(
        self, db: AsyncSession, customer_id: uuid.UUID, obj_in: CustomerDocumentCreate
    ) -> dict:
        await self.get_customer(db, customer_id)
        file_rec = await file_repository.get_by_id(db, obj_in.file_id)
        if not file_rec:
            raise NotFoundException(f"File ID '{obj_in.file_id}' not found.")

        doc = await customer_document_repository.create(
            db, obj_in={"customer_id": customer_id, "file_id": obj_in.file_id, "document_type": obj_in.document_type}
        )

        return {
            "id": doc.id,
            "customer_id": doc.customer_id,
            "file_id": doc.file_id,
            "document_type": doc.document_type,
            "file_name": file_rec.original_filename if file_rec else None,
            "mime_type": file_rec.mime_type if file_rec else None,
            "created_at": doc.created_at,
        }

    async def list_documents(self, db: AsyncSession, customer_id: uuid.UUID) -> List[dict]:
        await self.get_customer(db, customer_id)
        docs = await customer_document_repository.get_by_customer_id(db, customer_id)
        res = []
        for d in docs:
            file_rec = await file_repository.get_by_id(db, d.file_id)
            res.append({
                "id": d.id,
                "customer_id": d.customer_id,
                "file_id": d.file_id,
                "document_type": d.document_type,
                "file_name": file_rec.original_filename if file_rec else None,
                "mime_type": file_rec.mime_type if file_rec else None,
                "created_at": d.created_at,
            })
        return res

    async def activate_customer(
        self, db: AsyncSession, customer_id: uuid.UUID, current_user_id: Optional[uuid.UUID] = None
    ) -> Customer:
        customer = await self.get_customer(db, customer_id)
        customer.status = "Active"
        await db.commit()
        await db.refresh(customer)

        await audit_log_service.log_event(
            db=db,
            user_id=current_user_id,
            action="CUSTOMER_ACTIVATE",
            entity_type="Customer",
            entity_id=str(customer_id),
            new_data={"status": "Active"},
        )
        return customer

    async def deactivate_customer(
        self, db: AsyncSession, customer_id: uuid.UUID, current_user_id: Optional[uuid.UUID] = None
    ) -> Customer:
        customer = await self.get_customer(db, customer_id)
        customer.status = "Inactive"
        await db.commit()
        await db.refresh(customer)

        await audit_log_service.log_event(
            db=db,
            user_id=current_user_id,
            action="CUSTOMER_DEACTIVATE",
            entity_type="Customer",
            entity_id=str(customer_id),
            new_data={"status": "Inactive"},
        )
        return customer

    async def check_credit_limit(self, db: AsyncSession, customer_id: uuid.UUID, requested_amount: Decimal) -> bool:
        cust = await self.get_customer(db, customer_id)
        if cust.status != "Active":
            raise ValidationException(f"Customer '{cust.name}' is {cust.status.lower()} and cannot place new orders.")
        # If credit_limit is > 0, ensure requested_amount <= credit_limit
        if cust.credit_limit > Decimal("0.00") and requested_amount > cust.credit_limit:
            raise ValidationException(
                f"Requested order amount ({requested_amount}) exceeds customer credit limit ({cust.credit_limit})."
            )
        return True


customer_service = CustomerService()
