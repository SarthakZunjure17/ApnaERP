"""Phase v0.7.0 Procurement Domain Completion

Revision ID: e7f8a91b2c3d
Revises: d9e3f12a4b56
Create Date: 2026-08-04 16:20:00.000000

"""
from typing import Sequence, Union
import alembic.op as op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'e7f8a91b2c3d'
down_revision: Union[str, None] = 'd9e3f12a4b56'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Supplier Categories
    op.create_table(
        'supplier_categories',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('code', sa.String(length=50), nullable=False, comment='Unique supplier category code'),
        sa.Column('name', sa.String(length=100), nullable=False, comment='Category name'),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_supplier_categories_code'), 'supplier_categories', ['code'], unique=True)
    op.create_index(op.f('ix_supplier_categories_name'), 'supplier_categories', ['name'], unique=False)

    # 2. Suppliers
    op.create_table(
        'suppliers',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('code', sa.String(length=50), nullable=False, comment='Unique supplier master code'),
        sa.Column('name', sa.String(length=150), nullable=False, comment='Legal or trade name of supplier'),
        sa.Column('category_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('gst_vat_number', sa.String(length=50), nullable=True),
        sa.Column('tax_id', sa.String(length=50), nullable=True),
        sa.Column('payment_terms', sa.String(length=50), nullable=False, server_default='Net 30'),
        sa.Column('credit_limit', sa.Numeric(precision=18, scale=4), nullable=False, server_default='0.0'),
        sa.Column('currency', sa.String(length=10), nullable=False, server_default='USD'),
        sa.Column('bank_name', sa.String(length=100), nullable=True),
        sa.Column('bank_account_number', sa.String(length=50), nullable=True),
        sa.Column('bank_ifsc_swift', sa.String(length=50), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='Active'),
        sa.Column('is_preferred', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('rating', sa.Numeric(precision=3, scale=2), nullable=False, server_default='0.0'),
        sa.Column('ontime_delivery_rate', sa.Numeric(precision=5, scale=2), nullable=False, server_default='100.00'),
        sa.Column('quality_rating', sa.Numeric(precision=5, scale=2), nullable=False, server_default='100.00'),
        sa.Column('total_spend', sa.Numeric(precision=18, scale=4), nullable=False, server_default='0.0'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['category_id'], ['supplier_categories.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_suppliers_code'), 'suppliers', ['code'], unique=True)
    op.create_index(op.f('ix_suppliers_name'), 'suppliers', ['name'], unique=False)
    op.create_index(op.f('ix_suppliers_category_id'), 'suppliers', ['category_id'], unique=False)
    op.create_index(op.f('ix_suppliers_status'), 'suppliers', ['status'], unique=False)
    op.create_index(op.f('ix_suppliers_gst_vat_number'), 'suppliers', ['gst_vat_number'], unique=False)

    # 3. Supplier Contacts
    op.create_table(
        'supplier_contacts',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('supplier_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('contact_name', sa.String(length=100), nullable=False),
        sa.Column('designation', sa.String(length=100), nullable=True),
        sa.Column('email', sa.String(length=150), nullable=False),
        sa.Column('phone', sa.String(length=50), nullable=True),
        sa.Column('is_primary', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['supplier_id'], ['suppliers.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_supplier_contacts_supplier_id'), 'supplier_contacts', ['supplier_id'], unique=False)
    op.create_index(op.f('ix_supplier_contacts_email'), 'supplier_contacts', ['email'], unique=False)

    # 4. Supplier Addresses
    op.create_table(
        'supplier_addresses',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('supplier_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('address_type', sa.String(length=50), nullable=False, server_default='Billing'),
        sa.Column('address_line1', sa.String(length=255), nullable=False),
        sa.Column('address_line2', sa.String(length=255), nullable=True),
        sa.Column('city', sa.String(length=100), nullable=False),
        sa.Column('state', sa.String(length=100), nullable=False),
        sa.Column('country', sa.String(length=100), nullable=False),
        sa.Column('postal_code', sa.String(length=20), nullable=False),
        sa.Column('is_primary', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['supplier_id'], ['suppliers.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_supplier_addresses_supplier_id'), 'supplier_addresses', ['supplier_id'], unique=False)

    # 5. Supplier Documents
    op.create_table(
        'supplier_documents',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('supplier_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('file_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('document_type', sa.String(length=100), nullable=False),
        sa.Column('description', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['file_id'], ['files.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['supplier_id'], ['suppliers.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_supplier_documents_supplier_id'), 'supplier_documents', ['supplier_id'], unique=False)

    # 6. Supplier Ratings
    op.create_table(
        'supplier_ratings',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('supplier_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('reviewer_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('score', sa.Numeric(precision=3, scale=2), nullable=False),
        sa.Column('review_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('comments', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['reviewer_id'], ['users.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['supplier_id'], ['suppliers.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_supplier_ratings_supplier_id'), 'supplier_ratings', ['supplier_id'], unique=False)

    # 7. Purchase Requisitions
    op.create_table(
        'purchase_requisitions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('requisition_number', sa.String(length=50), nullable=False),
        sa.Column('requester_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('department_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('required_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('priority', sa.String(length=20), nullable=False, server_default='Medium'),
        sa.Column('status', sa.String(length=30), nullable=False, server_default='Draft'),
        sa.Column('total_estimated_amount', sa.Numeric(precision=18, scale=4), nullable=False, server_default='0.0'),
        sa.Column('remarks', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['department_id'], ['departments.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['requester_id'], ['users.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_purchase_requisitions_requisition_number'), 'purchase_requisitions', ['requisition_number'], unique=True)
    op.create_index(op.f('ix_purchase_requisitions_requester_id'), 'purchase_requisitions', ['requester_id'], unique=False)
    op.create_index(op.f('ix_purchase_requisitions_status'), 'purchase_requisitions', ['status'], unique=False)

    # 8. Purchase Requisition Items
    op.create_table(
        'purchase_requisition_items',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('requisition_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('product_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('quantity', sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column('fulfilled_quantity', sa.Numeric(precision=18, scale=4), nullable=False, server_default='0.0'),
        sa.Column('estimated_unit_price', sa.Numeric(precision=18, scale=4), nullable=False, server_default='0.0'),
        sa.Column('required_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.String(length=30), nullable=False, server_default='Pending'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['requisition_id'], ['purchase_requisitions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_purchase_requisition_items_requisition_id'), 'purchase_requisition_items', ['requisition_id'], unique=False)

    # 9. RFQs
    op.create_table(
        'rfqs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('rfq_number', sa.String(length=50), nullable=False),
        sa.Column('title', sa.String(length=150), nullable=False),
        sa.Column('requisition_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('submission_deadline', sa.DateTime(timezone=True), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='Draft'),
        sa.Column('terms_and_conditions', sa.Text(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['requisition_id'], ['purchase_requisitions.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_rfqs_rfq_number'), 'rfqs', ['rfq_number'], unique=True)
    op.create_index(op.f('ix_rfqs_status'), 'rfqs', ['status'], unique=False)

    # 10. RFQ Suppliers
    op.create_table(
        'rfq_suppliers',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('rfq_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('supplier_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('invited_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='Invited'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['rfq_id'], ['rfqs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['supplier_id'], ['suppliers.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_rfq_suppliers_rfq_id'), 'rfq_suppliers', ['rfq_id'], unique=False)

    # 11. Supplier Quotations
    op.create_table(
        'supplier_quotations',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('quotation_number', sa.String(length=50), nullable=False),
        sa.Column('rfq_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('supplier_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('quotation_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('validity_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('lead_time_days', sa.Integer(), nullable=False, server_default='7'),
        sa.Column('payment_terms', sa.String(length=50), nullable=True),
        sa.Column('currency', sa.String(length=10), nullable=False, server_default='USD'),
        sa.Column('subtotal', sa.Numeric(precision=18, scale=4), nullable=False, server_default='0.0'),
        sa.Column('tax_amount', sa.Numeric(precision=18, scale=4), nullable=False, server_default='0.0'),
        sa.Column('discount_amount', sa.Numeric(precision=18, scale=4), nullable=False, server_default='0.0'),
        sa.Column('total_amount', sa.Numeric(precision=18, scale=4), nullable=False, server_default='0.0'),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='Draft'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['rfq_id'], ['rfqs.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['supplier_id'], ['suppliers.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_supplier_quotations_quotation_number'), 'supplier_quotations', ['quotation_number'], unique=True)
    op.create_index(op.f('ix_supplier_quotations_supplier_id'), 'supplier_quotations', ['supplier_id'], unique=False)
    op.create_index(op.f('ix_supplier_quotations_status'), 'supplier_quotations', ['status'], unique=False)

    # 12. Supplier Quotation Items
    op.create_table(
        'supplier_quotation_items',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('quotation_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('product_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('quantity', sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column('unit_price', sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column('discount_pct', sa.Numeric(precision=5, scale=2), nullable=False, server_default='0.0'),
        sa.Column('tax_pct', sa.Numeric(precision=5, scale=2), nullable=False, server_default='0.0'),
        sa.Column('total_price', sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column('delivery_days', sa.Integer(), nullable=True),
        sa.Column('remarks', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['quotation_id'], ['supplier_quotations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_supplier_quotation_items_quotation_id'), 'supplier_quotation_items', ['quotation_id'], unique=False)

    # 13. Purchase Orders
    op.create_table(
        'purchase_orders',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('po_number', sa.String(length=50), nullable=False),
        sa.Column('origin_type', sa.String(length=30), nullable=False, server_default='Manual'),
        sa.Column('origin_document_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('supplier_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('order_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('expected_delivery_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('payment_terms', sa.String(length=50), nullable=True),
        sa.Column('currency', sa.String(length=10), nullable=False, server_default='USD'),
        sa.Column('shipping_address', sa.Text(), nullable=True),
        sa.Column('billing_address', sa.Text(), nullable=True),
        sa.Column('subtotal', sa.Numeric(precision=18, scale=4), nullable=False, server_default='0.0'),
        sa.Column('tax_amount', sa.Numeric(precision=18, scale=4), nullable=False, server_default='0.0'),
        sa.Column('discount_amount', sa.Numeric(precision=18, scale=4), nullable=False, server_default='0.0'),
        sa.Column('total_amount', sa.Numeric(precision=18, scale=4), nullable=False, server_default='0.0'),
        sa.Column('status', sa.String(length=30), nullable=False, server_default='Draft'),
        sa.Column('revision_number', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('approved_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['approved_by'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['supplier_id'], ['suppliers.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_purchase_orders_po_number'), 'purchase_orders', ['po_number'], unique=True)
    op.create_index(op.f('ix_purchase_orders_supplier_id'), 'purchase_orders', ['supplier_id'], unique=False)
    op.create_index(op.f('ix_purchase_orders_status'), 'purchase_orders', ['status'], unique=False)

    # 14. Purchase Order Items
    op.create_table(
        'purchase_order_items',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('purchase_order_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('product_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('description', sa.String(length=255), nullable=True),
        sa.Column('quantity', sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column('received_quantity', sa.Numeric(precision=18, scale=4), nullable=False, server_default='0.0'),
        sa.Column('returned_quantity', sa.Numeric(precision=18, scale=4), nullable=False, server_default='0.0'),
        sa.Column('unit_price', sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column('discount_pct', sa.Numeric(precision=5, scale=2), nullable=False, server_default='0.0'),
        sa.Column('tax_pct', sa.Numeric(precision=5, scale=2), nullable=False, server_default='0.0'),
        sa.Column('total_price', sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column('warehouse_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('storage_location_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('expected_delivery_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.String(length=30), nullable=False, server_default='Pending'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['purchase_order_id'], ['purchase_orders.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['storage_location_id'], ['storage_locations.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['warehouse_id'], ['warehouses.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_purchase_order_items_purchase_order_id'), 'purchase_order_items', ['purchase_order_id'], unique=False)

    # 15. Purchase Returns
    op.create_table(
        'purchase_returns',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('return_number', sa.String(length=50), nullable=False),
        sa.Column('purchase_order_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('supplier_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('warehouse_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('return_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('reason_code', sa.String(length=50), nullable=False),
        sa.Column('supplier_return_ref', sa.String(length=100), nullable=True),
        sa.Column('total_return_amount', sa.Numeric(precision=18, scale=4), nullable=False, server_default='0.0'),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='Draft'),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('approved_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('remarks', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['approved_by'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['purchase_order_id'], ['purchase_orders.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['supplier_id'], ['suppliers.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['warehouse_id'], ['warehouses.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_purchase_returns_return_number'), 'purchase_returns', ['return_number'], unique=True)

    # 16. Purchase Return Items
    op.create_table(
        'purchase_return_items',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('purchase_return_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('po_item_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('product_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('return_quantity', sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column('unit_price', sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column('reason', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['po_item_id'], ['purchase_order_items.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['purchase_return_id'], ['purchase_returns.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_purchase_return_items_purchase_return_id'), 'purchase_return_items', ['purchase_return_id'], unique=False)

    # 17. Procurement Report Snapshots
    op.create_table(
        'procurement_report_snapshots',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('snapshot_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('total_purchase_spend', sa.Numeric(precision=18, scale=4), nullable=False, server_default='0.0'),
        sa.Column('open_po_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('open_requisitions_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('active_suppliers_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('delayed_orders_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('metrics_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_procurement_report_snapshots_snapshot_date'), 'procurement_report_snapshots', ['snapshot_date'], unique=False)


def downgrade() -> None:
    op.drop_table('procurement_report_snapshots')
    op.drop_table('purchase_return_items')
    op.drop_table('purchase_returns')
    op.drop_table('purchase_order_items')
    op.drop_table('purchase_orders')
    op.drop_table('supplier_quotation_items')
    op.drop_table('supplier_quotations')
    op.drop_table('rfq_suppliers')
    op.drop_table('rfqs')
    op.drop_table('purchase_requisition_items')
    op.drop_table('purchase_requisitions')
    op.drop_table('supplier_ratings')
    op.drop_table('supplier_documents')
    op.drop_table('supplier_addresses')
    op.drop_table('supplier_contacts')
    op.drop_table('suppliers')
    op.drop_table('supplier_categories')
