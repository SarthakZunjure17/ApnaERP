"""phase_v061_enhance_stock_ledger_and_balances

Revision ID: f9b0c1d2e3f5
Revises: f1a2b3c4d5e6
Create Date: 2026-09-05 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'f9b0c1d2e3f5'
down_revision: Union[str, None] = 'f1a2b3c4d5e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    ledger_cols = [c['name'] for c in inspector.get_columns('stock_ledgers')] if 'stock_ledgers' in inspector.get_table_names() else []
    
    if 'movement_type' not in ledger_cols:
        op.add_column('stock_ledgers', sa.Column('movement_type', sa.String(length=50), server_default='STOCK_IN', nullable=False, comment='Generic movement type: STOCK_IN, STOCK_OUT, ADJUSTMENT'))
        try:
            op.create_index(op.f('ix_stock_ledgers_movement_type'), 'stock_ledgers', ['movement_type'], unique=False)
        except Exception:
            pass

    if 'quantity_before' not in ledger_cols:
        op.add_column('stock_ledgers', sa.Column('quantity_before', sa.Numeric(precision=18, scale=4), server_default='0.0', nullable=False, comment='Locked stock balance quantity before movement'))

    if 'quantity_after' not in ledger_cols:
        op.add_column('stock_ledgers', sa.Column('quantity_after', sa.Numeric(precision=18, scale=4), server_default='0.0', nullable=False, comment='Locked stock balance quantity after movement'))

    if 'idempotency_key' not in ledger_cols:
        op.add_column('stock_ledgers', sa.Column('idempotency_key', sa.String(length=255), nullable=True, comment='Client-supplied or system idempotency key for movement deduplication'))
        try:
            op.create_index(op.f('ix_stock_ledgers_idempotency_key'), 'stock_ledgers', ['idempotency_key'], unique=True)
        except Exception:
            pass

    if 'reason' not in ledger_cols:
        op.add_column('stock_ledgers', sa.Column('reason', sa.String(length=255), nullable=True, comment='Business reason for movement'))

    if 'notes' not in ledger_cols:
        op.add_column('stock_ledgers', sa.Column('notes', sa.Text(), nullable=True, comment='Optional descriptive notes'))

    if 'metadata_json' not in ledger_cols:
        op.add_column('stock_ledgers', sa.Column('metadata_json', sa.JSON(), nullable=True, comment='Extensible JSON metadata'))

    # If transaction_type_id is not nullable in postgresql, make it nullable
    try:
        op.alter_column('stock_ledgers', 'transaction_type_id', nullable=True)
    except Exception:
        pass


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    ledger_cols = [c['name'] for c in inspector.get_columns('stock_ledgers')] if 'stock_ledgers' in inspector.get_table_names() else []

    if 'idempotency_key' in ledger_cols:
        try:
            op.drop_index(op.f('ix_stock_ledgers_idempotency_key'), table_name='stock_ledgers')
        except Exception:
            pass
        op.drop_column('stock_ledgers', 'idempotency_key')

    if 'movement_type' in ledger_cols:
        try:
            op.drop_index(op.f('ix_stock_ledgers_movement_type'), table_name='stock_ledgers')
        except Exception:
            pass
        op.drop_column('stock_ledgers', 'movement_type')

    if 'quantity_before' in ledger_cols:
        op.drop_column('stock_ledgers', 'quantity_before')

    if 'quantity_after' in ledger_cols:
        op.drop_column('stock_ledgers', 'quantity_after')

    if 'reason' in ledger_cols:
        op.drop_column('stock_ledgers', 'reason')

    if 'notes' in ledger_cols:
        op.drop_column('stock_ledgers', 'notes')

    if 'metadata_json' in ledger_cols:
        op.drop_column('stock_ledgers', 'metadata_json')
