"""phase_v140_finance_company_and_enhancements

Revision ID: f1a2b3c4d5f6
Revises: e1f2a3b4c5d6
Create Date: 2026-09-08 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'f1a2b3c4d5f6'
down_revision: Union[str, None] = 'e1f2a3b4c5d6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create companies table
    op.create_table(
        'companies',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('code', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=150), nullable=False),
        sa.Column('legal_name', sa.String(length=200), nullable=True),
        sa.Column('tax_id', sa.String(length=50), nullable=True),
        sa.Column('base_currency_code', sa.String(length=10), server_default='USD', nullable=False),
        sa.Column('fiscal_year_start_month', sa.Integer(), server_default='1', nullable=False),
        sa.Column('retained_earnings_account_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('default_bank_account_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('default_cash_account_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('default_receivable_account_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('default_payable_account_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('address_line1', sa.String(length=255), nullable=True),
        sa.Column('address_line2', sa.String(length=255), nullable=True),
        sa.Column('city', sa.String(length=100), nullable=True),
        sa.Column('state', sa.String(length=100), nullable=True),
        sa.Column('postal_code', sa.String(length=20), nullable=True),
        sa.Column('country', sa.String(length=100), nullable=True),
        sa.Column('phone', sa.String(length=50), nullable=True),
        sa.Column('email', sa.String(length=100), nullable=True),
        sa.Column('website', sa.String(length=150), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.ForeignKeyConstraint(['retained_earnings_account_id'], ['chart_of_accounts.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['default_bank_account_id'], ['chart_of_accounts.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['default_cash_account_id'], ['chart_of_accounts.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['default_receivable_account_id'], ['chart_of_accounts.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['default_payable_account_id'], ['chart_of_accounts.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code')
    )
    op.create_index(op.f('ix_companies_code'), 'companies', ['code'], unique=True)
    op.create_index(op.f('ix_companies_name'), 'companies', ['name'], unique=False)
    op.create_index(op.f('ix_companies_is_active'), 'companies', ['is_active'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_companies_is_active'), table_name='companies')
    op.drop_index(op.f('ix_companies_name'), table_name='companies')
    op.drop_index(op.f('ix_companies_code'), table_name='companies')
    op.drop_table('companies')
