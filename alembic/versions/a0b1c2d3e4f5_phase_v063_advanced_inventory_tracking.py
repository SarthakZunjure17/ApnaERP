"""phase_v063_advanced_inventory_tracking

Revision ID: a0b1c2d3e4f5
Revises: ('e1f2a3b4c5d6', 'f9b0c1d2e3f5')
Create Date: 2026-09-05 19:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'a0b1c2d3e4f5'
down_revision: Union[str, Sequence[str], None] = ('e1f2a3b4c5d6', 'f9b0c1d2e3f5')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    try:
        inspector = sa.inspect(conn)
        tables = inspector.get_table_names()
    except Exception:
        inspector = None
        tables = []

    # 1. Products - tracking_type
    if 'products' in tables:
        prod_cols = [c['name'] for c in inspector.get_columns('products')]
        if 'tracking_type' not in prod_cols:
            op.add_column('products', sa.Column('tracking_type', sa.String(length=20), server_default='NONE', nullable=False, comment='Inventory tracking mode: NONE, BATCH, SERIAL'))

    # 2. Stock Ledgers - batch_id, serial_numbers
    if 'stock_ledgers' in tables:
        sl_cols = [c['name'] for c in inspector.get_columns('stock_ledgers')]
        if 'batch_id' not in sl_cols:
            op.add_column('stock_ledgers', sa.Column('batch_id', sa.UUID(), nullable=True, comment='Optional reference to batch/lot'))
            try:
                op.create_foreign_key('fk_stock_ledgers_batch_id', 'stock_ledgers', 'batches', ['batch_id'], ['id'], ondelete='SET NULL')
                op.create_index(op.f('ix_stock_ledgers_batch_id'), 'stock_ledgers', ['batch_id'], unique=False)
            except Exception:
                pass
        if 'serial_numbers' not in sl_cols:
            op.add_column('stock_ledgers', sa.Column('serial_numbers', postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment='Optional serial numbers list'))

    # 3. Stock Reservations - released_at, consumed_at, notes, reference_type, reference_id
    if 'stock_reservations' in tables:
        res_cols = [c['name'] for c in inspector.get_columns('stock_reservations')]
        if 'released_at' not in res_cols:
            op.add_column('stock_reservations', sa.Column('released_at', sa.DateTime(timezone=True), nullable=True, comment='Timestamp when reservation was released'))
        if 'consumed_at' not in res_cols:
            op.add_column('stock_reservations', sa.Column('consumed_at', sa.DateTime(timezone=True), nullable=True, comment='Timestamp when reservation was consumed'))
        if 'notes' not in res_cols:
            op.add_column('stock_reservations', sa.Column('notes', sa.Text(), nullable=True, comment='Context notes'))
        if 'reference_type' not in res_cols:
            op.add_column('stock_reservations', sa.Column('reference_type', sa.String(length=50), nullable=True, comment='Reference document type'))
        if 'reference_id' not in res_cols:
            op.add_column('stock_reservations', sa.Column('reference_id', sa.UUID(), nullable=True, comment='Reference document ID'))

    # 4. Goods Receipt Items - batch_id, batch_number, expiry_date, manufacturing_date, serial_numbers
    if 'goods_receipt_items' in tables:
        gri_cols = [c['name'] for c in inspector.get_columns('goods_receipt_items')]
        if 'batch_id' not in gri_cols:
            op.add_column('goods_receipt_items', sa.Column('batch_id', sa.UUID(), nullable=True, comment='Associated product batch ID'))
            try:
                op.create_foreign_key('fk_goods_receipt_items_batch_id', 'goods_receipt_items', 'batches', ['batch_id'], ['id'], ondelete='SET NULL')
            except Exception:
                pass
        if 'batch_number' not in gri_cols:
            op.add_column('goods_receipt_items', sa.Column('batch_number', sa.String(length=100), nullable=True, comment='Batch/lot number identifier'))
        if 'expiry_date' not in gri_cols:
            op.add_column('goods_receipt_items', sa.Column('expiry_date', sa.DateTime(timezone=True), nullable=True, comment='Batch expiry date'))
        if 'manufacturing_date' not in gri_cols:
            op.add_column('goods_receipt_items', sa.Column('manufacturing_date', sa.DateTime(timezone=True), nullable=True, comment='Batch manufacturing date'))
        if 'serial_numbers' not in gri_cols:
            op.add_column('goods_receipt_items', sa.Column('serial_numbers', postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment='Serial numbers list'))

    # 5. Goods Issue Items - batch_id, serial_numbers, reservation_id
    if 'goods_issue_items' in tables:
        gii_cols = [c['name'] for c in inspector.get_columns('goods_issue_items')]
        if 'batch_id' not in gii_cols:
            op.add_column('goods_issue_items', sa.Column('batch_id', sa.UUID(), nullable=True, comment='Associated product batch ID'))
            try:
                op.create_foreign_key('fk_goods_issue_items_batch_id', 'goods_issue_items', 'batches', ['batch_id'], ['id'], ondelete='SET NULL')
            except Exception:
                pass
        if 'serial_numbers' not in gii_cols:
            op.add_column('goods_issue_items', sa.Column('serial_numbers', postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment='Serial numbers list'))
        if 'reservation_id' not in gii_cols:
            op.add_column('goods_issue_items', sa.Column('reservation_id', sa.UUID(), nullable=True, comment='Optional linked stock reservation ID'))
            try:
                op.create_foreign_key('fk_goods_issue_items_reservation_id', 'goods_issue_items', 'stock_reservations', ['reservation_id'], ['id'], ondelete='SET NULL')
            except Exception:
                pass

    # 6. Stock Transfer Items - batch_id, serial_numbers
    if 'stock_transfer_items' in tables:
        sti_cols = [c['name'] for c in inspector.get_columns('stock_transfer_items')]
        if 'batch_id' not in sti_cols:
            op.add_column('stock_transfer_items', sa.Column('batch_id', sa.UUID(), nullable=True, comment='Associated product batch ID'))
            try:
                op.create_foreign_key('fk_stock_transfer_items_batch_id', 'stock_transfer_items', 'batches', ['batch_id'], ['id'], ondelete='SET NULL')
            except Exception:
                pass
        if 'serial_numbers' not in sti_cols:
            op.add_column('stock_transfer_items', sa.Column('serial_numbers', postgresql.JSONB(astext_type=sa.Text()), nullable=True, comment='Serial numbers list'))


def downgrade() -> None:
    conn = op.get_bind()
    try:
        inspector = sa.inspect(conn)
        tables = inspector.get_table_names()
    except Exception:
        inspector = None
        tables = []

    if 'stock_transfer_items' in tables:
        sti_cols = [c['name'] for c in inspector.get_columns('stock_transfer_items')]
        if 'serial_numbers' in sti_cols:
            op.drop_column('stock_transfer_items', 'serial_numbers')
        if 'batch_id' in sti_cols:
            try:
                op.drop_constraint('fk_stock_transfer_items_batch_id', 'stock_transfer_items', type_='foreignkey')
            except Exception:
                pass
            op.drop_column('stock_transfer_items', 'batch_id')

    if 'goods_issue_items' in tables:
        gii_cols = [c['name'] for c in inspector.get_columns('goods_issue_items')]
        if 'reservation_id' in gii_cols:
            try:
                op.drop_constraint('fk_goods_issue_items_reservation_id', 'goods_issue_items', type_='foreignkey')
            except Exception:
                pass
            op.drop_column('goods_issue_items', 'reservation_id')
        if 'serial_numbers' in gii_cols:
            op.drop_column('goods_issue_items', 'serial_numbers')
        if 'batch_id' in gii_cols:
            try:
                op.drop_constraint('fk_goods_issue_items_batch_id', 'goods_issue_items', type_='foreignkey')
            except Exception:
                pass
            op.drop_column('goods_issue_items', 'batch_id')

    if 'goods_receipt_items' in tables:
        gri_cols = [c['name'] for c in inspector.get_columns('goods_receipt_items')]
        if 'serial_numbers' in gri_cols:
            op.drop_column('goods_receipt_items', 'serial_numbers')
        if 'manufacturing_date' in gri_cols:
            op.drop_column('goods_receipt_items', 'manufacturing_date')
        if 'expiry_date' in gri_cols:
            op.drop_column('goods_receipt_items', 'expiry_date')
        if 'batch_number' in gri_cols:
            op.drop_column('goods_receipt_items', 'batch_number')
        if 'batch_id' in gri_cols:
            try:
                op.drop_constraint('fk_goods_receipt_items_batch_id', 'goods_receipt_items', type_='foreignkey')
            except Exception:
                pass
            op.drop_column('goods_receipt_items', 'batch_id')

    if 'stock_reservations' in tables:
        res_cols = [c['name'] for c in inspector.get_columns('stock_reservations')]
        if 'reference_id' in res_cols:
            op.drop_column('stock_reservations', 'reference_id')
        if 'reference_type' in res_cols:
            op.drop_column('stock_reservations', 'reference_type')
        if 'notes' in res_cols:
            op.drop_column('stock_reservations', 'notes')
        if 'consumed_at' in res_cols:
            op.drop_column('stock_reservations', 'consumed_at')
        if 'released_at' in res_cols:
            op.drop_column('stock_reservations', 'released_at')

    if 'stock_ledgers' in tables:
        sl_cols = [c['name'] for c in inspector.get_columns('stock_ledgers')]
        if 'serial_numbers' in sl_cols:
            op.drop_column('stock_ledgers', 'serial_numbers')
        if 'batch_id' in sl_cols:
            try:
                op.drop_index(op.f('ix_stock_ledgers_batch_id'), table_name='stock_ledgers')
                op.drop_constraint('fk_stock_ledgers_batch_id', 'stock_ledgers', type_='foreignkey')
            except Exception:
                pass
            op.drop_column('stock_ledgers', 'batch_id')

    if 'products' in tables:
        prod_cols = [c['name'] for c in inspector.get_columns('products')]
        if 'tracking_type' in prod_cols:
            op.drop_column('products', 'tracking_type')
