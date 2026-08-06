"""phase v1.0.0 implement Finance Core

Revision ID: b0c1d2e3f4a5
Revises: a9b0c1d2e3f4
Create Date: 2026-08-06 13:25:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'b0c1d2e3f4a5'
down_revision = 'a9b0c1d2e3f4'
branch_labels = None
depends_on = None


def upgrade():
    # 1. account_groups
    op.create_table(
        'account_groups',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('code', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('category', sa.String(length=50), nullable=False),
        sa.Column('parent_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('display_order', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.ForeignKeyConstraint(['parent_id'], ['account_groups.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code')
    )

    # 2. chart_of_accounts
    op.create_table(
        'chart_of_accounts',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('account_code', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=150), nullable=False),
        sa.Column('account_type', sa.String(length=50), nullable=False),
        sa.Column('account_group_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('parent_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('currency_code', sa.String(length=10), server_default='USD', nullable=False),
        sa.Column('is_system', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('is_control', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('opening_balance', sa.Numeric(precision=18, scale=2), server_default='0.00', nullable=False),
        sa.Column('current_balance', sa.Numeric(precision=18, scale=2), server_default='0.00', nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['account_group_id'], ['account_groups.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['parent_id'], ['chart_of_accounts.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('account_code')
    )

    # 3. fiscal_years
    op.create_table(
        'fiscal_years',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('code', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=False),
        sa.Column('status', sa.String(length=20), server_default='Draft', nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code')
    )

    # 4. fiscal_periods
    op.create_table(
        'fiscal_periods',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('fiscal_year_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('period_number', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=False),
        sa.Column('is_locked', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('is_closed', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.ForeignKeyConstraint(['fiscal_year_id'], ['fiscal_years.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('fiscal_year_id', 'period_number', name='uq_fiscal_year_period')
    )

    # 5. currencies
    op.create_table(
        'currencies',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('code', sa.String(length=10), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('symbol', sa.String(length=10), nullable=False),
        sa.Column('is_base', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('decimal_places', sa.Integer(), server_default='2', nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code')
    )

    # 6. exchange_rates
    op.create_table(
        'exchange_rates',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('from_currency_code', sa.String(length=10), nullable=False),
        sa.Column('to_currency_code', sa.String(length=10), nullable=False),
        sa.Column('rate', sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column('effective_date', sa.Date(), nullable=False),
        sa.Column('source', sa.String(length=50), server_default='Manual', nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('from_currency_code', 'to_currency_code', 'effective_date', name='uq_exchange_rate_date')
    )

    # 7. cost_centers
    op.create_table(
        'cost_centers',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('code', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=150), nullable=False),
        sa.Column('parent_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('department_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('business_unit', sa.String(length=100), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.ForeignKeyConstraint(['department_id'], ['departments.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['parent_id'], ['cost_centers.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code')
    )

    # 8. accounting_dimensions
    op.create_table(
        'accounting_dimensions',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('dimension_type', sa.String(length=50), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('is_required', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )

    # 9. journal_types
    op.create_table(
        'journal_types',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('code', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('prefix', sa.String(length=10), server_default='JV', nullable=False),
        sa.Column('requires_approval', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('approval_threshold', sa.Numeric(precision=18, scale=2), server_default='0.00', nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code')
    )

    # 10. journals
    op.create_table(
        'journals',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('journal_number', sa.String(length=50), nullable=False),
        sa.Column('journal_type_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('posting_date', sa.Date(), nullable=False),
        sa.Column('fiscal_period_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('currency_code', sa.String(length=10), server_default='USD', nullable=False),
        sa.Column('exchange_rate', sa.Numeric(precision=18, scale=6), server_default='1.000000', nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('reference_module', sa.String(length=50), nullable=True),
        sa.Column('reference_id', sa.String(length=100), nullable=True),
        sa.Column('status', sa.String(length=30), server_default='Draft', nullable=False),
        sa.Column('total_debit', sa.Numeric(precision=18, scale=2), server_default='0.00', nullable=False),
        sa.Column('total_credit', sa.Numeric(precision=18, scale=2), server_default='0.00', nullable=False),
        sa.Column('posted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('posted_by_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('reversed_journal_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('reversal_reason', sa.Text(), nullable=True),
        sa.Column('approved_by_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['approved_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['fiscal_period_id'], ['fiscal_periods.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['journal_type_id'], ['journal_types.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['posted_by_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['reversed_journal_id'], ['journals.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('journal_number')
    )

    # 11. journal_lines
    op.create_table(
        'journal_lines',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('journal_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('line_number', sa.Integer(), nullable=False),
        sa.Column('account_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('cost_center_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('debit', sa.Numeric(precision=18, scale=2), server_default='0.00', nullable=False),
        sa.Column('credit', sa.Numeric(precision=18, scale=2), server_default='0.00', nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('dimensions', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('reconciled', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.ForeignKeyConstraint(['account_id'], ['chart_of_accounts.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['cost_center_id'], ['cost_centers.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['journal_id'], ['journals.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # 12. tax_categories
    op.create_table(
        'tax_categories',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('code', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('tax_type', sa.String(length=50), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code')
    )

    # 13. tax_rates
    op.create_table(
        'tax_rates',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('tax_category_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('code', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('rate_percentage', sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column('effective_from', sa.Date(), nullable=False),
        sa.Column('effective_to', sa.Date(), nullable=True),
        sa.Column('account_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.ForeignKeyConstraint(['account_id'], ['chart_of_accounts.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['tax_category_id'], ['tax_categories.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code')
    )

    # 14. posting_rules
    op.create_table(
        'posting_rules',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('event_name', sa.String(length=100), nullable=False),
        sa.Column('rule_code', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=150), nullable=False),
        sa.Column('journal_type_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('debit_account_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('credit_account_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tax_category_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('conditions', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(['credit_account_id'], ['chart_of_accounts.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['debit_account_id'], ['chart_of_accounts.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['journal_type_id'], ['journal_types.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['tax_category_id'], ['tax_categories.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('rule_code')
    )

    # 15. accounting_events
    op.create_table(
        'accounting_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), server_default=sa.text('gen_random_uuid()'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('event_type', sa.String(length=100), nullable=False),
        sa.Column('event_name', sa.String(length=100), nullable=False),
        sa.Column('entity_type', sa.String(length=50), nullable=False),
        sa.Column('entity_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('payload', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade():
    op.drop_table('accounting_events')
    op.drop_table('posting_rules')
    op.drop_table('tax_rates')
    op.drop_table('tax_categories')
    op.drop_table('journal_lines')
    op.drop_table('journals')
    op.drop_table('journal_types')
    op.drop_table('accounting_dimensions')
    op.drop_table('cost_centers')
    op.drop_table('exchange_rates')
    op.drop_table('currencies')
    op.drop_table('fiscal_periods')
    op.drop_table('fiscal_years')
    op.drop_table('chart_of_accounts')
    op.drop_table('account_groups')
