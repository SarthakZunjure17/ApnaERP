"""phase_v130_enterprise_integrations

Revision ID: e1f2a3b4c5d6
Revises: d1e2f3a4b5c6
Create Date: 2026-08-07 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'e1f2a3b4c5d6'
down_revision: Union[str, None] = 'd1e2f3a4b5c6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. API Keys
    op.create_table(
        'api_keys',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('key_hash', sa.String(length=255), nullable=False),
        sa.Column('prefix', sa.String(length=16), nullable=False),
        sa.Column('name', sa.String(length=150), nullable=False),
        sa.Column('owner_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('scopes', postgresql.JSONB(as_text=True), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_revoked', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('usage_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('key_hash')
    )
    op.create_index(op.f('ix_api_keys_key_hash'), 'api_keys', ['key_hash'], unique=True)
    op.create_index(op.f('ix_api_keys_prefix'), 'api_keys', ['prefix'], unique=False)
    op.create_index(op.f('ix_api_keys_owner_id'), 'api_keys', ['owner_id'], unique=False)
    op.create_index(op.f('ix_api_keys_is_revoked'), 'api_keys', ['is_revoked'], unique=False)

    # 2. Webhook Subscriptions
    op.create_table(
        'webhook_subscriptions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('name', sa.String(length=150), nullable=False),
        sa.Column('target_url', sa.Text(), nullable=False),
        sa.Column('secret_token', sa.String(length=255), nullable=False),
        sa.Column('event_types', postgresql.JSONB(as_text=True), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('headers_json', postgresql.JSONB(as_text=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_webhook_subscriptions_is_active'), 'webhook_subscriptions', ['is_active'], unique=False)

    # 3. Webhook Deliveries
    op.create_table(
        'webhook_deliveries',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('subscription_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('event_type', sa.String(length=100), nullable=False),
        sa.Column('payload_json', postgresql.JSONB(as_text=True), nullable=False),
        sa.Column('response_status', sa.Integer(), nullable=True),
        sa.Column('response_body', sa.Text(), nullable=True),
        sa.Column('attempt_count', sa.Integer(), server_default='1', nullable=False),
        sa.Column('next_retry_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.String(length=30), server_default='Pending', nullable=False),
        sa.ForeignKeyConstraint(['subscription_id'], ['webhook_subscriptions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_webhook_deliveries_subscription_id'), 'webhook_deliveries', ['subscription_id'], unique=False)
    op.create_index(op.f('ix_webhook_deliveries_event_type'), 'webhook_deliveries', ['event_type'], unique=False)
    op.create_index(op.f('ix_webhook_deliveries_status'), 'webhook_deliveries', ['status'], unique=False)

    # 4. Provider Configurations
    op.create_table(
        'provider_configurations',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('is_deleted', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('provider_type', sa.String(length=50), nullable=False),
        sa.Column('provider_name', sa.String(length=50), nullable=False),
        sa.Column('settings_json', postgresql.JSONB(as_text=True), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('is_default', sa.Boolean(), server_default='false', nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_provider_configurations_provider_type'), 'provider_configurations', ['provider_type'], unique=False)
    op.create_index(op.f('ix_provider_configurations_provider_name'), 'provider_configurations', ['provider_name'], unique=False)
    op.create_index(op.f('ix_provider_configurations_is_active'), 'provider_configurations', ['is_active'], unique=False)

    # 5. Backup Metadata
    op.create_table(
        'backup_metadata',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('backup_name', sa.String(length=200), nullable=False),
        sa.Column('storage_path', sa.Text(), nullable=False),
        sa.Column('file_size_bytes', sa.Integer(), server_default='0', nullable=False),
        sa.Column('backup_type', sa.String(length=30), server_default='FullDatabase', nullable=False),
        sa.Column('status', sa.String(length=30), server_default='Completed', nullable=False),
        sa.Column('checksum', sa.String(length=128), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('backup_name')
    )
    op.create_index(op.f('ix_backup_metadata_backup_name'), 'backup_metadata', ['backup_name'], unique=True)
    op.create_index(op.f('ix_backup_metadata_status'), 'backup_metadata', ['status'], unique=False)

    # 6. System Configurations
    op.create_table(
        'system_configurations',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('config_key', sa.String(length=100), nullable=False),
        sa.Column('config_value', sa.Text(), nullable=False),
        sa.Column('value_type', sa.String(length=30), server_default='String', nullable=False),
        sa.Column('category', sa.String(length=50), server_default='General', nullable=False),
        sa.Column('is_encrypted', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('is_public', sa.Boolean(), server_default='false', nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('config_key')
    )
    op.create_index(op.f('ix_system_configurations_config_key'), 'system_configurations', ['config_key'], unique=True)
    op.create_index(op.f('ix_system_configurations_category'), 'system_configurations', ['category'], unique=False)


def downgrade() -> None:
    op.drop_table('system_configurations')
    op.drop_table('backup_metadata')
    op.drop_table('provider_configurations')
    op.drop_table('webhook_deliveries')
    op.drop_table('webhook_subscriptions')
    op.drop_table('api_keys')
