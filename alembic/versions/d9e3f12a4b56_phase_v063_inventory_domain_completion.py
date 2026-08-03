"""phase_v063_inventory_domain_completion

Revision ID: d9e3f12a4b56
Revises: 'b8b2e8a866c5'
Create Date: 2026-08-03 13:38:00.000000+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'd9e3f12a4b56'
down_revision: Union[str, None] = 'b8b2e8a866c5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Batches Table
    op.create_table(
        'batches',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('batch_number', sa.String(length=100), nullable=False, comment='Unique identifier for the product batch'),
        sa.Column('product_id', sa.UUID(), nullable=False, comment='Reference to Product master record'),
        sa.Column('manufacturing_date', sa.DateTime(timezone=True), nullable=True, comment='Batch manufacturing date'),
        sa.Column('expiry_date', sa.DateTime(timezone=True), nullable=True, comment='Batch expiration date'),
        sa.Column('supplier_batch_ref', sa.String(length=100), nullable=True, comment='External supplier batch reference number'),
        sa.Column('current_quantity', sa.Numeric(precision=18, scale=4), nullable=False, server_default='0.0', comment='Current physical quantity remaining in this batch'),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='Active', comment='Batch status: Active, Expired, Consumed'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_batches_batch_number'), 'batches', ['batch_number'], unique=True)
    op.create_index(op.f('ix_batches_product_id'), 'batches', ['product_id'], unique=False)
    op.create_index(op.f('ix_batches_expiry_date'), 'batches', ['expiry_date'], unique=False)
    op.create_index(op.f('ix_batches_status'), 'batches', ['status'], unique=False)

    # 2. Serial Numbers Table
    op.create_table(
        'serial_numbers',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('serial_number', sa.String(length=100), nullable=False, comment='Globally unique serial number string'),
        sa.Column('product_id', sa.UUID(), nullable=False, comment='Reference to serialized Product master record'),
        sa.Column('warehouse_id', sa.UUID(), nullable=True, comment='Current warehouse location of the serialized item'),
        sa.Column('storage_location_id', sa.UUID(), nullable=True, comment='Current storage location/rack/bin of the serialized item'),
        sa.Column('batch_id', sa.UUID(), nullable=True, comment='Optional associated batch ID'),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='Available', comment='Status: Available, Reserved, Sold, Returned, Scrapped, Lost'),
        sa.Column('history', postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment='Chronological movement and lifecycle history log'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['batch_id'], ['batches.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['storage_location_id'], ['storage_locations.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['warehouse_id'], ['warehouses.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_serial_numbers_serial_number'), 'serial_numbers', ['serial_number'], unique=True)
    op.create_index(op.f('ix_serial_numbers_product_id'), 'serial_numbers', ['product_id'], unique=False)
    op.create_index(op.f('ix_serial_numbers_warehouse_id'), 'serial_numbers', ['warehouse_id'], unique=False)
    op.create_index(op.f('ix_serial_numbers_storage_location_id'), 'serial_numbers', ['storage_location_id'], unique=False)
    op.create_index(op.f('ix_serial_numbers_batch_id'), 'serial_numbers', ['batch_id'], unique=False)
    op.create_index(op.f('ix_serial_numbers_status'), 'serial_numbers', ['status'], unique=False)

    # 3. Lots Table
    op.create_table(
        'lots',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('lot_number', sa.String(length=100), nullable=False, comment='Unique lot identification code'),
        sa.Column('product_id', sa.UUID(), nullable=False, comment='Reference to Product master record'),
        sa.Column('production_lot', sa.String(length=100), nullable=True, comment='Internal production run/lot code'),
        sa.Column('supplier_lot', sa.String(length=100), nullable=True, comment='Supplier-provided lot code'),
        sa.Column('traceability_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment='Extended lineage, QA test results, or certificate metadata'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_lots_lot_number'), 'lots', ['lot_number'], unique=True)
    op.create_index(op.f('ix_lots_product_id'), 'lots', ['product_id'], unique=False)

    # 4. Stock Reservations Table
    op.create_table(
        'stock_reservations',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('reservation_number', sa.String(length=50), nullable=False, comment='Unique stock reservation tracking number'),
        sa.Column('product_id', sa.UUID(), nullable=False, comment='Reference to Product master record'),
        sa.Column('warehouse_id', sa.UUID(), nullable=False, comment='Target Warehouse for reserved stock'),
        sa.Column('storage_location_id', sa.UUID(), nullable=True, comment='Optional target storage location'),
        sa.Column('batch_id', sa.UUID(), nullable=True, comment='Optional target batch'),
        sa.Column('quantity', sa.Numeric(precision=18, scale=4), nullable=False, comment='Reserved stock quantity'),
        sa.Column('reserved_for_type', sa.String(length=50), nullable=False, comment='Downstream module or demand type: Sales, Manufacturing, Procurement, Internal'),
        sa.Column('reserved_for_id', sa.UUID(), nullable=True, comment='Optional document ID'),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='Active', comment='Reservation status: Active, Fulfilled, Expired, Cancelled'),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True, comment='Optional expiration date/time'),
        sa.Column('remarks', sa.Text(), nullable=True, comment='Reason or context notes'),
        sa.Column('created_by', sa.UUID(), nullable=True, comment='User ID who created the reservation'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['batch_id'], ['batches.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['storage_location_id'], ['storage_locations.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['warehouse_id'], ['warehouses.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_stock_reservations_reservation_number'), 'stock_reservations', ['reservation_number'], unique=True)
    op.create_index(op.f('ix_stock_reservations_product_id'), 'stock_reservations', ['product_id'], unique=False)
    op.create_index(op.f('ix_stock_reservations_warehouse_id'), 'stock_reservations', ['warehouse_id'], unique=False)
    op.create_index(op.f('ix_stock_reservations_storage_location_id'), 'stock_reservations', ['storage_location_id'], unique=False)
    op.create_index(op.f('ix_stock_reservations_batch_id'), 'stock_reservations', ['batch_id'], unique=False)
    op.create_index(op.f('ix_stock_reservations_reserved_for_type'), 'stock_reservations', ['reserved_for_type'], unique=False)
    op.create_index(op.f('ix_stock_reservations_reserved_for_id'), 'stock_reservations', ['reserved_for_id'], unique=False)
    op.create_index(op.f('ix_stock_reservations_status'), 'stock_reservations', ['status'], unique=False)
    op.create_index(op.f('ix_stock_reservations_expires_at'), 'stock_reservations', ['expires_at'], unique=False)

    # 5. Cycle Counts Table
    op.create_table(
        'cycle_counts',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('count_number', sa.String(length=50), nullable=False, comment='Unique count document tracking number'),
        sa.Column('warehouse_id', sa.UUID(), nullable=False, comment='Target warehouse being audited'),
        sa.Column('storage_location_id', sa.UUID(), nullable=True, comment='Optional target sub-location/rack/bin'),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='Draft', comment='Status: Draft, In Progress, Completed, Approved, Cancelled'),
        sa.Column('planned_date', sa.DateTime(timezone=True), nullable=True, comment='Planned date of cycle count'),
        sa.Column('counted_by_id', sa.UUID(), nullable=True, comment='User ID of auditor performing the count'),
        sa.Column('approved_by_id', sa.UUID(), nullable=True, comment='User ID of inventory manager approving the count'),
        sa.Column('notes', sa.Text(), nullable=True, comment='Audit remarks or notes'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['approved_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['counted_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['storage_location_id'], ['storage_locations.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['warehouse_id'], ['warehouses.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_cycle_counts_count_number'), 'cycle_counts', ['count_number'], unique=True)
    op.create_index(op.f('ix_cycle_counts_warehouse_id'), 'cycle_counts', ['warehouse_id'], unique=False)
    op.create_index(op.f('ix_cycle_counts_storage_location_id'), 'cycle_counts', ['storage_location_id'], unique=False)
    op.create_index(op.f('ix_cycle_counts_status'), 'cycle_counts', ['status'], unique=False)

    # 6. Cycle Count Items Table
    op.create_table(
        'cycle_count_items',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('cycle_count_id', sa.UUID(), nullable=False, comment='Parent cycle count document ID'),
        sa.Column('product_id', sa.UUID(), nullable=False, comment='Audited Product master ID'),
        sa.Column('batch_id', sa.UUID(), nullable=True, comment='Optional audited Batch ID'),
        sa.Column('system_qty', sa.Numeric(precision=18, scale=4), nullable=False, comment='Recorded quantity in StockBalance'),
        sa.Column('counted_qty', sa.Numeric(precision=18, scale=4), nullable=False, comment='Actual physically counted quantity'),
        sa.Column('variance_qty', sa.Numeric(precision=18, scale=4), nullable=False, comment='Calculated variance: (counted_qty - system_qty)'),
        sa.Column('remarks', sa.Text(), nullable=True, comment='Item specific discrepancy notes'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['batch_id'], ['batches.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['cycle_count_id'], ['cycle_counts.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_cycle_count_items_cycle_count_id'), 'cycle_count_items', ['cycle_count_id'], unique=False)
    op.create_index(op.f('ix_cycle_count_items_product_id'), 'cycle_count_items', ['product_id'], unique=False)
    op.create_index(op.f('ix_cycle_count_items_batch_id'), 'cycle_count_items', ['batch_id'], unique=False)

    # 7. Inventory Analytics Snapshots Table
    op.create_table(
        'inventory_analytics_snapshots',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('snapshot_date', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('total_inventory_value', sa.Numeric(precision=18, scale=4), nullable=False, server_default='0.0'),
        sa.Column('total_items_count', sa.Numeric(precision=18, scale=4), nullable=False, server_default='0.0'),
        sa.Column('turnover_ratio', sa.Numeric(precision=10, scale=4), nullable=False, server_default='0.0'),
        sa.Column('warehouse_utilization_pct', sa.Numeric(precision=5, scale=2), nullable=False, server_default='0.0'),
        sa.Column('reserved_stock_qty', sa.Numeric(precision=18, scale=4), nullable=False, server_default='0.0'),
        sa.Column('available_stock_qty', sa.Numeric(precision=18, scale=4), nullable=False, server_default='0.0'),
        sa.Column('expiring_stock_qty', sa.Numeric(precision=18, scale=4), nullable=False, server_default='0.0'),
        sa.Column('metrics_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_inventory_analytics_snapshots_snapshot_date'), 'inventory_analytics_snapshots', ['snapshot_date'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_inventory_analytics_snapshots_snapshot_date'), table_name='inventory_analytics_snapshots')
    op.drop_table('inventory_analytics_snapshots')

    op.drop_index(op.f('ix_cycle_count_items_batch_id'), table_name='cycle_count_items')
    op.drop_index(op.f('ix_cycle_count_items_product_id'), table_name='cycle_count_items')
    op.drop_index(op.f('ix_cycle_count_items_cycle_count_id'), table_name='cycle_count_items')
    op.drop_table('cycle_count_items')

    op.drop_index(op.f('ix_cycle_counts_status'), table_name='cycle_counts')
    op.drop_index(op.f('ix_cycle_counts_storage_location_id'), table_name='cycle_counts')
    op.drop_index(op.f('ix_cycle_counts_warehouse_id'), table_name='cycle_counts')
    op.drop_index(op.f('ix_cycle_counts_count_number'), table_name='cycle_counts')
    op.drop_table('cycle_counts')

    op.drop_index(op.f('ix_stock_reservations_expires_at'), table_name='stock_reservations')
    op.drop_index(op.f('ix_stock_reservations_status'), table_name='stock_reservations')
    op.drop_index(op.f('ix_stock_reservations_reserved_for_id'), table_name='stock_reservations')
    op.drop_index(op.f('ix_stock_reservations_reserved_for_type'), table_name='stock_reservations')
    op.drop_index(op.f('ix_stock_reservations_batch_id'), table_name='stock_reservations')
    op.drop_index(op.f('ix_stock_reservations_storage_location_id'), table_name='stock_reservations')
    op.drop_index(op.f('ix_stock_reservations_warehouse_id'), table_name='stock_reservations')
    op.drop_index(op.f('ix_stock_reservations_product_id'), table_name='stock_reservations')
    op.drop_index(op.f('ix_stock_reservations_reservation_number'), table_name='stock_reservations')
    op.drop_table('stock_reservations')

    op.drop_index(op.f('ix_lots_product_id'), table_name='lots')
    op.drop_index(op.f('ix_lots_lot_number'), table_name='lots')
    op.drop_table('lots')

    op.drop_index(op.f('ix_serial_numbers_status'), table_name='serial_numbers')
    op.drop_index(op.f('ix_serial_numbers_batch_id'), table_name='serial_numbers')
    op.drop_index(op.f('ix_serial_numbers_storage_location_id'), table_name='serial_numbers')
    op.drop_index(op.f('ix_serial_numbers_warehouse_id'), table_name='serial_numbers')
    op.drop_index(op.f('ix_serial_numbers_product_id'), table_name='serial_numbers')
    op.drop_index(op.f('ix_serial_numbers_serial_number'), table_name='serial_numbers')
    op.drop_table('serial_numbers')

    op.drop_index(op.f('ix_batches_status'), table_name='batches')
    op.drop_index(op.f('ix_batches_expiry_date'), table_name='batches')
    op.drop_index(op.f('ix_batches_product_id'), table_name='batches')
    op.drop_index(op.f('ix_batches_batch_number'), table_name='batches')
    op.drop_table('batches')
