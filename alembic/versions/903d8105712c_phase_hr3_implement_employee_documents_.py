"""phase_hr3_implement_employee_documents_table

Revision ID: 903d8105712c
Revises: 'd04dad64b43e'
Create Date: 2026-07-26 15:44:14.763966+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '903d8105712c'
down_revision: Union[str, None] = 'd04dad64b43e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('employee_documents',
    sa.Column('employee_id', sa.UUID(), nullable=False),
    sa.Column('file_id', sa.UUID(), nullable=False),
    sa.Column('document_type', sa.String(length=50), nullable=False),
    sa.Column('document_number', sa.String(length=100), nullable=True),
    sa.Column('issue_date', sa.Date(), nullable=True),
    sa.Column('expiry_date', sa.Date(), nullable=True),
    sa.Column('verification_status', sa.String(length=50), nullable=False),
    sa.Column('verified_by', sa.UUID(), nullable=True),
    sa.Column('verified_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('notes', sa.Text(), nullable=True),
    sa.Column('is_mandatory', sa.Boolean(), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('id', sa.UUID(), nullable=False, comment='Primary Key UUID'),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='Record creation timestamp (UTC)'),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False, comment='Record last update timestamp (UTC)'),
    sa.Column('is_deleted', sa.Boolean(), server_default='false', nullable=False, comment='Soft deletion flag'),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True, comment='Timestamp when record was soft-deleted (UTC)'),
    sa.ForeignKeyConstraint(['employee_id'], ['employees.id'], name=op.f('fk_employee_documents_employee_id_employees'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['file_id'], ['files.id'], name=op.f('fk_employee_documents_file_id_files'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['verified_by'], ['users.id'], name=op.f('fk_employee_documents_verified_by_users'), ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_employee_documents'))
    )
    op.create_index(op.f('ix_employee_documents_document_type'), 'employee_documents', ['document_type'], unique=False)
    op.create_index(op.f('ix_employee_documents_employee_id'), 'employee_documents', ['employee_id'], unique=False)
    op.create_index(op.f('ix_employee_documents_file_id'), 'employee_documents', ['file_id'], unique=False)
    op.create_index(op.f('ix_employee_documents_id'), 'employee_documents', ['id'], unique=False)
    op.create_index(op.f('ix_employee_documents_is_deleted'), 'employee_documents', ['is_deleted'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_employee_documents_is_deleted'), table_name='employee_documents')
    op.drop_index(op.f('ix_employee_documents_id'), table_name='employee_documents')
    op.drop_index(op.f('ix_employee_documents_file_id'), table_name='employee_documents')
    op.drop_index(op.f('ix_employee_documents_employee_id'), table_name='employee_documents')
    op.drop_index(op.f('ix_employee_documents_document_type'), table_name='employee_documents')
    op.drop_table('employee_documents')
