"""phase_v060_inventory_foundation_enhancements

Revision ID: f1a2b3c4d5e6
Revises: e1f2a3b4c5d6
Create Date: 2026-08-08 10:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'f1a2b3c4d5e6'
down_revision: Union[str, None] = 'e1f2a3b4c5d6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Enhance unit_of_measures table
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    uom_cols = [c['name'] for c in inspector.get_columns('unit_of_measures')] if 'unit_of_measures' in inspector.get_table_names() else []
    
    if 'code' not in uom_cols:
        op.add_column('unit_of_measures', sa.Column('code', sa.String(length=50), nullable=True, comment='Unique UOM code identifier'))
        try:
            op.create_index(op.f('ix_unit_of_measures_code'), 'unit_of_measures', ['code'], unique=True)
        except Exception:
            pass

    # 2. Enhance warehouses table
    wh_cols = [c['name'] for c in inspector.get_columns('warehouses')] if 'warehouses' in inspector.get_table_names() else []
    
    if 'description' not in wh_cols:
        op.add_column('warehouses', sa.Column('description', sa.String(length=255), nullable=True, comment='Detailed warehouse description'))
    if 'warehouse_type' not in wh_cols:
        op.add_column('warehouses', sa.Column('warehouse_type', sa.String(length=50), server_default='MAIN', nullable=False, comment='Warehouse type: MAIN, DISTRIBUTION, RETAIL, VIRTUAL, TRANSIT'))
        try:
            op.create_index(op.f('ix_warehouses_warehouse_type'), 'warehouses', ['warehouse_type'], unique=False)
        except Exception:
            pass
    if 'address_line_1' not in wh_cols:
        op.add_column('warehouses', sa.Column('address_line_1', sa.String(length=255), nullable=True, comment='Primary street address line'))
    if 'address_line_2' not in wh_cols:
        op.add_column('warehouses', sa.Column('address_line_2', sa.String(length=255), nullable=True, comment='Secondary address line'))
    if 'city' not in wh_cols:
        op.add_column('warehouses', sa.Column('city', sa.String(length=100), nullable=True, comment='City'))
    if 'state' not in wh_cols:
        op.add_column('warehouses', sa.Column('state', sa.String(length=100), nullable=True, comment='State or Province'))
    if 'country' not in wh_cols:
        op.add_column('warehouses', sa.Column('country', sa.String(length=100), nullable=True, comment='Country'))
    if 'postal_code' not in wh_cols:
        op.add_column('warehouses', sa.Column('postal_code', sa.String(length=20), nullable=True, comment='Postal or ZIP code'))
    if 'timezone' not in wh_cols:
        op.add_column('warehouses', sa.Column('timezone', sa.String(length=50), server_default='UTC', nullable=False, comment='Facility operating timezone'))
    if 'manager_employee_id' not in wh_cols:
        op.add_column('warehouses', sa.Column('manager_employee_id', sa.UUID(), nullable=True, comment='Assigned warehouse manager employee ID'))
        try:
            op.create_foreign_key(
                op.f('fk_warehouses_manager_employee_id_employees'),
                'warehouses', 'employees',
                ['manager_employee_id'], ['id'],
                ondelete='SET NULL'
            )
            op.create_index(op.f('ix_warehouses_manager_employee_id'), 'warehouses', ['manager_employee_id'], unique=False)
        except Exception:
            pass

    # 3. Enhance storage_locations table
    loc_cols = [c['name'] for c in inspector.get_columns('storage_locations')] if 'storage_locations' in inspector.get_table_names() else []
    if 'description' not in loc_cols:
        op.add_column('storage_locations', sa.Column('description', sa.String(length=255), nullable=True, comment='Storage location description or notes'))

    # 4. Enhance products table
    prod_cols = [c['name'] for c in inspector.get_columns('products')] if 'products' in inspector.get_table_names() else []
    if 'model_number' not in prod_cols:
        op.add_column('products', sa.Column('model_number', sa.String(length=100), nullable=True, comment='Model number or manufacturer part identifier'))
        try:
            op.create_index(op.f('ix_products_model_number'), 'products', ['model_number'], unique=False)
        except Exception:
            pass
    if 'is_active' not in prod_cols:
        op.add_column('products', sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False, comment='Active product flag'))
        try:
            op.create_index(op.f('ix_products_is_active'), 'products', ['is_active'], unique=False)
        except Exception:
            pass
    if 'is_stockable' not in prod_cols:
        op.add_column('products', sa.Column('is_stockable', sa.Boolean(), server_default=sa.text('true'), nullable=False, comment='Flag indicating if item is physically tracked in inventory'))
        try:
            op.create_index(op.f('ix_products_is_stockable'), 'products', ['is_stockable'], unique=False)
        except Exception:
            pass
    if 'is_sellable' not in prod_cols:
        op.add_column('products', sa.Column('is_sellable', sa.Boolean(), server_default=sa.text('true'), nullable=False, comment='Flag indicating if item can be ordered on sales orders'))
    if 'is_purchasable' not in prod_cols:
        op.add_column('products', sa.Column('is_purchasable', sa.Boolean(), server_default=sa.text('true'), nullable=False, comment='Flag indicating if item can be ordered on purchase orders'))
    if 'reorder_level' not in prod_cols:
        op.add_column('products', sa.Column('reorder_level', sa.Numeric(precision=18, scale=4), nullable=True, comment='Global minimum stock reorder point threshold'))
    if 'reorder_quantity' not in prod_cols:
        op.add_column('products', sa.Column('reorder_quantity', sa.Numeric(precision=18, scale=4), nullable=True, comment='Standard suggested reorder batch quantity'))
    if 'minimum_stock' not in prod_cols:
        op.add_column('products', sa.Column('minimum_stock', sa.Numeric(precision=18, scale=4), nullable=True, comment='Absolute minimum safety buffer threshold'))
    if 'maximum_stock' not in prod_cols:
        op.add_column('products', sa.Column('maximum_stock', sa.Numeric(precision=18, scale=4), nullable=True, comment='Maximum storage capacity ceiling threshold'))
    if 'lead_time_days' not in prod_cols:
        op.add_column('products', sa.Column('lead_time_days', sa.Integer(), server_default='0', nullable=False, comment='Standard procurement lead time in days'))
    if 'default_unit_price' not in prod_cols:
        op.add_column('products', sa.Column('default_unit_price', sa.Numeric(precision=18, scale=4), nullable=True, comment='Default base sales price per unit'))
    if 'metadata_json' not in prod_cols:
        op.add_column('products', sa.Column('metadata_json', sa.JSON(), nullable=True, comment='Flexible JSON metadata attributes'))

    # 5. Create product_warehouses table
    existing_tables = inspector.get_table_names()
    if 'product_warehouses' not in existing_tables:
        op.create_table(
            'product_warehouses',
            sa.Column('id', sa.UUID(), nullable=False, comment='Primary Key UUID'),
            sa.Column('product_id', sa.UUID(), nullable=False, comment='Foreign key referencing target Product master record'),
            sa.Column('warehouse_id', sa.UUID(), nullable=False, comment='Foreign key referencing target Warehouse facility'),
            sa.Column('preferred_location_id', sa.UUID(), nullable=True, comment='Optional default/preferred StorageLocation'),
            sa.Column('reorder_level', sa.Numeric(precision=18, scale=4), nullable=True, comment='Warehouse-specific stock reorder point threshold'),
            sa.Column('reorder_quantity', sa.Numeric(precision=18, scale=4), nullable=True, comment='Warehouse-specific suggested replenishment order quantity'),
            sa.Column('minimum_stock', sa.Numeric(precision=18, scale=4), nullable=True, comment='Warehouse-specific minimum safety stock floor threshold'),
            sa.Column('maximum_stock', sa.Numeric(precision=18, scale=4), nullable=True, comment='Warehouse-specific maximum storage capacity ceiling threshold'),
            sa.Column('safety_stock', sa.Numeric(precision=18, scale=4), nullable=True, comment='Warehouse-specific designated safety buffer quantity'),
            sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False, comment='Active status flag'),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.ForeignKeyConstraint(['preferred_location_id'], ['storage_locations.id'], name=op.f('fk_product_warehouses_preferred_location_id_storage_locations'), ondelete='SET NULL'),
            sa.ForeignKeyConstraint(['product_id'], ['products.id'], name=op.f('fk_product_warehouses_product_id_products'), ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['warehouse_id'], ['warehouses.id'], name=op.f('fk_product_warehouses_warehouse_id_warehouses'), ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id', name=op.f('pk_product_warehouses')),
            sa.UniqueConstraint('product_id', 'warehouse_id', name='uq_product_warehouse')
        )
        op.create_index(op.f('ix_product_warehouses_id'), 'product_warehouses', ['id'], unique=False)
        op.create_index(op.f('ix_product_warehouses_is_active'), 'product_warehouses', ['is_active'], unique=False)
        op.create_index(op.f('ix_product_warehouses_preferred_location_id'), 'product_warehouses', ['preferred_location_id'], unique=False)
        op.create_index(op.f('ix_product_warehouses_product_id'), 'product_warehouses', ['product_id'], unique=False)
        op.create_index(op.f('ix_product_warehouses_warehouse_id'), 'product_warehouses', ['warehouse_id'], unique=False)

    # 6. Create inventory_policies table
    if 'inventory_policies' not in existing_tables:
        op.create_table(
            'inventory_policies',
            sa.Column('id', sa.UUID(), nullable=False, comment='Primary Key UUID'),
            sa.Column('warehouse_id', sa.UUID(), nullable=True, comment='Target Warehouse facility, or NULL for global policy'),
            sa.Column('valuation_method', sa.String(length=50), server_default='FIFO', nullable=False, comment='Valuation method: FIFO, LIFO, WEIGHTED_AVERAGE, STANDARD'),
            sa.Column('costing_method', sa.String(length=50), server_default='STANDARD', nullable=False, comment='Costing strategy: STANDARD, ACTUAL, MOVING_AVERAGE'),
            sa.Column('negative_stock_allowed', sa.Boolean(), server_default=sa.text('false'), nullable=False, comment='Policy permitting negative balances'),
            sa.Column('default_reorder_strategy', sa.String(length=50), server_default='MIN_MAX', nullable=False, comment='Replenishment strategy'),
            sa.Column('default_reservation_behavior', sa.String(length=50), server_default='STRICT', nullable=False, comment='Stock reservation behavior'),
            sa.Column('low_stock_alert_enabled', sa.Boolean(), server_default=sa.text('true'), nullable=False, comment='Flag triggering low stock alerts'),
            sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False, comment='Active status flag'),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
            sa.ForeignKeyConstraint(['warehouse_id'], ['warehouses.id'], name=op.f('fk_inventory_policies_warehouse_id_warehouses'), ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id', name=op.f('pk_inventory_policies')),
            sa.UniqueConstraint('warehouse_id', name='uq_inventory_policy_warehouse')
        )
        op.create_index(op.f('ix_inventory_policies_id'), 'inventory_policies', ['id'], unique=False)
        op.create_index(op.f('ix_inventory_policies_is_active'), 'inventory_policies', ['is_active'], unique=False)
        op.create_index(op.f('ix_inventory_policies_warehouse_id'), 'inventory_policies', ['warehouse_id'], unique=False)


def downgrade() -> None:
    op.drop_table('inventory_policies')
    op.drop_table('product_warehouses')
    # Column drops can be executed if supported by dialect
