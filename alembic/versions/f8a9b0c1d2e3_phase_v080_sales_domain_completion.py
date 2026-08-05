"""Phase v0.8.0 Sales Domain Completion

Revision ID: f8a9b0c1d2e3
Revises: e7f8a91b2c3d
Create Date: 2026-08-05 18:00:00.000000

"""
from typing import Sequence, Union
import alembic.op as op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'f8a9b0c1d2e3'
down_revision: Union[str, None] = 'e7f8a91b2c3d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Customer Categories
    op.create_table(
        'customer_categories',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('code', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_customer_categories_code'), 'customer_categories', ['code'], unique=True)
    op.create_index(op.f('ix_customer_categories_name'), 'customer_categories', ['name'], unique=False)

    # 2. Customers
    op.create_table(
        'customers',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('customer_code', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('category_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('phone', sa.String(length=50), nullable=True),
        sa.Column('website', sa.String(length=255), nullable=True),
        sa.Column('tax_id', sa.String(length=100), nullable=True),
        sa.Column('credit_limit', sa.Numeric(precision=18, scale=2), server_default='0.00', nullable=False),
        sa.Column('credit_days', sa.Numeric(precision=5, scale=0), server_default='30', nullable=False),
        sa.Column('payment_terms', sa.String(length=100), server_default='Net 30', nullable=False),
        sa.Column('status', sa.String(length=20), server_default='Active', nullable=False),
        sa.Column('is_preferred', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('rating', sa.Numeric(precision=3, scale=2), server_default='5.00', nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['category_id'], ['customer_categories.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_customers_customer_code'), 'customers', ['customer_code'], unique=True)
    op.create_index(op.f('ix_customers_name'), 'customers', ['name'], unique=False)
    op.create_index(op.f('ix_customers_email'), 'customers', ['email'], unique=False)
    op.create_index(op.f('ix_customers_status'), 'customers', ['status'], unique=False)
    op.create_index(op.f('ix_customers_tax_id'), 'customers', ['tax_id'], unique=False)

    # 3. Customer Contacts
    op.create_table(
        'customer_contacts',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('customer_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('contact_person', sa.String(length=150), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('phone', sa.String(length=50), nullable=True),
        sa.Column('designation', sa.String(length=100), nullable=True),
        sa.Column('is_primary', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['customer_id'], ['customers.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_customer_contacts_customer_id'), 'customer_contacts', ['customer_id'], unique=False)

    # 4. Customer Addresses
    op.create_table(
        'customer_addresses',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('customer_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('address_type', sa.String(length=20), server_default='Billing', nullable=False),
        sa.Column('address_line1', sa.String(length=255), nullable=False),
        sa.Column('address_line2', sa.String(length=255), nullable=True),
        sa.Column('city', sa.String(length=100), nullable=False),
        sa.Column('state', sa.String(length=100), nullable=False),
        sa.Column('postal_code', sa.String(length=20), nullable=False),
        sa.Column('country', sa.String(length=100), server_default='India', nullable=False),
        sa.Column('is_default', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['customer_id'], ['customers.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_customer_addresses_customer_id'), 'customer_addresses', ['customer_id'], unique=False)

    # 5. Customer Documents
    op.create_table(
        'customer_documents',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('customer_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('file_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('document_type', sa.String(length=100), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['customer_id'], ['customers.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['file_id'], ['files.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_customer_documents_customer_id'), 'customer_documents', ['customer_id'], unique=False)

    # 6. Price Lists
    op.create_table(
        'price_lists',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('code', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=150), nullable=False),
        sa.Column('currency', sa.String(length=10), server_default='INR', nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('valid_from', sa.DateTime(timezone=True), nullable=True),
        sa.Column('valid_to', sa.DateTime(timezone=True), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_price_lists_code'), 'price_lists', ['code'], unique=True)
    op.create_index(op.f('ix_price_lists_name'), 'price_lists', ['name'], unique=False)

    # 7. Pricing Rules
    op.create_table(
        'pricing_rules',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('price_list_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('product_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('min_quantity', sa.Numeric(precision=18, scale=4), server_default='1.0000', nullable=False),
        sa.Column('unit_price', sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column('valid_from', sa.DateTime(timezone=True), nullable=True),
        sa.Column('valid_to', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['price_list_id'], ['price_lists.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_pricing_rules_price_list_id'), 'pricing_rules', ['price_list_id'], unique=False)
    op.create_index(op.f('ix_pricing_rules_product_id'), 'pricing_rules', ['product_id'], unique=False)

    # 8. Discount Rules
    op.create_table(
        'discount_rules',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('code', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=150), nullable=False),
        sa.Column('discount_type', sa.String(length=20), server_default='Line', nullable=False),
        sa.Column('calculation_type', sa.String(length=20), server_default='Percentage', nullable=False),
        sa.Column('discount_value', sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column('min_order_value', sa.Numeric(precision=18, scale=4), server_default='0.0000', nullable=False),
        sa.Column('min_quantity', sa.Numeric(precision=18, scale=4), server_default='0.0000', nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('valid_from', sa.DateTime(timezone=True), nullable=True),
        sa.Column('valid_to', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_discount_rules_code'), 'discount_rules', ['code'], unique=True)
    op.create_index(op.f('ix_discount_rules_name'), 'discount_rules', ['name'], unique=False)

    # 9. Sales Quotations
    op.create_table(
        'sales_quotations',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('quotation_number', sa.String(length=100), nullable=False),
        sa.Column('customer_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('quotation_date', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('validity_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('currency', sa.String(length=10), server_default='INR', nullable=False),
        sa.Column('status', sa.String(length=20), server_default='Draft', nullable=False),
        sa.Column('revision_number', sa.Integer(), server_default='1', nullable=False),
        sa.Column('subtotal_amount', sa.Numeric(precision=18, scale=2), server_default='0.00', nullable=False),
        sa.Column('discount_amount', sa.Numeric(precision=18, scale=2), server_default='0.00', nullable=False),
        sa.Column('tax_amount', sa.Numeric(precision=18, scale=2), server_default='0.00', nullable=False),
        sa.Column('total_amount', sa.Numeric(precision=18, scale=2), server_default='0.00', nullable=False),
        sa.Column('remarks', sa.Text(), nullable=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('approved_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['customer_id'], ['customers.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['approved_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_sales_quotations_quotation_number'), 'sales_quotations', ['quotation_number'], unique=True)
    op.create_index(op.f('ix_sales_quotations_customer_id'), 'sales_quotations', ['customer_id'], unique=False)
    op.create_index(op.f('ix_sales_quotations_status'), 'sales_quotations', ['status'], unique=False)

    # 10. Sales Quotation Items
    op.create_table(
        'sales_quotation_items',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('quotation_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('product_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('description', sa.String(length=255), nullable=True),
        sa.Column('quantity', sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column('unit_price', sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column('discount_type', sa.String(length=20), server_default='Percentage', nullable=False),
        sa.Column('discount_value', sa.Numeric(precision=18, scale=4), server_default='0.0000', nullable=False),
        sa.Column('discount_amount', sa.Numeric(precision=18, scale=2), server_default='0.00', nullable=False),
        sa.Column('tax_rate', sa.Numeric(precision=5, scale=2), server_default='0.00', nullable=False),
        sa.Column('tax_amount', sa.Numeric(precision=18, scale=2), server_default='0.00', nullable=False),
        sa.Column('line_total', sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column('warehouse_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.ForeignKeyConstraint(['quotation_id'], ['sales_quotations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['warehouse_id'], ['warehouses.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_sales_quotation_items_quotation_id'), 'sales_quotation_items', ['quotation_id'], unique=False)
    op.create_index(op.f('ix_sales_quotation_items_product_id'), 'sales_quotation_items', ['product_id'], unique=False)

    # 11. Sales Orders
    op.create_table(
        'sales_orders',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('order_number', sa.String(length=100), nullable=False),
        sa.Column('customer_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('quotation_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('order_date', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('status', sa.String(length=20), server_default='Draft', nullable=False),
        sa.Column('delivery_status', sa.String(length=20), server_default='Pending', nullable=False),
        sa.Column('revision_number', sa.Integer(), server_default='1', nullable=False),
        sa.Column('currency', sa.String(length=10), server_default='INR', nullable=False),
        sa.Column('subtotal_amount', sa.Numeric(precision=18, scale=2), server_default='0.00', nullable=False),
        sa.Column('discount_amount', sa.Numeric(precision=18, scale=2), server_default='0.00', nullable=False),
        sa.Column('tax_amount', sa.Numeric(precision=18, scale=2), server_default='0.00', nullable=False),
        sa.Column('total_amount', sa.Numeric(precision=18, scale=2), server_default='0.00', nullable=False),
        sa.Column('payment_terms', sa.String(length=100), server_default='Net 30', nullable=False),
        sa.Column('shipping_address_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('billing_address_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('remarks', sa.Text(), nullable=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('approved_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['customer_id'], ['customers.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['quotation_id'], ['sales_quotations.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['shipping_address_id'], ['customer_addresses.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['billing_address_id'], ['customer_addresses.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['approved_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_sales_orders_order_number'), 'sales_orders', ['order_number'], unique=True)
    op.create_index(op.f('ix_sales_orders_customer_id'), 'sales_orders', ['customer_id'], unique=False)
    op.create_index(op.f('ix_sales_orders_status'), 'sales_orders', ['status'], unique=False)
    op.create_index(op.f('ix_sales_orders_delivery_status'), 'sales_orders', ['delivery_status'], unique=False)

    # 12. Sales Order Items
    op.create_table(
        'sales_order_items',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('sales_order_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('product_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('description', sa.String(length=255), nullable=True),
        sa.Column('quantity', sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column('delivered_quantity', sa.Numeric(precision=18, scale=4), server_default='0.0000', nullable=False),
        sa.Column('unit_price', sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column('discount_type', sa.String(length=20), server_default='Percentage', nullable=False),
        sa.Column('discount_value', sa.Numeric(precision=18, scale=4), server_default='0.0000', nullable=False),
        sa.Column('discount_amount', sa.Numeric(precision=18, scale=2), server_default='0.00', nullable=False),
        sa.Column('tax_rate', sa.Numeric(precision=5, scale=2), server_default='0.00', nullable=False),
        sa.Column('tax_amount', sa.Numeric(precision=18, scale=2), server_default='0.00', nullable=False),
        sa.Column('line_total', sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column('warehouse_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('delivery_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.String(length=20), server_default='Pending', nullable=False),
        sa.ForeignKeyConstraint(['sales_order_id'], ['sales_orders.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['warehouse_id'], ['warehouses.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_sales_order_items_sales_order_id'), 'sales_order_items', ['sales_order_id'], unique=False)
    op.create_index(op.f('ix_sales_order_items_product_id'), 'sales_order_items', ['product_id'], unique=False)

    # 13. Delivery Orders
    op.create_table(
        'delivery_orders',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('delivery_number', sa.String(length=100), nullable=False),
        sa.Column('sales_order_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('warehouse_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('goods_issue_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('dispatch_date', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('carrier', sa.String(length=100), nullable=True),
        sa.Column('tracking_number', sa.String(length=100), nullable=True),
        sa.Column('status', sa.String(length=20), server_default='Draft', nullable=False),
        sa.Column('delivery_notes', sa.Text(), nullable=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['sales_order_id'], ['sales_orders.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['warehouse_id'], ['warehouses.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['goods_issue_id'], ['goods_issues.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_delivery_orders_delivery_number'), 'delivery_orders', ['delivery_number'], unique=True)
    op.create_index(op.f('ix_delivery_orders_sales_order_id'), 'delivery_orders', ['sales_order_id'], unique=False)
    op.create_index(op.f('ix_delivery_orders_tracking_number'), 'delivery_orders', ['tracking_number'], unique=False)
    op.create_index(op.f('ix_delivery_orders_status'), 'delivery_orders', ['status'], unique=False)

    # 14. Delivery Order Items
    op.create_table(
        'delivery_order_items',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('delivery_order_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('sales_order_item_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('product_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('quantity', sa.Numeric(precision=18, scale=4), nullable=False),
        sa.ForeignKeyConstraint(['delivery_order_id'], ['delivery_orders.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['sales_order_item_id'], ['sales_order_items.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_delivery_order_items_delivery_order_id'), 'delivery_order_items', ['delivery_order_id'], unique=False)

    # 15. Sales Returns
    op.create_table(
        'sales_returns',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('return_number', sa.String(length=100), nullable=False),
        sa.Column('sales_order_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('delivery_order_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('customer_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('warehouse_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('goods_receipt_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('return_date', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('status', sa.String(length=20), server_default='Draft', nullable=False),
        sa.Column('reason_code', sa.String(length=50), nullable=False),
        sa.Column('total_refund_amount', sa.Numeric(precision=18, scale=2), server_default='0.00', nullable=False),
        sa.Column('remarks', sa.Text(), nullable=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('approved_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['sales_order_id'], ['sales_orders.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['delivery_order_id'], ['delivery_orders.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['customer_id'], ['customers.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['warehouse_id'], ['warehouses.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['goods_receipt_id'], ['goods_receipts.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['approved_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_sales_returns_return_number'), 'sales_returns', ['return_number'], unique=True)
    op.create_index(op.f('ix_sales_returns_sales_order_id'), 'sales_returns', ['sales_order_id'], unique=False)
    op.create_index(op.f('ix_sales_returns_customer_id'), 'sales_returns', ['customer_id'], unique=False)
    op.create_index(op.f('ix_sales_returns_status'), 'sales_returns', ['status'], unique=False)

    # 16. Sales Return Items
    op.create_table(
        'sales_return_items',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('sales_return_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('sales_order_item_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('product_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('quantity', sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column('unit_price', sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column('refund_amount', sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column('reason', sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(['sales_return_id'], ['sales_returns.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['sales_order_item_id'], ['sales_order_items.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_sales_return_items_sales_return_id'), 'sales_return_items', ['sales_return_id'], unique=False)

    # 17. Sales Report Snapshots
    op.create_table(
        'sales_report_snapshots',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('snapshot_date', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('period_type', sa.String(length=20), server_default='Daily', nullable=False),
        sa.Column('total_revenue', sa.Numeric(precision=18, scale=2), server_default='0.00', nullable=False),
        sa.Column('total_orders', sa.Numeric(precision=10, scale=0), server_default='0', nullable=False),
        sa.Column('avg_order_value', sa.Numeric(precision=18, scale=2), server_default='0.00', nullable=False),
        sa.Column('metrics_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_sales_report_snapshots_snapshot_date'), 'sales_report_snapshots', ['snapshot_date'], unique=False)
    op.create_index(op.f('ix_sales_report_snapshots_period_type'), 'sales_report_snapshots', ['period_type'], unique=False)


def downgrade() -> None:
    op.drop_table('sales_report_snapshots')
    op.drop_table('sales_return_items')
    op.drop_table('sales_returns')
    op.drop_table('delivery_order_items')
    op.drop_table('delivery_orders')
    op.drop_table('sales_order_items')
    op.drop_table('sales_orders')
    op.drop_table('sales_quotation_items')
    op.drop_table('sales_quotations')
    op.drop_table('discount_rules')
    op.drop_table('pricing_rules')
    op.drop_table('price_lists')
    op.drop_table('customer_documents')
    op.drop_table('customer_addresses')
    op.drop_table('customer_contacts')
    op.drop_table('customers')
    op.drop_table('customer_categories')
