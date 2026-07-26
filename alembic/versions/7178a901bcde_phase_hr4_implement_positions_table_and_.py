"""phase_hr4_implement_positions_table_and_extend_employees

Revision ID: 7178a901bcde
Revises: '903d8105712c'
Create Date: 2026-07-26 21:44:00.000000+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '7178a901bcde'
down_revision: Union[str, None] = '903d8105712c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create positions table
    op.create_table(
        'positions',
        sa.Column('code', sa.String(length=50), nullable=False, comment='Unique position code (e.g. POS-ENG-001)'),
        sa.Column('title', sa.String(length=150), nullable=False, comment='Job title (e.g. Senior Backend Engineer)'),
        sa.Column('description', sa.Text(), nullable=True, comment='Detailed position role description'),
        sa.Column('department_id', sa.UUID(), nullable=False, comment='FK referencing owning Department'),
        sa.Column('parent_position_id', sa.UUID(), nullable=True, comment='Parent reporting position for hierarchy tree'),
        sa.Column('employment_category', sa.String(length=50), nullable=False, server_default='Permanent', comment='Employment category'),
        sa.Column('grade', sa.String(length=50), nullable=True, comment='Job grade'),
        sa.Column('level', sa.String(length=50), nullable=True, comment='Job level'),
        sa.Column('maximum_headcount', sa.Integer(), nullable=False, server_default='1', comment='Maximum allowed headcount capacity'),
        sa.Column('current_headcount', sa.Integer(), nullable=False, server_default='0', comment='Current count of active assigned employees'),
        sa.Column('is_managerial', sa.Boolean(), nullable=False, server_default='false', comment='True if position holds manager authority'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true', comment='Position active status flag'),
        sa.Column('id', sa.UUID(), nullable=False, comment='Primary Key UUID'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='Record creation timestamp (UTC)'),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='Record last update timestamp (UTC)'),
        sa.Column('is_deleted', sa.Boolean(), server_default='false', nullable=False, comment='Soft deletion flag'),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True, comment='Timestamp when record was soft-deleted (UTC)'),
        sa.ForeignKeyConstraint(['department_id'], ['departments.id'], name=op.f('fk_positions_department_id_departments'), ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['parent_position_id'], ['positions.id'], name=op.f('fk_positions_parent_position_id_positions'), ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_positions'))
    )
    op.create_index(op.f('ix_positions_code'), 'positions', ['code'], unique=True)
    op.create_index(op.f('ix_positions_department_id'), 'positions', ['department_id'], unique=False)
    op.create_index(op.f('ix_positions_id'), 'positions', ['id'], unique=False)
    op.create_index(op.f('ix_positions_is_deleted'), 'positions', ['is_deleted'], unique=False)
    op.create_index(op.f('ix_positions_parent_position_id'), 'positions', ['parent_position_id'], unique=False)
    op.create_index(op.f('ix_positions_title'), 'positions', ['title'], unique=False)

    # 2. Add position_id, employment_start_date, employment_end_date to employees table
    op.add_column('employees', sa.Column('position_id', sa.UUID(), nullable=True, comment='FK referencing occupied Position'))
    op.add_column('employees', sa.Column('employment_start_date', sa.Date(), nullable=True))
    op.add_column('employees', sa.Column('employment_end_date', sa.Date(), nullable=True))
    op.create_index(op.f('ix_employees_position_id'), 'employees', ['position_id'], unique=False)
    op.create_foreign_key(
        op.f('fk_employees_position_id_positions'),
        'employees',
        'positions',
        ['position_id'],
        ['id'],
        ondelete='SET NULL'
    )


def downgrade() -> None:
    op.drop_constraint(op.f('fk_employees_position_id_positions'), 'employees', type_='foreignkey')
    op.drop_index(op.f('ix_employees_position_id'), table_name='employees')
    op.drop_column('employees', 'employment_end_date')
    op.drop_column('employees', 'employment_start_date')
    op.drop_column('employees', 'position_id')

    op.drop_index(op.f('ix_positions_title'), table_name='positions')
    op.drop_index(op.f('ix_positions_parent_position_id'), table_name='positions')
    op.drop_index(op.f('ix_positions_is_deleted'), table_name='positions')
    op.drop_index(op.f('ix_positions_id'), table_name='positions')
    op.drop_index(op.f('ix_positions_department_id'), table_name='positions')
    op.drop_index(op.f('ix_positions_code'), table_name='positions')
    op.drop_table('positions')
